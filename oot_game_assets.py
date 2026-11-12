"""Game asset importer and runtime lookup API for Nintendo Switch 2 assets.

Reads unpacked game assets (romfs) provided by the user, converts textures
and localized game text into portable formats (PNG and JSON), and caches them
under USER_DATA_DIR/game_assets/.

No game art or text is distributed with this repository.
"""
import datetime
import json
import os
import struct
from typing import Any, Callable, Dict, List, Optional, Tuple

import app_paths


class MissingDependencyError(ImportError):
    """Raised when dependencies required for game asset import are missing."""
    pass


def check_dependencies() -> None:
    """Check that zstandard, texture2ddecoder, and Pillow (PIL) are installed."""
    missing = []
    try:
        import zstandard  # noqa: F401
    except ImportError:
        missing.append("zstandard")

    try:
        import texture2ddecoder  # noqa: F401
    except ImportError:
        missing.append("texture2ddecoder")

    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        missing.append("Pillow")

    if missing:
        raise MissingDependencyError(
            f"Missing required package(s) for game asset import: {', '.join(missing)}. "
            f"Install them with: pip install {' '.join(missing)}"
        )


# In-memory JSON cache
_CACHED_ITEMS: Optional[Dict[str, Dict[str, str]]] = None
_CACHED_THREADS: Optional[Dict[str, Any]] = None
_CACHED_SONGS: Optional[Dict[str, List[str]]] = None
_CACHED_MANIFEST: Optional[Dict[str, Any]] = None


def assets_dir() -> str:
    """Return the absolute path to USER_DATA_DIR/game_assets."""
    return os.path.join(app_paths.USER_DATA_DIR, "game_assets")


def reload() -> None:
    """Clear in-memory cached asset data so subsequent lookups re-read disk."""
    global _CACHED_ITEMS, _CACHED_THREADS, _CACHED_SONGS, _CACHED_MANIFEST
    _CACHED_ITEMS = None
    _CACHED_THREADS = None
    _CACHED_SONGS = None
    _CACHED_MANIFEST = None


def has_assets() -> bool:
    """Return True if manifest.json exists and icons/ has at least one PNG file."""
    adir = assets_dir()
    manifest_path = os.path.join(adir, "manifest.json")
    icons_dir = os.path.join(adir, "icons")
    if not os.path.isfile(manifest_path) or not os.path.isdir(icons_dir):
        return False
    try:
        with os.scandir(icons_dir) as entries:
            for entry in entries:
                if entry.name.endswith(".png") and entry.is_file():
                    return True
    except OSError:
        return False
    return False


def icon_path(actor_name: str) -> Optional[str]:
    """Return path to icons/<actor_name>.png if present, else None."""
    if not actor_name:
        return None
    p = os.path.join(assets_dir(), "icons", f"{actor_name}.png")
    return p if os.path.isfile(p) else None


def _load_json_cached(rel_path: str) -> Optional[Any]:
    p = os.path.join(assets_dir(), rel_path)
    if not os.path.isfile(p):
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def item_text(actor_name: str) -> Tuple[Optional[str], Optional[str]]:
    """Return (name, caption) for actor_name from items.json, or (None, None)."""
    global _CACHED_ITEMS
    if _CACHED_ITEMS is None:
        _CACHED_ITEMS = _load_json_cached(os.path.join("text", "items.json")) or {}
    entry = _CACHED_ITEMS.get(actor_name)
    if not entry or not isinstance(entry, dict):
        return (None, None)
    return (entry.get("name"), entry.get("caption"))


def chapter_text(chapter_id: str) -> Optional[Dict[str, Any]]:
    """Return threads.json entry for chapter_id, or None."""
    global _CACHED_THREADS
    if _CACHED_THREADS is None:
        _CACHED_THREADS = _load_json_cached(os.path.join("text", "threads.json")) or {}
    return _CACHED_THREADS.get(str(chapter_id))


def song_text(index: int) -> Tuple[Optional[str], Optional[str]]:
    """Return (title, caption) for song index 0..12 from songs.json, or (None, None)."""
    global _CACHED_SONGS
    if _CACHED_SONGS is None:
        _CACHED_SONGS = _load_json_cached(os.path.join("text", "songs.json")) or {}
    titles = _CACHED_SONGS.get("titles", [])
    captions = _CACHED_SONGS.get("captions", [])
    if 0 <= index < len(titles) and 0 <= index < len(captions):
        return (titles[index], captions[index])
    return (None, None)


# ---------------------------------------------------------------------------
# SARC Archive Unpacking
# ---------------------------------------------------------------------------

def sarc_files(data: bytes) -> Dict[str, bytes]:
    """Unpack a SARC archive into a dict of {relpath: file_bytes}."""
    if len(data) < 0x20 or data[:4] != b"SARC":
        raise ValueError("Invalid SARC header")
    hdr_len, bom = struct.unpack_from("<HH", data, 4)
    e = "<" if bom == 0xFEFF else ">"
    data_off = struct.unpack_from(e + "I", data, 0x0C)[0]
    sfat = hdr_len
    if data[sfat:sfat + 4] != b"SFAT":
        raise ValueError("Invalid SFAT header in SARC")
    n = struct.unpack_from(e + "H", data, sfat + 6)[0]
    nodes = []
    for i in range(n):
        o = sfat + 0x0C + 0x10 * i
        _h, attr, s, en = struct.unpack_from(e + "IIII", data, o)
        nodes.append((attr, s, en))
    sfnt = sfat + 0x0C + 0x10 * n
    name_base = sfnt + 8
    out: Dict[str, bytes] = {}
    for attr, s, en in nodes:
        if attr & 0x01000000:
            no = name_base + (attr & 0xFFFF) * 4
            nul = data.find(b"\0", no)
            name = data[no:nul].decode("utf-8", "replace") if nul != -1 else data[no:].decode("utf-8", "replace")
        else:
            name = "%x" % s
        out[name] = data[data_off + s:data_off + en]
    return out


# ---------------------------------------------------------------------------
# MSBT Text Parsing
# ---------------------------------------------------------------------------

def parse_msbt(data: bytes, strip_tags: bool = True) -> Dict[str, str]:
    """Parse Nintendo MsgStdBn (MSBT) binary data into {label: text}.
    
    If byte 0x0C == 0, text is decoded as UTF-8; otherwise UTF-16.
    If strip_tags is True, control codes 0x0E (group, type, size, params) and
    0x0F (group, type) are omitted, preserving newlines and text characters.
    """
    if len(data) < 0x20 or data[:8] != b"MsgStdBn":
        raise ValueError("Invalid MsgStdBn header")
    e = "<" if data[8:10] == b"\xff\xfe" else ">"
    utf8 = (data[0x0C] == 0)
    nsec = struct.unpack_from(e + "H", data, 0x0E)[0]
    o = 0x20
    secs: Dict[bytes, bytes] = {}
    for _ in range(nsec):
        if o + 16 > len(data):
            break
        mag = data[o:o + 4]
        size = struct.unpack_from(e + "I", data, o + 4)[0]
        secs[mag] = data[o + 16:o + 16 + size]
        o += 16 + size
        o = (o + 15) & ~15

    labels: Dict[int, str] = {}
    lb = secs.get(b"LBL1")
    if lb and len(lb) >= 4:
        n = struct.unpack_from(e + "I", lb, 0)[0]
        for i in range(n):
            if 4 + 8 * i + 8 > len(lb):
                break
            cnt, off = struct.unpack_from(e + "II", lb, 4 + 8 * i)
            p = off
            for _ in range(cnt):
                if p >= len(lb):
                    break
                l = lb[p]
                name = lb[p + 1:p + 1 + l].decode("utf-8", "replace")
                idx = struct.unpack_from(e + "I", lb, p + 1 + l)[0]
                labels[idx] = name
                p += 1 + l + 4

    tx = secs.get(b"TXT2")
    if not tx or len(tx) < 4:
        return {}
    n = struct.unpack_from(e + "I", tx, 0)[0]
    offs = [struct.unpack_from(e + "I", tx, 4 + 4 * i)[0] for i in range(n)] + [len(tx)]
    out: Dict[str, str] = {}
    for i in range(n):
        raw = tx[offs[i]:offs[i + 1]]
        s = ""
        p = 0
        if utf8:
            buf = bytearray()
            while p < len(raw):
                c = raw[p]
                if c == 0x0E:
                    if buf:
                        s += buf.decode("utf-8", "replace")
                        buf = bytearray()
                    if p + 7 <= len(raw):
                        g, t, sz = struct.unpack_from(e + "HHH", raw, p + 1)
                        prm = raw[p + 7:p + 7 + sz]
                        if not strip_tags:
                            s += "<%d.%d:%s>" % (g, t, prm.hex())
                        p += 7 + sz
                    else:
                        break
                elif c == 0x0F:
                    if buf:
                        s += buf.decode("utf-8", "replace")
                        buf = bytearray()
                    if p + 5 <= len(raw):
                        g, t = struct.unpack_from(e + "HH", raw, p + 1)
                        if not strip_tags:
                            s += "</%d.%d>" % (g, t)
                        p += 5
                    else:
                        break
                elif c == 0:
                    p += 1
                else:
                    buf.append(c)
                    p += 1
            if buf:
                s += buf.decode("utf-8", "replace")
        else:
            while p + 1 < len(raw):
                c = struct.unpack_from(e + "H", raw, p)[0]
                if c == 0x0E:
                    if p + 8 <= len(raw):
                        g, t, sz = struct.unpack_from(e + "HHH", raw, p + 2)
                        prm = raw[p + 8:p + 8 + sz]
                        if not strip_tags:
                            s += "<%d.%d:%s>" % (g, t, prm.hex())
                        p += 8 + sz
                    else:
                        break
                elif c == 0x0F:
                    if p + 6 <= len(raw):
                        g, t = struct.unpack_from(e + "HH", raw, p + 2)
                        if not strip_tags:
                            s += "</%d.%d>" % (g, t)
                        p += 6
                    else:
                        break
                elif c == 0:
                    p += 2
                else:
                    s += chr(c)
                    p += 2
        lbl = labels.get(i, str(i))
        out[lbl] = s
    return out


# ---------------------------------------------------------------------------
# Texture / BNTX Deswizzling & Decoding
# ---------------------------------------------------------------------------

ASTC_BLOCKS = {
    0x2D: (4, 4), 0x2E: (5, 4), 0x2F: (5, 5), 0x30: (6, 5), 0x31: (6, 6), 0x32: (8, 5),
    0x33: (8, 6), 0x34: (8, 8), 0x35: (10, 5), 0x36: (10, 6), 0x37: (10, 8), 0x38: (10, 10),
    0x39: (12, 10), 0x3A: (12, 12)
}

BC_FORMATS = {
    0x1A: ("bc1", 8),
    0x1C: ("bc3", 16),
    0x1D: ("bc4", 8),
    0x1E: ("bc5", 16),
    0x20: ("bc7", 16),
}


def div_round_up(a: int, b: int) -> int:
    """Integer ceiling division."""
    return (a + b - 1) // b


def deswizzle(data: bytes, width_blocks: int, height_blocks: int, bpb: int, block_height: int) -> bytes:
    """Tegra block-linear to linear layout using Switch 2 NVN2 intra-GOB swizzle.
    
    bpb = bytes per block (e.g. 16 for ASTC/BC3/BC5/BC7, 8 for BC1/BC4).
    block_height = height in GOBs (power of two).
    """
    gob_w, gob_h = 64, 8
    row_bytes = width_blocks * bpb
    gobs_x = div_round_up(row_bytes, gob_w)
    out = bytearray(width_blocks * height_blocks * bpb)
    block_rows = block_height * gob_h
    data_len = len(data)
    for y in range(height_blocks):
        for xb in range(0, row_bytes, 16):
            gob_addr = ((y // block_rows) * gobs_x * block_height
                        + (xb // gob_w) * block_height
                        + (y % block_rows) // gob_h) * 512
            x = xb % gob_w
            yy = y % gob_h
            # Switch 2 (NVN2) intra-GOB unit address
            addr = (gob_addr + ((x >> 4) & 1) * 64 + ((x >> 5) & 1) * 256
                    + (yy & 1) * 16 + ((yy >> 1) & 1) * 32 + ((yy >> 2) & 1) * 128)
            dst = y * row_bytes + xb
            n = min(16, row_bytes - xb)
            if addr + n <= data_len:
                out[dst:dst + n] = data[addr:addr + n]
            elif addr < data_len:
                avail = data_len - addr
                out[dst:dst + avail] = data[addr:data_len]
    return bytes(out)


def decode_bntx(data: bytes):
    """Decode a single BNTX texture buffer to a Pillow RGBA Image."""
    import texture2ddecoder
    from PIL import Image

    i = data.find(b"BRTI")
    if i < 0:
        raise ValueError("BRTI block not found in BNTX")
    fmt = struct.unpack_from("<I", data, i + 0x1C)[0]
    w, h = struct.unpack_from("<II", data, i + 0x24)
    layout = struct.unpack_from("<I", data, i + 0x34)[0]
    size = struct.unpack_from("<I", data, i + 0x50)[0]
    j = data.find(b"BRTD")
    if j < 0:
        raise ValueError("BRTD block not found in BNTX")
    tex_data = data[j + 0x10:j + 0x10 + size]
    ftype = fmt >> 8
    block_height = 1 << layout

    if ftype in ASTC_BLOCKS:
        bw, bh = ASTC_BLOCKS[ftype]
        wb, hb = div_round_up(w, bw), div_round_up(h, bh)
        lin = deswizzle(tex_data, wb, hb, 16, block_height)
        rgba = texture2ddecoder.decode_astc(lin, wb * bw, hb * bh, bw, bh)
        img = Image.frombytes("RGBA", (wb * bw, hb * bh), rgba, "raw", "BGRA").crop((0, 0, w, h))
    elif ftype in BC_FORMATS:
        name, bpb = BC_FORMATS[ftype]
        wb, hb = div_round_up(w, 4), div_round_up(h, 4)
        lin = deswizzle(tex_data, wb, hb, bpb, block_height)
        decode_fn = getattr(texture2ddecoder, "decode_" + name)
        rgba = decode_fn(lin, wb * 4, hb * 4)
        img = Image.frombytes("RGBA", (wb * 4, hb * 4), rgba, "raw", "BGRA").crop((0, 0, w, h))
    else:
        raise ValueError(f"BNTX texture format 0x{fmt:X} not supported")
    return img


# ---------------------------------------------------------------------------
# Romfs Discovery & Zstandard Decompression
# ---------------------------------------------------------------------------

def find_romfs_roots(folder: str) -> List[str]:
    """Discover romfs directories in priority order: updates/<n>/romfs (highest n first), then romfs/.
    
    If folder itself directly contains UI/Tex/Icon, returns [folder].
    """
    if not folder or not os.path.isdir(folder):
        return []

    roots: List[str] = []
    updates_dir = os.path.join(folder, "updates")
    if os.path.isdir(updates_dir):
        subdirs = []
        try:
            for entry in os.scandir(updates_dir):
                if entry.is_dir():
                    r_path = os.path.join(entry.path, "romfs")
                    if os.path.isdir(r_path):
                        val = int(entry.name) if entry.name.isdigit() else entry.name
                        subdirs.append((val, r_path))
        except OSError:
            pass
        # Sort descending (integer numeric sort prioritized)
        subdirs.sort(key=lambda x: (isinstance(x[0], int), x[0]), reverse=True)
        for _, r_path in subdirs:
            roots.append(r_path)

    base_romfs = os.path.join(folder, "romfs")
    if os.path.isdir(base_romfs):
        roots.append(base_romfs)

    if not roots:
        # Check if folder itself is the romfs root
        if os.path.isdir(os.path.join(folder, "UI", "Tex", "Icon")):
            roots.append(folder)

    return roots


class ZstdContext:
    """Helper for decompressing .zs files using dictionary pack if present."""

    def __init__(self, roots: List[str]):
        import zstandard
        self._plain = zstandard.ZstdDecompressor()
        self._dicts: Dict[str, Any] = {}

        # Look for Pack/ZsDic.pack.zs in roots
        for r in roots:
            p = os.path.join(r, "Pack", "ZsDic.pack.zs")
            if os.path.isfile(p):
                try:
                    with open(p, "rb") as f:
                        raw = f.read()
                    pack_data = self._plain.decompress(raw, max_output_size=1 << 28)
                    for name, blob in sarc_files(pack_data).items():
                        self._dicts[name] = zstandard.ZstdCompressionDict(blob)
                    break
                except Exception:
                    pass

    def decompress(self, data: bytes) -> bytes:
        import zstandard
        # Try prioritized dictionary names first
        preferred = ["zs.zsdic", "bcett.byml.zsdic", "pack.zsdic", "bkprb.zsdic"]
        for name in preferred + [k for k in self._dicts if k not in preferred]:
            if name in self._dicts:
                try:
                    return zstandard.ZstdDecompressor(dict_data=self._dicts[name]).decompress(
                        data, max_output_size=1 << 30
                    )
                except zstandard.ZstdError:
                    continue
        # Fall back to plain zstd
        return self._plain.decompress(data, max_output_size=1 << 30)

    def read_zs_file(self, path: str) -> bytes:
        with open(path, "rb") as f:
            raw = f.read()
        return self.decompress(raw)


def _detect_language(roots: List[str]) -> str:
    """Determine Mals language to import, preferring system language or USen."""
    available: List[str] = []
    for r in roots:
        mals_dir = os.path.join(r, "Mals")
        if os.path.isdir(mals_dir):
            try:
                for entry in os.scandir(mals_dir):
                    if entry.name.endswith(".sarc.zs") and ".Product." in entry.name:
                        lang = entry.name.split(".Product.")[0]
                        if lang and lang not in available:
                            available.append(lang)
            except OSError:
                pass

    if not available:
        return "USen"

    # Try mapping system locale
    try:
        import locale
        loc = locale.getdefaultlocale()[0] or ""
    except Exception:
        loc = ""

    prefix = loc.split("_")[0].lower() if loc else ""
    mapping = {
        "de": "EUde",
        "fr": "EUfr",
        "es": "EUes",
        "it": "EUit",
        "ja": "JPja",
        "nl": "EUnl",
        "ru": "EUru",
        "ko": "KRko",
        "zh": "CNzh",
        "en": "USen",
    }
    match = mapping.get(prefix)
    if match and match in available:
        return match

    if "USen" in available:
        return "USen"

    return sorted(available)[0]


def _atomic_write_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def _atomic_save_image(path: str, img: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp.{os.getpid()}"
    img.save(tmp, "PNG")
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# Import Pipeline
# ---------------------------------------------------------------------------

def import_from_folder(
    folder: str,
    progress: Optional[Callable[[int, int, str], None]] = None,
    cancel: Optional[Callable[[], bool]] = None,
) -> Dict[str, Any]:
    """Import icons and game text from an unpacked game folder into USER_DATA_DIR/game_assets.
    
    Args:
        folder: Unpacked game root or romfs directory.
        progress: Optional callback progress(done: int, total: int, label: str).
        cancel: Optional callback cancel() -> bool. If returns True, stops early.
        
    Returns:
        dict summary with counts and metadata.
    """
    check_dependencies()
    from PIL import Image

    roots = find_romfs_roots(folder)
    has_icon_dir = any(os.path.isdir(os.path.join(r, "UI", "Tex", "Icon")) for r in roots)
    if not roots or not has_icon_dir:
        raise FileNotFoundError(
            "Could not find game assets ('UI/Tex/Icon') in the selected folder.\n"
            "Please unpack your game dump using Lichii/Eden:\n"
            "  eden-cli.exe --unpack-nup <game>.nup <folder>"
        )

    zstd_ctx = ZstdContext(roots)
    adir = assets_dir()
    icons_dir = os.path.join(adir, "icons")
    text_dir = os.path.join(adir, "text")
    os.makedirs(icons_dir, exist_ok=True)
    os.makedirs(text_dir, exist_ok=True)

    # 1. Discover Icon files in priority order
    icon_map: Dict[str, str] = {}
    for r in roots:
        idir = os.path.join(r, "UI", "Tex", "Icon")
        if not os.path.isdir(idir):
            continue
        try:
            for entry in os.scandir(idir):
                if entry.name.endswith(".bntx.zs") and entry.is_file():
                    name = entry.name[:-8]
                    # Skip shadow set
                    if name.endswith("_Sh"):
                        continue
                    if name not in icon_map:
                        icon_map[name] = entry.path
        except OSError:
            pass

    # 2. Discover Mals localized messages SARC
    lang = _detect_language(roots)
    mals_sarc_path: Optional[str] = None
    for r in roots:
        mdir = os.path.join(r, "Mals")
        if not os.path.isdir(mdir):
            continue
        try:
            for entry in os.scandir(mdir):
                if entry.name.startswith(f"{lang}.Product.") and entry.name.endswith(".sarc.zs"):
                    mals_sarc_path = entry.path
                    break
        except OSError:
            pass
        if mals_sarc_path:
            break

    total_steps = len(icon_map) + (1 if mals_sarc_path else 0)
    done_steps = 0

    if progress:
        progress(0, total_steps, "Reading localized game text...")

    items: Dict[str, Dict[str, str]] = {}
    threads: Dict[str, Dict[str, Any]] = {}
    songs: Dict[str, List[str]] = {"titles": [], "captions": []}

    # Process text from Mals
    if mals_sarc_path:
        if cancel and cancel():
            return {"cancelled": True}
        raw_sarc = zstd_ctx.read_zs_file(mals_sarc_path)
        sarc_entries = sarc_files(raw_sarc)
        norm_sarc = {k.replace("\\", "/").lstrip("./"): v for k, v in sarc_entries.items()}

        # 2a. Items: ActorMsg/PouchContent.msbt
        pouch_bytes = norm_sarc.get("ActorMsg/PouchContent.msbt")
        if pouch_bytes:
            pouch_text = parse_msbt(pouch_bytes, strip_tags=True)
            for lbl, txt in pouch_text.items():
                if lbl.endswith("_Name"):
                    actor = lbl[:-5]
                    items.setdefault(actor, {"name": "", "caption": ""})["name"] = txt
                elif lbl.endswith("_Caption"):
                    actor = lbl[:-8]
                    items.setdefault(actor, {"name": "", "caption": ""})["caption"] = txt

        # 2b. Threads: ChallengeMsg/Info_<id>.msbt
        for path_k, file_bytes in norm_sarc.items():
            if path_k.startswith("ChallengeMsg/Info_") and path_k.endswith(".msbt"):
                cid = path_k[len("ChallengeMsg/Info_"):-len(".msbt")]
                info_text = parse_msbt(file_bytes, strip_tags=True)
                title = info_text.get("Name", "")
                sections = {k: v for k, v in info_text.items() if k != "Name"}
                threads[cid] = {"title": title, "sections": sections}

        # 2c. Songs: LayoutMsg/Ocarina_00.msbt
        ocarina_bytes = norm_sarc.get("LayoutMsg/Ocarina_00.msbt")
        if ocarina_bytes:
            ocarina_text = parse_msbt(ocarina_bytes, strip_tags=True)
            songs["titles"] = [ocarina_text.get(f"Title_{i:02d}", "") for i in range(13)]
            songs["captions"] = [ocarina_text.get(f"Caption_{i:02d}", "") for i in range(13)]

        done_steps += 1
        if progress:
            progress(done_steps, total_steps, "Writing text catalogs...")

    # Write JSON files atomically
    _atomic_write_json(os.path.join(text_dir, "items.json"), items)
    _atomic_write_json(os.path.join(text_dir, "threads.json"), threads)
    _atomic_write_json(os.path.join(text_dir, "songs.json"), songs)

    # 3. Process and convert icons
    resample_lanczos = getattr(Image, "Resampling", Image).LANCZOS
    icon_count = 0
    for name, bntx_zs_path in sorted(icon_map.items()):
        if cancel and cancel():
            return {"cancelled": True}
        done_steps += 1
        if progress:
            progress(done_steps, total_steps, f"Decoding icon {name}...")

        try:
            bntx_raw = zstd_ctx.read_zs_file(bntx_zs_path)
            img = decode_bntx(bntx_raw)
            # Downscale so longest side <= 256 px, preserve alpha
            max_side = max(img.width, img.height)
            if max_side > 256:
                scale = 256.0 / max_side
                nw = max(1, int(round(img.width * scale)))
                nh = max(1, int(round(img.height * scale)))
                img = img.resize((nw, nh), resample_lanczos)
            dest_png = os.path.join(icons_dir, f"{name}.png")
            _atomic_save_image(dest_png, img)
            icon_count += 1
        except Exception:
            # Skip invalid texture if any
            continue

    # 4. Manifest
    manifest_data = {
        "source": roots,
        "imported": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "counts": {
            "icons": icon_count,
            "items": len(items),
            "threads": len(threads),
            "songs": len(songs.get("titles", [])),
        },
        "lang": lang,
        "version": 1,
    }
    _atomic_write_json(os.path.join(adir, "manifest.json"), manifest_data)

    # Invalidate cache
    reload()

    if progress:
        progress(total_steps, total_steps, "Import complete.")

    return {
        "icons": icon_count,
        "items": len(items),
        "threads": len(threads),
        "songs": len(songs.get("titles", [])),
        "lang": lang,
        "source": roots,
    }
