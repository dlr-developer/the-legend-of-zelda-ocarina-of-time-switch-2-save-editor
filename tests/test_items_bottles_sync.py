"""Tests for auto-checking bottles, Echo Gem, Magic Beans and items guide sync."""

import json
import os
import sys
import unittest

# Ensure test isolation and repo root on sys.path
import tests._isolate

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import tkinter as tk
from oot_guides import GuidesFrame


class DummyApp:
    """Minimal app stub for GuidesFrame auto-check testing."""

    def __init__(self, slot=None, app_dir=None, resource_dir=None):
        self.settings = {}
        self.palette = {}
        self.active_slot = slot
        self.app_dir = app_dir or REPO_ROOT
        self.resource_dir = resource_dir or REPO_ROOT

    def store_settings(self):
        pass


class FakeSaveSlot:
    """Fake save slot returning values from a dictionary."""

    def __init__(self, flags=None):
        self.flags = dict(flags or {})
        self.loaded = True

    def get(self, h, default=0):
        return self.flags.get(h, default)


class TestItemsBottlesSync(unittest.TestCase):
    """Test bottles and items guide auto-checks and items.json schema."""

    @classmethod
    def setUpClass(cls):
        try:
            cls.root = tk.Tk()
            cls.root.withdraw()
        except tk.TclError:
            cls.root = None

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "root", None):
            try:
                cls.root.destroy()
            except Exception:
                pass

    def _compute_auto(self, flags, guide_id, extra_app_attrs=None):
        slot = FakeSaveSlot(flags)
        app = DummyApp(slot=slot)
        if extra_app_attrs:
            for k, v in extra_app_attrs.items():
                setattr(app, k, v)
        if self.root:
            gf = GuidesFrame(self.root, app, app_dir=REPO_ROOT, resource_dir=REPO_ROOT)
            try:
                return gf.compute_auto_checked_entries(guide_id)
            finally:
                gf.destroy()
        gf = GuidesFrame.__new__(GuidesFrame)
        gf.app = app
        return gf.compute_auto_checked_entries(guide_id)

    def test_bottle_flags_auto_check(self):
        """Each bottle flag alone ticks exactly its own entry in bottles and matching All Items entry."""
        bottle_specs = [
            (1, 9, 0x4D62DE75),   # Potion Shop
            (2, 11, 0x084DA83F),  # Lon Lon Super Cucco
            (3, 17, 0x7A7961C3),  # Cucco Lady
            (4, 32, 0x170B5DF2),  # Ruto's Letter
        ]
        all_bottle_items = {9, 11, 17, 32, 47}

        for bottle_n, item_n, flag in bottle_specs:
            auto_bottles = self._compute_auto({flag: 1}, "bottles")
            self.assertEqual(auto_bottles, {bottle_n})

            auto_items = self._compute_auto({flag: 1}, "items")
            self.assertIn(item_n, auto_items)
            self.assertEqual(auto_items & all_bottle_items, {item_n})

        # Ghost Shop coupon checks
        # 499 ticks nothing
        auto_bottles_499 = self._compute_auto({0xE3407CEE: 499}, "bottles")
        self.assertEqual(auto_bottles_499, set())
        auto_items_499 = self._compute_auto({0xE3407CEE: 499}, "items")
        self.assertEqual(auto_items_499 & all_bottle_items, set())

        # 500 ticks bottle 5 and item 47
        auto_bottles_500 = self._compute_auto({0xE3407CEE: 500}, "bottles")
        self.assertEqual(auto_bottles_500, {5})
        auto_items_500 = self._compute_auto({0xE3407CEE: 500}, "items")
        self.assertIn(47, auto_items_500)
        self.assertEqual(auto_items_500 & all_bottle_items, {47})

    def test_held_bottles_with_no_source_flags_tick_nothing(self):
        """Holding 3 bottles with no source flags ticks nothing in bottles."""
        held_bottles = {
            0xD53CE3A7: 1,  # PouchData.BottleA
            0xFCA29A04: 1,  # PouchData.BottleB
            0x893216A1: 1,  # PouchData.BottleC
        }
        auto_bottles = self._compute_auto(held_bottles, "bottles")
        self.assertEqual(auto_bottles, set())

        # Also verify app.bottles UI fallback does not tick bottles guide
        class MockBottleVar:
            def __init__(self, val):
                self.val = val

            def get(self):
                return self.val

        extra = {
            "bottles": [
                {"var": MockBottleVar("Red Potion")},
                {"var": MockBottleVar("Lon Lon Milk")},
                {"var": MockBottleVar("Fairy")},
            ]
        }
        auto_bottles_ui = self._compute_auto(held_bottles, "bottles", extra_app_attrs=extra)
        self.assertEqual(auto_bottles_ui, set())

    def test_echo_gem_and_magic_beans_flags(self):
        """Echo Gem and Magic Beans flags tick #25 and #30."""
        # Echo Gem via IsGet.Item_AgonyStone (0xDD587ED8)
        auto_echo_isget = self._compute_auto({0xDD587ED8: 1}, "items")
        self.assertIn(25, auto_echo_isget)

        # Echo Gem via PouchData.Item_AgonyStone.StockNum (0xF3B14CE2 > 0)
        auto_echo_pouch = self._compute_auto({0xF3B14CE2: 1}, "items")
        self.assertIn(25, auto_echo_pouch)

        # Echo Gem not checked when both are 0
        auto_echo_none = self._compute_auto({0xF3B14CE2: 0, 0xDD587ED8: 0}, "items")
        self.assertNotIn(25, auto_echo_none)

        # Magic Beans via IsGet.Item_MagicBean (0x6D39C600)
        auto_beans = self._compute_auto({0x6D39C600: 1}, "items")
        self.assertIn(30, auto_beans)

        # Dead hash 0x4A6B8851 does not tick #30
        auto_beans_dead = self._compute_auto({0x4A6B8851: 1}, "items")
        self.assertNotIn(30, auto_beans_dead)

    def test_items_json_structure_and_no_collectibles(self):
        """items.json has 70 entries numbered 1..70, total 70, no collectibles group, and items result never contains 71-74."""
        items_path = os.path.join(REPO_ROOT, "guides", "items.json")
        with open(items_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data.get("total"), 70)
        self.assertEqual(len(data.get("entries", [])), 70)
        self.assertNotIn("and general items", data.get("intro", ""))

        entry_nums = [entry["n"] for entry in data["entries"]]
        self.assertEqual(entry_nums, list(range(1, 71)))

        for entry in data["entries"]:
            self.assertNotEqual(entry.get("group"), "Any time and collectibles")

        # compute_auto_checked_entries("items") never contains 71-74, even with legacy flags
        legacy_flags = {
            0x51EC97B3: 1,   # Legacy Heart Pieces check
            0x04735978: 100, # Legacy Tokens check
        }
        auto_items = self._compute_auto(legacy_flags, "items")
        self.assertEqual(auto_items & {71, 72, 73, 74}, set())

    def test_deleted_fallback_hashes_alone_do_not_tick(self):
        """Deleted fallback hashes do not tick items entries."""
        fallback_checks = [
            (0x409540C5, 10),
            (0xA08F47BE, 19),
            (0x196E812D, 22),
            (0x43734D88, 33),
            (0x075C539A, 43),
            (0x27BE1283, 54),
            (0x4E7D65E1, 64),
            (0x944B88BE, 70),
        ]
        for dead_hash, item_n in fallback_checks:
            auto_items = self._compute_auto({dead_hash: 1}, "items")
            self.assertNotIn(item_n, auto_items, f"Hash {hex(dead_hash)} should not tick item {item_n}")


if __name__ == "__main__":
    unittest.main()
