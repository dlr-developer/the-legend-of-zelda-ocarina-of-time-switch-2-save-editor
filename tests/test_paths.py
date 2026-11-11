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

import tkinter as tk
from unittest.mock import patch

from tests._isolate import TEST_TMP_DIR
from oot_save_editor import (
    APP_NAME,
    APP_VERSION,
    USER_DATA_DIR,
    LEGACY_DATA_DIR,
    OOTEditor,
    get_user_data_dir,
    get_legacy_data_dir,
    migrate_user_data,
    migrate_legacy_user_data,
    seed_cheat_library,
    read_library,
    library_builds,
    list_backups,
    cleanup_staging_items,
    safe_copy,
)


class TestPathsAndData(unittest.TestCase):
    def test_version_format(self):
        """Verify APP_VERSION adheres to semantic versioning."""
        self.assertRegex(APP_VERSION, r"^\d+\.\d+\.\d+$")

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

    def test_app_name_switch2(self):
        """APP_NAME must reflect Switch 2."""
        self.assertEqual(APP_NAME, "The Legend of Zelda Ocarina of Time Switch 2 Save Editor")

    def test_legacy_data_dir_resolution(self):
        """get_legacy_data_dir resolves to the legacy Switch Save Editor folder in APPDATA."""
        with tempfile.TemporaryDirectory() as td_appdata:
            orig_appdata = os.environ.get("APPDATA")
            try:
                os.environ["APPDATA"] = td_appdata
                legacy_dir = get_legacy_data_dir()
                expected = os.path.join(td_appdata, "The Legend of Zelda Ocarina of Time Switch Save Editor")
                self.assertEqual(os.path.normpath(legacy_dir), os.path.normpath(expected))
            finally:
                if orig_appdata is not None:
                    os.environ["APPDATA"] = orig_appdata
                else:
                    os.environ.pop("APPDATA", None)

    def test_legacy_migration_copied_once_never_deletes_or_overwrites(self):
        """Legacy folder contents copied once into user_data_dir, never deletes or overwrites."""
        with tempfile.TemporaryDirectory() as legacy_dir, tempfile.TemporaryDirectory() as user_data_dir:
            # 1. Setup legacy files
            legacy_settings_file = os.path.join(legacy_dir, "settings.json")
            with open(legacy_settings_file, "w", encoding="utf-8") as f:
                json.dump({"theme": "Dark", "save_folder": "legacy/save"}, f)

            b1_dir = os.path.join(legacy_dir, "backups", "bk_1")
            b2_dir = os.path.join(legacy_dir, "backups", "bk_2")
            os.makedirs(b1_dir, exist_ok=True)
            os.makedirs(b2_dir, exist_ok=True)
            with open(os.path.join(b1_dir, "progress.sav"), "w", encoding="utf-8") as f:
                f.write("legacy_bk1")
            with open(os.path.join(b2_dir, "progress.sav"), "w", encoding="utf-8") as f:
                f.write("legacy_bk2")

            legacy_cheat_file = os.path.join(legacy_dir, "cheats", "build_1", "cheats.txt")
            os.makedirs(os.path.dirname(legacy_cheat_file), exist_ok=True)
            with open(legacy_cheat_file, "w", encoding="utf-8") as f:
                f.write("legacy_cheat")

            legacy_guide_file = os.path.join(legacy_dir, "guides", "custom.json")
            os.makedirs(os.path.dirname(legacy_guide_file), exist_ok=True)
            with open(legacy_guide_file, "w", encoding="utf-8") as f:
                f.write('{"guide": "legacy"}')

            # 2. Setup user_data_dir with existing bk_1 and existing settings
            existing_bk1 = os.path.join(user_data_dir, "backups", "bk_1")
            os.makedirs(existing_bk1, exist_ok=True)
            with open(os.path.join(existing_bk1, "progress.sav"), "w", encoding="utf-8") as f:
                f.write("existing_bk1_protected")

            existing_settings = {"theme": "Light"}
            user_settings_file = os.path.join(user_data_dir, "settings.json")
            with open(user_settings_file, "w", encoding="utf-8") as f:
                json.dump(existing_settings, f)

            # 3. Perform legacy migration
            settings = dict(existing_settings)
            counts = migrate_legacy_user_data(legacy_dir, user_data_dir, settings)

            # bk_1 should NOT be overwritten; only bk_2 should migrate
            self.assertEqual(counts.backups, 1)
            self.assertEqual(counts.cheats, 1)
            self.assertEqual(counts.guides, 1)
            # settings already existed, so should not overwrite
            self.assertEqual(counts.settings, 0)
            self.assertEqual(settings.get("migrated_from_legacy_dir"), legacy_dir)

            # 4. Verify existing files were preserved (not overwritten)
            with open(os.path.join(existing_bk1, "progress.sav"), "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), "existing_bk1_protected")
            with open(user_settings_file, "r", encoding="utf-8") as f:
                saved_sets = json.load(f)
                self.assertEqual(saved_sets["theme"], "Light")
                self.assertEqual(saved_sets["migrated_from_legacy_dir"], legacy_dir)

            # 5. Verify missing files were copied
            self.assertTrue(os.path.exists(os.path.join(user_data_dir, "backups", "bk_2", "progress.sav")))
            self.assertTrue(os.path.exists(os.path.join(user_data_dir, "cheats", "build_1", "cheats.txt")))
            self.assertTrue(os.path.exists(os.path.join(user_data_dir, "guides", "custom.json")))

            # 6. Verify legacy originals were NEVER deleted or modified
            self.assertTrue(os.path.exists(legacy_settings_file))
            self.assertTrue(os.path.exists(os.path.join(b1_dir, "progress.sav")))
            self.assertTrue(os.path.exists(os.path.join(b2_dir, "progress.sav")))
            self.assertTrue(os.path.exists(legacy_cheat_file))
            self.assertTrue(os.path.exists(legacy_guide_file))

            # 7. Verify migration runs once
            counts2 = migrate_legacy_user_data(legacy_dir, user_data_dir, settings)
            self.assertEqual(counts2.total, 0)

    def test_legacy_migration_settings_preserved_when_missing(self):
        """When destination settings.json is missing, legacy settings are copied and recorded."""
        with tempfile.TemporaryDirectory() as legacy_dir, tempfile.TemporaryDirectory() as user_data_dir:
            legacy_settings_file = os.path.join(legacy_dir, "settings.json")
            with open(legacy_settings_file, "w", encoding="utf-8") as f:
                json.dump({"theme": "Dark", "save_folder": "legacy/path"}, f)

            settings = {}
            counts = migrate_legacy_user_data(legacy_dir, user_data_dir, settings)
            self.assertEqual(counts.settings, 1)

            dest_settings_file = os.path.join(user_data_dir, "settings.json")
            self.assertTrue(os.path.exists(dest_settings_file))
            with open(dest_settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.assertEqual(data["theme"], "Dark")
                self.assertEqual(data["save_folder"], "legacy/path")
                self.assertEqual(data["migrated_from_legacy_dir"], legacy_dir)

    def test_legacy_migration_followed_by_app_dir_migration(self):
        """Legacy migration followed by APP_DIR backup migration both succeed without collisions."""
        with tempfile.TemporaryDirectory() as legacy_dir, \
             tempfile.TemporaryDirectory() as app_dir, \
             tempfile.TemporaryDirectory() as user_data_dir:

            # Legacy backup
            os.makedirs(os.path.join(legacy_dir, "backups", "legacy_bk"), exist_ok=True)
            with open(os.path.join(legacy_dir, "backups", "legacy_bk", "progress.sav"), "w", encoding="utf-8") as f:
                f.write("legacy")

            # App dir backup
            os.makedirs(os.path.join(app_dir, "backups", "app_bk"), exist_ok=True)
            with open(os.path.join(app_dir, "backups", "app_bk", "progress.sav"), "w", encoding="utf-8") as f:
                f.write("app")

            settings = {}
            # 1. Run legacy migration
            legacy_counts = migrate_legacy_user_data(legacy_dir, user_data_dir, settings)
            self.assertEqual(legacy_counts.backups, 1)

            # 2. Run existing APP_DIR migration
            app_bks, _ = migrate_user_data(app_dir, user_data_dir, settings)
            self.assertEqual(app_bks, 1)

            # Both backups now exist in user_data_dir
            self.assertTrue(os.path.exists(os.path.join(user_data_dir, "backups", "legacy_bk", "progress.sav")))
            self.assertTrue(os.path.exists(os.path.join(user_data_dir, "backups", "app_bk", "progress.sav")))

            # Originals are untouched
            self.assertTrue(os.path.exists(os.path.join(legacy_dir, "backups", "legacy_bk", "progress.sav")))
            self.assertTrue(os.path.exists(os.path.join(app_dir, "backups", "app_bk", "progress.sav")))

    def test_user_data_dir_isolated_from_real_appdata(self):
        """USER_DATA_DIR must be isolated under the test temporary directory during test runs."""
        norm_user_data = os.path.normpath(USER_DATA_DIR)
        norm_tmp = os.path.normpath(TEST_TMP_DIR)
        self.assertTrue(
            norm_user_data.startswith(norm_tmp) or os.path.commonpath([norm_user_data, norm_tmp]) == norm_tmp,
            f"USER_DATA_DIR ({USER_DATA_DIR}) is not under TEST_TMP_DIR ({TEST_TMP_DIR})",
        )

    def test_backups_frame_pause_menu_button_width(self):
        """Switch 2 Pause Menu button must retain its full requested width at default window size."""
        try:
            root_probe = tk.Tk()
            root_probe.destroy()
        except tk.TclError:
            raise unittest.SkipTest("Tk display not available")

        app = OOTEditor()
        try:
            app.update_idletasks()
            app.update()
            btn = getattr(app, "pause_menu_button", None)
            self.assertIsNotNone(btn, "Pause menu button should be stored on app as pause_menu_button")
            req_w = btn.winfo_reqwidth()
            act_w = btn.winfo_width()
            self.assertGreater(req_w, 0, "Button requested width must be greater than 0")
            self.assertGreaterEqual(
                act_w,
                req_w,
                f"Pause menu button width ({act_w}px) was squeezed below requested width ({req_w}px)",
            )
        finally:
            app.destroy()

    def test_run_once_pinned_after_deletion_legacy(self):
        """Pin run-once behavior for legacy migration: deleting a migrated backup does not re-copy on re-run."""
        with tempfile.TemporaryDirectory() as legacy_dir, tempfile.TemporaryDirectory() as user_data_dir:
            bk_dir = os.path.join(legacy_dir, "backups", "pinned_legacy_bk")
            os.makedirs(bk_dir, exist_ok=True)
            with open(os.path.join(bk_dir, "progress.sav"), "w", encoding="utf-8") as f:
                f.write("legacy_save")

            settings = {}
            # 1. Run migration first time
            counts1 = migrate_legacy_user_data(legacy_dir, user_data_dir, settings)
            self.assertEqual(counts1.backups, 1)
            migrated_bk = os.path.join(user_data_dir, "backups", "pinned_legacy_bk")
            self.assertTrue(os.path.exists(migrated_bk))

            # 2. Delete the migrated backup from the new folder
            shutil.rmtree(migrated_bk)
            self.assertFalse(os.path.exists(migrated_bk))

            # 3. Migrate again with the same settings dict -> stays deleted, counts 0
            counts2 = migrate_legacy_user_data(legacy_dir, user_data_dir, settings)
            self.assertEqual(counts2.total, 0)
            self.assertFalse(os.path.exists(migrated_bk), "Deleted backup must not be re-copied on second run")

    def test_run_once_pinned_after_deletion_app_dir(self):
        """Pin run-once behavior for app_dir migration: deleting a migrated backup does not re-copy on re-run."""
        with tempfile.TemporaryDirectory() as app_dir, tempfile.TemporaryDirectory() as user_data_dir:
            bk_dir = os.path.join(app_dir, "backups", "pinned_app_bk")
            os.makedirs(bk_dir, exist_ok=True)
            with open(os.path.join(bk_dir, "progress.sav"), "w", encoding="utf-8") as f:
                f.write("app_save")

            settings = {}
            # 1. Run migration first time
            bks1, _ = migrate_user_data(app_dir, user_data_dir, settings)
            self.assertEqual(bks1, 1)
            migrated_bk = os.path.join(user_data_dir, "backups", "pinned_app_bk")
            self.assertTrue(os.path.exists(migrated_bk))

            # 2. Delete the migrated backup from the new folder
            shutil.rmtree(migrated_bk)
            self.assertFalse(os.path.exists(migrated_bk))

            # 3. Migrate again with the same settings dict -> stays deleted, counts 0
            bks2, cheats2 = migrate_user_data(app_dir, user_data_dir, settings)
            self.assertEqual(bks2, 0)
            self.assertEqual(cheats2, 0)
            self.assertFalse(os.path.exists(migrated_bk), "Deleted backup must not be re-copied on second run")

    def test_partial_copy_failure_and_recovery(self):
        """Safe migration leaves no partial backup on 2nd-file failure, does not raise, avoids marker, and recovers later."""
        with tempfile.TemporaryDirectory() as legacy_dir, tempfile.TemporaryDirectory() as user_data_dir:
            bk_source = os.path.join(legacy_dir, "backups", "bk_two_files")
            os.makedirs(bk_source, exist_ok=True)
            f1 = os.path.join(bk_source, "file1.sav")
            f2 = os.path.join(bk_source, "file2.sav")
            with open(f1, "w", encoding="utf-8") as f:
                f.write("file1_content")
            with open(f2, "w", encoding="utf-8") as f:
                f.write("file2_content")

            final_dst = os.path.join(user_data_dir, "backups", "bk_two_files")
            partial_dst = f"{final_dst}.partial-{os.getpid()}"

            # Monkeypatch copy2 to raise OSError on the 2nd file copied
            orig_copy2 = shutil.copy2
            call_count = [0]

            def failing_copy2(src, dst, *args, **kwargs):
                call_count[0] += 1
                if call_count[0] == 2:
                    raise OSError("Disk full error on 2nd file")
                return orig_copy2(src, dst, *args, **kwargs)

            settings = {}
            with patch("shutil.copy2", side_effect=failing_copy2):
                # App-level call does not raise
                try:
                    counts = migrate_legacy_user_data(legacy_dir, user_data_dir, settings)
                except Exception as ex:
                    self.fail(f"migrate_legacy_user_data raised unexpectedly: {ex}")

            # Assert: no partial backup left under its final name
            self.assertFalse(os.path.exists(final_dst), "Final destination backup must not exist after failure")
            self.assertFalse(os.path.exists(partial_dst), "Staging .partial folder should be cleaned up")
            # Marker not written
            self.assertNotIn("migrated_from_legacy_dir", settings)
            self.assertEqual(counts.backups, 0)

            # Later successful run completes the backup
            counts_success = migrate_legacy_user_data(legacy_dir, user_data_dir, settings)
            self.assertEqual(counts_success.backups, 1)
            self.assertTrue(os.path.exists(final_dst), "Backup folder should exist after successful run")
            self.assertTrue(os.path.exists(os.path.join(final_dst, "file1.sav")))
            self.assertTrue(os.path.exists(os.path.join(final_dst, "file2.sav")))
            self.assertEqual(settings.get("migrated_from_legacy_dir"), legacy_dir)

    def test_legacy_migration_skipped_in_portable_mode(self):
        """In portable mode (portable.txt exists), legacy %APPDATA% migration is skipped completely."""
        with tempfile.TemporaryDirectory() as app_dir, \
             tempfile.TemporaryDirectory() as legacy_dir, \
             tempfile.TemporaryDirectory() as user_data_dir:

            # Create portable.txt in app_dir
            with open(os.path.join(app_dir, "portable.txt"), "w", encoding="utf-8") as f:
                f.write("portable")

            # Create legacy backup
            os.makedirs(os.path.join(legacy_dir, "backups", "pc_backup"), exist_ok=True)
            with open(os.path.join(legacy_dir, "backups", "pc_backup", "progress.sav"), "w", encoding="utf-8") as f:
                f.write("host_pc_data")

            settings = {}
            counts = migrate_legacy_user_data(legacy_dir, user_data_dir, settings, app_dir=app_dir)
            self.assertEqual(counts.total, 0)
            self.assertFalse(os.path.exists(os.path.join(user_data_dir, "backups", "pc_backup")))
            self.assertNotIn("migrated_from_legacy_dir", settings)

    def test_leftover_partial_folder_not_counted_or_listed_and_migration_removes_it(self):
        """A leftover x.partial folder is not counted or listed; migration removes it; real backups untouched."""
        with tempfile.TemporaryDirectory() as legacy_dir, tempfile.TemporaryDirectory() as user_data_dir:
            dest_backups = os.path.join(user_data_dir, "backups")
            os.makedirs(dest_backups, exist_ok=True)

            # Real existing backup in destination
            real_bk = os.path.join(dest_backups, "OOT_Backup_2026-11-09_12-00-00")
            os.makedirs(real_bk, exist_ok=True)
            with open(os.path.join(real_bk, "progress.sav"), "w", encoding="utf-8") as f:
                f.write("real_backup_content")

            # Leftover staging folder in destination (from a killed process or crash)
            stale_partial = os.path.join(dest_backups, "OOT_Backup_broken.partial")
            os.makedirs(stale_partial, exist_ok=True)
            with open(os.path.join(stale_partial, "progress.sav"), "w", encoding="utf-8") as f:
                f.write("partial_junk")

            # Additional per-process staging folder
            stale_pid_partial = os.path.join(dest_backups, "OOT_Backup_killed.partial-99999")
            os.makedirs(stale_pid_partial, exist_ok=True)
            with open(os.path.join(stale_pid_partial, "progress.sav"), "w", encoding="utf-8") as f:
                f.write("pid_partial_junk")

            # 1. Verify list_backups skips all staging folders
            listed = list_backups(dest_backups)
            self.assertEqual(listed, ["OOT_Backup_2026-11-09_12-00-00"])
            self.assertNotIn("OOT_Backup_broken.partial", listed)
            self.assertNotIn("OOT_Backup_killed.partial-99999", listed)

            # 2. Setup a legacy backup to migrate
            legacy_bk = os.path.join(legacy_dir, "backups", "legacy_bk")
            os.makedirs(legacy_bk, exist_ok=True)
            with open(os.path.join(legacy_bk, "progress.sav"), "w", encoding="utf-8") as f:
                f.write("legacy_content")

            # Also create a stale staging file in cheats to verify destination cleanup
            dest_cheats = os.path.join(user_data_dir, "cheats")
            os.makedirs(dest_cheats, exist_ok=True)
            stale_cheat_partial = os.path.join(dest_cheats, "code.txt.partial")
            with open(stale_cheat_partial, "w", encoding="utf-8") as f:
                f.write("partial_cheat")

            # Run migration
            settings = {}
            counts = migrate_legacy_user_data(legacy_dir, user_data_dir, settings)
            self.assertEqual(counts.backups, 1)

            # 3. Assert leftover staging items were removed
            self.assertFalse(os.path.exists(stale_partial), "Stale .partial directory must be removed by migration")
            self.assertFalse(os.path.exists(stale_pid_partial), "Stale .partial-<pid> directory must be removed by migration")
            self.assertFalse(os.path.exists(stale_cheat_partial), "Stale cheat .partial file must be removed by migration")

            # 4. Assert real backups are untouched
            self.assertTrue(os.path.exists(real_bk))
            with open(os.path.join(real_bk, "progress.sav"), "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), "real_backup_content")

            # Legacy backup migrated
            migrated_bk = os.path.join(dest_backups, "legacy_bk")
            self.assertTrue(os.path.exists(migrated_bk))
            with open(os.path.join(migrated_bk, "progress.sav"), "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), "legacy_content")

            # Legacy source untouched
            self.assertTrue(os.path.exists(os.path.join(legacy_bk, "progress.sav")))

    def test_safe_copy_dst_created_between_copy_and_replace(self):
        """When dst is created between copy and replace, staging is removed, dst is untouched, and no exception is raised."""
        with tempfile.TemporaryDirectory() as td:
            # Test for directory safe_copy
            src_dir = os.path.join(td, "src_bk")
            dst_dir = os.path.join(td, "dst_bk")
            os.makedirs(src_dir, exist_ok=True)
            with open(os.path.join(src_dir, "progress.sav"), "w", encoding="utf-8") as f:
                f.write("src_content")

            orig_copy2 = shutil.copy2

            def copy2_with_concurrent_creation(s, d, *args, **kwargs):
                # Simulate concurrent process creating dst_dir during copy
                os.makedirs(dst_dir, exist_ok=True)
                with open(os.path.join(dst_dir, "progress.sav"), "w", encoding="utf-8") as f_dst:
                    f_dst.write("concurrent_winner")
                return orig_copy2(s, d, *args, **kwargs)

            partial_dir = f"{dst_dir}.partial-{os.getpid()}"
            with patch("shutil.copy2", side_effect=copy2_with_concurrent_creation):
                result = safe_copy(src_dir, dst_dir)

            # Assertions
            self.assertFalse(result, "safe_copy must return False (skipped) when dst appeared meanwhile")
            self.assertFalse(os.path.exists(partial_dir), "Staging copy must be removed")
            self.assertTrue(os.path.exists(dst_dir), "Destination must still exist")
            with open(os.path.join(dst_dir, "progress.sav"), "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), "concurrent_winner", "Destination must remain untouched")

            # Verify src was not modified
            with open(os.path.join(src_dir, "progress.sav"), "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), "src_content")

            # Test for file safe_copy
            src_file = os.path.join(td, "src.txt")
            dst_file = os.path.join(td, "dst.txt")
            with open(src_file, "w", encoding="utf-8") as f:
                f.write("src_file_content")

            def file_copy2_with_concurrent_creation(s, d, *args, **kwargs):
                with open(dst_file, "w", encoding="utf-8") as f_dst:
                    f_dst.write("concurrent_file_winner")
                return orig_copy2(s, d, *args, **kwargs)

            partial_file = f"{dst_file}.partial-{os.getpid()}"
            with patch("shutil.copy2", side_effect=file_copy2_with_concurrent_creation):
                file_result = safe_copy(src_file, dst_file)

            self.assertFalse(file_result, "safe_copy file must return False (skipped) when dst appeared meanwhile")
            self.assertFalse(os.path.exists(partial_file), "Staging file must be removed")
            with open(dst_file, "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), "concurrent_file_winner", "Destination file must remain untouched")

    def test_list_backups_empty_or_nonexistent(self):
        """list_backups returns [] for non-existent, empty, or invalid paths."""
        self.assertEqual(list_backups(None), [])
        self.assertEqual(list_backups(""), [])
        self.assertEqual(list_backups("nonexistent_path_12345"), [])
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(list_backups(td), [])


if __name__ == "__main__":
    unittest.main()
