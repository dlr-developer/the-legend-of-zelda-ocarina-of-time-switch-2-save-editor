import os
import sys
import unittest
import tempfile
import json
import time
import tkinter as tk
from tkinter import ttk

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from oot_guides import GuidesFrame, PIL_AVAILABLE

if PIL_AVAILABLE:
    from PIL import Image


class DummyApp:
    def __init__(self, app_dir=None, resource_dir=None):
        self.settings = {}
        self.palette = {}
        self.active_slot = None
        self.app_dir = app_dir
        self.resource_dir = resource_dir

    def store_settings(self):
        pass


class TestGuidesUI(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
            self.root.withdraw()
        except tk.TclError:
            raise unittest.SkipTest("Tk display not available")

    def tearDown(self):
        if hasattr(self, "root") and self.root:
            try:
                self.root.destroy()
            except Exception:
                pass

    def _wait_for_guide(self, gf, guide_id):
        guide = gf.guides_by_id.get(guide_id)
        if not guide:
            return
        total = len(guide.get("entries", []))
        for _ in range(100):
            self.root.update()
            if len(gf.cards_by_guide.get(guide_id, [])) >= total and gf._batch_job is None:
                break
            time.sleep(0.005)

    def test_filter_order(self):
        """a) Filter order: check 2 and 5, filter Checked, then All; assert packed cards are 1..36 in order."""
        app = DummyApp(app_dir=REPO_ROOT, resource_dir=REPO_ROOT)
        gf = GuidesFrame(self.root, app, app_dir=REPO_ROOT, resource_dir=REPO_ROOT)
        gf.pack(fill="both", expand=True)
        gf.select_guide("heart_pieces")
        self._wait_for_guide(gf, "heart_pieces")

        cards = {c.n: c for c in gf.cards_by_guide["heart_pieces"]}
        cards[2].check_var.set(True)
        cards[2]._on_toggle()
        cards[5].check_var.set(True)
        cards[5]._on_toggle()

        # Filter Checked
        gf.combo_status.set("Checked")
        gf._apply_filters()
        self.root.update()

        # Filter All
        gf.combo_status.set("All")
        gf._apply_filters()
        self.root.update()

        card_map = {c.border_frame: c.n for c in gf.cards_by_guide["heart_pieces"]}
        packed_numbers = [card_map[s] for s in gf.cards_inner.pack_slaves() if s in card_map]
        self.assertEqual(packed_numbers, list(range(1, 37)), "Packed cards must be in 1..36 order after re-filtering")

    def test_guide_isolation(self):
        """b) Guide isolation: load heart_pieces plus temp second guide (3 entries), select heart_pieces then second; assert only 3 cards of second guide are mapped/packed."""
        with tempfile.TemporaryDirectory() as td:
            guides_dir = os.path.join(td, "guides")
            os.makedirs(guides_dir, exist_ok=True)
            with open(os.path.join(guides_dir, "second_guide.json"), "w", encoding="utf-8") as f:
                json.dump({
                    "id": "second_guide",
                    "title": "Second Guide",
                    "total": 3,
                    "entries": [
                        {"n": 1, "title": "Second #1", "steps": "Step 1"},
                        {"n": 2, "title": "Second #2", "steps": "Step 2"},
                        {"n": 3, "title": "Second #3", "steps": "Step 3"}
                    ]
                }, f)

            app = DummyApp(app_dir=td, resource_dir=REPO_ROOT)
            gf = GuidesFrame(self.root, app, app_dir=td, resource_dir=REPO_ROOT)
            gf.pack(fill="both", expand=True)

            # Select heart_pieces first
            gf.select_guide("heart_pieces")
            self._wait_for_guide(gf, "heart_pieces")
            hp_frames = {c.border_frame for c in gf.cards_by_guide["heart_pieces"]}
            self.assertEqual(len([s for s in gf.cards_inner.pack_slaves() if s in hp_frames]), 36)

            # Select second_guide
            gf.select_guide("second_guide")
            self._wait_for_guide(gf, "second_guide")

            packed_slaves = gf.cards_inner.pack_slaves()
            self.assertEqual(len(packed_slaves), 3, "Only the 3 cards of second_guide should be packed")

            second_card_frames = {c.border_frame for c in gf.cards_by_guide["second_guide"]}
            for slave in packed_slaves:
                self.assertIn(slave, second_card_frames, "Packed slave must belong to second_guide")

            hp_card_frames = {c.border_frame for c in gf.cards_by_guide["heart_pieces"]}
            for hp_frame in hp_card_frames:
                self.assertNotIn(hp_frame, packed_slaves, "heart_pieces cards must not be packed")
                self.assertFalse(hp_frame.winfo_ismapped(), "heart_pieces cards must not be mapped")

    def test_toggle_under_filter(self):
        """c) Toggle under filter: filter Checked, uncheck one, assert its card is no longer packed."""
        app = DummyApp(app_dir=REPO_ROOT, resource_dir=REPO_ROOT)
        gf = GuidesFrame(self.root, app, app_dir=REPO_ROOT, resource_dir=REPO_ROOT)
        gf.pack(fill="both", expand=True)
        gf.select_guide("heart_pieces")
        self._wait_for_guide(gf, "heart_pieces")

        cards = {c.n: c for c in gf.cards_by_guide["heart_pieces"]}
        cards[2].check_var.set(True)
        cards[2]._on_toggle()
        cards[5].check_var.set(True)
        cards[5]._on_toggle()

        # Filter Checked
        gf.combo_status.set("Checked")
        gf._apply_filters()
        self.root.update()

        # Verify initial filtered state has both packed
        packed_slaves = gf.cards_inner.pack_slaves()
        self.assertIn(cards[2].border_frame, packed_slaves)
        self.assertIn(cards[5].border_frame, packed_slaves)

        # Uncheck card 2
        cards[2].check_var.set(False)
        cards[2]._on_toggle()
        self.root.update()

        # Card 2 should no longer be packed
        packed_slaves = gf.cards_inner.pack_slaves()
        self.assertNotIn(cards[2].border_frame, packed_slaves, "Unchecked card 2 should no longer be packed under Checked filter")
        self.assertIn(cards[5].border_frame, packed_slaves, "Card 5 should still be packed")

    def test_scroll_position_maintained_on_toggle_and_check_all(self):
        """Scroll position: maintain position on toggle / check-all, reset to 0 on filter combobox / guide switch."""
        app = DummyApp(app_dir=REPO_ROOT, resource_dir=REPO_ROOT)
        gf = GuidesFrame(self.root, app, app_dir=REPO_ROOT, resource_dir=REPO_ROOT)
        gf.pack(fill="both", expand=True)
        gf.select_guide("heart_pieces")
        self._wait_for_guide(gf, "heart_pieces")

        # Move scroll position down
        gf.canvas.yview_moveto(0.4)
        pos_before = gf.canvas.yview()[0]
        self.assertGreater(pos_before, 0.0)

        # Toggle a card
        card1 = gf.cards_by_guide["heart_pieces"][0]
        card1.check_var.set(True)
        card1._on_toggle()
        self.root.update()

        pos_after_toggle = gf.canvas.yview()[0]
        self.assertAlmostEqual(pos_before, pos_after_toggle, delta=0.05,
                               msg="Scroll position should be maintained after card toggle")

        # Check all
        gf._check_all()
        self.root.update()

        pos_after_check_all = gf.canvas.yview()[0]
        self.assertAlmostEqual(pos_before, pos_after_check_all, delta=0.05,
                               msg="Scroll position should be maintained after check all")

        # Combobox change should reset scroll to top
        gf.combo_era.set("Adult")
        gf._apply_filters(reset_scroll=True)
        self.root.update()
        self.assertEqual(gf.canvas.yview()[0], 0.0, "Scroll position must reset to 0.0 on combobox change")

    def test_mousewheel_containment(self):
        """Mousewheel: handler targets canvas and descendants, ignores unrelated widgets."""
        self.root.deiconify()
        self.root.geometry("800x600+100+100")

        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True)

        app = DummyApp(app_dir=REPO_ROOT, resource_dir=REPO_ROOT)
        gf = GuidesFrame(nb, app, app_dir=REPO_ROOT, resource_dir=REPO_ROOT)
        nb.add(gf, text="Guides")

        other_frame = ttk.Frame(nb)
        other_lbl = ttk.Label(other_frame, text="Other Tab")
        other_lbl.pack()
        nb.add(other_frame, text="Other")

        gf.select_guide("heart_pieces")
        self._wait_for_guide(gf, "heart_pieces")
        nb.select(gf)
        self.root.update()

        card = gf.cards_by_guide["heart_pieces"][0]

        class MockEvent:
            def __init__(self, x_root, y_root, delta=120):
                self.x_root = x_root
                self.y_root = y_root
                self.delta = delta

        # Over canvas child (card badge) -> should scroll
        x = card.badge.winfo_rootx() + 2
        y = card.badge.winfo_rooty() + 2
        self.assertTrue(gf._should_scroll(MockEvent(x, y)))

        # Over left pane treeview -> should not scroll canvas
        tree_x = gf.guide_tree.winfo_rootx() + 5
        tree_y = gf.guide_tree.winfo_rooty() + 5
        self.assertFalse(gf._should_scroll(MockEvent(tree_x, tree_y)))

        # Switch to other tab -> should not scroll canvas
        nb.select(other_frame)
        self.root.update()
        self.assertFalse(gf._should_scroll(MockEvent(x, y)))

        self.root.withdraw()

    def test_story_progress_subtab_first_and_selected(self):
        """Part A: Story Progress tab is first and selected in Progress & Inspector."""
        try:
            probe = tk.Tk()
            probe.destroy()
        except tk.TclError:
            raise unittest.SkipTest("Tk display not available")

        from oot_save_editor import OOTEditor
        app = OOTEditor()
        try:
            app.withdraw()
            self.assertTrue(hasattr(app, "walk_tree"))
            self.assertIsNotNone(app.walk_tree)

            self.assertTrue(hasattr(app, "progress_sub_nb"))
            sub_nb = app.progress_sub_nb
            tabs = sub_nb.tabs()
            self.assertGreaterEqual(len(tabs), 3)

            # Story Progress is the first sub-tab
            self.assertEqual(sub_nb.tab(tabs[0], "text"), "Story Progress")
            self.assertEqual(sub_nb.tab(tabs[1], "text"), "Progress Flags")
            self.assertEqual(sub_nb.tab(tabs[2], "text"), "Field Inspector (READ ONLY)")

            # Story Progress is the selected sub-tab on startup
            self.assertEqual(sub_nb.select(), tabs[0])
        finally:
            app.destroy()

    def test_guides_list_has_no_story_item(self):
        """Part A: Guides list has no 'story' item and selects the first guide by order."""
        app = DummyApp(app_dir=REPO_ROOT, resource_dir=REPO_ROOT)
        gf = GuidesFrame(self.root, app, app_dir=REPO_ROOT, resource_dir=REPO_ROOT)
        gf.pack(fill="both", expand=True)
        self.root.update()

        # No 'story' item in guide_tree
        self.assertFalse(gf.guide_tree.exists("story"))
        children = gf.guide_tree.get_children()
        self.assertNotIn("story", children)

        # Selected item should be the first guide by order
        first_id = gf.guides[0]["id"]
        self.assertEqual(min(g.get("order", 999999) for g in gf.guides), gf.guides[0].get("order", 999999))
        self.assertEqual(gf.selected_item, f"guide:{first_id}")
        self.assertIsNotNone(gf.current_guide)
        self.assertEqual(gf.current_guide.get("id"), first_id)

    def test_group_headings_and_area_filter(self):
        """Part B: Group headings appear in order and respect the Area filter; combobox is hidden when no groups."""
        with tempfile.TemporaryDirectory() as td:
            guides_dir = os.path.join(td, "guides")
            os.makedirs(guides_dir, exist_ok=True)
            with open(os.path.join(guides_dir, "grouped_guide.json"), "w", encoding="utf-8") as f:
                json.dump({
                    "id": "grouped_guide",
                    "title": "Grouped Guide",
                    "total": 4,
                    "entries": [
                        {"n": 1, "group": "Forest Area", "title": "Entry 1", "steps": "Step 1"},
                        {"n": 2, "group": "Forest Area", "title": "Entry 2", "steps": "Step 2"},
                        {"n": 3, "group": "Mountain Area", "title": "Entry 3", "steps": "Step 3"},
                        {"n": 4, "group": "Lake Area", "title": "Entry 4", "steps": "Step 4"}
                    ]
                }, f)
            with open(os.path.join(guides_dir, "nogroup_guide.json"), "w", encoding="utf-8") as f:
                json.dump({
                    "id": "nogroup_guide",
                    "title": "No Group Guide",
                    "total": 1,
                    "entries": [
                        {"n": 1, "title": "No Group Entry", "steps": "Step"}
                    ]
                }, f)

            app = DummyApp(app_dir=td, resource_dir=td)
            gf = GuidesFrame(self.root, app, app_dir=td, resource_dir=td)
            gf.pack(fill="both", expand=True)
            gf.select_guide("grouped_guide")
            self._wait_for_guide(gf, "grouped_guide")

            # Area combobox should be visible with values in first-appearance order
            self.assertEqual(gf.combo_area.winfo_manager(), "pack")
            self.assertEqual(list(gf.combo_area["values"]), ["All", "Forest Area", "Mountain Area", "Lake Area"])
            self.assertEqual(gf.combo_area.get(), "All")

            headings = gf.headings_by_guide.get("grouped_guide", {})
            self.assertIn("Forest Area", headings)
            self.assertIn("Mountain Area", headings)
            self.assertIn("Lake Area", headings)

            slaves = gf.cards_inner.pack_slaves()
            card1_frame = [c.border_frame for c in gf.cards_by_guide["grouped_guide"] if c.n == 1][0]
            card3_frame = [c.border_frame for c in gf.cards_by_guide["grouped_guide"] if c.n == 3][0]

            self.assertLess(slaves.index(headings["Forest Area"].frame), slaves.index(card1_frame))
            self.assertLess(slaves.index(headings["Mountain Area"].frame), slaves.index(card3_frame))

            # Filter by Area: Mountain Area
            gf.combo_area.set("Mountain Area")
            gf._apply_filters(reset_scroll=True)
            self.root.update()

            packed_slaves = gf.cards_inner.pack_slaves()
            self.assertIn(headings["Mountain Area"].frame, packed_slaves)
            self.assertNotIn(headings["Forest Area"].frame, packed_slaves)
            self.assertNotIn(headings["Lake Area"].frame, packed_slaves)

            # Guide without groups hides Area combobox
            self.assertTrue(gf.guide_tree.exists("guide:nogroup_guide"))
            gf.select_guide("nogroup_guide")
            self.root.update()
            self.assertEqual(gf.current_guide.get("id"), "nogroup_guide")
            self.assertEqual(gf.combo_area.winfo_manager(), "")

    def test_skulltulas_save_counter(self):
        """Part B: skulltulas save_counter compares against v_tokens with 'Save file: N / 100'."""
        with tempfile.TemporaryDirectory() as td:
            guides_dir = os.path.join(td, "guides")
            os.makedirs(guides_dir, exist_ok=True)
            with open(os.path.join(guides_dir, "skulltula_guide.json"), "w", encoding="utf-8") as f:
                json.dump({
                    "id": "skulltulas",
                    "title": "Gold Skulltulas",
                    "save_counter": "skulltulas",
                    "total": 100,
                    "entries": [
                        {"n": 1, "title": "Token 1", "steps": "Step 1"}
                    ]
                }, f)

            app = DummyApp(app_dir=td, resource_dir=td)
            app.active_slot = True
            app.v_tokens = tk.StringVar(value="42")
            gf = GuidesFrame(self.root, app, app_dir=td, resource_dir=td)
            gf.pack(fill="both", expand=True)
            gf.select_guide("skulltulas")
            self.root.update()

            self.assertIn("Save file: 42 / 100", gf.lbl_save.cget("text"))

            # Dynamic update via trace
            app.v_tokens.set("85")
            self.root.update()
            self.assertIn("Save file: 85 / 100", gf.lbl_save.cget("text"))

    def test_synthetic_150_entry_lazy_batch_build(self):
        """Part C: 150-entry synthetic guide builds first <=15 immediately and rest eventually in order."""
        with tempfile.TemporaryDirectory() as td:
            guides_dir = os.path.join(td, "guides")
            os.makedirs(guides_dir, exist_ok=True)
            entries = [{"n": i, "title": f"Entry {i}", "steps": f"Steps for entry {i}"} for i in range(1, 151)]
            with open(os.path.join(guides_dir, "big_guide.json"), "w", encoding="utf-8") as f:
                json.dump({
                    "id": "big_guide",
                    "title": "Big Synthetic Guide",
                    "total": 150,
                    "entries": entries
                }, f)

            app = DummyApp(app_dir=td, resource_dir=td)
            gf = GuidesFrame(self.root, app, app_dir=td, resource_dir=td)
            gf.pack(fill="both", expand=True)
            gf.select_guide("big_guide")

            # Check that initial build built at most 15 cards
            self.assertLessEqual(len(gf.cards_by_guide.get("big_guide", [])), 15)

            # Wait for all batches to finish
            self._wait_for_guide(gf, "big_guide")
            built_cards = gf.cards_by_guide.get("big_guide", [])
            self.assertEqual(len(built_cards), 150)

            # Check card order 1..150
            card_numbers = [c.n for c in built_cards]
            self.assertEqual(card_numbers, list(range(1, 151)))

            # Check packed slaves are in order 1..150
            card_map = {c.border_frame: c.n for c in built_cards}
            packed_numbers = [card_map[s] for s in gf.cards_inner.pack_slaves() if s in card_map]
            self.assertEqual(packed_numbers, list(range(1, 151)))

    def test_batch_build_cancelled_on_guide_switch(self):
        """Part C: guide switch cancels or ignores stale batches."""
        with tempfile.TemporaryDirectory() as td:
            guides_dir = os.path.join(td, "guides")
            os.makedirs(guides_dir, exist_ok=True)
            entries1 = [{"n": i, "title": f"Guide1-{i}", "steps": f"Steps {i}"} for i in range(1, 50)]
            entries2 = [{"n": i, "title": f"Guide2-{i}", "steps": f"Steps {i}"} for i in range(1, 10)]
            with open(os.path.join(guides_dir, "g1.json"), "w", encoding="utf-8") as f:
                json.dump({"id": "g1", "title": "Guide 1", "total": 49, "entries": entries1}, f)
            with open(os.path.join(guides_dir, "g2.json"), "w", encoding="utf-8") as f:
                json.dump({"id": "g2", "title": "Guide 2", "total": 9, "entries": entries2}, f)

            app = DummyApp(app_dir=td, resource_dir=td)
            gf = GuidesFrame(self.root, app, app_dir=td, resource_dir=td)
            gf.pack(fill="both", expand=True)

            gf.select_guide("g1")
            # Immediately switch to g2 before g1 finishes background batches
            gf.select_guide("g2")
            self._wait_for_guide(gf, "g2")

            self.assertEqual(gf.current_guide["id"], "g2")
            g2_slaves = [s for s in gf.cards_inner.pack_slaves() if s in {c.border_frame for c in gf.cards_by_guide.get("g2", [])}]
            self.assertEqual(len(g2_slaves), 9)

            g1_slaves = [s for s in gf.cards_inner.pack_slaves() if s in {c.border_frame for c in gf.cards_by_guide.get("g1", [])}]
            self.assertEqual(len(g1_slaves), 0)

    def test_destroy_cancels_pending_batch_job(self):
        """Part C: destroy() cancels any pending _batch_job."""
        with tempfile.TemporaryDirectory() as td:
            guides_dir = os.path.join(td, "guides")
            os.makedirs(guides_dir, exist_ok=True)
            entries = [{"n": i, "title": f"Entry {i}", "steps": f"Steps {i}"} for i in range(1, 50)]
            with open(os.path.join(guides_dir, "big.json"), "w", encoding="utf-8") as f:
                json.dump({"id": "big", "title": "Big Guide", "total": 49, "entries": entries}, f)

            app = DummyApp(app_dir=td, resource_dir=td)
            gf = GuidesFrame(self.root, app, app_dir=td, resource_dir=td)
            gf.pack(fill="both", expand=True)
            gf.select_guide("big")
            self.assertIsNotNone(gf._batch_job)
            gf.destroy()
            self.assertIsNone(gf._batch_job)

    def test_area_filter_applies_when_tab_hidden(self):
        """Part B: Area filter uses _has_groups so chosen area works even when hidden."""
        with tempfile.TemporaryDirectory() as td:
            guides_dir = os.path.join(td, "guides")
            os.makedirs(guides_dir, exist_ok=True)
            with open(os.path.join(guides_dir, "grouped.json"), "w", encoding="utf-8") as f:
                json.dump({
                    "id": "grouped",
                    "title": "Grouped",
                    "total": 3,
                    "entries": [
                        {"n": 1, "group": "Area A", "title": "E1", "steps": "S1"},
                        {"n": 2, "group": "Area B", "title": "E2", "steps": "S2"},
                        {"n": 3, "group": "Area A", "title": "E3", "steps": "S3"},
                    ]
                }, f)

            app = DummyApp(app_dir=td, resource_dir=td)
            gf = GuidesFrame(self.root, app, app_dir=td, resource_dir=td)
            gf.pack(fill="both", expand=True)
            gf.select_guide("grouped")
            self._wait_for_guide(gf, "grouped")

            self.assertTrue(gf._has_groups)
            self.assertFalse(gf.lbl_area.winfo_ismapped())

            gf.combo_area.set("Area A")
            gf._apply_filters(reset_scroll=True)

            card_map = {c.border_frame: c.n for c in gf.cards_by_guide["grouped"]}
            visible_ns = [card_map[s] for s in gf.cards_inner.pack_slaves() if s in card_map]
            self.assertEqual(visible_ns, [1, 3])

            gf._check_all()
            self.assertIn(1, gf.checked_set)
            self.assertIn(3, gf.checked_set)
            self.assertNotIn(2, gf.checked_set)


    def test_no_cards_at_startup_until_guides_shown(self):
        """No cards exist after constructing the app until the Guides tab is shown."""
        try:
            probe = tk.Tk()
            probe.destroy()
        except tk.TclError:
            raise unittest.SkipTest("Tk display not available")

        from oot_save_editor import OOTEditor
        app = OOTEditor()
        try:
            app.withdraw()
            # Ensure another notebook tab (e.g. index 0) is selected and flush pending startup events
            app.notebook.select(0)
            app.update()
            self.assertTrue(hasattr(app, "guides_frame"))
            gf = app.guides_frame
            total_cards = sum(len(c) for c in gf.cards_by_guide.values())
            self.assertEqual(total_cards, 0, "No cards should exist after startup update before Guides tab is shown")

            guides_tab_index = None
            for idx, tab_id in enumerate(app.notebook.tabs()):
                if app.notebook.tab(tab_id, "text") == "Guides":
                    guides_tab_index = idx
                    break
            self.assertIsNotNone(guides_tab_index, "Guides tab should exist in notebook")

            app.notebook.select(guides_tab_index)
            app.update()

            first_id = gf.current_guide["id"]
            built = gf.cards_by_guide.get(first_id, [])
            self.assertGreater(len(built), 0, "Cards must be built once Guides tab is selected/shown")
        finally:
            app.destroy()

    def test_batches_keep_entry_order_with_headings(self):
        """Batches append cards in entry order and keep group headings positioned before their group."""
        with tempfile.TemporaryDirectory() as td:
            guides_dir = os.path.join(td, "guides")
            os.makedirs(guides_dir, exist_ok=True)
            entries = []
            for i in range(1, 41):
                if i <= 12:
                    grp = "Area One"
                elif i <= 28:
                    grp = "Area Two"
                else:
                    grp = "Area Three"
                entries.append({"n": i, "group": grp, "title": f"Entry {i}", "steps": f"Steps {i}"})

            with open(os.path.join(guides_dir, "order_test.json"), "w", encoding="utf-8") as f:
                json.dump({
                    "id": "order_test",
                    "title": "Order Test Guide",
                    "total": 40,
                    "entries": entries
                }, f)

            app = DummyApp(app_dir=td, resource_dir=td)
            gf = GuidesFrame(self.root, app, app_dir=td, resource_dir=td)
            gf.pack(fill="both", expand=True)
            gf.select_guide("order_test")
            self._wait_for_guide(gf, "order_test")

            cards = gf.cards_by_guide.get("order_test", [])
            self.assertEqual(len(cards), 40)
            card_map = {c.border_frame: c.n for c in cards}
            slaves = gf.cards_inner.pack_slaves()
            packed_numbers = [card_map[s] for s in slaves if s in card_map]
            self.assertEqual(packed_numbers, list(range(1, 41)), "Cards must remain packed in strict 1..40 order")

            headings = gf.headings_by_guide.get("order_test", {})
            self.assertIn("Area One", headings)
            self.assertIn("Area Two", headings)
            self.assertIn("Area Three", headings)

            h1_idx = slaves.index(headings["Area One"].frame)
            c1_idx = slaves.index(cards[0].border_frame)
            self.assertLess(h1_idx, c1_idx)

            h2_idx = slaves.index(headings["Area Two"].frame)
            c13_idx = slaves.index(cards[12].border_frame)
            self.assertLess(h2_idx, c13_idx)
            self.assertGreater(h2_idx, slaves.index(cards[11].border_frame))

            h3_idx = slaves.index(headings["Area Three"].frame)
            c29_idx = slaves.index(cards[28].border_frame)
            self.assertLess(h3_idx, c29_idx)
            self.assertGreater(h3_idx, slaves.index(cards[27].border_frame))

    def test_filter_after_full_build_still_correct(self):
        """Full filter pass after all batches have built correctly filters and restores card views."""
        with tempfile.TemporaryDirectory() as td:
            guides_dir = os.path.join(td, "guides")
            os.makedirs(guides_dir, exist_ok=True)
            entries = []
            for i in range(1, 35):
                era = "Child" if i % 2 == 1 else "Adult"
                entries.append({"n": i, "era": era, "title": f"Entry {i}", "steps": f"Steps {i}"})

            with open(os.path.join(guides_dir, "filter_full.json"), "w", encoding="utf-8") as f:
                json.dump({
                    "id": "filter_full",
                    "title": "Filter Full Test",
                    "total": 34,
                    "entries": entries
                }, f)

            app = DummyApp(app_dir=td, resource_dir=td)
            gf = GuidesFrame(self.root, app, app_dir=td, resource_dir=td)
            gf.pack(fill="both", expand=True)
            gf.select_guide("filter_full")
            self._wait_for_guide(gf, "filter_full")

            cards = gf.cards_by_guide.get("filter_full", [])
            self.assertEqual(len(cards), 34)

            # Filter Era: Adult (2, 4, 6... 34)
            gf.combo_era.set("Adult")
            gf._apply_filters(reset_scroll=True)
            self.root.update()

            card_map = {c.border_frame: c.n for c in cards}
            visible_ns = [card_map[s] for s in gf.cards_inner.pack_slaves() if s in card_map]
            expected_adult = [i for i in range(1, 35) if i % 2 == 0]
            self.assertEqual(visible_ns, expected_adult)

            # Reset back to All
            gf.combo_era.set("All")
            gf._apply_filters(reset_scroll=True)
            self.root.update()

            visible_ns_all = [card_map[s] for s in gf.cards_inner.pack_slaves() if s in card_map]
            self.assertEqual(visible_ns_all, list(range(1, 35)))

    def test_no_image_shows_no_placeholder(self):
        """When an entry has no bundled image, no placeholder canvas or buttons are shown."""
        with tempfile.TemporaryDirectory() as td:
            guides_dir = os.path.join(td, "guides")
            os.makedirs(guides_dir, exist_ok=True)
            with open(os.path.join(guides_dir, "no_img.json"), "w", encoding="utf-8") as f:
                json.dump({
                    "id": "no_img",
                    "title": "No Image Guide",
                    "total": 1,
                    "entries": [
                        {"n": 1, "title": "Entry without image", "steps": "Step 1"}
                    ]
                }, f)

            app = DummyApp(app_dir=td, resource_dir=td)
            gf = GuidesFrame(self.root, app, app_dir=td, resource_dir=td)
            gf.pack(fill="both", expand=True)
            gf.select_guide("no_img")
            self._wait_for_guide(gf, "no_img")

            card = gf.cards_by_guide["no_img"][0]
            self.assertIsNone(card.ss_display, "ss_display must be None when no image is present")
            self.assertEqual(card.ss_frame.winfo_manager(), "", "ss_frame must not be packed when no image is present")

    def test_no_apply_filters_calls_from_batch_callbacks_during_plain_build(self):
        """Plain build of 150-entry synthetic guide does not call _apply_filters from batch callbacks."""
        with tempfile.TemporaryDirectory() as td:
            guides_dir = os.path.join(td, "guides")
            os.makedirs(guides_dir, exist_ok=True)
            entries = [{"n": i, "title": f"Entry {i}", "steps": f"Steps for entry {i}"} for i in range(1, 151)]
            with open(os.path.join(guides_dir, "big_guide.json"), "w", encoding="utf-8") as f:
                json.dump({
                    "id": "big_guide",
                    "title": "Big Synthetic Guide",
                    "total": 150,
                    "entries": entries
                }, f)

            app = DummyApp(app_dir=td, resource_dir=td)
            gf = GuidesFrame(self.root, app, app_dir=td, resource_dir=td)
            gf.pack(fill="both", expand=True)

            apply_filter_calls = 0
            orig_apply_filters = gf._apply_filters

            def counted_apply_filters(*args, **kwargs):
                nonlocal apply_filter_calls
                apply_filter_calls += 1
                return orig_apply_filters(*args, **kwargs)

            gf._apply_filters = counted_apply_filters

            gf.select_guide("big_guide")
            self._wait_for_guide(gf, "big_guide")

            built_cards = gf.cards_by_guide.get("big_guide", [])
            self.assertEqual(len(built_cards), 150)
            self.assertEqual(apply_filter_calls, 0, "Expected 0 _apply_filters calls from batch callbacks during plain build")

    def test_on_slot_changed_refreshes_filters_when_status_not_all(self):
        """Changing save slot reapplies filters when Status filter is not 'All' so cards do not go stale."""
        with tempfile.TemporaryDirectory() as td:
            guides_dir = os.path.join(td, "guides")
            os.makedirs(guides_dir, exist_ok=True)
            entries = [
                {"n": 1, "title": "Entry 1", "steps": "Step 1"},
                {"n": 2, "title": "Entry 2", "steps": "Step 2"},
            ]
            with open(os.path.join(guides_dir, "slot_filter_test.json"), "w", encoding="utf-8") as f:
                json.dump({
                    "id": "slot_filter_test",
                    "title": "Slot Filter Test Guide",
                    "total": 2,
                    "entries": entries
                }, f)

            app = DummyApp(app_dir=td, resource_dir=td)
            slot1_dir = os.path.join(td, "slot1")
            slot2_dir = os.path.join(td, "slot2")
            os.makedirs(slot1_dir, exist_ok=True)
            os.makedirs(slot2_dir, exist_ok=True)

            slot1_key = os.path.normpath(os.path.abspath(slot1_dir))
            slot2_key = os.path.normpath(os.path.abspath(slot2_dir))

            # slot 1 has entry 1 checked; slot 2 has entry 2 checked
            app.settings = {
                "guide_checks": {
                    slot1_key: {"slot_filter_test": [1]},
                    slot2_key: {"slot_filter_test": [2]},
                }
            }

            Slot = type("Slot", (), {})
            slot1 = Slot()
            slot1.slot_dir = slot1_dir
            slot2 = Slot()
            slot2.slot_dir = slot2_dir

            app.active_slot = slot1

            gf = GuidesFrame(self.root, app, app_dir=td, resource_dir=td)
            gf.pack(fill="both", expand=True)
            gf.select_guide("slot_filter_test")
            self._wait_for_guide(gf, "slot_filter_test")

            # Set status filter to "Checked"
            gf.combo_status.set("Checked")
            gf._apply_filters(reset_scroll=True)
            self.root.update()

            cards = gf.cards_by_guide["slot_filter_test"]
            card_map = {c.border_frame: c.n for c in cards}

            visible_on_slot1 = [card_map[s] for s in gf.cards_inner.pack_slaves() if s in card_map]
            self.assertEqual(visible_on_slot1, [1])

            # Switch to slot 2 and invoke on_slot_changed
            app.active_slot = slot2
            gf.on_slot_changed()
            self.root.update()

            visible_on_slot2 = [card_map[s] for s in gf.cards_inner.pack_slaves() if s in card_map]
            self.assertEqual(visible_on_slot2, [2])


class TestAdaptiveGeometry(unittest.TestCase):
    def test_adaptive_geometry_1920x1080(self):
        from oot_save_editor import compute_adaptive_geometry
        # 1920x1080 standard screen
        w, h, min_w, min_h = compute_adaptive_geometry(1920, 1080, 1000, 700)
        self.assertEqual((w, h, min_w, min_h), (1060, 780, 920, 620))

    def test_adaptive_geometry_1366x768(self):
        from oot_save_editor import compute_adaptive_geometry
        # 1366x768 screen where height is clamped to 92% screen cap (706)
        w, h, min_w, min_h = compute_adaptive_geometry(1366, 768, 1000, 700)
        self.assertEqual((w, h, min_w, min_h), (1060, 706, 920, 620))

    def test_adaptive_geometry_1024x768(self):
        from oot_save_editor import compute_adaptive_geometry
        # 1024x768 screen where both width (942) and height (706) are clamped to 92% screen cap
        w, h, min_w, min_h = compute_adaptive_geometry(1024, 768, 1000, 700)
        self.assertEqual((w, h, min_w, min_h), (942, 706, 920, 620))

    def test_adaptive_geometry_huge_needed_size(self):
        from oot_save_editor import compute_adaptive_geometry
        # Huge needed size on 1920x1080 clamped to 92% screen cap (1766x993)
        w, h, min_w, min_h = compute_adaptive_geometry(1920, 1080, 5000, 4000)
        self.assertEqual((w, h, min_w, min_h), (1766, 993, 920, 620))


if __name__ == "__main__":
    unittest.main()
