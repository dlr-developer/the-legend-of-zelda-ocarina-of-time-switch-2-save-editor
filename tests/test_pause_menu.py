"""
Unit tests for the Switch 2 Pause Menu View (oot_pause_menu.py).
Tests two-way synchronization, quantity clamping, wheel step adjustments,
Max/Empty shortcuts, tier cycling, subscreen tab navigation, and Song Book interactions.
"""

import os
import sys
import unittest
import tkinter as tk

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import tests._isolate

# Skip test module if Tkinter GUI display cannot be started
try:
    _tk_probe = tk.Tk()
    _tk_probe.withdraw()
    _tk_probe.destroy()
except Exception as _tk_err:
    raise unittest.SkipTest(f"Tk GUI display is not available: {_tk_err}")

from oot_pause_menu import OOTTextureMenuFrame
import oot_scarecrow


class DummyEvent:
    """Mock Tkinter event for wheel and click simulations."""
    def __init__(self, delta=0, state=0, num=None, x=0, y=0):
        self.delta = delta
        self.state = state
        self.num = num
        self.x = x
        self.y = y


class DummyEditor:
    """Mock OOTEditor fulfilling Tk variables and callback methods used by the Pause Menu."""
    def __init__(self, root):
        self.root = root

        # Stats & Counters
        self.v_hearts = tk.StringVar(value="3")
        self.v_hp = tk.StringVar(value="12")
        self.v_double_defense = tk.BooleanVar(value=False)
        self.v_magic = tk.StringVar(value="None")
        self.v_magic_points = tk.StringVar(value="0")
        self.v_rupees = tk.StringVar(value="0")
        self.v_tokens = tk.StringVar(value="0")
        self.v_heart_pieces_total = tk.StringVar(value="0")
        self.v_heart_pieces_held = tk.StringVar(value="0")
        self.v_hearts_from_pieces = tk.StringVar(value="0")
        self.v_boss_containers = tk.StringVar(value="0")

        # Mutually exclusive & single active items
        self.hookshot_var = tk.StringVar(value="None")
        self.active_mask_var = tk.StringVar(value="None")
        self.child_quest_var = tk.StringVar(value="None")

        # Scarecrow's Song
        self.scarecrow_state_var = tk.StringVar(value="Not taught")
        self.scarecrow_note_vars = [tk.StringVar(value="-") for _ in range(8)]
        self.scarecrow_available = True

        # Special items & tools
        self.special_item_vars = {
            0x938D56BF: (tk.BooleanVar(value=False), "Fairy Bow"),
            0x80D34CE9: (tk.BooleanVar(value=False), "Fairy Slingshot"),
            0xA1D76D31: (tk.BooleanVar(value=False), "Boomerang"),
            0x1AAFDB66: (tk.BooleanVar(value=False), "Megaton Hammer"),
            0x49D1C374: (tk.BooleanVar(value=False), "Lens of Truth"),
            0xB796C16D: (tk.BooleanVar(value=False), "Din's Fire"),
            0x47F2CA87: (tk.BooleanVar(value=False), "Farore's Wind"),
            0xF0828CD0: (tk.BooleanVar(value=False), "Nayru's Love"),
            0x5E529AB9: (tk.BooleanVar(value=False), "Fire Arrow"),
            0x40735A8D: (tk.BooleanVar(value=False), "Ice Arrow"),
            0xBFB285C8: (tk.BooleanVar(value=False), "Light Arrow"),
            0xB7DF60F1: (tk.BooleanVar(value=False), "Fairy Ocarina"),
            0x54E2A3D1: (tk.BooleanVar(value=False), "Ocarina of Time"),
            0xFEB4D56B: (tk.BooleanVar(value=False), "Gerudo Pass"),
        }

        # Ammo items
        self.ammo_vars = {
            "arrows": (tk.StringVar(value="0"), 50, None),
            "bombs": (tk.StringVar(value="0"), 40, None),
            "bombchus": (tk.StringVar(value="0"), 30, None),
            "seeds": (tk.StringVar(value="0"), 50, None),
            "sticks": (tk.StringVar(value="0"), 30, None),
            "nuts": (tk.StringVar(value="0"), 40, None),
            "beans": (tk.StringVar(value="0"), 10, None),
            "scrub": (tk.StringVar(value="0"), 30, None),
        }

        # Dedicated Bottles
        self.bottle_vars = {
            f"bottle_{i}": tk.StringVar(value="(Not Acquired / Locked)")
            for i in range(1, 6)
        }

        # Equipment & Upgrades
        self.equip_vars = {
            "sword": tk.StringVar(value="Kokiri Sword"),
            "shield": tk.StringVar(value="Deku Shield"),
            "tunic": tk.StringVar(value="Kokiri Tunic"),
            "boots": tk.StringVar(value="Kokiri Boots"),
            "strength": tk.StringVar(value="None"),
            "scale": tk.StringVar(value="Default (1 meter)"),
            "wallet": tk.StringVar(value="Default Child's Wallet (99)"),
            "bomb_bag": tk.StringVar(value="Bomb Bag (20)"),
            "quiver": tk.StringVar(value="Quiver (30)"),
            "bullet_bag": tk.StringVar(value="Deku-Seed Bag (30)"),
            "stick_bag": tk.StringVar(value="Deku-Stick Bag (10)"),
            "nut_bag": tk.StringVar(value="Deku-Nut Bag (20)"),
        }

        self.owned_swords = {
            "Kokiri Sword": tk.BooleanVar(value=True),
            "Master Sword": tk.BooleanVar(value=False),
            "Biggoron's Sword": tk.BooleanVar(value=False),
        }
        self.owned_shields = {
            "Deku Shield": tk.BooleanVar(value=True),
            "Hylian Shield": tk.BooleanVar(value=False),
            "Mirror Shield": tk.BooleanVar(value=False),
        }
        self.owned_tunics = {
            "Kokiri Tunic": tk.BooleanVar(value=True),
            "Goron Tunic": tk.BooleanVar(value=False),
            "Zora Tunic": tk.BooleanVar(value=False),
        }
        self.owned_boots = {
            "Kokiri Boots": tk.BooleanVar(value=True),
            "Iron Boots": tk.BooleanVar(value=False),
            "Hover Boots": tk.BooleanVar(value=False),
        }

        # 3 Stones & 6 Medallions (hashes from oot_save_editor STONES_MEDALLIONS)
        self.quest_vars = {
            0xCBD1E58C: tk.BooleanVar(value=False),  # Kokiri's Emerald
            0x7D69AD47: tk.BooleanVar(value=False),  # Goron's Ruby
            0xB8E3BF45: tk.BooleanVar(value=False),  # Zora's Sapphire
            0x235C7D9A: tk.BooleanVar(value=False),  # Light Medallion
            0x692D57CB: tk.BooleanVar(value=False),  # Forest Medallion
            0x5CE254A6: tk.BooleanVar(value=False),  # Fire Medallion
            0x0151A68F: tk.BooleanVar(value=False),  # Water Medallion
            0x204D2063: tk.BooleanVar(value=False),  # Shadow Medallion
            0x0C7A5FD0: tk.BooleanVar(value=False),  # Spirit Medallion
        }

        # 12 Songs (bit indices 0..11)
        self.song_vars = {i: tk.BooleanVar(value=False) for i in range(12)}

        # Tracking flags for callbacks
        self.standard_view_called = False
        self.quest_tab_scarecrow_called = False
        self.sync_equipped_called = False
        self.saved = False

    def switch_to_standard_view(self):
        self.standard_view_called = True

    def switch_to_quest_tab_scarecrow(self):
        self.quest_tab_scarecrow_called = True

    def _sync_equipped_options(self):
        self.sync_equipped_called = True

    def _on_bag_or_capacity_changed(self, key):
        pass

    def _recalc_hearts_from_components(self):
        tot = int(self.v_heart_pieces_total.get() or 0)
        self.v_heart_pieces_held.set(str(tot % 4))

    def _on_hp_change(self):
        pass

    def _on_total_hearts_change(self):
        pass

    def _on_magic_level_change(self):
        pass

    def _on_mp_change(self):
        pass

    def _max_rupees_to_wallet(self):
        self.v_rupees.set("500")

    def heal_link(self):
        tot = int(self.v_hearts.get() or 3)
        self.v_hp.set(str(tot * 4))

    def refill_magic(self):
        self.v_magic_points.set("24")

    def save(self):
        self.saved = True


class TestPauseMenu(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.editor = DummyEditor(self.root)
        self.menu = OOTTextureMenuFrame(self.root, self.editor)
        self.menu.pack(fill="both", expand=True)
        self.root.update_idletasks()

    def tearDown(self):
        if hasattr(self, "root") and self.root:
            try:
                self.root.destroy()
            except Exception:
                pass

    def test_quantity_clamps_at_zero_and_capacity(self):
        """Check that quantity +/- clamps strictly between 0 and current capacity."""
        # 1. Deku Sticks (initial capacity from stick_bag is 10)
        self.editor.ammo_vars["sticks"][0].set("0")
        # Decrement at 0 clamps to 0
        self.menu.change_quantity("sticks", -1)
        self.assertEqual(self.editor.ammo_vars["sticks"][0].get(), "0")

        # Increment up to capacity
        self.menu.change_quantity("sticks", 5)
        self.assertEqual(self.editor.ammo_vars["sticks"][0].get(), "5")

        # Increment exceeding capacity clamps to 10
        self.menu.change_quantity("sticks", 10)
        self.assertEqual(self.editor.ammo_vars["sticks"][0].get(), "10")
        self.menu.change_quantity("sticks", 5)
        self.assertEqual(self.editor.ammo_vars["sticks"][0].get(), "10")

        # Decrement below 0 clamps to 0
        self.menu.change_quantity("sticks", -20)
        self.assertEqual(self.editor.ammo_vars["sticks"][0].get(), "0")

        # 2. Gold Skulltula tokens clamp between 0 and 100
        self.editor.v_tokens.set("0")
        self.menu.change_quantity("tokens", -5)
        self.assertEqual(self.editor.v_tokens.get(), "0")
        self.menu.change_quantity("tokens", 150)
        self.assertEqual(self.editor.v_tokens.get(), "100")
        self.menu.change_quantity("tokens", -120)
        self.assertEqual(self.editor.v_tokens.get(), "0")

        # 3. Heart Pieces held clamp between 0 and 3
        self.editor.v_heart_pieces_total.set("0")
        self.menu.change_quantity("heart_pieces", -1)
        self.assertEqual(int(self.editor.v_heart_pieces_total.get()) % 4, 0)
        self.menu.change_quantity("heart_pieces", 2)
        self.assertEqual(int(self.editor.v_heart_pieces_total.get()) % 4, 2)
        self.menu.change_quantity("heart_pieces", 5)
        self.assertEqual(int(self.editor.v_heart_pieces_total.get()) % 4, 3)

    def test_wheel_and_shift_wheel_steps(self):
        """Check that normal mouse wheel adjusts by 1 and Shift+wheel adjusts by 10."""
        self.editor.ammo_vars["bombs"][0].set("5")

        # Normal wheel up (delta > 0, state without shift) -> +1
        ev_up = DummyEvent(delta=120, state=0)
        self.menu._handle_wheel(ev_up, "bombs")
        self.assertEqual(self.editor.ammo_vars["bombs"][0].get(), "6")

        # Normal wheel down (delta < 0, state without shift) -> -1
        ev_down = DummyEvent(delta=-120, state=0)
        self.menu._handle_wheel(ev_down, "bombs")
        self.assertEqual(self.editor.ammo_vars["bombs"][0].get(), "5")

        # Shift + wheel up (delta > 0, state with Shift = 0x0001) -> +10
        ev_shift_up = DummyEvent(delta=120, state=0x0001)
        self.menu._handle_wheel(ev_shift_up, "bombs")
        self.assertEqual(self.editor.ammo_vars["bombs"][0].get(), "15")

        # Shift + wheel down (delta < 0, state with Shift = 0x0001) -> -10
        ev_shift_down = DummyEvent(delta=-120, state=0x0001)
        self.menu._handle_wheel(ev_shift_down, "bombs")
        self.assertEqual(self.editor.ammo_vars["bombs"][0].get(), "5")

    def test_max_and_empty_shortcuts(self):
        """Check that set_quantity_max sets to capacity and set_quantity_empty sets to 0."""
        # Bombs capacity with Bomb Bag (20)
        self.menu.set_quantity_max("bombs")
        self.assertEqual(self.editor.ammo_vars["bombs"][0].get(), "20")

        self.menu.set_quantity_empty("bombs")
        self.assertEqual(self.editor.ammo_vars["bombs"][0].get(), "0")

        # Arrows max unlocks Bow
        self.editor.special_item_vars[0x938D56BF][0].set(False)
        self.menu.set_quantity_max("arrows")
        self.assertEqual(self.editor.ammo_vars["arrows"][0].get(), "30")
        self.assertTrue(self.editor.special_item_vars[0x938D56BF][0].get(), "Max arrows must ensure Fairy Bow is owned")

        # Arrows empty keeps Bow owned
        self.menu.set_quantity_empty("arrows")
        self.assertEqual(self.editor.ammo_vars["arrows"][0].get(), "0")
        self.assertTrue(self.editor.special_item_vars[0x938D56BF][0].get(), "Emptying arrows must keep Fairy Bow owned")

        # Gold Skulltula tokens
        self.menu.set_quantity_max("tokens")
        self.assertEqual(self.editor.v_tokens.get(), "100")
        self.menu.set_quantity_empty("tokens")
        self.assertEqual(self.editor.v_tokens.get(), "0")

    def test_tier_cycling_for_hookshot(self):
        """Check that clicking hookshot cycles None -> Hookshot -> Longshot -> None."""
        self.editor.hookshot_var.set("None")

        # Click 1: None -> Hookshot
        self.menu._on_inv_slot_click("hookshot")
        self.assertEqual(self.editor.hookshot_var.get(), "Hookshot")

        # Click 2: Hookshot -> Longshot
        self.menu._on_inv_slot_click("hookshot")
        self.assertEqual(self.editor.hookshot_var.get(), "Longshot")

        # Click 3: Longshot -> None
        self.menu._on_inv_slot_click("hookshot")
        self.assertEqual(self.editor.hookshot_var.get(), "None")

    def test_tab_cycling_with_qe_wraps_across_three_pages(self):
        """Check that cycling subscreens with q/e wraps cleanly across all three pages."""
        # Initial subscreen: 0 (Items)
        self.assertEqual(self.menu.active_subscreen, 0)

        # 'e' (Next, delta +1): 0 -> 1 (Equipment)
        self.menu.cycle_subscreen(1)
        self.assertEqual(self.menu.active_subscreen, 1)

        # 'e' (Next, delta +1): 1 -> 2 (Collection)
        self.menu.cycle_subscreen(1)
        self.assertEqual(self.menu.active_subscreen, 2)

        # 'e' (Next, delta +1): 2 -> 0 (Wraps to Items)
        self.menu.cycle_subscreen(1)
        self.assertEqual(self.menu.active_subscreen, 0)

        # 'q' (Previous, delta -1): 0 -> 2 (Wraps to Collection)
        self.menu.cycle_subscreen(-1)
        self.assertEqual(self.menu.active_subscreen, 2)

        # 'q' (Previous, delta -1): 2 -> 1 (Equipment)
        self.menu.cycle_subscreen(-1)
        self.assertEqual(self.menu.active_subscreen, 1)

        # 'q' (Previous, delta -1): 1 -> 0 (Items)
        self.menu.cycle_subscreen(-1)
        self.assertEqual(self.menu.active_subscreen, 0)

    def test_song_book_entry_toggles_song_vars_and_scarecrow_switch(self):
        """Check clicking a Song Book entry toggles song_vars, and clicking Scarecrow switches to Quest tab."""
        # Switch to Collection subscreen
        self.menu.show_subscreen(2)

        # Find Song 0 (Zelda's Lullaby) in song arc hit boxes
        song0 = next((s for s, x, y, rad in self.menu.song_hit_boxes if s["bit_idx"] == 0), None)
        self.assertIsNotNone(song0)

        # Click Zelda's Lullaby toggles False -> True
        self.assertFalse(self.editor.song_vars[0].get())
        ev0 = DummyEvent(x=self.menu.song_hit_boxes[0][1], y=self.menu.song_hit_boxes[0][2])
        self.menu._on_song_arc_click(ev0)
        self.assertTrue(self.editor.song_vars[0].get())

        # Click again toggles True -> False
        self.menu._on_song_arc_click(ev0)
        self.assertFalse(self.editor.song_vars[0].get())

        # Find Scarecrow's Song hit box
        sc_entry = next((item for item in self.menu.song_hit_boxes if item[0]["is_scarecrow"]), None)
        self.assertIsNotNone(sc_entry)
        _, sc_x, sc_y, _ = sc_entry

        ev_sc = DummyEvent(x=sc_x, y=sc_y)
        self.menu._on_song_arc_click(ev_sc)
        self.assertTrue(self.editor.quest_tab_scarecrow_called,
                        "Clicking Scarecrow's Song must call editor.switch_to_quest_tab_scarecrow")


if __name__ == "__main__":
    unittest.main()
