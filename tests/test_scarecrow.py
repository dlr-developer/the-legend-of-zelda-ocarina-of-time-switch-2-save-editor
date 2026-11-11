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

import oot_scarecrow
from oot_guides import GuidesLoader


class TestScarecrowSong(unittest.TestCase):
    """Test Scarecrow's Song binary reading/writing, states, validation, and labels."""

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
        expected = ["Down", "Right", "Down", "Right", "Down", "Right", "Down", "Right"]
        self.assertEqual(labels, expected)

        # Helper note_label function also matches
        helper_labels = [oot_scarecrow.note_label(n) for n in notes]
        self.assertEqual(helper_labels, expected)

    def test_unknown_note_label_and_bent_notes(self):
        """Unknown note values format as '? (<n>)' and bent notes contain '(bent)'."""
        self.assertEqual(oot_scarecrow.note_label(25), "? (25)")
        self.assertEqual(oot_scarecrow.note_label(0), "-")
        self.assertEqual(oot_scarecrow.note_label(4), "A")
        self.assertEqual(oot_scarecrow.note_label(7), "Down")
        self.assertEqual(oot_scarecrow.note_label(11), "Right")
        self.assertEqual(oot_scarecrow.note_label(13), "Left")
        self.assertEqual(oot_scarecrow.note_label(16), "Up")
        self.assertEqual(oot_scarecrow.note_label(8), "F# (bent)")
        self.assertEqual(oot_scarecrow.note_label(1), "Low B (bent)")

    def test_guides_has_song_scarecrow(self):
        """oot_guides has_song returns True only when IsGet.Item_Melody_ScarecrowSong is set."""
        loader = GuidesLoader()

        class FakeSaveSlot:
            def __init__(self, flags):
                self.flags = flags

            def get(self, h, default=0):
                return self.flags.get(h, default)

        # When only child flags are set (0xFDF0F4B8 or 0x8C1DA521 or old 0x3A4126EC), not learned
        s_taught = FakeSaveSlot({0xFDF0F4B8: 1, 0x8C1DA521: 1, 0x3A4126EC: 1})
        auto_taught = loader.get_save_auto_checked(s_taught, "songs", app=None)
        self.assertNotIn(13, auto_taught)

        # When IsGet.Item_Melody_ScarecrowSong (0x5E86FB4D) is set, it is auto-checked
        s_learned = FakeSaveSlot({0x5E86FB4D: 1})
        auto_learned = loader.get_save_auto_checked(s_learned, "songs", app=None)
        self.assertIn(13, auto_learned)


if __name__ == "__main__":
    unittest.main()
