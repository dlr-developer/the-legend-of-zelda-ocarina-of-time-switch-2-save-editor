"""Unit tests for oot_collectibles reader module."""
import json
import os
import struct
import sys
import tempfile
import unittest

# Ensure repo root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import tests._isolate
from oot_collectibles import (
    FIELD_KEY64_OFFSET,
    HEADER_END_PROGRESS,
    SUPPORTED_GUIDES,
    collected_entries,
    load_table,
    read_key64_set,
)


class TestCollectiblesKeyList(unittest.TestCase):
    """Test reading 64-bit key sets from synthetic progress.sav byte buffers."""

    def test_key_list_terminated_by_zero(self):
        """Buffer with field table entry for 0xA3DB7114 pointing at [k1, k2, 0, junk] returns {k1, k2}."""
        k1 = 13609975487234437568
        k2 = 16101480770659370603
        junk = 999999999999999999
        list_offset = HEADER_END_PROGRESS

        # Build synthetic p_bytes with field at offset 44 pointing to list_offset
        p_bytes = bytearray(list_offset + 64)
        p_fields = {FIELD_KEY64_OFFSET: 44}
        struct.pack_into("<I", p_bytes, 44, list_offset)
        struct.pack_into("<QQQQ", p_bytes, list_offset, k1, k2, 0, junk)

        keys = read_key64_set(p_bytes, p_fields)
        self.assertEqual(keys, {k1, k2})

    def test_key_list_missing_field(self):
        """Missing field in p_fields returns empty set."""
        p_bytes = bytearray(HEADER_END_PROGRESS + 32)
        p_fields = {}
        self.assertEqual(read_key64_set(p_bytes, p_fields), set())
        self.assertEqual(read_key64_set(None, None), set())
        self.assertEqual(read_key64_set(b"", {}), set())

    def test_key_list_offset_out_of_range(self):
        """Offset out of range (< 0x175D8 or >= len(file)) returns empty set."""
        p_bytes = bytearray(HEADER_END_PROGRESS + 64)
        p_fields = {FIELD_KEY64_OFFSET: 44}

        # Offset before HEADER_END_PROGRESS (0x175D8): a nonzero key sits there,
        # so only the bound check (not a zero terminator) can make this empty.
        struct.pack_into("<I", p_bytes, 44, 0x1000)
        struct.pack_into("<Q", p_bytes, 0x1000, 0x1111222233334444)
        self.assertEqual(read_key64_set(p_bytes, p_fields), set())

        # Offset >= len(p_bytes)
        struct.pack_into("<I", p_bytes, 44, len(p_bytes))
        self.assertEqual(read_key64_set(p_bytes, p_fields), set())

        struct.pack_into("<I", p_bytes, 44, len(p_bytes) + 100)
        self.assertEqual(read_key64_set(p_bytes, p_fields), set())

    def test_key_list_running_to_eof_without_zero(self):
        """List running to EOF without 0 returns all keys."""
        k1 = 0x1111222233334444
        k2 = 0x5555666677778888
        list_offset = HEADER_END_PROGRESS

        # Exact length: 2 u64 keys, no terminating zero
        p_bytes = bytearray(list_offset + 16)
        p_fields = {FIELD_KEY64_OFFSET: 44}
        struct.pack_into("<I", p_bytes, 44, list_offset)
        struct.pack_into("<QQ", p_bytes, list_offset, k1, k2)

        keys = read_key64_set(p_bytes, p_fields)
        self.assertEqual(keys, {k1, k2})

        # Trailing leftover bytes fewer than 8 bytes
        p_bytes_with_junk = bytearray(list_offset + 21)
        struct.pack_into("<I", p_bytes_with_junk, 44, list_offset)
        struct.pack_into("<QQ", p_bytes_with_junk, list_offset, k1, k2)
        p_bytes_with_junk[list_offset + 16:list_offset + 21] = b"\xAA\xBB\xCC\xDD\xEE"

        keys_with_junk = read_key64_set(p_bytes_with_junk, p_fields)
        self.assertEqual(keys_with_junk, {k1, k2})


class TestCollectedEntries(unittest.TestCase):
    """Test collected_entries logic with inline flag table."""

    def setUp(self):
        self.inline_table = {
            "_about": "Test table metadata",
            "_sources": {},
            "test_guide": {
                "_missing_from_guide": {
                    "sources": [{"type": "flag", "name": "SkippedFlag", "hash": "0x11111111"}]
                },
                "_meta_info": "Should be ignored",
                "1": {
                    # key64 source
                    "sources": [{"type": "key64", "id": "1001"}]
                },
                "2": {
                    # chest source
                    "sources": [{"type": "chest", "id": "2001", "hash": "0x22222222"}]
                },
                "3": {
                    # flag source
                    "sources": [{"type": "flag", "name": "FlagThree", "hash": "0x33333333"}]
                },
                "4": {
                    # ANY semantics: key64 missing, flag present
                    "sources": [
                        {"type": "key64", "id": "4001"},
                        {"type": "flag", "name": "FlagFour", "hash": "0x44444444"},
                    ]
                },
                "5": {
                    # Neither source satisfied
                    "sources": [
                        {"type": "key64", "id": "5001"},
                        {"type": "chest", "hash": "0x55555555"},
                    ]
                },
            },
        }

    def test_collected_entries_sources_and_any_semantics(self):
        """Cover key64, chest, flag sources, ANY semantics, and skipping '_' keys."""
        key64_set = {1001}
        flags = {
            0x22222222: 1,  # entry 2 chest
            0x44444444: 1,  # entry 4 flag
            0x11111111: 1,  # _missing_from_guide flag (must be skipped!)
        }
        get_flag = lambda h: flags.get(h, 0)

        result = collected_entries("test_guide", key64_set, get_flag, self.inline_table)
        self.assertEqual(result, {1, 2, 4})

    def test_unknown_guide_and_empty_table(self):
        """Unknown guide_id or empty table returns empty set."""
        key64_set = {1001}
        get_flag = lambda h: 1

        self.assertEqual(collected_entries("unknown_guide", key64_set, get_flag, self.inline_table), set())
        self.assertEqual(collected_entries("test_guide", key64_set, get_flag, {}), set())
        self.assertEqual(collected_entries("test_guide", key64_set, get_flag, None), set())


class TestLoadTable(unittest.TestCase):
    """Test load_table with missing and valid files."""

    def test_load_table_missing_file_returns_empty_dict(self):
        """load_table with a missing file returns {} without raising an exception."""
        result = load_table(paths=["nonexistent_collectible_flags_xyz.json"])
        self.assertEqual(result, {})

        result_str = load_table(paths="nonexistent_collectible_flags_xyz.json")
        self.assertEqual(result_str, {})

    def test_load_table_invalid_file_returns_empty_dict(self):
        """load_table with invalid JSON returns {} without raising an exception."""
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            f.write("not valid json content {{{")
            tmp_path = f.name
        try:
            result = load_table(paths=[tmp_path])
            self.assertEqual(result, {})
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    def test_load_table_valid_file(self):
        """load_table with a valid JSON file returns parsed dictionary."""
        payload = {"gold_skulltulas": {}, "heart_pieces": {}, "fairy_thoughts": {}}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(payload, f)
            tmp_path = f.name
        try:
            result = load_table(paths=[tmp_path])
            self.assertEqual(result, payload)
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    def test_supported_guides_constant(self):
        """SUPPORTED_GUIDES constant contains the three expected guides."""
        self.assertEqual(SUPPORTED_GUIDES, ("gold_skulltulas", "heart_pieces", "fairy_thoughts"))


if __name__ == "__main__":
    unittest.main()
