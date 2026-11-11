"""Unit tests for cheat file installation scanning, uninstallation, and save autodetection."""
import tests._isolate  # Must be imported first to isolate APPDATA and HOME

import os
import shutil
import sys
import tempfile
import unittest

# Ensure repo root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from oot_save_editor import (
    TITLE_ID,
    ALT_TITLE_IDS,
    ALL_TITLE_IDS,
    YUZU_FAMILY_EMULATORS,
    candidate_roots,
    all_emulators,
    installed_cheat_files,
    remove_installed_cheats,
    newest_save_mtime,
    pick_newest_save_folder,
)


class TestCheatInstall(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="oot_test_cheats_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_candidate_roots_includes_lichii(self):
        """candidate_roots must look for lichii alongside eden, yuzu, etc."""
        self.assertIn("lichii", YUZU_FAMILY_EMULATORS)

        # Setup a fake APPDATA with lichii save directory
        fake_appdata = os.path.join(self.test_dir, "fake_appdata")
        lichii_save = os.path.join(fake_appdata, "lichii", "nand", "user", "save")
        os.makedirs(lichii_save, exist_ok=True)

        orig_appdata = os.environ.get("APPDATA")
        try:
            os.environ["APPDATA"] = fake_appdata
            roots = candidate_roots()
            normalized = [os.path.normcase(os.path.abspath(r)) for r in roots]
            self.assertIn(os.path.normcase(os.path.abspath(lichii_save)), normalized)
        finally:
            if orig_appdata is not None:
                os.environ["APPDATA"] = orig_appdata
            else:
                os.environ.pop("APPDATA", None)

    def test_installed_cheat_files_eden_and_lichii(self):
        """installed_cheat_files finds files in fake eden and fake lichii roots and marks is_ours correctly."""
        eden_root = os.path.join(self.test_dir, "eden")
        lichii_root = os.path.join(self.test_dir, "lichii")

        eden_cheat_dir = os.path.join(
            eden_root, "load", TITLE_ID, "OOT Save Editor Cheats", "cheats"
        )
        lichii_cheat_dir = os.path.join(
            lichii_root, "load", TITLE_ID, "OOT Save Editor Cheats", "cheats"
        )
        os.makedirs(eden_cheat_dir, exist_ok=True)
        os.makedirs(lichii_cheat_dir, exist_ok=True)

        eden_cheat_file = os.path.join(eden_cheat_dir, "E0F3CCFAF50065AE.txt")
        with open(eden_cheat_file, "w", encoding="utf-8") as f:
            f.write("[Max Rupees]\n04000000 00000000 000003E7\n\n[Infinite Ammo]\n04000000 00000004 00000032\n")

        lichii_cheat_file = os.path.join(lichii_cheat_dir, "E0F3CCFAF50065AE.txt")
        with open(lichii_cheat_file, "w", encoding="utf-8") as f:
            f.write("[Moon Jump]\n04000000 00000008 00000001\n")

        results = installed_cheat_files(roots=[eden_root, lichii_root])
        self.assertEqual(len(results), 2)

        by_emu = {r["emulator"]: r for r in results}
        self.assertIn("eden", by_emu)
        self.assertIn("lichii", by_emu)

        # Check Eden entry
        e_entry = by_emu["eden"]
        self.assertEqual(os.path.normcase(os.path.abspath(e_entry["path"])), os.path.normcase(os.path.abspath(eden_cheat_file)))
        self.assertEqual(e_entry["build_id"], "E0F3CCFAF50065AE")
        self.assertEqual(e_entry["mod_folder"], "OOT Save Editor Cheats")
        self.assertTrue(e_entry["is_ours"])
        self.assertEqual(e_entry["names"], ["Max Rupees", "Infinite Ammo"])

        # Check Lichii entry
        l_entry = by_emu["lichii"]
        self.assertEqual(os.path.normcase(os.path.abspath(l_entry["path"])), os.path.normcase(os.path.abspath(lichii_cheat_file)))
        self.assertEqual(l_entry["build_id"], "E0F3CCFAF50065AE")
        self.assertEqual(l_entry["mod_folder"], "OOT Save Editor Cheats")
        self.assertTrue(l_entry["is_ours"])
        self.assertEqual(l_entry["names"], ["Moon Jump"])

    def test_installed_cheat_files_other_mod_folder(self):
        """A file in another mod folder is listed but has is_ours False."""
        eden_root = os.path.join(self.test_dir, "eden")
        other_cheat_dir = os.path.join(
            eden_root, "load", TITLE_ID, "Community Cheats Pack", "cheats"
        )
        os.makedirs(other_cheat_dir, exist_ok=True)
        other_cheat_file = os.path.join(other_cheat_dir, "E0F3CCFAF50065AE.txt")
        with open(other_cheat_file, "w", encoding="utf-8") as f:
            f.write("[Invincible]\n04000000 0000000C 00000001\n")

        results = installed_cheat_files(roots=[eden_root])
        self.assertEqual(len(results), 1)

        entry = results[0]
        self.assertEqual(entry["emulator"], "eden")
        self.assertEqual(entry["mod_folder"], "Community Cheats Pack")
        self.assertFalse(entry["is_ours"])
        self.assertEqual(entry["names"], ["Invincible"])
        self.assertEqual(entry["build_id"], "E0F3CCFAF50065AE")

    def test_remove_installed_cheats_deletes_only_ours_and_empty_folders(self):
        """uninstall-all helper deletes only is_ours files and removes only empty folders."""
        eden_root = os.path.join(self.test_dir, "eden")
        lichii_root = os.path.join(self.test_dir, "lichii")

        # 1. Eden: has our cheat file. After removal, cheats and OOT Save Editor Cheats should be deleted.
        eden_our_cheats = os.path.join(eden_root, "load", TITLE_ID, "OOT Save Editor Cheats", "cheats")
        os.makedirs(eden_our_cheats, exist_ok=True)
        eden_file = os.path.join(eden_our_cheats, "E0F3CCFAF50065AE.txt")
        with open(eden_file, "w", encoding="utf-8") as f:
            f.write("[Max Rupees]\n04000000 00000000 000003E7\n")

        # 2. Eden: also has another mod. Must NOT be deleted.
        eden_other_dir = os.path.join(eden_root, "load", TITLE_ID, "OtherMod", "cheats")
        os.makedirs(eden_other_dir, exist_ok=True)
        other_file = os.path.join(eden_other_dir, "OTHER.txt")
        with open(other_file, "w", encoding="utf-8") as f:
            f.write("[Other]\n04000000 00000000 00000001\n")

        # 3. Lichii: has our cheat file, BUT has an extra file in 'OOT Save Editor Cheats'.
        # cheats/ should be deleted when empty, but 'OOT Save Editor Cheats' should NOT be deleted.
        lichii_our_mod = os.path.join(lichii_root, "load", TITLE_ID, "OOT Save Editor Cheats")
        lichii_our_cheats = os.path.join(lichii_our_mod, "cheats")
        os.makedirs(lichii_our_cheats, exist_ok=True)
        lichii_file = os.path.join(lichii_our_cheats, "E0F3CCFAF50065AE.txt")
        with open(lichii_file, "w", encoding="utf-8") as f:
            f.write("[Moon Jump]\n04000000 00000008 00000001\n")
        extra_file = os.path.join(lichii_our_mod, "custom_mod_info.txt")
        with open(extra_file, "w", encoding="utf-8") as f:
            f.write("user extra content\n")

        # Scan all installed files
        all_files = installed_cheat_files(roots=[eden_root, lichii_root])
        self.assertEqual(len(all_files), 3)

        # Call remove helper
        removed = remove_installed_cheats(all_files)
        norm_removed = [os.path.normcase(os.path.abspath(p)) for p in removed]

        self.assertEqual(len(removed), 2)
        self.assertIn(os.path.normcase(os.path.abspath(eden_file)), norm_removed)
        self.assertIn(os.path.normcase(os.path.abspath(lichii_file)), norm_removed)
        self.assertNotIn(os.path.normcase(os.path.abspath(other_file)), norm_removed)

        # Eden: our file removed
        self.assertFalse(os.path.exists(eden_file))
        # Eden: cheats dir removed because empty
        self.assertFalse(os.path.exists(eden_our_cheats))
        # Eden: 'OOT Save Editor Cheats' dir removed because empty
        self.assertFalse(os.path.exists(os.path.join(eden_root, "load", TITLE_ID, "OOT Save Editor Cheats")))
        # Eden: OtherMod file and dirs NOT deleted
        self.assertTrue(os.path.exists(other_file))
        self.assertTrue(os.path.exists(eden_other_dir))

        # Lichii: our file removed
        self.assertFalse(os.path.exists(lichii_file))
        # Lichii: cheats dir removed because empty
        self.assertFalse(os.path.exists(lichii_our_cheats))
        # Lichii: 'OOT Save Editor Cheats' dir NOT removed because it still has extra_file!
        self.assertTrue(os.path.exists(lichii_our_mod))
        self.assertTrue(os.path.exists(extra_file))

    def test_pick_newest_save_folder_by_mtime(self):
        """autodetect-style newest-folder helper picks the newer of two fake save folders by mtime."""
        save_folder_old = os.path.join(self.test_dir, "save_old")
        save_folder_new = os.path.join(self.test_dir, "save_new")

        prog_old = os.path.join(save_folder_old, "slot_0", "progress.sav")
        prog_new = os.path.join(save_folder_new, "slot_1", "progress.sav")

        os.makedirs(os.path.dirname(prog_old), exist_ok=True)
        os.makedirs(os.path.dirname(prog_new), exist_ok=True)

        with open(prog_old, "wb") as f:
            f.write(b"old_save_data")
        with open(prog_new, "wb") as f:
            f.write(b"new_save_data")

        # Set specific modification times (old = 1,000,000s; new = 2,000,000s)
        os.utime(prog_old, (1000000.0, 1000000.0))
        os.utime(prog_new, (2000000.0, 2000000.0))

        # Folder with newer progress.sav should be picked
        chosen = pick_newest_save_folder([save_folder_old, save_folder_new])
        self.assertEqual(chosen, save_folder_new)

        chosen_reverse = pick_newest_save_folder([save_folder_new, save_folder_old])
        self.assertEqual(chosen_reverse, save_folder_new)

        # Update old save to be even newer (3,000,000s)
        os.utime(prog_old, (3000000.0, 3000000.0))
        chosen_updated = pick_newest_save_folder([save_folder_old, save_folder_new])
        self.assertEqual(chosen_updated, save_folder_old)


if __name__ == "__main__":
    unittest.main()
