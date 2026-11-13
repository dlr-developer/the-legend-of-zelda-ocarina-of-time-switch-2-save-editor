"""
OOTS2-19 tests: Giant's Knife tier, Great Fairy gift flags, editable top bar,
textured menus with flat fallback, and the pause-menu toggle button.
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

import oot_pause_menu
from oot_pause_menu import OOTTextureMenuFrame, HDTextureManager, upper_left_run, PAUSE_MENU_LAYOUT
from tests.test_pause_menu import DummyEditor, DummyEvent


def _slot(page, slot_id):
    slots = PAUSE_MENU_LAYOUT["plus_menu"]["pages"][page]["slots"]
    return next(s for s in slots if s["id"] == slot_id)


class PolishEditor(DummyEditor):
    def __init__(self, root):
        super().__init__(root)
        self.owned_swords["Giant's Knife"] = tk.BooleanVar(value=False)
        self.v_gift_spin = tk.BooleanVar(value=False)
        self.v_gift_magic = tk.BooleanVar(value=False)


class PolishBase(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.editor = PolishEditor(self.root)
        self.menu = OOTTextureMenuFrame(self.root, self.editor)
        self.menu.pack(fill="both", expand=True)
        self.root.update_idletasks()

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass


class TestGiantsKnife(PolishBase):
    def test_slot_shows_giant_then_biggoron(self):
        slot = _slot("Equipment", "Pa_Epuipment_00")
        actor, owned, _, _, _, _ = self.menu.get_slot_state(slot)
        self.assertFalse(owned)

        self.editor.owned_swords["Giant's Knife"].set(True)
        actor, owned, _, _, _, _ = self.menu.get_slot_state(slot)
        self.assertEqual(actor, "Weapon_Sword_Giant")
        self.assertTrue(owned)

        self.editor.owned_swords["Biggoron's Sword"].set(True)
        actor, owned, _, _, _, _ = self.menu.get_slot_state(slot)
        self.assertEqual(actor, "Weapon_Sword_Biggoron")

    def test_activation_cycles_none_giant_biggoron_none(self):
        slot = _slot("Equipment", "Pa_Epuipment_00")
        giant = self.editor.owned_swords["Giant's Knife"]
        big = self.editor.owned_swords["Biggoron's Sword"]
        self.menu.activate_slot(slot)
        self.assertEqual((giant.get(), big.get()), (True, False))
        self.menu.activate_slot(slot)
        self.assertEqual((giant.get(), big.get()), (False, True))
        self.menu.activate_slot(slot)
        self.assertEqual((giant.get(), big.get()), (False, False))

    def test_upgrade_keeps_the_big_sword_equipped(self):
        """Giant's Knife equipped -> cycling to Biggoron's Sword keeps the big sword equipped."""
        slot = _slot("Equipment", "Pa_Epuipment_00")
        self.editor.owned_swords["Giant's Knife"].set(True)
        self.editor.equip_vars["sword"].set("Giant's Knife")
        self.menu.activate_slot(slot)
        self.assertEqual(self.editor.equip_vars["sword"].get(), "Biggoron's Sword")

    def test_right_click_equips_shown_tier(self):
        self.editor.owned_swords["Giant's Knife"].set(True)
        self.menu.show_subscreen("Equipment")
        slot = _slot("Equipment", "Pa_Epuipment_00")
        cx, cy = self.menu.to_canvas(*slot["pos"])
        self.menu._on_canvas_right_click(DummyEvent(x=cx, y=cy))
        self.assertEqual(self.editor.equip_vars["sword"].get(), "Giant's Knife")
        self.assertEqual(self.menu._get_equipped_sword_actor(), "Weapon_Sword_Giant")

    def test_giant_icon_file(self):
        self.assertEqual(oot_pause_menu.ACTOR_TO_GENERATED_FILE["Weapon_Sword_Giant"], "sword_giants_knife.png")


class TestGiftSlots(PolishBase):
    def test_owned_follows_gift_vars(self):
        spin = _slot("Collection", "Pa_Fairy_00")
        magic = _slot("Collection", "Pa_Fairy_01")
        self.assertFalse(self.menu.get_slot_state(spin)[1])
        self.assertFalse(self.menu.get_slot_state(magic)[1])

        self.editor.v_gift_spin.set(True)
        self.assertTrue(self.menu.get_slot_state(spin)[1])
        self.assertFalse(self.menu.get_slot_state(magic)[1])

        # the magic meter size no longer decides ownership
        self.editor.v_magic.set("Double Magic Meter (48 MP)")
        self.assertFalse(self.menu.get_slot_state(magic)[1])
        self.editor.v_gift_magic.set(True)
        self.assertTrue(self.menu.get_slot_state(magic)[1])

    def test_gift_names_come_from_the_plain_entries(self):
        items = oot_pause_menu.MENU_TEXT["items"]
        self.assertFalse([k for k in items if k.endswith("_Tier2")])
        self.assertFalse(hasattr(self.menu, "_fairy_text_actor"))
        for slot_id, actor in (("Pa_Fairy_00", "Item_FairyBless_MP"), ("Pa_Fairy_01", "Item_FairyBless_MPDouble")):
            self.assertEqual(self.menu.get_slot_state(_slot("Collection", slot_id))[0], actor)
            self.assertEqual(self.menu.get_actor_text(actor)[0], items[actor]["name"])
        self.assertEqual(items["Item_FairyBless_MP"]["name"], "Gift of Improved Spin")
        self.assertEqual(items["Item_FairyBless_MPDouble"]["name"], "Gift of Doubled Magic")
        # the magic meter size no longer changes the gift's name
        self.editor.v_magic.set("Double Magic Meter (48 MP)")
        magic_actor = self.menu.get_slot_state(_slot("Collection", "Pa_Fairy_01"))[0]
        self.assertEqual(magic_actor, "Item_FairyBless_MPDouble")

    def test_activation_toggles_the_right_var(self):
        self.menu.activate_slot(_slot("Collection", "Pa_Fairy_00"))
        self.assertTrue(self.editor.v_gift_spin.get())
        self.assertFalse(self.editor.v_gift_magic.get())
        self.menu.activate_slot(_slot("Collection", "Pa_Fairy_01"))
        self.assertTrue(self.editor.v_gift_magic.get())
        self.menu.activate_slot(_slot("Collection", "Pa_Fairy_00"))
        self.assertFalse(self.editor.v_gift_spin.get())
        self.assertTrue(self.editor.v_gift_magic.get())

    def test_icon_mapping(self):
        m = oot_pause_menu.ACTOR_TO_GENERATED_FILE
        self.assertEqual(m["Item_FairyBless_MP"], "gift_spin.png")
        self.assertEqual(m["Item_FairyBless_MPDouble"], "gift_magic.png")
        for size in ("Small", "Medium", "Large"):
            self.assertEqual(m[f"Item_NutBag_{size}"], "item_nut_bag.png")
            self.assertEqual(m[f"Item_StickBag_{size}"], "item_stick_bag.png")


class TestTopBar(PolishBase):
    def _center(self, name):
        self.menu.refresh_visuals()
        x1, y1, x2, y2 = self.menu._topbar_hits[name]
        return (x1 + x2) / 2, (y1 + y2) / 2

    def test_hit_areas_on_every_tab(self):
        for page in self.menu.pages:
            self.menu.show_subscreen(page)
            self.assertEqual(set(self.menu._topbar_hits), {"hearts", "magic", "rupees"}, page)

    def test_wheel_rupees_ctrl_adds_100_and_clamps(self):
        self.editor.equip_vars["wallet"].set("Giant's Wallet (500)")
        self.editor.v_rupees.set("350")
        x, y = self._center("rupees")
        self.menu._on_canvas_wheel(DummyEvent(delta=120, state=0x0004, x=x, y=y))
        self.assertEqual(self.editor.v_rupees.get(), "450")
        self.menu._on_canvas_wheel(DummyEvent(delta=120, state=0x0004, x=x, y=y))
        self.assertEqual(self.editor.v_rupees.get(), "500")
        self.menu._on_canvas_wheel(DummyEvent(delta=-120, state=0x0001, x=x, y=y))
        self.assertEqual(self.editor.v_rupees.get(), "490")
        self.menu._on_canvas_wheel(DummyEvent(delta=-120, x=x, y=y))
        self.assertEqual(self.editor.v_rupees.get(), "489")

    def test_wheel_hearts_changes_hp_by_four_and_clamps(self):
        self.editor.v_hp.set("8")
        x, y = self._center("hearts")
        self.menu._on_canvas_wheel(DummyEvent(delta=120, x=x, y=y))
        self.assertEqual(self.editor.v_hp.get(), "12")
        self.menu._on_canvas_wheel(DummyEvent(delta=120, x=x, y=y))
        self.assertEqual(self.editor.v_hp.get(), "12")   # clamped at max (3 hearts)
        for _ in range(5):
            self.menu._on_canvas_wheel(DummyEvent(delta=-120, x=x, y=y))
        self.assertEqual(self.editor.v_hp.get(), "1")    # clamped at 1 quarter

    def test_shift_wheel_hearts_changes_max_hearts(self):
        x, y = self._center("hearts")
        self.menu._on_canvas_wheel(DummyEvent(delta=120, state=0x0001, x=x, y=y))
        self.assertEqual(self.editor.v_hearts.get(), "4")
        self.menu._on_canvas_wheel(DummyEvent(delta=-120, state=0x0001, x=x, y=y))
        self.menu._on_canvas_wheel(DummyEvent(delta=-120, state=0x0001, x=x, y=y))
        self.assertEqual(self.editor.v_hearts.get(), "3")

    def test_wheel_magic_clamps_to_meter(self):
        self.editor.v_magic.set("Standard Magic Meter (24 MP)")
        self.editor.v_magic_points.set("23")
        x, y = self._center("magic")
        self.menu._on_canvas_wheel(DummyEvent(delta=120, x=x, y=y))
        self.menu._on_canvas_wheel(DummyEvent(delta=120, x=x, y=y))
        self.assertEqual(self.editor.v_magic_points.get(), "24")

    def test_rupee_popup_binds_editor_vars(self):
        x, y = self._center("rupees")
        self.menu._on_canvas_click(DummyEvent(x=x, y=y))
        popup = self.menu._popup
        self.assertIsNotNone(popup)
        sb = self.menu._popup_widgets["rupees"]
        self.assertEqual(str(sb.cget("textvariable")), str(self.editor.v_rupees))
        self.assertEqual(str(self.menu._popup_widgets["wallet"].cget("textvariable")),
                         str(self.editor.equip_vars["wallet"]))
        self.editor.v_rupees.set("42")
        self.assertEqual(sb.get(), "42")
        self.menu._close_topbar_popup()
        self.assertIsNone(self.menu._popup)

    def test_hearts_and_magic_popups_bind_editor_vars(self):
        self.menu._open_topbar_popup("hearts")
        w = self.menu._popup_widgets
        self.assertEqual(str(w["hp"].cget("textvariable")), str(self.editor.v_hp))
        self.assertEqual(str(w["hearts"].cget("textvariable")), str(self.editor.v_hearts))
        self.assertEqual(str(w["boss"].cget("textvariable")), str(self.editor.v_boss_containers))
        self.assertEqual(str(w["pieces"].cget("textvariable")), str(self.editor.v_heart_pieces_total))
        self.menu._open_topbar_popup("magic")
        w = self.menu._popup_widgets
        self.assertEqual(str(w["magic"].cget("textvariable")), str(self.editor.v_magic))
        self.assertEqual(str(w["mp"].cget("textvariable")), str(self.editor.v_magic_points))
        self.menu._close_topbar_popup()

    def test_hover_draws_outline_and_resets(self):
        x, y = self._center("hearts")
        self.menu._on_canvas_motion(DummyEvent(x=x, y=y))
        self.assertTrue(self.menu.canvas.find_withtag("topbar_hover"))
        self.menu._on_canvas_leave()
        self.assertFalse(self.menu.canvas.find_withtag("topbar_hover"))


class TestTextures(PolishBase):
    def test_textures_load_and_fall_back(self):
        if not oot_pause_menu.PIL_AVAILABLE:
            self.skipTest("Pillow not installed")
        for page in ("Collection", "Equipment", "Items", "Key Items"):
            self.menu.show_subscreen(page)
            self.menu.refresh_visuals()
            self.assertTrue(self.menu.canvas.find_withtag("topbar_texture"), page)
            if page in ("Collection", "Equipment", "Items"):
                self.assertTrue(self.menu.canvas.find_withtag("panel_wood"), page)

    def test_missing_texture_uses_flat_colours(self):
        self.menu.textures = HDTextureManager(base_dir=os.path.join(REPO_ROOT, "no_such_dir"))
        for page in self.menu.pages:
            self.menu.show_subscreen(page)
            self.menu.refresh_visuals()
            self.assertFalse(self.menu.canvas.find_withtag("topbar_texture"))
            self.assertFalse(self.menu.canvas.find_withtag("panel_wood"))
        self.assertIsNone(self.menu.textures.get_tiled("ui_panel_wood.png", 100, 100, 50))
        self.assertIsNone(self.menu.textures.get_stretched("ui_topbar.png", 100, 20))

    def test_cache_cleared_on_resize(self):
        if not oot_pause_menu.PIL_AVAILABLE:
            self.skipTest("Pillow not installed")
        self.menu.show_subscreen("Collection")
        self.menu.refresh_visuals()
        self.assertTrue(self.menu.textures.cache)
        self.menu.set_canvas_size(960, 540)
        keys = [k for k in self.menu.textures.cache if k[0] in ("tiled", "stretched")]
        self.assertTrue(keys)
        self.assertTrue(all(k[2] <= 960 for k in keys if k[0] == "tiled"))

    def test_upper_left_run(self):
        square = [0, 0, 10, 0, 10, 10, 0, 10]
        run = upper_left_run(square, 5, 5)
        self.assertGreaterEqual(len(run), 4)
        self.assertEqual(upper_left_run([0, 0, 1, 1], 0, 0), [])


class TestSaveFlags(unittest.TestCase):
    def test_gift_flags_are_independent_of_magic_meter(self):
        import oot_save_editor as se

        class FakeSlot:
            def __init__(self):
                self.written = {}

            def set(self, h, v):
                self.written[h] = v

        class Stub:
            pass

        root = tk.Tk()
        root.withdraw()
        try:
            stub = Stub()
            stub.v_gift_spin = tk.BooleanVar(value=True)
            stub.v_gift_magic = tk.BooleanVar(value=False)
            stub.v_double_defense = tk.BooleanVar(value=False)
            stub.v_magic = tk.StringVar(value="Double Magic Meter (48 MP)")
            slot = FakeSlot()
            se.OOTEditor._write_blessing_flags(stub, slot)
            self.assertEqual(slot.written[0x5E671D92], 1)
            self.assertEqual(slot.written[0x5F043856], 0)
            self.assertEqual(slot.written[se.BLESSING_DEFENSE_DOUBLE], 0)

            stub.v_gift_spin.set(False)
            stub.v_gift_magic.set(True)
            stub.v_magic.set("None")
            slot = FakeSlot()
            se.OOTEditor._write_blessing_flags(stub, slot)
            self.assertEqual(slot.written[0x5E671D92], 0)
            self.assertEqual(slot.written[0x5F043856], 1)
        finally:
            root.destroy()


class TestEditorIntegration(unittest.TestCase):
    """Real editor window: Giant's Knife checkbox var, gift vars, review diff and the toggle button."""

    def setUp(self):
        from oot_save_editor import OOTEditor
        self.app = OOTEditor()
        self.app.withdraw()

    def tearDown(self):
        try:
            self.app.destroy()
        except Exception:
            pass

    def test_editor_has_giant_and_gift_vars(self):
        self.assertIn("Giant's Knife", self.app.owned_swords)
        self.app.owned_swords["Giant's Knife"].set(True)
        self.app._sync_equipped_options()
        self.assertIn("Giant's Knife", list(self.app.equipped_combos["sword"].cget("values")))
        self.app.owned_swords["Giant's Knife"].set(False)
        self.assertFalse(self.app.v_gift_spin.get())
        self.assertFalse(self.app.v_gift_magic.get())

    def test_review_diff_lists_giant_and_gifts(self):
        self.app.snapshot_current()
        self.app.v_gift_spin.set(True)
        self.app.v_gift_magic.set(True)
        self.app.owned_swords["Giant's Knife"].set(True)
        text = " | ".join(d[1] for d in self.app.describe_changes())
        self.assertIn("Gift of Improved Spin", text)
        self.assertIn("Gift of Doubled Magic", text)
        self.assertIn("Giant's Knife", text)

    def test_toggle_button_label_follows_view(self):
        self.app.active_slot = object()   # switch_to_texture_view only needs a truthy slot
        btn = self.app.pause_menu_button
        self.assertIn("Switch 2 Pause Menu", btn.cget("text"))
        self.app.switch_to_texture_view()
        self.assertIn("Back to Save Editor", btn.cget("text"))
        self.app.switch_to_standard_view()
        self.assertIn("Switch 2 Pause Menu", btn.cget("text"))
        self.assertEqual(btn.cget("bg"), "#e60012")

    def test_pause_button_color_follows_view_state(self):
        btn = self.app.pause_menu_button
        self.assertEqual(btn.cget("bg"), "#e60012")
        self.app._pause_view_active = True
        self.app._update_pause_button_color()
        self.assertEqual(btn.cget("bg"), "#1f9d3a")
        self.app._update_pause_button_color(hover=True)
        self.assertEqual(btn.cget("bg"), "#2fbf4e")
        self.app._pause_view_active = False
        self.app._update_pause_button_color()
        self.assertEqual(btn.cget("bg"), "#e60012")

    def test_big_sword_dropdown_syncs_both_ways(self):
        a = self.app
        g, b = a.owned_swords["Giant's Knife"], a.owned_swords["Biggoron's Sword"]
        self.assertEqual(a.big_sword_var.get(), "None")
        a.big_sword_var.set("Giant's Knife")
        a._on_big_sword_pick()
        self.assertTrue(g.get())
        self.assertFalse(b.get())
        a.big_sword_var.set("Biggoron's Sword")
        a._on_big_sword_pick()
        self.assertFalse(g.get())
        self.assertTrue(b.get())
        # flags changed elsewhere update the dropdown
        b.set(False)
        g.set(True)
        self.assertEqual(a.big_sword_var.get(), "Giant's Knife")
        g.set(False)
        self.assertEqual(a.big_sword_var.get(), "None")
        # both set (loaded save): shows Biggoron, leaves the flags alone
        g.set(True)
        b.set(True)
        self.assertEqual(a.big_sword_var.get(), "Biggoron's Sword")
        self.assertTrue(g.get())

    def test_unlock_all_gives_biggoron_only(self):
        self.app.unlock_all_stored_equipment()
        self.assertTrue(self.app.owned_swords["Biggoron's Sword"].get())
        self.assertFalse(self.app.owned_swords["Giant's Knife"].get())

    def test_toggle_command_switches_both_ways(self):
        self.app.active_slot = object()
        self.app.update()
        self.app.toggle_pause_view()
        self.app.update()
        self.assertIn("Back to Save Editor", self.app.pause_menu_button.cget("text"))
        self.app.toggle_pause_view()
        self.app.update()
        self.assertIn("Switch 2 Pause Menu", self.app.pause_menu_button.cget("text"))


if __name__ == "__main__":
    unittest.main()
