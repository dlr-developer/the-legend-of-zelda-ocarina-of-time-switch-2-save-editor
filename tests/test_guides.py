import os
import sys
import unittest
import tempfile
import json

# Ensure repo root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from oot_guides import (
    load_guides,
    load_guide_file,
    get_checked_entries,
    set_checked_entries,
    get_slot_key,
    SAVE_COUNTERS,
)


class TestGuidesLoader(unittest.TestCase):
    def test_load_heart_pieces(self):
        hp_path = os.path.join(REPO_ROOT, "guides", "heart_pieces.json")
        guide = load_guide_file(hp_path)
        self.assertIsNotNone(guide, "heart_pieces.json failed to load")
        self.assertEqual(guide.get("id"), "heart_pieces")
        self.assertEqual(guide.get("total"), 36)

        entries = guide.get("entries", [])
        self.assertEqual(len(entries), 36)

        numbers = [e["n"] for e in entries]
        self.assertEqual(numbers, list(range(1, 37)), "Entries must be numbered 1..36 uniquely")
        self.assertEqual(len(set(numbers)), 36)

        for e in entries:
            self.assertTrue(bool(e.get("title")), f"Entry {e.get('n')} missing title")
            self.assertTrue(bool(e.get("area")), f"Entry {e.get('n')} missing area")
            self.assertTrue(bool(e.get("era")), f"Entry {e.get('n')} missing era")
            self.assertTrue(bool(e.get("steps")), f"Entry {e.get('n')} missing steps")

    def test_malformed_guide_skipped_without_raising(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            guides_dir = os.path.join(tmp_dir, "guides")
            os.makedirs(guides_dir, exist_ok=True)

            # 1. Invalid JSON
            with open(os.path.join(guides_dir, "broken_syntax.json"), "w", encoding="utf-8") as f:
                f.write("{ invalid json")

            # 2. Missing required top-level fields
            with open(os.path.join(guides_dir, "missing_fields.json"), "w", encoding="utf-8") as f:
                json.dump({"id": "broken1"}, f)

            # 3. Duplicate entry n
            with open(os.path.join(guides_dir, "dup_entries.json"), "w", encoding="utf-8") as f:
                json.dump({
                    "id": "dup",
                    "title": "Dup Test",
                    "total": 2,
                    "entries": [
                        {"n": 1, "title": "A", "steps": "Step A"},
                        {"n": 1, "title": "B", "steps": "Step B"}
                    ]
                }, f)

            # 4. Entry missing steps
            with open(os.path.join(guides_dir, "missing_steps.json"), "w", encoding="utf-8") as f:
                json.dump({
                    "id": "nosteps",
                    "title": "No Steps Test",
                    "total": 1,
                    "entries": [
                        {"n": 1, "title": "A"}
                    ]
                }, f)

            messages = []
            def status_cb(msg):
                messages.append(msg)

            # Should not raise any exception and skip bad files
            guides = load_guides(resource_dir=tmp_dir, app_dir=tmp_dir, status_callback=status_cb)
            self.assertEqual(len(guides), 0)
            self.assertTrue(len(messages) >= 4, "Should have logged status messages for skipped files")

    def test_app_dir_wins_and_order_sorting(self):
        with tempfile.TemporaryDirectory() as res_dir, tempfile.TemporaryDirectory() as app_dir:
            res_guides = os.path.join(res_dir, "guides")
            app_guides = os.path.join(app_dir, "guides")
            os.makedirs(res_guides, exist_ok=True)
            os.makedirs(app_guides, exist_ok=True)

            with open(os.path.join(res_guides, "guide_a.json"), "w", encoding="utf-8") as f:
                json.dump({
                    "id": "guide_a", "title": "Guide A", "order": 2, "total": 1,
                    "entries": [{"n": 1, "title": "A1", "steps": "Steps"}]
                }, f)

            with open(os.path.join(res_guides, "guide_b.json"), "w", encoding="utf-8") as f:
                json.dump({
                    "id": "guide_b", "title": "Guide B Res", "order": 1, "total": 1,
                    "entries": [{"n": 1, "title": "B1", "steps": "Steps"}]
                }, f)

            # Same id 'guide_b' in app_dir -> should override res_dir
            with open(os.path.join(app_guides, "guide_b.json"), "w", encoding="utf-8") as f:
                json.dump({
                    "id": "guide_b", "title": "Guide B App", "order": 1, "total": 1,
                    "entries": [{"n": 1, "title": "B1 App", "steps": "Steps"}]
                }, f)

            # Guide with no order
            with open(os.path.join(app_guides, "guide_c.json"), "w", encoding="utf-8") as f:
                json.dump({
                    "id": "guide_c", "title": "Guide C", "total": 1,
                    "entries": [{"n": 1, "title": "C1", "steps": "Steps"}]
                }, f)

            guides = load_guides(resource_dir=res_dir, app_dir=app_dir)
            self.assertEqual(len(guides), 3)

            # Order should be guide_b (order=1), guide_a (order=2), guide_c (no order)
            self.assertEqual(guides[0]["id"], "guide_b")
            self.assertEqual(guides[0]["title"], "Guide B App", "APP_DIR guide should override RESOURCE_DIR guide")
            self.assertEqual(guides[1]["id"], "guide_a")
            self.assertEqual(guides[2]["id"], "guide_c")

    def test_group_and_save_counter_fields(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            guide_path = os.path.join(tmp_dir, "skulltulas.json")
            with open(guide_path, "w", encoding="utf-8") as f:
                json.dump({
                    "id": "skulltulas",
                    "title": "Gold Skulltulas",
                    "save_counter": "skulltulas",
                    "total": 100,
                    "entries": [
                        {"n": 1, "group": "Kokiri Forest", "title": "Token 1", "steps": "Step 1"},
                        {"n": 2, "group": "Lost Woods", "title": "Token 2", "steps": "Step 2"}
                    ]
                }, f)

            guide = load_guide_file(guide_path)
            self.assertIsNotNone(guide)
            self.assertEqual(guide.get("save_counter"), "skulltulas")
            self.assertEqual(guide["entries"][0].get("group"), "Kokiri Forest")
            self.assertEqual(guide["entries"][1].get("group"), "Lost Woods")

            # Verify lookup table has skulltulas configuration
            self.assertIn("skulltulas", SAVE_COUNTERS)
            self.assertEqual(SAVE_COUNTERS["skulltulas"]["var_name"], "v_tokens")
            self.assertEqual(SAVE_COUNTERS["skulltulas"]["total"], 100)


class TestCheckStateHelpers(unittest.TestCase):
    def test_check_state_round_trip(self):
        settings = {}
        slot_key = r"C:\Saves\Slot1"
        guide_id = "heart_pieces"

        # Initially empty
        initial = get_checked_entries(settings, slot_key, guide_id)
        self.assertEqual(initial, set())

        # Save unsorted entries
        set_checked_entries(settings, slot_key, guide_id, [5, 2, 12, 1])

        # Verify raw persistence structure in settings
        self.assertIn("guide_checks", settings)
        self.assertIn(slot_key, settings["guide_checks"])
        self.assertIn(guide_id, settings["guide_checks"][slot_key])
        self.assertEqual(settings["guide_checks"][slot_key][guide_id], [1, 2, 5, 12])

        # Verify retrieval via helper
        checked = get_checked_entries(settings, slot_key, guide_id)
        self.assertEqual(checked, {1, 2, 5, 12})

        # Test another slot_key isolation (e.g. "no-save")
        no_save_key = "no-save"
        set_checked_entries(settings, no_save_key, guide_id, [7])
        self.assertEqual(get_checked_entries(settings, no_save_key, guide_id), {7})
        self.assertEqual(get_checked_entries(settings, slot_key, guide_id), {1, 2, 5, 12})

    def test_get_slot_key(self):
        self.assertEqual(get_slot_key(None), "no-save")
        self.assertEqual(get_slot_key(""), "no-save")
        raw_path = os.path.join(".", "relative", "path")
        expected = os.path.normpath(os.path.abspath(raw_path))
        self.assertEqual(get_slot_key(raw_path), expected)


if __name__ == "__main__":
    unittest.main()
