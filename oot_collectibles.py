"""
The Legend of Zelda: Ocarina of Time (Nintendo Switch 2) - Collectible Reader Module
Reads Gold Skulltulas, Pieces of Heart, and Fairy Thoughts from progress.sav
using 64-bit placement key sets and named Bool flags from collectible_flags.json.
Pure Python module with no GUI/Tk dependencies.
"""

import json
import os
import struct

from app_paths import APP_DIR, RESOURCE_DIR

SUPPORTED_GUIDES = ("gold_skulltulas", "heart_pieces", "fairy_thoughts")
HEADER_END_PROGRESS = 0x175D8
FIELD_KEY64_OFFSET = 0xA3DB7114

_CACHED_TABLE = None


def load_table(paths=None):
    """Load collectible_flags.json from the first matching path.

    Tries RESOURCE_DIR/collectible_flags.json then APP_DIR/collectible_flags.json
    (or custom paths if provided). Caches the result when using default paths.
    Returns {} on missing or invalid file without raising an exception.
    """
    global _CACHED_TABLE
    if paths is None and _CACHED_TABLE is not None:
        return _CACHED_TABLE

    if paths is None:
        candidate_paths = [
            os.path.join(RESOURCE_DIR, "collectible_flags.json"),
            os.path.join(APP_DIR, "collectible_flags.json"),
        ]
    elif isinstance(paths, (str, bytes, os.PathLike)):
        candidate_paths = [paths]
    else:
        candidate_paths = list(paths)

    for p in candidate_paths:
        if not p or not os.path.exists(p):
            continue
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                if paths is None:
                    _CACHED_TABLE = data
                return data
        except Exception:
            continue

    if paths is None:
        _CACHED_TABLE = {}
    return {}


def read_key64_set(p_bytes, p_fields):
    """Read set of 64-bit integer placement keys from progress.sav bytes.

    Field 0xA3DB7114 in p_fields points to a u32 file offset.
    From that offset, little-endian u64 values are read until 0 or EOF.
    If the field is missing, or the offset is < 0x175D8 or >= len(p_bytes),
    returns an empty set.
    """
    if not p_bytes or not p_fields or FIELD_KEY64_OFFSET not in p_fields:
        return set()

    val_offset = p_fields[FIELD_KEY64_OFFSET]
    if val_offset + 4 > len(p_bytes):
        return set()

    list_offset = struct.unpack_from("<I", p_bytes, val_offset)[0]
    if list_offset < HEADER_END_PROGRESS or list_offset >= len(p_bytes):
        return set()

    keys = set()
    curr = list_offset
    total_len = len(p_bytes)
    while curr + 8 <= total_len:
        val = struct.unpack_from("<Q", p_bytes, curr)[0]
        if val == 0:
            break
        keys.add(val)
        curr += 8

    return keys


def collected_entries(guide_id, key64_set, get_flag, table):
    """Return the set of collected guide entry numbers (n) as integers.

    Args:
        guide_id: Guide identifier (e.g. 'gold_skulltulas', 'heart_pieces', 'fairy_thoughts').
        key64_set: Iterable/set of 64-bit integer placement IDs.
        get_flag: Callable(hash_int) returning named field value (0 if absent).
        table: Dict loaded from collectible_flags.json.

    Returns:
        set[int]: Set of completed entry numbers (n). Unknown guide_id or empty table -> empty set.
    """
    if not table or not isinstance(table, dict) or guide_id not in table:
        return set()

    guide_data = table.get(guide_id)
    if not isinstance(guide_data, dict):
        return set()

    if not isinstance(key64_set, set):
        key64_set = set(key64_set) if key64_set else set()

    collected = set()
    for entry_key, entry_info in guide_data.items():
        if entry_key.startswith("_"):
            continue
        try:
            entry_n = int(entry_key)
        except (ValueError, TypeError):
            continue
        if not isinstance(entry_info, dict):
            continue

        sources = entry_info.get("sources", [])
        if not isinstance(sources, list):
            continue

        for src in sources:
            if not isinstance(src, dict):
                continue
            stype = src.get("type")
            if stype == "key64":
                raw_id = src.get("id")
                if raw_id is not None:
                    try:
                        k_id = int(raw_id)
                    except (ValueError, TypeError):
                        continue
                    if k_id in key64_set:
                        collected.add(entry_n)
                        break
            elif stype in ("chest", "flag"):
                raw_hash = src.get("hash")
                if raw_hash is not None:
                    try:
                        h_int = int(raw_hash, 16) if isinstance(raw_hash, str) else int(raw_hash)
                    except (ValueError, TypeError):
                        continue
                    if get_flag(h_int):
                        collected.add(entry_n)
                        break

    return collected
