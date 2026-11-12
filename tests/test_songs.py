"""
OOTSE-21 tests: songs use their own IsGet / HavePlayedGetEvent flags, never story flags,
and are written only when the user changed them.
"""

import os
import shutil
import struct
import sys
import tempfile
import unittest
import tkinter as tk

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import tests._isolate

try:
    _tk_probe = tk.Tk()
    _tk_probe.withdraw()
    _tk_probe.destroy()
except Exception as _tk_err:
    raise unittest.SkipTest(f"Tk GUI display is not available: {_tk_err}")

import oot_save_editor as se

# name -> (bit_idx, IsGet.Item_Melody_*, HavePlayedGetEvent.Item_Melody_*)
EXPECTED = {
    "Zelda's Lullaby": (0, 0x01C20002, 0xE1D07750),
    "Epona's Song": (1, 0xB492AC33, 0xF4E14AC4),
    "Saria's Song": (2, 0xD3F8BFCC, 0xF9EC2A28),
    "Song of Time": (3, 0x03B3450E, 0x99EC6052),
    "Sun's Song": (4, 0x165DD1AD, 0x56383EA6),
    "Song of Storms": (5, 0x2B39DD4F, 0x398A8D72),
    "Minuet of Forest": (6, 0xDC0A0B54, 0x035F129A),
    "Bolero of Fire": (7, 0x49041AB9, 0x570522B0),
    "Serenade of Water": (8, 0x3FA63986, 0xAF0CEB1A),
    "Requiem of Spirit": (9, 0x802A36A8, 0xB53851E0),
    "Nocturne of Shadow": (10, 0xC2FB95F4, 0xE631AD85),
    "Prelude of Light": (11, 0xD6320BA4, 0xEF7B5505),
}
TOMB = (0x4B415FBB, 0xCF7DAD5C, 0x3EAC8ADA)
STORY = TOMB + (0x0895A9FF, 0xBE4E744F, 0xDB8433F7)
SUN_ISGET, SUN_EVENT = 0x165DD1AD, 0x56383EA6


def _write_fake_slot(slot_dir, values):
    """Minimal progress.sav/caption.sav: header + one (hash, int) field per entry."""
    os.makedirs(slot_dir, exist_ok=True)
    p = bytearray(se.HEADER_END_PROGRESS)
    struct.pack_into("<III", p, 0, 0x01020304, 0x002D80EB, se.HEADER_END_PROGRESS)
    for i, (h, v) in enumerate(values.items()):
        struct.pack_into("<I", p, 40 + 8 * i, h)
        struct.pack_into("<i", p, 44 + 8 * i, v)
    c = bytearray(se.HEADER_END_CAPTION)
    struct.pack_into("<III", c, 0, 0x01020304, 0x002D80EB, se.HEADER_END_CAPTION)
    with open(os.path.join(slot_dir, "progress.sav"), "wb") as f:
        f.write(p)
    with open(os.path.join(slot_dir, "caption.sav"), "wb") as f:
        f.write(c)


class TestSongTable(unittest.TestCase):
    def test_songs_table_matches_game_fields(self):
        self.assertEqual(len(se.SONGS), 12)
        for name, bit, isget, event, _ in se.SONGS:
            self.assertEqual(EXPECTED[name], (bit, isget, event), name)
        used = {h for _, _, i, e, _ in se.SONGS for h in (i, e)}
        self.assertFalse(used & set(STORY))


class SongEditorBase(unittest.TestCase):
    VALUES = {}

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        values = {h: 0 for h in STORY}
        for _, _, i, e, _ in se.SONGS:
            values[i] = 0
            values[e] = 0
        values.update(self.VALUES)
        _write_fake_slot(os.path.join(self.tmp, "slot_00"), values)
        self.app = se.OOTEditor()
        self.app.withdraw()
        self.app.root_dir.set(self.tmp)
        self.app.slot_names = ["slot_00"]
        self.app.slot_box["values"] = ["slot_00"]
        self.app.slot_box.current(0)
        self.app.load_slot()
        self.assertTrue(self.app.active_slot.loaded)
        self.writes = []
        slot = self.app.active_slot
        real_set = slot.set
        slot.set = lambda h, v: (self.writes.append((h, v)), real_set(h, v))[1]
        self.app.make_backup = lambda *a, **k: None
        self.app.confirm_changes = lambda diffs: True
        self._orig_boxes = {n: getattr(se.messagebox, n) for n in ("showinfo", "showerror", "showwarning", "askyesno")}
        for n in self._orig_boxes:
            setattr(se.messagebox, n, lambda *a, **k: True)

    def tearDown(self):
        for n, f in self._orig_boxes.items():
            setattr(se.messagebox, n, f)
        try:
            self.app.destroy()
        except Exception:
            pass
        shutil.rmtree(self.tmp, ignore_errors=True)

    def force_save(self):
        self.app.describe_changes = lambda: [("forced", "a", "b")]
        self.app.save()

    def song_writes(self):
        song_hashes = {h for _, _, i, e, _ in se.SONGS for h in (i, e)}
        return {h: v for h, v in self.writes if h in song_hashes or h in STORY}


class TestTombFlagsDoNotLearnSunsSong(SongEditorBase):
    VALUES = {h: 1 for h in TOMB}

    def test_tomb_flags_alone_do_not_mean_learned(self):
        self.assertFalse(self.app.song_vars[4].get())


class TestIsGetLearnsSunsSong(SongEditorBase):
    VALUES = {SUN_ISGET: 1}

    def test_isget_means_learned(self):
        self.assertTrue(self.app.song_vars[4].get())

    def test_save_without_changes_writes_no_song_field(self):
        self.force_save()
        self.assertEqual(self.song_writes(), {})
        slot = se.SaveSlot(os.path.join(self.tmp, "slot_00"))
        self.assertEqual(slot.get(SUN_ISGET), 1)
        self.assertEqual(slot.get(SUN_EVENT), 0)
        for h in TOMB:
            self.assertEqual(slot.get(h), 0)


class TestLearningSunsSong(SongEditorBase):
    def test_learning_writes_only_its_own_two_flags(self):
        self.assertFalse(self.app.song_vars[4].get())
        self.app.song_vars[4].set(True)
        self.force_save()
        self.assertEqual(self.song_writes(), {SUN_ISGET: 1, SUN_EVENT: 1})
        for h in STORY:
            self.assertNotIn(h, self.song_writes())

    def test_unlearning_clears_only_its_own_two_flags(self):
        self.app.song_vars[4].set(True)
        self.force_save()
        self.writes.clear()
        self.app.song_vars[4].set(False)
        self.force_save()
        self.assertEqual(self.song_writes(), {SUN_ISGET: 0, SUN_EVENT: 0})


if __name__ == "__main__":
    unittest.main()
