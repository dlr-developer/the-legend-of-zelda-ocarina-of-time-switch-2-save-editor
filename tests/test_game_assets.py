"""Unit tests for oot_game_assets module."""
import os
import struct
import sys
import tempfile
import unittest

# Ensure repo root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import tests._isolate  # MUST be first to isolate user data directories

import app_paths
import oot_game_assets
from oot_game_assets import (
    MissingDependencyError,
    chapter_text,
    decode_bntx,
    deswizzle,
    div_round_up,
    find_romfs_roots,
    has_assets,
    icon_path,
    import_from_folder,
    item_text,
    parse_msbt,
    reload,
    song_text,
)


def _swizzle_synthetic(linear_data: bytes, width_blocks: int, height_blocks: int, bpb: int, block_height: int) -> bytes:
    """Inverse of deswizzle used for synthetic round-trip tests."""
    gob_w, gob_h = 64, 8
    row_bytes = width_blocks * bpb
    gobs_x = div_round_up(row_bytes, gob_w)
    block_rows = block_height * gob_h
    total_block_y = div_round_up(height_blocks, block_rows) * block_rows
    swizzled_size = (total_block_y // gob_h) * gobs_x * 512
    swizzled = bytearray(swizzled_size)
    for y in range(height_blocks):
        for xb in range(0, row_bytes, 16):
            gob_addr = ((y // block_rows) * gobs_x * block_height
                        + (xb // gob_w) * block_height
                        + (y % block_rows) // gob_h) * 512
            x = xb % gob_w
            yy = y % gob_h
            addr = (gob_addr + ((x >> 4) & 1) * 64 + ((x >> 5) & 1) * 256
                    + (yy & 1) * 16 + ((yy >> 1) & 1) * 32 + ((yy >> 2) & 1) * 128)
            dst = y * row_bytes + xb
            n = min(16, row_bytes - xb)
            swizzled[addr:addr + n] = linear_data[dst:dst + n]
    return bytes(swizzled)


def _build_linear_blocks(width_blocks: int, height_blocks: int, bpb: int = 16) -> bytes:
    """Create a buffer of sequentially numbered 16-byte blocks."""
    total_blocks = width_blocks * height_blocks
    buf = bytearray(total_blocks * bpb)
    for i in range(total_blocks):
        struct.pack_into("<QQ", buf, i * 16, i, i ^ 0x0123456789ABCDEF)
    return bytes(buf)


def _build_synthetic_msbt(labels_and_texts: list, encoding_utf8: bool = True) -> bytes:
    """Build a valid minimal MsgStdBn binary containing LBL1 and TXT2 sections."""
    e = "<"
    enc_byte = 0 if encoding_utf8 else 1

    # Build LBL1
    lbl_body = bytearray(struct.pack(e + "I", 1))  # 1 bucket
    bucket_entries = bytearray()
    for idx, (label_name, _) in enumerate(labels_and_texts):
        lbl_bytes = label_name.encode("utf-8")
        bucket_entries += struct.pack(e + "B", len(lbl_bytes)) + lbl_bytes + struct.pack(e + "I", idx)
    lbl_body += struct.pack(e + "II", len(labels_and_texts), 12)
    lbl_body += bucket_entries

    lbl_pad = (16 - (len(lbl_body) % 16)) % 16
    lbl1_sec = b"LBL1" + struct.pack(e + "I", len(lbl_body)) + (b"\x00" * 8) + lbl_body + (b"\x00" * lbl_pad)

    # Build TXT2
    n_strings = len(labels_and_texts)
    txt_header = bytearray(struct.pack(e + "I", n_strings))
    txt_strings = bytearray()
    offsets = []
    base_offset = 4 + 4 * n_strings

    for _, raw_bytes in labels_and_texts:
        offsets.append(base_offset + len(txt_strings))
        txt_strings += raw_bytes

    for off in offsets:
        txt_header += struct.pack(e + "I", off)
    txt_body = txt_header + txt_strings
    txt_pad = (16 - (len(txt_body) % 16)) % 16
    txt2_sec = b"TXT2" + struct.pack(e + "I", len(txt_body)) + (b"\x00" * 8) + txt_body + (b"\x00" * txt_pad)

    # Header
    total_file_size = 0x20 + len(lbl1_sec) + len(txt2_sec)
    hdr = bytearray(0x20)
    hdr[:8] = b"MsgStdBn"
    hdr[8:10] = b"\xff\xfe"  # Little-endian BOM
    hdr[0x0C] = enc_byte
    struct.pack_into(e + "H", hdr, 0x0E, 2)  # 2 sections
    struct.pack_into(e + "I", hdr, 0x10, total_file_size)

    return bytes(hdr + lbl1_sec + txt2_sec)


def _build_fake_bntx(width: int, height: int, fmt: int = 0x1A00, tex_size: int = 512) -> bytes:
    """Build minimal synthetic BNTX buffer with BRTI and BRTD chunks."""
    brti = bytearray(0x60)
    brti[:4] = b"BRTI"
    struct.pack_into("<I", brti, 0x1C, fmt)
    struct.pack_into("<II", brti, 0x24, width, height)
    struct.pack_into("<I", brti, 0x34, 0)  # layout = 0 -> block_height = 1
    struct.pack_into("<I", brti, 0x50, tex_size)

    brtd = bytearray(0x10 + tex_size)
    brtd[:4] = b"BRTD"
    return bytes(b"BNTX" + (b"\x00" * 12) + brti + brtd)


def _build_synthetic_sarc(files: dict) -> bytes:
    """Build a minimal valid SARC archive containing the given files."""
    e = "<"
    file_items = list(files.items())
    n = len(file_items)

    sfnt_names = bytearray()
    nodes = []
    current_data_off = 0
    file_data_blobs = bytearray()

    for name, content in file_items:
        name_bytes = name.encode("utf-8") + b"\x00"
        name_pad = (4 - (len(name_bytes) % 4)) % 4
        name_offset = len(sfnt_names)
        sfnt_names += name_bytes + (b"\x00" * name_pad)

        start = current_data_off
        end = start + len(content)
        file_data_blobs += content
        align_pad = (4 - (len(content) % 4)) % 4
        file_data_blobs += b"\x00" * align_pad
        current_data_off = len(file_data_blobs)

        attr = 0x01000000 | (name_offset // 4)
        nodes.append((attr, start, end))

    sfat_sec = bytearray(b"SFAT")
    sfat_sec += struct.pack(e + "HHI", 0x0C, n, 0x00000065)
    for attr, s, en in nodes:
        sfat_sec += struct.pack(e + "IIII", 0, attr, s, en)

    sfnt_pad = (4 - (len(sfnt_names) % 4)) % 4
    sfnt_body = sfnt_names + (b"\x00" * sfnt_pad)
    sfnt_sec = bytearray(b"SFNT")
    sfnt_sec += struct.pack(e + "HH", 8, 0) + sfnt_body

    hdr_len = 0x14
    data_off = hdr_len + len(sfat_sec) + len(sfnt_sec)
    data_pad = (4 - (data_off % 4)) % 4
    data_off += data_pad

    total_size = data_off + len(file_data_blobs)
    hdr = bytearray(hdr_len)
    hdr[:4] = b"SARC"
    struct.pack_into(e + "HH", hdr, 4, hdr_len, 0xFEFF)
    struct.pack_into(e + "I", hdr, 8, total_size)
    struct.pack_into(e + "I", hdr, 12, data_off)
    struct.pack_into(e + "H", hdr, 16, 0x0100)

    return bytes(hdr + sfat_sec + sfnt_sec + (b"\x00" * data_pad) + file_data_blobs)


class TestGameAssets(unittest.TestCase):
    """Test suite for game asset decompression, parsing, discovery, and lookup API."""

    def setUp(self):
        reload()

    def tearDown(self):
        reload()

    def test_deswizzle_roundtrip(self):
        """Deswizzle returns original linear buffer for sizes 86x86 and 172x172 (block height 16)."""
        # Test 86x86 blocks
        lin_86 = _build_linear_blocks(86, 86, bpb=16)
        swiz_86 = _swizzle_synthetic(lin_86, 86, 86, bpb=16, block_height=16)
        deswiz_86 = deswizzle(swiz_86, 86, 86, bpb=16, block_height=16)
        self.assertEqual(deswiz_86, lin_86)

        # Test 172x172 blocks
        lin_172 = _build_linear_blocks(172, 172, bpb=16)
        swiz_172 = _swizzle_synthetic(lin_172, 172, 172, bpb=16, block_height=16)
        deswiz_172 = deswizzle(swiz_172, 172, 172, bpb=16, block_height=16)
        self.assertEqual(deswiz_172, lin_172)

    def test_msbt_parsing_and_tag_stripping(self):
        """Hand-built minimal UTF-8 MSBT with 0x0E control tag parses with tags stripped."""
        # Text with 0x0E control tag: "Boomerang " + tag + " Special\nLine 2"
        # Tag format: 0x0E + group(H)=1 + type(H)=2 + size(H)=2 + params(2 bytes)=0xABCD
        tag_0e = b"\x0e" + struct.pack("<HHH", 1, 2, 2) + b"\xab\xcd"
        raw_text = b"Boomerang " + tag_0e + b"Special\nLine 2\x00"

        msbt_data = _build_synthetic_msbt([("Item_Boomerang_Name", raw_text)], encoding_utf8=True)
        parsed = parse_msbt(msbt_data, strip_tags=True)

        self.assertIn("Item_Boomerang_Name", parsed)
        self.assertEqual(parsed["Item_Boomerang_Name"], "Boomerang Special\nLine 2")

    def test_find_romfs_roots_priority(self):
        """find_romfs_roots on tree with romfs/ and updates/131072/romfs/ returns update first."""
        with tempfile.TemporaryDirectory() as td:
            romfs_base = os.path.join(td, "romfs")
            romfs_upd = os.path.join(td, "updates", "131072", "romfs")
            os.makedirs(romfs_base, exist_ok=True)
            os.makedirs(romfs_upd, exist_ok=True)

            roots = find_romfs_roots(td)
            self.assertEqual(len(roots), 2)
            self.assertEqual(roots[0], romfs_upd)
            self.assertEqual(roots[1], romfs_base)

    def test_lookup_api_empty_and_populated(self):
        """icon_path and item_text return None when empty; return values when populated."""
        with tempfile.TemporaryDirectory() as td:
            # Point USER_DATA_DIR to temporary directory
            orig_user_data = app_paths.USER_DATA_DIR
            try:
                app_paths.USER_DATA_DIR = td
                reload()

                # When nothing is imported
                self.assertFalse(has_assets())
                self.assertIsNone(icon_path("Item_Test"))
                self.assertEqual(item_text("Item_Test"), (None, None))
                self.assertIsNone(chapter_text("01"))
                self.assertEqual(song_text(0), (None, None))

                # Populate fake assets
                adir = oot_game_assets.assets_dir()
                icons_dir = os.path.join(adir, "icons")
                text_dir = os.path.join(adir, "text")
                os.makedirs(icons_dir, exist_ok=True)
                os.makedirs(text_dir, exist_ok=True)

                # Write fake manifest
                manifest_path = os.path.join(adir, "manifest.json")
                with open(manifest_path, "w", encoding="utf-8") as f:
                    f.write('{"source": ["test"], "imported": "2026-11-12T00:00:00", "counts": {"icons": 1}, "lang": "USen", "version": 1}')

                # Write fake icon
                icon_file = os.path.join(icons_dir, "Item_Test.png")
                with open(icon_file, "wb") as f:
                    f.write(b"\x89PNG\r\n\x1a\nfake_png_data")

                # Write fake items.json
                items_file = os.path.join(text_dir, "items.json")
                with open(items_file, "w", encoding="utf-8") as f:
                    f.write('{"Item_Test": {"name": "Test Item", "caption": "A test caption."}}')

                # Write fake threads.json
                threads_file = os.path.join(text_dir, "threads.json")
                with open(threads_file, "w", encoding="utf-8") as f:
                    f.write('{"01": {"title": "Chapter 1", "sections": {"Desc": "Intro"}}}')

                # Write fake songs.json
                songs_file = os.path.join(text_dir, "songs.json")
                with open(songs_file, "w", encoding="utf-8") as f:
                    f.write('{"titles": ["Zelda\'s Lullaby"], "captions": ["Plays a soothing melody."]}')

                reload()

                self.assertTrue(has_assets())
                self.assertEqual(icon_path("Item_Test"), icon_file)
                self.assertIsNone(icon_path("NonExistent"))
                self.assertEqual(item_text("Item_Test"), ("Test Item", "A test caption."))
                self.assertEqual(item_text("NonExistent"), (None, None))
                self.assertEqual(chapter_text("01"), {"title": "Chapter 1", "sections": {"Desc": "Intro"}})
                self.assertIsNone(chapter_text("99"))
                self.assertEqual(song_text(0), ("Zelda's Lullaby", "Plays a soothing melody."))
                self.assertEqual(song_text(5), (None, None))

            finally:
                app_paths.USER_DATA_DIR = orig_user_data
                reload()

    def test_missing_dependency_error(self):
        """import_from_folder raises clear MissingDependencyError when dependencies missing."""
        orig_check = oot_game_assets.check_dependencies

        def mock_check():
            raise MissingDependencyError(
                "Missing required package(s) for game asset import: zstandard. "
                "Install them with: pip install zstandard"
            )

        try:
            oot_game_assets.check_dependencies = mock_check
            self.assertTrue(issubclass(MissingDependencyError, ImportError))
            with self.assertRaises(MissingDependencyError) as ctx:
                import_from_folder("non_existent_folder")
            self.assertIn("Missing required package(s)", str(ctx.exception))
            self.assertIn("zstandard", str(ctx.exception))
        finally:
            oot_game_assets.check_dependencies = orig_check

    def test_decode_bntx_size_limits(self):
        """decode_bntx on a fake BRTI with width 100000 raises ValueError quickly; width 0 raises."""
        try:
            import texture2ddecoder  # noqa: F401
            from PIL import Image  # noqa: F401
        except ImportError:
            self.skipTest("texture2ddecoder and Pillow required for decode_bntx test")

        # Fake BRTI with width 100000 raises ValueError quickly without allocation
        bntx_huge = _build_fake_bntx(width=100000, height=64)
        with self.assertRaises(ValueError) as ctx:
            decode_bntx(bntx_huge)
        self.assertIn("Invalid texture dimensions", str(ctx.exception))

        # Width 0 raises ValueError
        bntx_zero_w = _build_fake_bntx(width=0, height=64)
        with self.assertRaises(ValueError) as ctx:
            decode_bntx(bntx_zero_w)
        self.assertIn("Invalid texture dimensions", str(ctx.exception))

        # Height 0 raises ValueError
        bntx_zero_h = _build_fake_bntx(width=64, height=0)
        with self.assertRaises(ValueError) as ctx:
            decode_bntx(bntx_zero_h)
        self.assertIn("Invalid texture dimensions", str(ctx.exception))

        # Linear byte count exceeding texture data size raises ValueError
        bntx_too_short = _build_fake_bntx(width=256, height=256, tex_size=16)
        with self.assertRaises(ValueError) as ctx:
            decode_bntx(bntx_too_short)
        self.assertIn("exceeds texture data", str(ctx.exception))

    def test_parse_msbt_truncated_lbl1(self):
        """parse_msbt on a truncated LBL1 raises ValueError (not struct.error)."""
        valid_msbt = _build_synthetic_msbt([("TestLabel", b"TestValue\x00")])
        lbl_idx = valid_msbt.find(b"LBL1")
        self.assertGreaterEqual(lbl_idx, 0)

        # Truncate after LBL1 magic
        with self.assertRaises(ValueError):
            parse_msbt(valid_msbt[:lbl_idx + 4])

        # Truncate within LBL1 section header
        with self.assertRaises(ValueError):
            parse_msbt(valid_msbt[:lbl_idx + 12])

        # Truncate within LBL1 bucket table / entries
        with self.assertRaises(ValueError):
            parse_msbt(valid_msbt[:lbl_idx + 24])

    def test_import_from_folder_error_isolation_and_skipped_counts(self):
        """import_from_folder on fake romfs with corrupt files reports skipped counts and writes manifest."""
        try:
            import zstandard
            import texture2ddecoder  # noqa: F401
            from PIL import Image  # noqa: F401
        except ImportError:
            self.skipTest("zstandard, texture2ddecoder, and Pillow required for import test")

        with tempfile.TemporaryDirectory() as td:
            orig_user_data = app_paths.USER_DATA_DIR
            try:
                app_paths.USER_DATA_DIR = td
                reload()

                romfs = os.path.join(td, "romfs")
                icon_dir = os.path.join(romfs, "UI", "Tex", "Icon")
                mals_dir = os.path.join(romfs, "Mals")
                os.makedirs(icon_dir, exist_ok=True)
                os.makedirs(mals_dir, exist_ok=True)

                cctx = zstandard.ZstdCompressor()

                # Corrupt .bntx.zs
                corrupt_bntx_path = os.path.join(icon_dir, "Corrupt_Icon.bntx.zs")
                with open(corrupt_bntx_path, "wb") as f:
                    f.write(cctx.compress(b"corrupt texture data without BRTI"))

                # Mals SARC containing a corrupt MSBT
                corrupt_msbt = b"MsgStdBn" + b"\x00" * 32
                mals_sarc = _build_synthetic_sarc({"ActorMsg/PouchContent.msbt": corrupt_msbt})
                mals_path = os.path.join(mals_dir, "USen.Product.100.sarc.zs")
                with open(mals_path, "wb") as f:
                    f.write(cctx.compress(mals_sarc))

                summary = import_from_folder(romfs)

                self.assertIn("skipped", summary)
                self.assertEqual(summary["skipped"]["icons"], 1)
                self.assertEqual(summary["skipped"]["texts"], 1)

                manifest_path = os.path.join(oot_game_assets.assets_dir(), "manifest.json")
                self.assertTrue(os.path.isfile(manifest_path))
            finally:
                app_paths.USER_DATA_DIR = orig_user_data
                reload()

    def test_reimport_stale_cleanup_and_cancelled_import(self):
        """re-import removes stale icons; cancelled import leaves previous game_assets intact."""
        try:
            import zstandard
            import texture2ddecoder  # noqa: F401
            from PIL import Image  # noqa: F401
        except ImportError:
            self.skipTest("zstandard, texture2ddecoder, and Pillow required for reimport test")

        with tempfile.TemporaryDirectory() as td:
            orig_user_data = app_paths.USER_DATA_DIR
            try:
                app_paths.USER_DATA_DIR = td
                reload()

                adir = oot_game_assets.assets_dir()
                icons_dir = os.path.join(adir, "icons")
                os.makedirs(icons_dir, exist_ok=True)

                stale_png = os.path.join(icons_dir, "Stale_Old_Icon.png")
                with open(stale_png, "wb") as f:
                    f.write(b"\x89PNG\r\n\x1a\nstale")
                manifest_path = os.path.join(adir, "manifest.json")
                with open(manifest_path, "w", encoding="utf-8") as f:
                    f.write('{"counts": {"icons": 1}}')

                romfs = os.path.join(td, "romfs")
                src_icons = os.path.join(romfs, "UI", "Tex", "Icon")
                os.makedirs(src_icons, exist_ok=True)

                cctx = zstandard.ZstdCompressor()
                valid_bntx = _build_fake_bntx(4, 4, fmt=0x1A00, tex_size=512)
                with open(os.path.join(src_icons, "New_Valid_Icon.bntx.zs"), "wb") as f:
                    f.write(cctx.compress(valid_bntx))

                # Cancelled import leaves previous game_assets intact
                cancelled_res = import_from_folder(romfs, cancel=lambda: True)
                self.assertTrue(cancelled_res.get("cancelled"))
                self.assertTrue(os.path.isfile(stale_png))
                temp_dirs = [d for d in os.listdir(td) if d.startswith("game_assets.tmp-")]
                self.assertEqual(temp_dirs, [])

                # Successful re-import removes stale icons
                full_res = import_from_folder(romfs)
                self.assertFalse(full_res.get("cancelled"))
                self.assertFalse(os.path.isfile(stale_png))
                self.assertTrue(os.path.isfile(os.path.join(icons_dir, "New_Valid_Icon.png")))
                self.assertTrue(os.path.isfile(manifest_path))
                temp_dirs = [d for d in os.listdir(td) if d.startswith("game_assets.tmp-")]
                self.assertEqual(temp_dirs, [])
            finally:
                app_paths.USER_DATA_DIR = orig_user_data
                reload()

    def test_icon_path_traversal_returns_none(self):
        """icon_path("../x") returns None; traversal inputs in lookups return None/empty."""
        self.assertIsNone(icon_path("../x"))
        self.assertIsNone(icon_path("..\\x"))
        self.assertIsNone(icon_path("sub/icon"))
        self.assertIsNone(icon_path("sub\\icon"))
        self.assertEqual(item_text("../x"), (None, None))
        self.assertEqual(item_text("sub/item"), (None, None))
        self.assertIsNone(chapter_text("../x"))
        self.assertIsNone(chapter_text("sub/chapter"))


if __name__ == "__main__":
    unittest.main()
