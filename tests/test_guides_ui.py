import os
import sys
import unittest
import tempfile
import json
import tkinter as tk
from tkinter import ttk

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from oot_guides import GuidesFrame, save_screenshot_image, PIL_AVAILABLE

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

    def test_filter_order(self):
        """a) Filter order: check 2 and 5, filter Checked, then All; assert packed cards are 1..36 in order."""
        app = DummyApp(app_dir=REPO_ROOT, resource_dir=REPO_ROOT)
        gf = GuidesFrame(self.root, app, app_dir=REPO_ROOT, resource_dir=REPO_ROOT)
        gf.pack(fill="both", expand=True)
        gf.select_guide("heart_pieces")
        self.root.update()

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
            self.root.update()
            self.assertEqual(len(gf.cards_inner.pack_slaves()), 36)

            # Select second_guide
            gf.select_guide("second_guide")
            self.root.update()

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
        self.root.update()

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
        self.root.update()

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


class TestScreenshotHelper(unittest.TestCase):
    def test_transparency_atomic_save(self):
        """d) Transparency/atomic-save helper: RGBA PNG round-trips with alpha kept."""
        if not PIL_AVAILABLE or save_screenshot_image is None:
            raise unittest.SkipTest("Pillow not installed or save_screenshot_image not defined")

        with tempfile.TemporaryDirectory() as td:
            src_path = os.path.join(td, "test_input.png")
            dest_path = os.path.join(td, "dest_subdir", "test_output.png")

            # Create an RGBA image with partial transparency
            img = Image.new("RGBA", (100, 80), (255, 128, 0, 160))
            # Put a fully transparent pixel and an opaque pixel
            img.putpixel((0, 0), (0, 0, 0, 0))
            img.putpixel((1, 1), (50, 100, 150, 255))
            img.save(src_path, "PNG")

            save_screenshot_image(src_path, dest_path)

            self.assertTrue(os.path.exists(dest_path), "Destination file should exist")

            with Image.open(dest_path) as saved_img:
                self.assertEqual(saved_img.mode, "RGBA", "Saved image must preserve RGBA mode")
                self.assertEqual(saved_img.getpixel((0, 0))[3], 0, "Fully transparent alpha must be 0")
                self.assertEqual(saved_img.getpixel((1, 1))[3], 255, "Opaque alpha must be 255")
                self.assertEqual(saved_img.getpixel((10, 10))[3], 160, "Partial alpha must be 160")


if __name__ == "__main__":
    unittest.main()
