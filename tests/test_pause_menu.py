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
)
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


if __name__ == "__main__":
    unittest.main()
