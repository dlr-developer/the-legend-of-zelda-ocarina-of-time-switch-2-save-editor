import os
import sys
import unittest
import tkinter as tk
from tkinter import ttk

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import tests._isolate
import oot_save_editor as se
from oot_guides import GuidesFrame, GuideCard, get_checked_entries, set_checked_entries


class MockSave:
    def __init__(self, data=None):
        self.data = dict(data or {})
        self.loaded = True
        self.key64 = set()

    def get(self, k, default=0):
        return self.data.get(k, default)

    def set(self, k, val):
        self.data[k] = val

    def get_string(self, k, max_len=64):
        return self.data.get(k, "")

    def set_string(self, k, val, max_len=64):
        self.data[k] = val


class TestFeaturesUpdate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tk.Tk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass

    def test_song_detection_combined_hashes(self):
        """Verify songs are detected from IsGet hash or Event hash."""
        # Save has IsGet/event hashes for Zelda's Lullaby, Epona's Song,
        # Saria's Song, Song of Time, plus Song of Storms and Minuet of Forest
        s = MockSave({
            0x01C20002: 1,  # Zelda's Lullaby IsGet
            0xDB8433F7: 1,  # Epona's Song Event
            0xD3F8BFCC: 1,  # Saria's Song IsGet
            0xBE4E744F: 1,  # Song of Time Event
            0x2B39DD4F: 1,  # Song of Storms IsGet
            0xDC0A0B54: 1,  # Minuet of Forest IsGet
        })

        song_vars = {}
        for idx, (sname, bit_idx, isget_h, event_h, _) in enumerate(se.SONGS):
            isget_learned = bool(s.get(isget_h, 0)) if isget_h else False
            event_learned = bool(s.get(event_h, 0)) if event_h else False
            if bit_idx == 4:
                # Sun's Song: check Royal Family Tomb clear, open, or break flags
                tomb_learned = bool(s.get(0x4B415FBB, 0)) or bool(s.get(0xCF7DAD5C, 0)) or bool(s.get(0x3EAC8ADA, 0))
                learned = isget_learned or event_learned or tomb_learned
            else:
                learned = isget_learned or event_learned
            song_vars[sname] = learned

        self.assertTrue(song_vars["Zelda's Lullaby"])
        self.assertTrue(song_vars["Epona's Song"])
        self.assertTrue(song_vars["Saria's Song"])
        self.assertTrue(song_vars["Song of Time"])
        self.assertFalse(song_vars["Sun's Song"])
        self.assertTrue(song_vars["Song of Storms"])
        self.assertTrue(song_vars["Minuet of Forest"])
        self.assertFalse(song_vars["Bolero of Fire"])

    def test_cheats_checkboxes_and_batch_selection(self):
        """Verify cheats menu provides checkboxes and Select All / Deselect All."""
        class MockCheatsEditor:
            def __init__(self, parent):
                self.cheats = [
                    {"name": "Cheat 1", "description": "Desc 1", "enabled": False},
                    {"name": "Cheat 2", "description": "Desc 2", "enabled": True},
                    {"name": "Cheat 3", "description": "Desc 3", "enabled": False},
                ]
                self.cheat_rows_frame = ttk.Frame(parent)
                self.cheat_vars = []
                self.cheat_count_var = tk.StringVar(value="")

            refresh_cheats = se.OOTEditor.refresh_cheats
            _on_cheat_checkbox_toggle = se.OOTEditor._on_cheat_checkbox_toggle
            select_all_cheats = se.OOTEditor.select_all_cheats
            deselect_all_cheats = se.OOTEditor.deselect_all_cheats
            _update_cheat_count = se.OOTEditor._update_cheat_count

        tester = MockCheatsEditor(self.root)
        tester.refresh_cheats()

        self.assertEqual(len(tester.cheat_vars), 3)
        self.assertFalse(tester.cheat_vars[0].get())
        self.assertTrue(tester.cheat_vars[1].get())
        self.assertFalse(tester.cheat_vars[2].get())
        self.assertEqual(tester.cheat_count_var.get(), "1 of 3 cheats active")

        # Select all
        tester.select_all_cheats()
        self.assertTrue(all(v.get() for v in tester.cheat_vars))
        self.assertTrue(all(c["enabled"] for c in tester.cheats))
        self.assertEqual(tester.cheat_count_var.get(), "3 of 3 cheats active")

        # Deselect all
        tester.deselect_all_cheats()
        self.assertFalse(any(v.get() for v in tester.cheat_vars))
        self.assertFalse(any(c["enabled"] for c in tester.cheats))
        self.assertEqual(tester.cheat_count_var.get(), "0 of 3 cheats active")

    def test_guides_multiselect_shift_click(self):
        """Verify Shift+Click batch toggle sets all cards in range to target state."""
        class MockApp:
            def __init__(self):
                self.settings = {}
                self.active_slot = None

            def store_settings(self):
                pass

        gf = GuidesFrame(self.root, MockApp())
        gf.current_guide = {
            "id": "mock_guide",
            "title": "Mock Guide",
            "entries": [{"n": i, "title": f"Card {i}"} for i in range(1, 6)],
        }
        gf.checked_set = set()

        cards = [GuideCard(gf.cards_inner, entry, "mock_guide", gf) for entry in gf.current_guide["entries"]]
        gf.cards_by_guide["mock_guide"] = cards

        # Regular click on card 1 (n=1)
        cards[0]._on_title_click()
        self.assertEqual(gf.last_clicked_n, 1)
        self.assertTrue(cards[0].check_var.get())
        self.assertIn(1, gf.checked_set)

        # Shift-click on card 4 (n=4)
        gf.handle_shift_click(cards[3])
        self.assertEqual(gf.last_clicked_n, 4)
        # All cards 1 through 4 should now be checked (since card 4 was unchecked)
        for i in range(4):
            self.assertTrue(cards[i].check_var.get(), f"Card {i+1} should be checked")
            self.assertIn(i + 1, gf.checked_set)
        self.assertFalse(cards[4].check_var.get())

        # Shift-click on card 1 (which is currently checked) -> uncheck range 1..4
        gf.handle_shift_click(cards[0])
        for i in range(4):
            self.assertFalse(cards[i].check_var.get(), f"Card {i+1} should be unchecked")
            self.assertNotIn(i + 1, gf.checked_set)

    def test_guides_auto_check_milestones(self):
        """Verify compute_auto_checked_entries extracts completed game actions."""
        s = MockSave({
            0x01C20002: 1,  # Zelda's Lullaby IsGet
            0xDB8433F7: 1,  # Epona's Song Event
            0xD3F8BFCC: 1,  # Saria's Song IsGet
            0xBE4E744F: 1,  # Song of Time Event
            0x2B39DD4F: 1,  # Song of Storms
            0xDC0A0B54: 1,  # Minuet of Forest
            0xCBD1E58C: 1,  # Kokiri Emerald
            0x7D69AD47: 1,  # Goron Ruby
            0xB8E3BF45: 1,  # Zora Sapphire
            0x235C7D9A: 1,  # Light Medallion
            0x04735978: 50, # 50 Skulltula Tokens
            0xE3C6E4A3: 1,  # Skulltula House 50 reward
            0x3A4126EC: 1,  # Scarecrow's Song
        })

        class MockApp:
            def __init__(self, slot):
                self.active_slot = slot
                self.settings = {}
                self.song_vars = {}
                for sname, bit_idx, isget_h, event_h, _ in se.SONGS:
                    g = bool(slot.get(isget_h, 0)) if isget_h else False
                    e = bool(slot.get(event_h, 0)) if event_h else False
                    if bit_idx == 4:
                        t = bool(slot.get(0x4B415FBB, 0)) or bool(slot.get(0xCF7DAD5C, 0)) or bool(slot.get(0x3EAC8ADA, 0))
                        self.song_vars[bit_idx] = tk.BooleanVar(value=(g or e or t))
                    else:
                        self.song_vars[bit_idx] = tk.BooleanVar(value=(g or e))
                self.quest_vars = {
                    0xCBD1E58C: tk.BooleanVar(value=True),
                    0x7D69AD47: tk.BooleanVar(value=True),
                    0xB8E3BF45: tk.BooleanVar(value=True),
                    0x235C7D9A: tk.BooleanVar(value=True),
                }
                self.owned_swords = {"Kokiri Sword": tk.BooleanVar(value=True), "Master Sword": tk.BooleanVar(value=True)}
                self.owned_shields = {"Deku Shield": tk.BooleanVar(value=True)}
                self.owned_tunics = {"Kokiri Tunic": tk.BooleanVar(value=True)}
                self.owned_boots = {"Kokiri Boots": tk.BooleanVar(value=True)}
                self.v_tokens = tk.StringVar(value="50")
                self.v_heart_pieces_total = tk.StringVar(value="4")

            def store_settings(self):
                pass

        app = MockApp(s)
        gf = GuidesFrame(self.root, app)

        # Songs auto-check
        auto_songs = gf.compute_auto_checked_entries("songs")
        # 1: Zelda, 2: Saria, 3: Epona, 5: Time, 6: Storms, 7: Minuet, 13: Scarecrow
        self.assertEqual(auto_songs, {1, 2, 3, 5, 6, 7, 13})

        # Tunics auto-check
        auto_tunics = gf.compute_auto_checked_entries("tunics")
        self.assertIn(1, auto_tunics)

        # Heart pieces auto-check (token reward 50 -> entry 5)
        auto_hp = gf.compute_auto_checked_entries("heart_pieces")
        self.assertIn(5, auto_hp)

        # Story guide auto-check
        auto_story = gf.compute_auto_checked_entries("story_guide")
        # Emerald complete -> 1..19
        for n in range(1, 20):
            self.assertIn(n, auto_story)
        # Ruby complete -> 46..59
        for n in range(46, 60):
            self.assertIn(n, auto_story)
        # Sapphire complete -> 64..77
        for n in range(64, 78):
            self.assertIn(n, auto_story)
        # Light medallion complete -> 84..88
        for n in range(84, 89):
            self.assertIn(n, auto_story)


if __name__ == "__main__":
    unittest.main()
