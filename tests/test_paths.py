"""Unit tests for user data path resolution, portable mode, migration, cheat seeding, and versioning."""
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

# Ensure repo root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from oot_save_editor import (
    APP_NAME,
    APP_VERSION,
    get_user_data_dir,
    migrate_user_data,
    seed_cheat_library,
    read_library,
    library_builds,
)


class TestPathsAndData(unittest.TestCase):
    def test_version_format(self):
        """Verify APP_VERSION adheres to semantic versioning."""
        self.assertRegex(APP_VERSION, r"^\d+\.\d+\.\d+$")
        self.assertEqual(APP_VERSION, "1.0.0")

    def test_user_data_dir_portable_mode(self):
        """When portable.txt exists in app_dir, USER_DATA_DIR must be app_dir/data."""
        with tempfile.TemporaryDirectory() as td:
            portable_marker = os.path.join(td, "portable.txt")
            with open(portable_marker, "w", encoding="utf-8") as f:
                f.write("portable")

            data_dir = get_user_data_dir(app_dir=td)
            expected = os.path.join(td, "data")
            self.assertEqual(os.path.normpath(data_dir), os.path.normpath(expected))

    def test_user_data_dir_standard_appdata(self):
        """When portable.txt is absent, USER_DATA_DIR uses APPDATA without touching real paths."""
        with tempfile.TemporaryDirectory() as td_app, tempfile.TemporaryDirectory() as td_appdata:
            orig_appdata = os.environ.get("APPDATA")
            try:
                os.environ["APPDATA"] = td_appdata
                data_dir = get_user_data_dir(app_dir=td_app)
                expected = os.path.join(td_appdata, APP_NAME)
                self.assertEqual(os.path.normpath(data_dir), os.path.normpath(expected))
            finally:
                if orig_appdata is not None:
                    os.environ["APPDATA"] = orig_appdata
                else:
                    os.environ.pop("APPDATA", None)

    def test_user_data_dir_fallback_config(self):
        """When APPDATA is empty, fallback to ~/.config/<APP_NAME>."""
        with tempfile.TemporaryDirectory() as td_app:
            orig_appdata = os.environ.get("APPDATA")
            try:
                os.environ["APPDATA"] = ""
                data_dir = get_user_data_dir(app_dir=td_app)
                expected = os.path.join(os.path.expanduser("~/.config"), APP_NAME)
                self.assertEqual(os.path.normpath(data_dir), os.path.normpath(expected))
            finally:
                if orig_appdata is not None:
                    os.environ["APPDATA"] = orig_appdata
                else:
                    os.environ.pop("APPDATA", None)

    def test_migration_copies_missing_and_never_deletes(self):
        """Migration copies missing backup folders and cheats, never deletes originals, and runs once."""
        with tempfile.TemporaryDirectory() as old_app_dir, tempfile.TemporaryDirectory() as user_data_dir:
            # Set up old backups
            old_bks = os.path.join(old_app_dir, "backups")
            bk1 = os.path.join(old_bks, "backup_1")
            bk2 = os.path.join(old_bks, "backup_2")
            os.makedirs(bk1, exist_ok=True)
            os.makedirs(bk2, exist_ok=True)
            with open(os.path.join(bk1, "progress.sav"), "w", encoding="utf-8") as f:
                f.write("save1")
            with open(os.path.join(bk2, "progress.sav"), "w", encoding="utf-8") as f:
                f.write("save2")

            # Set up destination with backup_1 already existing
            new_bks = os.path.join(user_data_dir, "backups")
            new_bk1 = os.path.join(new_bks, "backup_1")
            os.makedirs(new_bk1, exist_ok=True)
            with open(os.path.join(new_bk1, "progress.sav"), "w", encoding="utf-8") as f:
                f.write("save1_existing")

            # Set up old cheats
            old_cheats = os.path.join(old_app_dir, "cheats", "folder1")
            os.makedirs(old_cheats, exist_ok=True)
            with open(os.path.join(old_cheats, "code.txt"), "w", encoding="utf-8") as f:
                f.write("cheat_code")

            settings = {}
            migrated_bks, migrated_cheats = migrate_user_data(old_app_dir, user_data_dir, settings)

            # Only backup_2 should be newly migrated
            self.assertEqual(migrated_bks, 1)
            self.assertEqual(migrated_cheats, 1)
            self.assertEqual(settings.get("backups_migrated_from"), old_app_dir)

            # Verify originals were never deleted or moved
            self.assertTrue(os.path.exists(os.path.join(bk1, "progress.sav")))
            self.assertTrue(os.path.exists(os.path.join(bk2, "progress.sav")))
            self.assertTrue(os.path.exists(os.path.join(old_cheats, "code.txt")))

            # Verify backup_2 exists in destination
            self.assertTrue(os.path.exists(os.path.join(new_bks, "backup_2", "progress.sav")))
            # Verify backup_1 was not overwritten
            with open(os.path.join(new_bk1, "progress.sav"), "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), "save1_existing")

            # Verify second run does nothing (runs once)
            bks2, cheats2 = migrate_user_data(old_app_dir, user_data_dir, settings)
            self.assertEqual(bks2, 0)
            self.assertEqual(cheats2, 0)

    def test_cheat_seeding_never_overwrites_user_files(self):
        """Seeding copies missing files from resource dir but never overwrites existing user files."""
        with tempfile.TemporaryDirectory() as res_dir, tempfile.TemporaryDirectory() as user_dir:
            res_sub = os.path.join(res_dir, "build_1")
            user_sub = os.path.join(user_dir, "build_1")
            res_sub2 = os.path.join(res_dir, "build_2")
            os.makedirs(res_sub, exist_ok=True)
            os.makedirs(user_sub, exist_ok=True)
            os.makedirs(res_sub2, exist_ok=True)

            with open(os.path.join(res_sub, "cheats.txt"), "w", encoding="utf-8") as f:
                f.write("bundled_v1")
            with open(os.path.join(user_sub, "cheats.txt"), "w", encoding="utf-8") as f:
                f.write("user_modified")
            with open(os.path.join(res_sub2, "cheats.txt"), "w", encoding="utf-8") as f:
                f.write("bundled_v2")

            copied = seed_cheat_library(user_cheat_dir=user_dir, resource_cheat_dir=res_dir)
            self.assertEqual(copied, 1)  # only build_2 was missing

            # Verify user_sub was NOT overwritten
            with open(os.path.join(user_sub, "cheats.txt"), "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), "user_modified")

            # Verify missing file was copied
            with open(os.path.join(user_dir, "build_2", "cheats.txt"), "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), "bundled_v2")

    def test_read_library_fallback_to_bundled(self):
        """read_library falls back to reading bundled cheats when user copy lacks the build."""
        with tempfile.TemporaryDirectory() as res_dir, tempfile.TemporaryDirectory() as user_dir:
            bid_bundled = "1111222233334444"
            bid_user = "AAAABBBBCCCCDDDD"

            game_sub_res = os.path.join(res_dir, f"0400486024DEC000 - The Legend of Zelda Ocarina of Time", f"v1 - {bid_bundled}")
            game_sub_user = os.path.join(user_dir, f"0400486024DEC000 - The Legend of Zelda Ocarina of Time", f"v2 - {bid_user}")
            os.makedirs(game_sub_res, exist_ok=True)
            os.makedirs(game_sub_user, exist_ok=True)

            with open(os.path.join(game_sub_res, f"{bid_bundled}.txt"), "w", encoding="utf-8") as f:
                f.write("[Bundled Cheat]\n00000000 00000000\n")
            with open(os.path.join(game_sub_res, "info.json"), "w", encoding="utf-8") as f:
                json.dump({"cheats": [{"name": "Bundled Cheat", "description": "from bundle"}]}, f)

            with open(os.path.join(game_sub_user, f"{bid_user}.txt"), "w", encoding="utf-8") as f:
                f.write("[User Cheat]\n11111111 11111111\n")
            with open(os.path.join(game_sub_user, "info.json"), "w", encoding="utf-8") as f:
                json.dump({"cheats": [{"name": "User Cheat", "description": "from user"}]}, f)

            # Test explicit lib_dir
            res_cheats = read_library(bid_bundled, lib_dir=res_dir)
            self.assertEqual(len(res_cheats), 1)
            self.assertEqual(res_cheats[0]["name"], "Bundled Cheat")

            user_cheats = read_library(bid_user, lib_dir=user_dir)
            self.assertEqual(len(user_cheats), 1)
            self.assertEqual(user_cheats[0]["name"], "User Cheat")


if __name__ == "__main__":
    unittest.main()
