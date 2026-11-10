"""Application paths and naming constants for The Legend of Zelda: Ocarina of Time Save Editor."""
import os
import sys

APP_NAME = "The Legend of Zelda Ocarina of Time Switch 2 Save Editor"
APP_DIR = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
RESOURCE_DIR = getattr(sys, "_MEIPASS", APP_DIR)


def get_user_data_dir(app_dir=None):
    """Determine the user data directory: APP_DIR/data if portable.txt exists, else %APPDATA%/<APP_NAME>."""
    base_dir = app_dir or APP_DIR
    if os.path.exists(os.path.join(base_dir, "portable.txt")):
        return os.path.join(base_dir, "data")
    appdata = os.environ.get("APPDATA")
    base = appdata if appdata else os.path.expanduser("~/.config")
    return os.path.join(base, APP_NAME)


def get_legacy_data_dir():
    """Determine the legacy Switch Save Editor user data directory."""
    appdata = os.environ.get("APPDATA")
    base = appdata if appdata else os.path.expanduser("~/.config")
    return os.path.join(base, "The Legend of Zelda Ocarina of Time Switch Save Editor")


USER_DATA_DIR = get_user_data_dir(APP_DIR)
LEGACY_DATA_DIR = get_legacy_data_dir()
SETTINGS_PATH = os.path.join(USER_DATA_DIR, "settings.json")
BACKUP_DIR = os.path.join(USER_DATA_DIR, "backups")
CHEAT_LIB_DIR = os.path.join(USER_DATA_DIR, "cheats")
