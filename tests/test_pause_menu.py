"""
Unit tests for the Switch 2 Pause Menu View (oot_pause_menu.py).
Tests two-way synchronization, quantity clamping, wheel step adjustments,
Max/Empty shortcuts, tier cycling, subscreen tab navigation, and Song Book interactions.
"""

import os
import sys
import math
import unittest
import tkinter as tk
from tkinter import ttk

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

from oot_pause_menu import (
    OOTTextureMenuFrame,
    compute_staff_note_y,
    compute_song_arc_positions,
    safe_int,
    PAUSE_MENU_LAYOUT,
    ACTOR_TEXT_FALLBACK,
)
import oot_scarecrow


class DummyEvent:
    """Mock Tkinter event for wheel and click simulations."""
    def __init__(self, delta=0, state=0, num=None, x=0, y=0, keysym=None):
        self.keysym = keysym
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
        self.adult_trade_var = tk.StringVar(value="None")

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

        # Save progress active_slot (progress.sav enum field values)
        self.active_slot = {}

        # Tracking flags for callbacks
        self.standard_view_called = False
        self.quest_tab_scarecrow_called = False
        self.sync_equipped_called = False
        self.saved = False
        self.bottle_selected_calls = []

    def _on_bottle_selected(self, b_num):
        self.bottle_selected_calls.append(b_num)

    def switch_to_standard_view(self):
        self.standard_view_called = True

    def switch_to_quest_tab_scarecrow(self):
        self.quest_tab_scarecrow_called = True

    def _sync_equipped_options(self):
        self.sync_equipped_called = True

    def _on_bag_or_capacity_changed(self, key):
        pass

    def ammo_capacity(self, key):
        from oot_save_editor import OOTEditor
        return OOTEditor.ammo_capacity(self, key)

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
        # Switch to Song Book subscreen (minus menu)
        self.menu.show_subscreen("Song Book")
        self.assertEqual(self.menu.menu_mode, "minus")
        self.assertEqual(self.menu.current_page_name(), "Song Book")

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

    def test_song_arc_places_13_circles_without_overlap_on_900x260(self):
        """Check that _render_song_arc places 13 circles with no two centers closer than 2*radius on a 900x260 canvas."""
        self.menu.show_subscreen(2)
        self.menu._render_song_arc(canvas_w=900, canvas_h=260)

        hit_boxes = self.menu.song_hit_boxes
        self.assertEqual(len(hit_boxes), 13, "Must place exactly 13 song circles on arc")

        radius = hit_boxes[0][3]
        min_allowed_dist = 2 * radius

        for i in range(len(hit_boxes)):
            s_i, xi, yi, rad_i = hit_boxes[i]
            for j in range(i + 1, len(hit_boxes)):
                s_j, xj, yj, rad_j = hit_boxes[j]
                dist = math.hypot(xi - xj, yi - yj)
                self.assertGreaterEqual(
                    dist, min_allowed_dist,
                    f"Centers of '{s_i['name']}' and '{s_j['name']}' ({dist:.1f}px) closer than 2*radius ({min_allowed_dist}px)"
                )

    def test_staff_note_y_strictly_decreasing_for_button_notes(self):
        """Check that staff note y-position is strictly decreasing for values [4, 7, 11, 13, 16] (higher pitch drawn higher)."""
        top_y = 40.0
        bot_y = 100.0
        pitches = [4, 7, 11, 13, 16]
        y_positions = [compute_staff_note_y(p, top_y, bot_y) for p in pitches]

        for i in range(len(y_positions) - 1):
            self.assertGreater(
                y_positions[i], y_positions[i + 1],
                f"y for pitch {pitches[i]} ({y_positions[i]}) not greater than y for pitch {pitches[i+1]} ({y_positions[i+1]})"
            )

    def test_staff_button_notes_sit_on_the_five_lines(self):
        """L, R, A, Y, X land exactly on the five equally spaced staff lines, bottom to top."""
        top_y, bot_y = 40.0, 100.0
        lines = [bot_y - i * (bot_y - top_y) / 4.0 for i in range(5)]
        for pitch, line_y in zip([4, 7, 11, 13, 16], lines):
            self.assertAlmostEqual(compute_staff_note_y(pitch, top_y, bot_y), line_y)

    def test_f2_ammo_capacity_none_tiers_and_max(self):
        """F2: Quiver 'None' -> capacity 0, Max leaves 0 and doesn't own bow; bomb bag 'None' -> 0; existing tiers unchanged."""
        # Quiver None -> capacity 0
        self.editor.equip_vars["quiver"].set("None")
        self.assertEqual(self.menu.get_ammo_capacity("arrows"), 0)

        # Max on arrows leaves 0 and does not set the bow var
        self.editor.special_item_vars[0x938D56BF][0].set(False)
        self.editor.ammo_vars["arrows"][0].set("0")
        self.menu.set_quantity_max("arrows")
        self.assertEqual(self.editor.ammo_vars["arrows"][0].get(), "0")
        self.assertFalse(
            self.editor.special_item_vars[0x938D56BF][0].get(),
            "Max on arrows with Quiver None must leave Fairy Bow unowned"
        )

        # change_quantity (+1) leaves 0 and does not set bow var
        self.menu.change_quantity("arrows", 1)
        self.assertEqual(self.editor.ammo_vars["arrows"][0].get(), "0")
        self.assertFalse(
            self.editor.special_item_vars[0x938D56BF][0].get(),
            "+1 on arrows with Quiver None must not own Fairy Bow"
        )

        # Bomb bag None -> capacity 0, Max leaves 0
        self.editor.equip_vars["bomb_bag"].set("None")
        self.assertEqual(self.menu.get_ammo_capacity("bombs"), 0)
        self.editor.ammo_vars["bombs"][0].set("0")
        self.menu.set_quantity_max("bombs")
        self.assertEqual(self.editor.ammo_vars["bombs"][0].get(), "0")

        # Existing tiers unchanged
        # Quivers: 30, 40, 50
        self.editor.equip_vars["quiver"].set("Quiver (30)")
        self.assertEqual(self.menu.get_ammo_capacity("arrows"), 30)
        self.editor.equip_vars["quiver"].set("Big Quiver (40)")
        self.assertEqual(self.menu.get_ammo_capacity("arrows"), 40)
        self.editor.equip_vars["quiver"].set("Biggest Quiver (50)")
        self.assertEqual(self.menu.get_ammo_capacity("arrows"), 50)

        # Bomb bags: 20, 30, 40
        self.editor.equip_vars["bomb_bag"].set("Bomb Bag (20)")
        self.assertEqual(self.menu.get_ammo_capacity("bombs"), 20)
        self.editor.equip_vars["bomb_bag"].set("Big Bomb Bag (30)")
        self.assertEqual(self.menu.get_ammo_capacity("bombs"), 30)
        self.editor.equip_vars["bomb_bag"].set("Biggest Bomb Bag (40)")
        self.assertEqual(self.menu.get_ammo_capacity("bombs"), 40)

        # Sticks: 10, 20, 30
        self.editor.equip_vars["stick_bag"].set("Deku-Stick Bag (10)")
        self.assertEqual(self.menu.get_ammo_capacity("sticks"), 10)
        self.editor.equip_vars["stick_bag"].set("Big Deku-Stick Bag (20)")
        self.assertEqual(self.menu.get_ammo_capacity("sticks"), 20)
        self.editor.equip_vars["stick_bag"].set("Biggest Deku-Stick Bag (30)")
        self.assertEqual(self.menu.get_ammo_capacity("sticks"), 30)

        # Nuts: 20, 30, 40
        self.editor.equip_vars["nut_bag"].set("Deku-Nut Bag (20)")
        self.assertEqual(self.menu.get_ammo_capacity("nuts"), 20)
        self.editor.equip_vars["nut_bag"].set("Big Deku-Nut Bag (30)")
        self.assertEqual(self.menu.get_ammo_capacity("nuts"), 30)
        self.editor.equip_vars["nut_bag"].set("Biggest Deku-Nut Bag (40)")
        self.assertEqual(self.menu.get_ammo_capacity("nuts"), 40)

        # Seeds: 30, 40, 50
        self.editor.equip_vars["bullet_bag"].set("Deku-Seed Bag (30)")
        self.assertEqual(self.menu.get_ammo_capacity("seeds"), 30)
        self.editor.equip_vars["bullet_bag"].set("Big Deku-Seed Bag (40)")
        self.assertEqual(self.menu.get_ammo_capacity("seeds"), 40)
        self.editor.equip_vars["bullet_bag"].set("Biggest Deku-Seed Bag (50)")
        self.assertEqual(self.menu.get_ammo_capacity("seeds"), 50)

    def test_f3_safe_int_with_non_numeric_var(self):
        """F3: A var holding non-numeric text like 'abc' does not raise and change_quantity(+1) treats it as 0."""
        # 1. Ammo var holding 'abc' -> change_quantity(+1) treats it as 0 -> sets to 1
        self.editor.ammo_vars["bombs"][0].set("abc")
        self.menu.change_quantity("bombs", 1)
        self.assertEqual(self.editor.ammo_vars["bombs"][0].get(), "1")

        # 2. Tokens var holding 'abc'
        self.editor.v_tokens.set("abc")
        self.menu.change_quantity("tokens", 1)
        self.assertEqual(self.editor.v_tokens.get(), "1")

        # 3. Heart pieces var holding 'abc'
        self.editor.v_heart_pieces_total.set("abc")
        self.menu.change_quantity("heart_pieces", 1)
        self.assertEqual(self.editor.v_heart_pieces_total.get(), "1")

        # 4. safe_int direct sanity checks
        self.assertEqual(safe_int("abc"), 0)
        self.assertEqual(safe_int("abc", default=5), 5)
        self.assertEqual(safe_int(" 42 "), 42)
        self.assertEqual(safe_int("", default=10), 10)

    def test_f1_refresh_pause_view_if_shown_hook(self):
        """F1: _refresh_pause_view_if_shown refreshes when frame is mapped and not when unmapped."""
        from oot_save_editor import OOTEditor

        class FakeTextureFrame:
            def __init__(self, mapped):
                self._mapped = mapped
                self.refreshed = False

            def winfo_ismapped(self):
                return self._mapped

            def refresh_visuals(self):
                self.refreshed = True

        class FakeEditor:
            def __init__(self, frame):
                self.texture_view_frame = frame

            def _refresh_pause_view_if_shown(self):
                return OOTEditor._refresh_pause_view_if_shown(self)

        # Mapped frame -> refreshed
        frame_mapped = FakeTextureFrame(mapped=True)
        ed_mapped = FakeEditor(frame_mapped)
        ed_mapped._refresh_pause_view_if_shown()
        self.assertTrue(frame_mapped.refreshed, "Must call refresh_visuals when frame is mapped")

        # Unmapped frame -> not refreshed
        frame_unmapped = FakeTextureFrame(mapped=False)
        ed_unmapped = FakeEditor(frame_unmapped)
        ed_unmapped._refresh_pause_view_if_shown()
        self.assertFalse(frame_unmapped.refreshed, "Must not call refresh_visuals when frame is unmapped")

        # None frame -> does not raise
        ed_none = FakeEditor(None)
        ed_none._refresh_pause_view_if_shown()

    def test_layout_loads_every_slot_and_scaling_halves_positions(self):
        """Layout loads: every slot id in pause_menu_layout.json Items/Equipment/Collection gets a canvas item;
        scaling 1920x1080 -> 960x540 halves positions."""
        for page in ("Collection", "Equipment", "Items"):
            self.menu.show_subscreen(page)
            # Reference size 1920x1080
            self.menu.set_canvas_size(1920, 1080)
            page_slots = PAUSE_MENU_LAYOUT["plus_menu"]["pages"][page]["slots"]
            coords_1920 = {}
            for slot in page_slots:
                items = self.menu.canvas.find_withtag(slot["id"])
                self.assertTrue(len(items) > 0, f"Slot {slot['id']} must get a canvas item")
                if slot.get("pos"):
                    coords = self.menu.canvas.coords(items[0])
                    coords_1920[slot["id"]] = coords

            # Half size 960x540
            self.menu.set_canvas_size(960, 540)
            for slot in page_slots:
                if slot.get("pos"):
                    items_960 = self.menu.canvas.find_withtag(slot["id"])
                    self.assertTrue(len(items_960) > 0)
                    coords = self.menu.canvas.coords(items_960[0])
                    c1920 = coords_1920[slot["id"]]
                    # First coordinate (x) must be halved
                    self.assertAlmostEqual(coords[0], c1920[0] / 2.0, delta=2.0,
                        msg=f"Slot {slot['id']} x position must be halved: {coords[0]} vs {c1920[0]/2.0}")
                    # Second coordinate (y) must be halved
                    self.assertAlmostEqual(coords[1], c1920[1] / 2.0, delta=2.0,
                        msg=f"Slot {slot['id']} y position must be halved: {coords[1]} vs {c1920[1]/2.0}")

    def test_tier_choice_highest_owned_tier(self):
        """Tier choice: wallet tiers -> highest owned tier actor chosen."""
        self.menu.show_subscreen("Collection")
        wallet_slot = next(s for s in PAUSE_MENU_LAYOUT["plus_menu"]["pages"]["Collection"]["slots"] if s["id"] == "Pa_Bag_00")

        # 1. Child wallet (99) -> Item_Wallet_Small
        self.editor.equip_vars["wallet"].set("Default Child's Wallet (99)")
        actor, owned, _, _, _, _ = self.menu.get_slot_state(wallet_slot)
        self.assertEqual(actor, "Item_Wallet_Small")
        self.assertTrue(owned)

        # 2. Adult's wallet (200) -> Item_Wallet_Medium
        self.editor.equip_vars["wallet"].set("Adult's Wallet (200)")
        actor, owned, _, _, _, _ = self.menu.get_slot_state(wallet_slot)
        self.assertEqual(actor, "Item_Wallet_Medium")
        self.assertTrue(owned)

        # 3. Giant's wallet (500) -> Item_Wallet_Large
        self.editor.equip_vars["wallet"].set("Giant's Wallet (500)")
        actor, owned, _, _, _, _ = self.menu.get_slot_state(wallet_slot)
        self.assertEqual(actor, "Item_Wallet_Large")
        self.assertTrue(owned)

        # 4. Tycoon's wallet (1000) -> Item_Wallet_Large
        self.editor.equip_vars["wallet"].set("Tycoon's Wallet (1000)")
        actor, owned, _, _, _, _ = self.menu.get_slot_state(wallet_slot)
        self.assertEqual(actor, "Item_Wallet_Large")
        self.assertTrue(owned)

        # 5. Scale tiers: Silver vs Gold
        scale_slot = next(s for s in PAUSE_MENU_LAYOUT["plus_menu"]["pages"]["Collection"]["slots"] if s["id"] == "Pa_Scales_00")
        self.editor.equip_vars["scale"].set("Silver Scale (6 meters)")
        actor, owned, _, _, _, _ = self.menu.get_slot_state(scale_slot)
        self.assertEqual(actor, "Item_Scale_Silver")
        self.editor.equip_vars["scale"].set("Golden Scale (8 meters)")
        actor, owned, _, _, _, _ = self.menu.get_slot_state(scale_slot)
        self.assertEqual(actor, "Item_Scale_Gold")

        # 6. Hookshot tiers: Hookshot vs Longshot
        self.menu.show_subscreen("Items")
        hook_slot = next(s for s in PAUSE_MENU_LAYOUT["plus_menu"]["pages"]["Items"]["slots"] if s["id"] == "Pa_ItemIcon_07")
        self.editor.hookshot_var.set("Hookshot")
        actor, owned, _, _, _, _ = self.menu.get_slot_state(hook_slot)
        self.assertEqual(actor, "Item_Hookshot")
        self.editor.hookshot_var.set("Longshot")
        actor, owned, _, _, _, _ = self.menu.get_slot_state(hook_slot)
        self.assertEqual(actor, "Item_Longshot")

    def test_icon_fallback_without_oot_game_assets(self):
        """Icon fallback: with oot_game_assets missing, slots still render (generated icons) and no exception."""
        import oot_pause_menu
        saved_assets = getattr(oot_pause_menu, "oot_game_assets", None)
        try:
            oot_pause_menu.oot_game_assets = None
            for page in ("Collection", "Equipment", "Items"):
                self.menu.show_subscreen(page)
                self.menu.refresh_visuals()
                self.assertTrue(len(self.menu.canvas.find_withtag("slot")) > 0)
        finally:
            oot_pause_menu.oot_game_assets = saved_assets

    def test_clicking_select_then_activate_toggles_and_cycles(self):
        """Clicking select then activate toggles the same editor var as before for a sample item (e.g. Boomerang) and a bottle cycles."""
        self.menu.show_subscreen("Items")
        self.menu.set_canvas_size(1920, 1080)

        # 1. Boomerang slot (Pa_ItemIcon_02)
        boom_slot = next(s for s in PAUSE_MENU_LAYOUT["plus_menu"]["pages"]["Items"]["slots"] if s["id"] == "Pa_ItemIcon_02")
        bx, by = self.menu.to_canvas(boom_slot["pos"][0], boom_slot["pos"][1])

        self.menu.selected_slot_id = None
        ev = DummyEvent(x=bx, y=by)

        # Click 1: selects slot
        self.menu._on_canvas_click(ev)
        self.assertEqual(self.menu.selected_slot_id, "Pa_ItemIcon_02")

        # Click 2: activates slot (toggles Boomerang var)
        cur_val = self.editor.special_item_vars[0xA1D76D31][0].get()
        self.menu._on_canvas_click(ev)
        self.assertEqual(self.editor.special_item_vars[0xA1D76D31][0].get(), not cur_val)

        # Click 3: toggles back
        self.menu._on_canvas_click(ev)
        self.assertEqual(self.editor.special_item_vars[0xA1D76D31][0].get(), cur_val)

        # 2. Bottle 1 slot (Pa_ItemIcon_17)
        bot_slot = next(s for s in PAUSE_MENU_LAYOUT["plus_menu"]["pages"]["Items"]["slots"] if s["id"] == "Pa_ItemIcon_17")
        bot_x, bot_y = self.menu.to_canvas(bot_slot["pos"][0], bot_slot["pos"][1])
        ev_bot = DummyEvent(x=bot_x, y=bot_y)

        self.editor.bottle_vars["bottle_1"].set("(Not Acquired / Locked)")
        # Click 1: selects bottle
        self.menu._on_canvas_click(ev_bot)
        self.assertEqual(self.menu.selected_slot_id, "Pa_ItemIcon_17")

        # Click 2: cycles content from locked to Empty Bottle
        self.menu._on_canvas_click(ev_bot)
        self.assertEqual(self.editor.bottle_vars["bottle_1"].get(), "Empty Bottle")

        # Click 3: cycles content to Red Potion
        self.menu._on_canvas_click(ev_bot)
        self.assertEqual(self.editor.bottle_vars["bottle_1"].get(), "Red Potion")

    def test_wheel_clamps_to_editor_ammo_capacity(self):
        """Wheel clamps strictly to editor.ammo_capacity."""
        self.menu.show_subscreen("Items")
        self.menu.set_canvas_size(1920, 1080)

        sticks_slot = next(s for s in PAUSE_MENU_LAYOUT["plus_menu"]["pages"]["Items"]["slots"] if s["id"] == "Pa_ItemIcon_00")
        sx, sy = self.menu.to_canvas(sticks_slot["pos"][0], sticks_slot["pos"][1])

        self.editor.equip_vars["stick_bag"].set("Deku-Stick Bag (10)")
        self.editor.ammo_vars["sticks"][0].set("0")
        max_cap = self.editor.ammo_capacity("sticks")
        self.assertEqual(max_cap, 10)

        # Wheel up by +1
        ev_up = DummyEvent(delta=120, state=0, x=sx, y=sy)
        self.menu._on_canvas_wheel(ev_up)
        self.assertEqual(self.editor.ammo_vars["sticks"][0].get(), "1")

        # Wheel up multiple times exceeding capacity clamps at max_cap (10)
        for _ in range(15):
            self.menu._on_canvas_wheel(ev_up)
        self.assertEqual(self.editor.ammo_vars["sticks"][0].get(), "10")

        # Shift+Wheel down (-10) clamps to 0
        ev_shift_down = DummyEvent(delta=-120, state=0x0001, x=sx, y=sy)
        self.menu._on_canvas_wheel(ev_shift_down)
        self.assertEqual(self.editor.ammo_vars["sticks"][0].get(), "0")

        # Wheel down at 0 stays at 0
        ev_down = DummyEvent(delta=-120, state=0, x=sx, y=sy)
        self.menu._on_canvas_wheel(ev_down)
        self.assertEqual(self.editor.ammo_vars["sticks"][0].get(), "0")

    def test_age_inference_and_dimming(self):
        """Age inference: equip_vars['sword'] = 'Master Sword' -> an 'era': 'C' slot is dimmed and an 'A' slot is not;
        'Kokiri Sword' -> the reverse; missing sword var -> nothing dimmed."""
        c_slot = {"id": "test_c", "era": "C"}
        a_slot = {"id": "test_a", "era": "A"}
        ca_slot = {"id": "test_ca", "era": "CA"}

        # 1. Master Sword -> Adult
        self.editor.equip_vars["sword"].set("Master Sword")
        _, _, _, dimmed_c, _, _ = self.menu.get_slot_state(c_slot)
        _, _, _, dimmed_a, _, _ = self.menu.get_slot_state(a_slot)
        _, _, _, dimmed_ca, _, _ = self.menu.get_slot_state(ca_slot)
        self.assertTrue(dimmed_c, "Child item must be dimmed for adult (Master Sword)")
        self.assertFalse(dimmed_a, "Adult item must not be dimmed for adult (Master Sword)")
        self.assertFalse(dimmed_ca, "CA item must never be dimmed")

        # Also support raw string assignment
        self.editor.equip_vars["sword"] = "Biggoron's Sword"
        _, _, _, dimmed_c, _, _ = self.menu.get_slot_state(c_slot)
        _, _, _, dimmed_a, _, _ = self.menu.get_slot_state(a_slot)
        self.assertTrue(dimmed_c, "Child item must be dimmed for Biggoron's Sword")
        self.assertFalse(dimmed_a, "Adult item must not be dimmed for Biggoron's Sword")

        # 2. Kokiri Sword -> Child
        self.editor.equip_vars["sword"] = tk.StringVar(value="Kokiri Sword")
        _, _, _, dimmed_c, _, _ = self.menu.get_slot_state(c_slot)
        _, _, _, dimmed_a, _, _ = self.menu.get_slot_state(a_slot)
        self.assertFalse(dimmed_c, "Child item must not be dimmed for child (Kokiri Sword)")
        self.assertTrue(dimmed_a, "Adult item must be dimmed for child (Kokiri Sword)")

        # 3. Missing sword var -> nothing dimmed
        del self.editor.equip_vars["sword"]
        _, _, _, dimmed_c, _, _ = self.menu.get_slot_state(c_slot)
        _, _, _, dimmed_a, _, _ = self.menu.get_slot_state(a_slot)
        self.assertFalse(dimmed_c, "Nothing dimmed when sword var is missing")
        self.assertFalse(dimmed_a, "Nothing dimmed when sword var is missing")

    def test_actor_text_fallback_has_no_captions_and_preview_draws_no_caption_when_assets_missing(self):
        """Fallback text: for every value in ACTOR_TEXT_FALLBACK, it is a plain str (a name, no caption);
        with oot_game_assets unavailable the preview draws no caption text item."""
        import oot_pause_menu
        self.assertTrue(len(ACTOR_TEXT_FALLBACK) > 0)
        for actor, name in ACTOR_TEXT_FALLBACK.items():
            self.assertIsInstance(
                name, str,
                f"ACTOR_TEXT_FALLBACK[{actor!r}] must be a plain str name, got {type(name)}"
            )

        saved_assets = getattr(oot_pause_menu, "oot_game_assets", None)
        try:
            oot_pause_menu.oot_game_assets = None
            self.menu.show_subscreen("Items")
            self.menu.set_canvas_size(1920, 1080)
            self.menu.refresh_visuals()

            caption_items = self.menu.canvas.find_withtag("preview_caption")
            self.assertEqual(len(caption_items), 0, "No caption text item must be drawn when oot_game_assets is unavailable")
        finally:
            oot_pause_menu.oot_game_assets = saved_assets

    def test_heart_piece_slot_quarters_filled(self):
        """Heart piece: with v_heart_pieces_held = 2 the canvas has exactly 2 filled quarter polygons tagged for the heart slot."""
        self.menu.show_subscreen("Collection")
        self.menu.set_canvas_size(1920, 1080)

        # 2 held pieces -> 2 filled quarter polygons tagged 'heart_quarter_filled'
        self.editor.v_heart_pieces_held.set("2")
        self.menu.refresh_visuals()

        filled_quarters = self.menu.canvas.find_withtag("heart_quarter_filled")
        self.assertEqual(len(filled_quarters), 2, f"Expected 2 filled quarter polygons for 2 pieces, got {len(filled_quarters)}")

        # 3 held pieces -> 3 filled quarter polygons
        self.editor.v_heart_pieces_held.set("3")
        self.menu.refresh_visuals()
        self.assertEqual(len(self.menu.canvas.find_withtag("heart_quarter_filled")), 3)

        # 0 held pieces -> 0 filled quarter polygons
        self.editor.v_heart_pieces_held.set("0")
        self.menu.refresh_visuals()
        self.assertEqual(len(self.menu.canvas.find_withtag("heart_quarter_filled")), 0)

    def test_preview_layout_at_1400x950_no_bbox_intersection(self):
        """At a 1400x950 canvas, the bboxes of preview_name and preview_caption do not intersect,
        and preview_divider lies between them (Items page, with a stub item_text returning a long caption containing '\n')."""
        import oot_pause_menu

        class StubGameAssets:
            @staticmethod
            def item_text(actor):
                return (
                    "Deku Stick",
                    "A long wooden stick that can be set\nablaze or used to give light.\n"
                    "It breaks easily when used as a weapon,\nso carry plenty of them!\n\n"
                    "Found by defeating Deku Babas or purchased in shops across Hyrule."
                )

        saved_assets = getattr(oot_pause_menu, "oot_game_assets", None)
        try:
            oot_pause_menu.oot_game_assets = StubGameAssets()
            self.menu.show_subscreen("Items")
            self.menu.set_canvas_size(1400, 950)
            self.menu.refresh_visuals()

            bbox_name = self.menu.canvas.bbox("preview_name")
            bbox_div = self.menu.canvas.bbox("preview_divider")
            bbox_cap = self.menu.canvas.bbox("preview_caption")

            self.assertIsNotNone(bbox_name, "preview_name must have a bounding box")
            self.assertIsNotNone(bbox_div, "preview_divider must have a bounding box")
            self.assertIsNotNone(bbox_cap, "preview_caption must have a bounding box")

            # Check that preview_name and preview_caption do not intersect
            self.assertLess(
                bbox_name[3], bbox_cap[1],
                f"preview_name bottom ({bbox_name[3]}) must be above preview_caption top ({bbox_cap[1]})"
            )

            # Check that preview_divider lies between them
            self.assertLessEqual(
                bbox_name[3], bbox_div[1],
                f"preview_name bottom ({bbox_name[3]}) must be <= divider top ({bbox_div[1]})"
            )
            self.assertLessEqual(
                bbox_div[3], bbox_cap[1],
                f"divider bottom ({bbox_div[3]}) must be <= caption top ({bbox_cap[1]})"
            )
        finally:
            oot_pause_menu.oot_game_assets = saved_assets

    def test_tab_text_bboxes_do_not_overlap(self):
        """Check that the four tab text items' bboxes do not overlap each other."""
        for width, height in ((1400, 950), (1920, 1080)):
            self.menu.set_canvas_size(width, height)
            self.menu.refresh_visuals()

            tabs = ["Collection", "Equipment", "Items", "System"]
            bboxes = []
            for tname in tabs:
                tag = f"tab_{tname}"
                bbox = self.menu.canvas.bbox(tag)
                self.assertIsNotNone(bbox, f"Tab '{tname}' must have a bbox on canvas at {width}x{height}")
                bboxes.append((tname, bbox))

            # Verify no two tab text bboxes overlap
            for i in range(len(bboxes)):
                t_i, box_i = bboxes[i]
                for j in range(i + 1, len(bboxes)):
                    t_j, box_j = bboxes[j]
                    no_overlap = (box_i[2] <= box_j[0]) or (box_j[2] <= box_i[0]) or (box_i[3] <= box_j[1]) or (box_j[3] <= box_i[1])
                    self.assertTrue(
                        no_overlap,
                        f"Tabs '{t_i}' {box_i} and '{t_j}' {box_j} overlap at {width}x{height}"
                    )

    def test_font_helper_returns_negative_size(self):
        """Check that _font returns a negative size (pixel sizing in Tkinter)."""
        import oot_pause_menu

        # Module-level helper
        f_mod = oot_pause_menu._font(30)
        self.assertIsInstance(f_mod, tuple)
        self.assertLess(f_mod[1], 0, f"_font module helper size must be negative, got {f_mod[1]}")

        # Instance helper on menu frame
        f_inst = self.menu._font(34, "bold")
        self.assertIsInstance(f_inst, tuple)
        self.assertLess(f_inst[1], 0, f"_font frame helper size must be negative, got {f_inst[1]}")
        self.assertEqual(f_inst[2], "bold")

        # Standard reference sizes: 11, 20, 22, 28, 30, 34, 44, 52, 56
        for px in (11, 20, 22, 28, 30, 34, 44, 52, 56):
            f = self.menu._font(px)
            self.assertLess(f[1], 0, f"Font size for {px}px at ref must be negative, got {f[1]}")

    def test_caption_unwrap_preserves_paragraphs_and_collapses_single_newlines(self):
        """T3: unwrap_caption replaces single newlines with space, collapses spaces, and preserves blank line paragraph breaks."""
        from oot_pause_menu import unwrap_caption

        text = "can be set\nablaze or\nused to give..."
        self.assertEqual(unwrap_caption(text), "can be set ablaze or used to give...")

        text_multi = "Line 1\nLine 2\n\nParagraph 2\nwith   spaces."
        self.assertEqual(unwrap_caption(text_multi), "Line 1 Line 2\n\nParagraph 2 with spaces.")

    def test_no_global_key_bindings_and_handlers_inert_when_hidden(self):
        """R1 (deterministic): no bind_all bindings, and key handlers do nothing while the view is hidden.

        Generated key events are not delivered to a withdrawn test window, so check the two
        guards directly instead of relying on event_generate.
        """
        for seq in ("<Key-a>", "<Key-A>", "<a>", "<space>", "<Return>", "<Key-q>", "<Key-e>",
                    "<Escape>", "<Key-b>", "<Key-Left>", "<Key-Right>", "<Key-Up>", "<Key-Down>"):
            self.assertEqual(self.root.bind_all(seq), "", f"global binding left for {seq}")

        self.menu.show_subscreen(1)  # Equipment
        self.menu.selected_slot_id = "Pa_Epuipment_01"  # Master Sword slot
        self.menu.pack_forget()
        self.root.update_idletasks()
        self.assertFalse(self.menu.winfo_ismapped())
        before = self.editor.owned_swords["Master Sword"].get()
        page = self.menu.active_subscreen
        self.menu._on_key_activate()
        self.menu._on_key_cycle_next()
        self.assertEqual(self.editor.owned_swords["Master Sword"].get(), before)
        self.assertEqual(self.menu.active_subscreen, page)

    def test_keyboard_bindings_scoped_to_pause_view(self):
        """R1: Keyboard shortcuts must not leak to the main editor when pause view is unmapped."""
        self.menu.show_subscreen(1)  # Equipment
        self.menu.selected_slot_id = "Pa_Epuipment_01"  # Master Sword slot
        self.menu.pack(fill="both", expand=True)
        self.root.update_idletasks()

        # Switch to standard view (pack_forget pause frame)
        self.menu.pack_forget()
        self.root.update_idletasks()

        entry = ttk.Entry(self.root)
        entry.pack()
        entry.focus_set()
        self.root.update_idletasks()

        initial_master = self.editor.owned_swords["Master Sword"].get()
        initial_subscreen = self.menu.active_subscreen

        # Type 'a' in the entry and root
        entry.event_generate("<Key-a>")
        self.root.update_idletasks()
        self.root.event_generate("<Key-a>")
        self.root.update_idletasks()

        # Type 'q' and 'e'
        entry.event_generate("<Key-q>")
        self.root.update_idletasks()
        self.root.event_generate("<Key-e>")
        self.root.update_idletasks()

        # Assert no editor variable changed and subscreen did not change
        self.assertEqual(self.editor.owned_swords["Master Sword"].get(), initial_master)
        self.assertEqual(self.menu.active_subscreen, initial_subscreen)
        entry.destroy()

    def test_trade_item_routing_and_choices(self):
        """R2: Every value assigned to child_quest_var is in CHILD_QUEST_CHOICES and adult_trade_var in ADULT_TRADE_CHOICES."""
        from oot_pause_menu import CHILD_QUEST_CHOICES, ADULT_TRADE_CHOICES

        # 1. Right-click menu commands
        menu = self.menu._on_child_trade_right_click()
        end_idx = menu.index("end")
        self.assertIsNotNone(end_idx)

        for i in range(end_idx + 1):
            if menu.type(i) == "command":
                menu.invoke(i)
                cq = self.editor.child_quest_var.get()
                at = self.editor.adult_trade_var.get()
                self.assertIn(cq, CHILD_QUEST_CHOICES)
                self.assertIn(at, ADULT_TRADE_CHOICES)

        # 2. Left-click activate cycling for child
        self.editor.equip_vars["sword"].set("Kokiri Sword")
        self.editor.child_quest_var.set("None")
        self.editor.adult_trade_var.set("None")

        for _ in range(len(CHILD_QUEST_CHOICES) * 2):
            self.menu._on_inv_slot_click("child_trade")
            self.assertIn(self.editor.child_quest_var.get(), CHILD_QUEST_CHOICES)
            self.assertEqual(self.editor.adult_trade_var.get(), "None")

        # 3. Left-click activate cycling for adult
        self.editor.equip_vars["sword"].set("Master Sword")
        self.editor.child_quest_var.set("None")
        self.editor.adult_trade_var.set("None")

        for _ in range(len(ADULT_TRADE_CHOICES) * 2):
            self.menu._on_inv_slot_click("child_trade")
            self.assertIn(self.editor.adult_trade_var.get(), ADULT_TRADE_CHOICES)
            self.assertEqual(self.editor.child_quest_var.get(), "None")

    def test_trade_item_display_priority(self):
        """R2 Display: verify inferred age and display priority for Pa_ItemIcon_23."""
        trade_slot = next(s for s in PAUSE_MENU_LAYOUT["plus_menu"]["pages"]["Items"]["slots"] if s["id"] == "Pa_ItemIcon_23")

        # Adult Link + adult trade item set -> shows adult item
        self.editor.equip_vars["sword"].set("Master Sword")
        self.editor.adult_trade_var.set("Pocket Egg")
        self.editor.child_quest_var.set("Weird Egg")
        actor, owned, _, _, _, _ = self.menu.get_slot_state(trade_slot)
        self.assertEqual(actor, "Item_PocketEgg")
        self.assertTrue(owned)

        # Adult Link + adult trade "None" + child quest set -> shows child item
        self.editor.adult_trade_var.set("None")
        actor, owned, _, _, _, _ = self.menu.get_slot_state(trade_slot)
        self.assertEqual(actor, "Item_WeirdEgg")
        self.assertTrue(owned)

        # Child Link + child quest set -> shows child item
        self.editor.equip_vars["sword"].set("Kokiri Sword")
        self.editor.child_quest_var.set("Zelda's Letter")
        self.editor.adult_trade_var.set("Cojiro")
        actor, owned, _, _, _, _ = self.menu.get_slot_state(trade_slot)
        self.assertEqual(actor, "Item_ZeldaLetter")
        self.assertTrue(owned)

        # Child Link + child quest "None" + adult trade set -> shows adult item
        self.editor.child_quest_var.set("None")
        actor, owned, _, _, _, _ = self.menu.get_slot_state(trade_slot)
        self.assertEqual(actor, "Item_CojiroCucco")
        self.assertTrue(owned)

        # Both "None" -> empty
        self.editor.adult_trade_var.set("None")
        self.editor.child_quest_var.set("None")
        actor, owned, _, _, _, _ = self.menu.get_slot_state(trade_slot)
        # Unowned slots keep their first listed actor for the preview; what matters is "not owned".
        self.assertEqual(actor, "Item_ClaimCheck")
        self.assertFalse(owned)

    def test_photoimage_cache_bounded_on_resize(self):
        """R3: PhotoImage cache must not grow unbounded across multiple resizes."""
        self.menu.show_subscreen("Items")
        page_slots = PAUSE_MENU_LAYOUT["plus_menu"]["pages"]["Items"]["slots"]
        slot_count = len(page_slots)

        sizes = [
            (800, 600), (960, 540), (1024, 768), (1280, 720), (1366, 768),
            (1440, 900), (1600, 900), (1920, 1080), (1200, 800), (1000, 700),
        ]
        self.menu.set_canvas_size(*sizes[0])
        first_len = len(self.menu.textures.cache)
        self.assertGreater(first_len, 0, "test needs at least one cached icon to be meaningful")
        for w, h in sizes:
            self.menu.set_canvas_size(w, h)
            cache_len = len(self.menu.textures.cache)
            self.assertLess(cache_len, 2 * slot_count, f"Cache size {cache_len} exceeded 2x slot count ({2 * slot_count}) at ({w}, {h})")
        # Coming back to the first size must not leave icons cached for the other sizes.
        self.menu.set_canvas_size(*sizes[0])
        self.assertEqual(len(self.menu.textures.cache), first_len)

    def test_rutos_letter_warning_callback_called(self):
        """R4: _on_bottle_selected(n) must be called when setting bottles via cycle or menu."""
        self.editor.bottle_selected_calls.clear()

        # Cycle bottle_1
        self.menu._on_inv_slot_click("bottle_1")
        self.assertIn(1, self.editor.bottle_selected_calls)

        # Set bottle_2 via menu helper
        self.menu._set_bottle_choice("bottle_2", "Ruto's Letter")
        self.assertIn(2, self.editor.bottle_selected_calls)

    def test_slot_icon_era_dimming_passed_to_get_actor_icon(self):
        """R5: get_actor_icon is called with dimmed=True for owned other-era slot and dimmed=False for same era."""
        calls = []
        original_get_actor_icon = self.menu.textures.get_actor_icon

        def spy_get_actor_icon(actor, size=(64, 64), dimmed=False):
            calls.append((actor, dimmed))
            return original_get_actor_icon(actor, size=size, dimmed=dimmed)

        self.menu.textures.get_actor_icon = spy_get_actor_icon
        try:
            self.menu.show_subscreen("Equipment")
            self.menu.set_canvas_size(1920, 1080)

            # Adult Link: Master Sword equipped, Kokiri Sword (era C) is owned
            self.editor.equip_vars["sword"].set("Master Sword")
            self.editor.owned_swords["Kokiri Sword"].set(True)
            calls.clear()
            self.menu.refresh_visuals()

            kokiri_calls = [c for c in calls if c[0] == "Weapon_Sword_Kokiri"]
            self.assertTrue(len(kokiri_calls) > 0)
            self.assertTrue(any(c[1] is True for c in kokiri_calls), "Expected dimmed=True for Kokiri Sword as adult")

            # Child Link: Kokiri Sword equipped
            self.editor.equip_vars["sword"].set("Kokiri Sword")
            calls.clear()
            self.menu.refresh_visuals()

            kokiri_calls = [c for c in calls if c[0] == "Weapon_Sword_Kokiri"]
            self.assertTrue(len(kokiri_calls) > 0)
            self.assertTrue(all(c[1] is False for c in kokiri_calls), "Expected dimmed=False for Kokiri Sword as child")
        finally:
            self.menu.textures.get_actor_icon = original_get_actor_icon

    def test_menu_switch_keys_chips_and_tab_cycling(self):
        """Check '-' key/chip switches to Key Items, q/e cycle minus tabs, '+' returns to Collection."""
        self.menu.show_subscreen("Collection")
        self.assertEqual(self.menu.menu_mode, "plus")
        self.assertEqual(self.menu.current_page_name(), "Collection")

        # Trigger minus menu via key handler
        self.menu._on_key_menu_minus()  # hidden view: must be inert
        self.assertEqual(self.menu.menu_mode, "plus")
        self.menu.set_menu_mode("minus")
        self.assertEqual(self.menu.menu_mode, "minus")
        self.assertEqual(self.menu.current_page_name(), "Key Items")

        # Cycle tabs with e / q
        self.menu.cycle_subscreen(1)
        self.assertEqual(self.menu.current_page_name(), "Threads of Time")
        self.menu.cycle_subscreen(1)
        self.assertEqual(self.menu.current_page_name(), "Song Book")
        self.menu.cycle_subscreen(1)
        self.assertEqual(self.menu.current_page_name(), "Key Items")
        self.menu.cycle_subscreen(-1)
        self.assertEqual(self.menu.current_page_name(), "Song Book")

        # Trigger plus menu via key handler
        self.menu.set_menu_mode("plus")
        self.assertEqual(self.menu.menu_mode, "plus")
        self.assertEqual(self.menu.current_page_name(), "Collection")

        # Test chip click to switch to minus menu
        chip_minus = getattr(self.menu, "_chip_positions", {}).get("minus")
        self.assertIsNotNone(chip_minus)
        mx, my, _ = chip_minus
        ev_click_m = DummyEvent(x=mx, y=my)
        self.menu._on_canvas_click(ev_click_m)
        self.assertEqual(self.menu.menu_mode, "minus")
        self.assertEqual(self.menu.current_page_name(), "Key Items")

        # Test chip click to switch back to plus menu
        chip_plus = getattr(self.menu, "_chip_positions", {}).get("plus")
        self.assertIsNotNone(chip_plus)
        px, py, _ = chip_plus
        ev_click_p = DummyEvent(x=px, y=py)
        self.menu._on_canvas_click(ev_click_p)
        self.assertEqual(self.menu.menu_mode, "plus")
        self.assertEqual(self.menu.current_page_name(), "Collection")

    def test_key_items_canvas_tags_and_toggle(self):
        """Check all medallions/stones in json get tagged canvas items and toggle quest_vars."""
        self.menu.show_subscreen("Key Items")
        self.assertEqual(self.menu.menu_mode, "minus")

        expected_ids = [
            "N_Info_03", "N_Info_04", "N_Info_05", "N_Info_06", "N_Info_08", "N_Info_07",
            "N_Info_00", "N_Info_01", "N_Info_02"
        ]
        for item_id in expected_ids:
            items = self.menu.canvas.find_withtag(item_id)
            self.assertTrue(len(items) > 0, f"Expected canvas items tagged with {item_id}")

        import oot_save_editor
        name_to_hash = {name: h for name, h, _ in oot_save_editor.STONES_MEDALLIONS}
        socket_table = [
            ("N_Info_00", "Kokiri's Emerald"),
            ("N_Info_01", "Goron's Ruby"),
            ("N_Info_02", "Zora's Sapphire"),
            ("N_Info_03", "Light Medallion"),
            ("N_Info_04", "Forest Medallion"),
            ("N_Info_05", "Fire Medallion"),
            ("N_Info_06", "Water Medallion"),
            ("N_Info_07", "Spirit Medallion"),
            ("N_Info_08", "Shadow Medallion"),
        ]

        for sock_id, name in socket_table:
            expected_hash = name_to_hash[name]
            socket_data = self.menu._key_item_sockets[sock_id]
            self.assertEqual(socket_data["hash"], expected_hash)

            # Ensure sock_id is not already selected before testing click-to-select
            if self.menu.selected_key_item_id == sock_id:
                other_id = "N_Info_08" if sock_id != "N_Info_08" else "N_Info_00"
                self.menu.selected_key_item_id = other_id

            sx, sy = socket_data["canvas_pos"]
            initial_vars = {k: v.get() for k, v in self.editor.quest_vars.items()}
            initial_val = initial_vars[expected_hash]

            # Click once to select
            self.menu._on_canvas_click(DummyEvent(x=sx, y=sy))
            self.assertEqual(self.menu.selected_key_item_id, sock_id)
            self.assertEqual({k: v.get() for k, v in self.editor.quest_vars.items()}, initial_vars)

            # Click again to activate (toggle)
            self.menu._on_canvas_click(DummyEvent(x=sx, y=sy))
            expected_flipped = dict(initial_vars)
            expected_flipped[expected_hash] = not initial_val
            self.assertEqual({k: v.get() for k, v in self.editor.quest_vars.items()}, expected_flipped)

            # Toggle it back
            self.menu._on_canvas_click(DummyEvent(x=sx, y=sy))
            self.assertEqual({k: v.get() for k, v in self.editor.quest_vars.items()}, initial_vars)

    def test_threads_of_time_murmur_and_display(self):
        """Check murmur3_32 vectors, chapter row display, and parent/child visibility."""
        from oot_pause_menu import murmur3_32

        # 1. Murmur3 reference vectors
        self.assertEqual(murmur3_32(""), 0)
        self.assertEqual(murmur3_32("hello"), 0x248bfa47)
        self.assertEqual(murmur3_32("The quick brown fox jumps over the lazy dog"), 0x2e4ff723)
        self.assertEqual(murmur3_32("Complete"), 0x4c0a63f4)

        # 2. Meet_DekuTree complete (0x3372689B), all others 0
        deku_field = 0x3372689B
        self.editor.active_slot = {deku_field: murmur3_32("Complete")}

        self.menu.show_subscreen("Threads of Time")
        visible = getattr(self.menu, "_threads_visible_chapters", [])
        self.assertEqual(len(visible), 1)
        ch, status = visible[0]
        self.assertEqual(ch["id"], "Meet_DekuTree")
        self.assertEqual(status, "Complete")

        # 3. Child chapter hidden when parent is hidden
        fire_stone_field = 0x1002B466  # Get_StoneOfFire, parent DoorOfTime
        self.editor.active_slot = {
            deku_field: murmur3_32("Complete"),
            fire_stone_field: murmur3_32("Complete"),
        }
        self.menu.show_subscreen("Threads of Time")
        visible = getattr(self.menu, "_threads_visible_chapters", [])
        visible_ids = [c["id"] for c, _ in visible]
        self.assertIn("Meet_DekuTree", visible_ids)
        self.assertNotIn("Get_StoneOfFire", visible_ids, "Child chapter must be hidden when parent is not started")

        # Set parent DoorOfTime in progress
        door_of_time_field = 0x378913CA
        self.editor.active_slot[door_of_time_field] = murmur3_32("Step01")
        self.menu.show_subscreen("Threads of Time")
        visible = getattr(self.menu, "_threads_visible_chapters", [])
        visible_ids = [c["id"] for c, _ in visible]
        self.assertIn("DoorOfTime", visible_ids)
        self.assertIn("Get_StoneOfFire", visible_ids)

    def test_song_of_time_toggles_bit_3_not_4(self):
        """Check selecting the Song of Time entry toggles song_vars[3] (not 4)."""
        self.menu.show_subscreen("Song Book")

        sot_entry = next((s for s, x, y, rad in self.menu.song_hit_boxes if s["name"] == "Song of Time"), None)
        self.assertIsNotNone(sot_entry)
        self.assertEqual(sot_entry["bit_idx"], 3, "Song of Time must map to bit_idx 3")

        self.assertFalse(self.editor.song_vars[3].get())
        self.assertFalse(self.editor.song_vars[4].get())

        _, sot_x, sot_y, _ = next(item for item in self.menu.song_hit_boxes if item[0]["name"] == "Song of Time")
        ev_sot = DummyEvent(x=sot_x, y=sot_y)
        self.menu._on_song_arc_click(ev_sot)

        self.assertTrue(self.editor.song_vars[3].get(), "Song of Time must toggle bit 3")
        self.assertFalse(self.editor.song_vars[4].get(), "Bit 4 (Sun's Song) must remain unchanged")

    def test_threads_of_time_wheel_scroll_and_clamp_selection(self):
        """R1: Wheel scrolling down advances offset and clamps selected index into visible window; wheel up returns to 0."""
        from oot_pause_menu import murmur3_32

        class CompleteSlot(dict):
            def get(self, key, default=None):
                return murmur3_32("Complete")
            def __getitem__(self, key):
                return murmur3_32("Complete")

        self.editor.active_slot = CompleteSlot()
        self.menu.show_subscreen("Threads of Time")
        self.assertEqual(len(self.menu._threads_visible_chapters), 20)
        self.assertEqual(self.menu._threads_scroll_offset, 0)
        self.assertEqual(self.menu._threads_selected_index, 0)

        # 5 wheel-down events (delta=-120)
        for _ in range(5):
            self.menu._on_canvas_wheel(DummyEvent(delta=-120))

        offset = self.menu._threads_scroll_offset
        selected = self.menu._threads_selected_index
        self.assertGreater(offset, 0)
        self.assertEqual(offset, 5)
        self.assertGreaterEqual(selected, offset)
        self.assertLessEqual(selected, offset + 6)

        # 5 wheel-up events (delta=120) -> back to 0
        for _ in range(5):
            self.menu._on_canvas_wheel(DummyEvent(delta=120))

        self.assertEqual(self.menu._threads_scroll_offset, 0)
        self.assertGreaterEqual(self.menu._threads_selected_index, 0)
        self.assertLessEqual(self.menu._threads_selected_index, 6)

    def test_threads_of_time_click_hit_area_ignores_clicks_below_last_row(self):
        """R2: Clicks below the 7 drawn rows (ref y 960 and 1000) leave selection unchanged."""
        from oot_pause_menu import murmur3_32

        class CompleteSlot(dict):
            def get(self, key, default=None):
                return murmur3_32("Complete")
            def __getitem__(self, key):
                return murmur3_32("Complete")

        self.editor.active_slot = CompleteSlot()
        self.menu.show_subscreen("Threads of Time")
        self.assertEqual(self.menu._threads_selected_index, 0)

        # Click at ref y 960 (below 7 drawn rows: 290 + 7*95 = 955) -> selection unchanged
        cx, cy_960 = self.menu.to_canvas(300, 960)
        self.menu._on_canvas_click(DummyEvent(x=cx, y=cy_960))
        self.assertEqual(self.menu._threads_selected_index, 0)

        # Click at ref y 1000 -> selection unchanged
        cx, cy_1000 = self.menu.to_canvas(300, 1000)
        self.menu._on_canvas_click(DummyEvent(x=cx, y=cy_1000))
        self.assertEqual(self.menu._threads_selected_index, 0)

    def test_scarecrow_bent_notes_draw_on_staff(self):
        """R4: Scarecrow bent notes (such as D# (bent)) draw on staff with '?' key cap."""
        import oot_scarecrow
        self.menu.show_subscreen("Song Book")
        self.menu.selected_song_id = "Scarecrow's Song"

        bent_label = oot_scarecrow.NOTE_LABELS[5]  # "D# (bent)"
        note_values = ["R", bent_label, "A"]
        if hasattr(self.editor, "scarecrow_note_vars"):
            for i, val in enumerate(note_values):
                if i < len(self.editor.scarecrow_note_vars):
                    self.editor.scarecrow_note_vars[i].set(val)
            for j in range(len(note_values), len(self.editor.scarecrow_note_vars)):
                self.editor.scarecrow_note_vars[j].set("-")
        else:
            self.editor.scarecrow_note_vars = note_values

        self.menu.refresh_visuals()

        caps = self.menu.canvas.find_withtag("staff_note_cap")
        self.assertEqual(len(caps), 3, f"Expected 3 drawn staff notes, got {len(caps)}")

        texts = self.menu.canvas.find_withtag("staff_note_text")
        self.assertEqual(len(texts), 3)
        rendered_labels = [self.menu.canvas.itemcget(t, "text") for t in texts]
        self.assertEqual(rendered_labels, ["R", "?", "A"])

    def test_font_cache_bounded_on_resize(self):
        """R5: Font cache must clear on canvas size change and remain bounded across multiple resizes."""
        self.menu.show_subscreen("Items")
        sizes = [
            (800, 600), (960, 540), (1024, 768), (1280, 720), (1366, 768),
            (1440, 900), (1600, 900), (1920, 1080), (1200, 800), (1000, 700),
        ]
        self.menu.set_canvas_size(*sizes[0])
        first_len = len(self.menu._font_cache)
        self.assertGreater(first_len, 0, "Font cache should contain entries for initial render")

        for w, h in sizes:
            self.menu.set_canvas_size(w, h)
            self.assertLess(len(self.menu._font_cache), 30, f"Font cache size {len(self.menu._font_cache)} exceeded bound at ({w}, {h})")

        # Returning to the first size must not grow the cache beyond first_len
        self.menu.set_canvas_size(*sizes[0])
        self.assertEqual(len(self.menu._font_cache), first_len)


if __name__ == "__main__":
    unittest.main()
