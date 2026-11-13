"""Tests for Scarecrow's Song save data handling, validation, and encoding."""

import os
import struct
import sys
import unittest

# Ensure isolation and repo root on sys.path
import tests._isolate

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import tkinter as tk

import oot_scarecrow
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


class TestScarecrowSong(unittest.TestCase):
    """Test Scarecrow's Song binary reading/writing, states, validation, and labels."""

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

    def _make_fake_buffer(self, offset_a=16, count=8, notes=None, buf_size=128):
        """Create a synthetic progress buffer with a field table entry pointing at count and notes."""
        buf = bytearray(buf_size)
        val_offset = 4
        p_fields = {oot_scarecrow.NOTE_FIELD: val_offset}
        struct.pack_into("<I", buf, val_offset, offset_a)
        if offset_a + 4 <= buf_size:
            struct.pack_into("<I", buf, offset_a, count)
        if notes and offset_a + 4 + len(notes) * 4 <= buf_size:
            for i, n in enumerate(notes):
                struct.pack_into("<I", buf, offset_a + 4 + 4 * i, n)
        return buf, p_fields

    def test_read_write_round_trip(self):
        """Round trip read/write on a fake buffer leaves count and buffer length unchanged."""
        initial_notes = [0] * 8
        buf, p_fields = self._make_fake_buffer(offset_a=16, count=8, notes=initial_notes, buf_size=128)
        initial_len = len(buf)

        read_back = oot_scarecrow.read_notes(buf, p_fields)
        self.assertEqual(read_back, [0, 0, 0, 0, 0, 0, 0, 0])

        new_notes = [7, 11, 7, 11, 7, 11, 7, 11]
        success = oot_scarecrow.write_notes(buf, p_fields, new_notes)
        self.assertTrue(success)

        read_new = oot_scarecrow.read_notes(buf, p_fields)
        self.assertEqual(read_new, new_notes)

        # Count at offset A must remain 8
        count = struct.unpack_from("<I", buf, 16)[0]
        self.assertEqual(count, 8)
        # Buffer length must be unchanged
        self.assertEqual(len(buf), initial_len)

    def test_invalid_layouts_rejected(self):
        """Missing field, wrong count, and out-of-range offsets return None/False and do not write."""
        initial_notes = [4, 7, 11, 13, 16, 4, 7, 11]
        buf, p_fields = self._make_fake_buffer(offset_a=16, count=8, notes=initial_notes, buf_size=128)
        buf_before = bytearray(buf)

        # 1. Missing field
        self.assertIsNone(oot_scarecrow.read_notes(buf, {}))
        self.assertFalse(oot_scarecrow.write_notes(buf, {}, [1] * 8))
        self.assertEqual(buf, buf_before)

        # 2. Count 7 instead of 8
        buf_c7, p_fields_c7 = self._make_fake_buffer(offset_a=16, count=7, notes=[0] * 7, buf_size=128)
        buf_c7_before = bytearray(buf_c7)
        self.assertIsNone(oot_scarecrow.read_notes(buf_c7, p_fields_c7))
        self.assertFalse(oot_scarecrow.write_notes(buf_c7, p_fields_c7, [7] * 8))
        self.assertEqual(buf_c7, buf_c7_before)

        # 3. Offset A completely out of range
        buf_oor, p_fields_oor = self._make_fake_buffer(offset_a=200, count=8, buf_size=128)
        buf_oor_before = bytearray(buf_oor)
        self.assertIsNone(oot_scarecrow.read_notes(buf_oor, p_fields_oor))
        self.assertFalse(oot_scarecrow.write_notes(buf_oor, p_fields_oor, [7] * 8))
        self.assertEqual(buf_oor, buf_oor_before)

        # 4. Offset A near end so values overflow buffer
        buf_trunc, p_fields_trunc = self._make_fake_buffer(offset_a=110, count=8, buf_size=128)
        self.assertIsNone(oot_scarecrow.read_notes(buf_trunc, p_fields_trunc))
        self.assertFalse(oot_scarecrow.write_notes(buf_trunc, p_fields_trunc, [7] * 8))

    def test_values_outside_range_rejected(self):
        """Note values < 0 or > 19 are rejected by write_notes without modifying the buffer."""
        buf, p_fields = self._make_fake_buffer(offset_a=16, count=8, notes=[0] * 8, buf_size=128)
        buf_before = bytearray(buf)

        # Value 20 is outside 0..19
        self.assertFalse(oot_scarecrow.write_notes(buf, p_fields, [7, 11, 7, 11, 7, 11, 7, 20]))
        self.assertEqual(buf, buf_before)

        # Negative value
        self.assertFalse(oot_scarecrow.write_notes(buf, p_fields, [-1, 11, 7, 11, 7, 11, 7, 11]))
        self.assertEqual(buf, buf_before)

        # Wrong length
        self.assertFalse(oot_scarecrow.write_notes(buf, p_fields, [7] * 7))
        self.assertFalse(oot_scarecrow.write_notes(buf, p_fields, [7] * 9))
        self.assertEqual(buf, buf_before)

    def test_state_from_flags(self):
        """state_from_flags resolves all three states correctly based on flag hashes."""
        # 1. Learned when 0x5E86FB4D is set
        get_learned = lambda h: 1 if h == oot_scarecrow.FLAG_IS_GET_SCARECROW else 0
        self.assertEqual(oot_scarecrow.state_from_flags(get_learned), "Learned")

        # 2. Taught (child) when either child flag is set and learned flag is unset
        get_child_bonooru = lambda h: 1 if h == oot_scarecrow.FLAG_ASK_BONOORU else 0
        self.assertEqual(oot_scarecrow.state_from_flags(get_child_bonooru), "Taught (child)")

        get_child_pierre = lambda h: 1 if h == oot_scarecrow.FLAG_ASK_PIERRE else 0
        self.assertEqual(oot_scarecrow.state_from_flags(get_child_pierre), "Taught (child)")

        # 3. Not taught when neither learned nor child flags are set
        get_not_taught = lambda h: 0
        self.assertEqual(oot_scarecrow.state_from_flags(get_not_taught), "Not taught")

    def test_flag_writes(self):
        """flag_writes produces correct 0/1 values for all 6 flags across all three states."""
        # 1. Not taught: all 6 flags = 0
        fw_not = oot_scarecrow.flag_writes("Not taught")
        self.assertEqual(len(fw_not), 6)
        for h in oot_scarecrow.CHILD_FLAGS:
            self.assertEqual(fw_not[h], 0)
        for h in oot_scarecrow.ADULT_FLAGS:
            self.assertEqual(fw_not[h], 0)

        # 2. Taught (child): CHILD = 1, ADULT = 0
        fw_taught = oot_scarecrow.flag_writes("Taught (child)")
        self.assertEqual(len(fw_taught), 6)
        for h in oot_scarecrow.CHILD_FLAGS:
            self.assertEqual(fw_taught[h], 1)
        for h in oot_scarecrow.ADULT_FLAGS:
            self.assertEqual(fw_taught[h], 0)

        # 3. Learned: CHILD = 1, ADULT = 1
        fw_learned = oot_scarecrow.flag_writes("Learned")
        self.assertEqual(len(fw_learned), 6)
        for h in oot_scarecrow.CHILD_FLAGS:
            self.assertEqual(fw_learned[h], 1)
        for h in oot_scarecrow.ADULT_FLAGS:
            self.assertEqual(fw_learned[h], 1)

    def test_validate(self):
        """Validation enforces non-zero notes for taught/learned and warns on existing song melodies."""
        # Empty slot in Learned -> error naming empty slot
        errs, warns = oot_scarecrow.validate("Learned", [7, 11, 0, 11, 7, 11, 7, 11])
        self.assertTrue(len(errs) > 0)
        self.assertTrue(any("slot 3" in e.lower() for e in errs))

        # Empty slot in Taught (child) -> error
        errs_t, warns_t = oot_scarecrow.validate("Taught (child)", [0, 11, 7, 11, 7, 11, 7, 11])
        self.assertTrue(len(errs_t) > 0)
        self.assertTrue(any("slot 1" in e.lower() for e in errs_t))

        # Not taught with empty notes -> no error
        errs_nt, warns_nt = oot_scarecrow.validate("Not taught", [0, 0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(len(errs_nt), 0)
        self.assertEqual(len(warns_nt), 0)

        # Valid notes without song clash -> no error, no warning
        valid_notes = [7, 11, 7, 11, 7, 11, 7, 11]
        errs_v, warns_v = oot_scarecrow.validate("Learned", valid_notes)
        self.assertEqual(len(errs_v), 0)
        self.assertEqual(len(warns_v), 0)

        # Notes containing Song of Time [11, 4, 7, 11, 4, 7] -> warning
        sot_notes = [11, 4, 7, 11, 4, 7, 7, 11]
        errs_sot, warns_sot = oot_scarecrow.validate("Learned", sot_notes)
        self.assertEqual(len(errs_sot), 0)
        self.assertTrue(any("Song of Time" in w for w in warns_sot))

    def test_lane_real_song_decodes(self):
        """Lane's real song [7, 11, 7, 11, 7, 11, 7, 11] decodes to Down, Right repeated."""
        notes = [7, 11, 7, 11, 7, 11, 7, 11]
        labels = [oot_scarecrow.NOTE_LABELS[n] for n in notes]
        expected = [oot_scarecrow.BUTTON_LABELS[n] for n in notes]
        self.assertEqual(labels, expected)

        # Helper note_label function also matches
        helper_labels = [oot_scarecrow.note_label(n) for n in notes]
        self.assertEqual(helper_labels, expected)

    def test_unknown_note_label_and_bent_notes(self):
        """Unknown note values format as '? (<n>)' and bent notes contain '(bent)'."""
        self.assertEqual(oot_scarecrow.note_label(25), "? (25)")
        self.assertEqual(oot_scarecrow.note_label(0), "-")
        self.assertEqual(oot_scarecrow.note_label(4), oot_scarecrow.BUTTON_LABELS[4])
        self.assertEqual(oot_scarecrow.note_label(7), oot_scarecrow.BUTTON_LABELS[7])
        self.assertEqual(oot_scarecrow.note_label(11), oot_scarecrow.BUTTON_LABELS[11])
        self.assertEqual(oot_scarecrow.note_label(13), oot_scarecrow.BUTTON_LABELS[13])
        self.assertEqual(oot_scarecrow.note_label(16), oot_scarecrow.BUTTON_LABELS[16])
        self.assertEqual(oot_scarecrow.note_label(8), f"{oot_scarecrow.PITCH_NAMES[8]} (bent)")
        self.assertEqual(oot_scarecrow.note_label(1), f"{oot_scarecrow.PITCH_NAMES[1]} (bent)")

    def test_picker_order_and_labels(self):
        """PICKER_ORDER is a plain list of ints, PICKER_LABELS is a plain list of strings."""
        self.assertIs(type(oot_scarecrow.PICKER_ORDER), list)
        self.assertIs(type(oot_scarecrow.PICKER_LABELS), list)
        self.assertTrue(all(isinstance(v, int) for v in oot_scarecrow.PICKER_ORDER))
        self.assertTrue(all(isinstance(l, str) for l in oot_scarecrow.PICKER_LABELS))
        self.assertEqual(oot_scarecrow.PICKER_ORDER, [4, 7, 11, 16, 13])
        self.assertEqual(oot_scarecrow.PICKER_LABELS, ["L", "R", "A", "X", "Y"])
        self.assertEqual(
            oot_scarecrow.PICKER_LABELS,
            [oot_scarecrow.NOTE_LABELS[v] for v in oot_scarecrow.PICKER_ORDER],
        )

    def test_validate_rejects_bent_notes_and_accepts_plain(self):
        """A changed song with a bent note is an error; plain button notes pass."""
        plain = [4, 7, 11, 16, 13, 4, 7, 11]
        errors, _ = oot_scarecrow.validate("Learned", plain)
        self.assertEqual(errors, [])
        bent = list(plain)
        bent[2] = 5
        errors, _ = oot_scarecrow.validate("Learned", bent)
        self.assertEqual(len(errors), 1)
        self.assertIn("Slot 3 has a bent note", errors[0])
        self.assertIn("Use L, R, A, X or Y.", errors[0])
        errors, _, do_write, _ = oot_scarecrow.save_plan("Learned", plain, "Learned", bent)
        self.assertTrue(errors)
        self.assertFalse(do_write)

    def test_guides_has_song_scarecrow(self):
        """oot_guides has_song uses scarecrow_state_var only when scarecrow_available is True."""
        class FakeSaveSlot:
            def __init__(self, flags):
                self.flags = flags
                self.loaded = True

            def get(self, h, default=0):
                return self.flags.get(h, default)

        # When scarecrow_available is False, only save flag 0x5E86FB4D determines bit 13
        s_taught = FakeSaveSlot({0xFDF0F4B8: 1, 0x8C1DA521: 1, 0x3A4126EC: 1})
        app = DummyApp(slot=s_taught)
        app.scarecrow_available = False
        if self.root:
            gf = GuidesFrame(self.root, app, app_dir=REPO_ROOT, resource_dir=REPO_ROOT)
        else:
            gf = GuidesFrame.__new__(GuidesFrame)
            gf.app = app
        auto_taught = gf.compute_auto_checked_entries("songs")
        self.assertNotIn(13, auto_taught)

        # When scarecrow_available is False and 0x5E86FB4D is set, bit 13 is checked
        s_learned = FakeSaveSlot({0x5E86FB4D: 1})
        app.active_slot = s_learned
        auto_learned = gf.compute_auto_checked_entries("songs")
        self.assertIn(13, auto_learned)

        # When scarecrow_available is True, scarecrow_state_var controls bit 13
        app.scarecrow_available = True
        app.scarecrow_state_var = tk.StringVar(value="Not taught")
        # Even if slot flag 0x5E86FB4D is 1, UI state "Not taught" overrides it
        auto_ui_not = gf.compute_auto_checked_entries("songs")
        self.assertNotIn(13, auto_ui_not)

        app.scarecrow_state_var.set("Learned")
        auto_ui_learned = gf.compute_auto_checked_entries("songs")
        self.assertIn(13, auto_ui_learned)

    def test_save_plan_unchanged(self):
        """Unchanged state and notes produces no validation errors/warnings and no writes."""
        notes = [7, 11, 7, 11, 7, 11, 7, 11]
        self.assertFalse(oot_scarecrow.scarecrow_changed("Learned", notes, "Learned", notes))
        errs, warns, write_notes, flags = oot_scarecrow.save_plan("Learned", notes, "Learned", notes)
        self.assertEqual(errs, [])
        self.assertEqual(warns, [])
        self.assertFalse(write_notes)
        self.assertEqual(flags, {})

    def test_save_plan_not_taught_game_song(self):
        """Saving as 'Not taught' with game-song notes produces no warning and writes zeros."""
        orig_notes = [7, 11, 7, 11, 7, 11, 7, 11]
        # Melody containing Zelda's Lullaby [13, 16, 11, 13, 16, 11]
        cur_notes = [13, 16, 11, 13, 16, 11, 4, 7]
        self.assertTrue(oot_scarecrow.scarecrow_changed("Learned", orig_notes, "Not taught", cur_notes))

        errs, warns, write_notes, flags = oot_scarecrow.save_plan(
            "Learned", orig_notes, "Not taught", cur_notes
        )
        self.assertEqual(errs, [])
        self.assertEqual(warns, [])
        self.assertTrue(write_notes)
        self.assertEqual(flags, oot_scarecrow.flag_writes("Not taught"))

        # Notes written must be zeros
        to_write = oot_scarecrow.notes_to_write("Not taught", cur_notes)
        self.assertEqual(to_write, [0] * 8)

        # Verify writing to buffer clears notes to zeros
        buf, p_fields = self._make_fake_buffer(offset_a=16, count=8, notes=orig_notes)
        ok = oot_scarecrow.write_notes(buf, p_fields, to_write)
        self.assertTrue(ok)
        self.assertEqual(oot_scarecrow.read_notes(buf, p_fields), [0] * 8)

    def test_save_plan_learned_note_25_rejected(self):
        """State 'Learned' with out-of-range note 25 gives error naming the slot and no writes."""
        orig_notes = [0] * 8
        cur_notes = [7, 11, 7, 11, 7, 11, 7, 25]
        errs, warns, write_notes, flags = oot_scarecrow.save_plan(
            "Not taught", orig_notes, "Learned", cur_notes
        )
        self.assertTrue(len(errs) > 0)
        self.assertTrue(any("slot 8" in e.lower() and "25" in e for e in errs))
        self.assertFalse(write_notes)
        self.assertEqual(flags, {})

    def test_save_plan_taught_empty_slot_rejected(self):
        """State 'Taught (child)' with empty note slot gives error naming slot and no writes."""
        orig_notes = [0] * 8
        cur_notes = [0, 11, 7, 11, 7, 11, 7, 11]
        errs, warns, write_notes, flags = oot_scarecrow.save_plan(
            "Not taught", orig_notes, "Taught (child)", cur_notes
        )
        self.assertTrue(len(errs) > 0)
        self.assertTrue(any("slot 1" in e.lower() for e in errs))
        self.assertFalse(write_notes)
        self.assertEqual(flags, {})

    def test_describe_changes_not_taught(self):
        """Changing to 'Not taught' reports '<old> -> Not taught (notes cleared)' without separate notes diff."""
        orig_notes = [7, 11, 7, 11, 7, 11, 7, 11]
        cur_notes = [0] * 8
        diffs = oot_scarecrow.describe_scarecrow_changes(
            "Learned", orig_notes, "Not taught", cur_notes
        )
        self.assertEqual(diffs, ["Scarecrow's Song: Learned -> Not taught (notes cleared)"])

        # When changing to Learned or Taught, notes diff is reported separately
        diffs_learned = oot_scarecrow.describe_scarecrow_changes(
            "Not taught", [0] * 8, "Learned", orig_notes
        )
        self.assertEqual(len(diffs_learned), 2)
        self.assertEqual(diffs_learned[0], "Scarecrow's Song: Not taught -> Learned")
        self.assertTrue(diffs_learned[1].startswith("Scarecrow's Song notes:"))

    def test_post_save_sync_re_read(self):
        """Post-save re-reading matches what is actually in the file buffer."""
        # When buffer notes are unchanged, read_notes returns existing notes
        buf, p_fields = self._make_fake_buffer(offset_a=16, count=8, notes=[7, 11, 7, 11, 7, 11, 7, 11])
        actual_notes = oot_scarecrow.read_notes(buf, p_fields)
        self.assertEqual(actual_notes, [7, 11, 7, 11, 7, 11, 7, 11])

        # When written with zeros, read_notes returns [0]*8 and labels are '-'
        oot_scarecrow.write_notes(buf, p_fields, [0] * 8)
        actual_zeros = oot_scarecrow.read_notes(buf, p_fields)
        self.assertEqual(actual_zeros, [0] * 8)
        self.assertEqual([oot_scarecrow.note_label(n) for n in actual_zeros], ["-"] * 8)


class TestSwitch2ButtonMapping(unittest.TestCase):
    """Pinned to the in-game song book (Lane's screenshots, 2026-11-11)."""

    def labels(self, notes):
        return " ".join(oot_scarecrow.note_label(n) for n in notes)

    def test_song_book_buttons(self):
        songs = oot_scarecrow.GAME_SONGS
        self.assertEqual(self.labels(songs["Zelda's Lullaby"]), "Y X A Y X A")
        self.assertEqual(self.labels(songs["Epona's Song"]), "X Y A X Y A")
        self.assertEqual(self.labels(songs["Saria's Song"]), "R A Y R A Y")
        self.assertEqual(self.labels(songs["Sun's Song"]), "A R X A R X")
        self.assertEqual(self.labels(songs["Song of Time"]), "A L R A L R")
        self.assertEqual(self.labels(songs["Song of Storms"]), "L R X L R X")
        self.assertEqual(self.labels(songs["Minuet of Forest"]), "L X Y A Y A")
        self.assertEqual(self.labels(songs["Bolero of Fire"]), "R L R L A R A R")
        self.assertEqual(self.labels(songs["Prelude of Light"]), "X A X A Y X")

    def test_lane_scarecrow_song(self):
        self.assertEqual(self.labels([7, 11, 7, 11, 7, 11, 7, 11]), "R A R A R A R A")


if __name__ == "__main__":
    unittest.main()

