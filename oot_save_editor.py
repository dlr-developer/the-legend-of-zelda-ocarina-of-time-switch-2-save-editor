"""The Legend of Zelda: Ocarina of Time (64-bit) (Switch 2 / NX2) save editor.

Works with saves from Lichii, Eden, Yuzu, Suyu, Sudachi, Citron, Torzu, Ryujinx,
and saves dumped from a Nintendo Switch running Atmosphère.

Save files use Nintendo's modern GameData container (magic 0x01020304, revision 0x002d80eb)
with 32-bit MurmurHash3 key-value pairs in progress.sav and slot metadata in caption.sav.
"""
import copy
import glob
import hashlib
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import tkinter as tk
import webbrowser
from datetime import datetime
from tkinter import filedialog, messagebox, simpledialog, ttk

APP_NAME = "The Legend of Zelda Ocarina of Time Switch Save Editor"
APP_DIR = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
BACKUP_DIR = os.path.join(APP_DIR, "backups")
CHEAT_LIB_DIR = os.path.join(APP_DIR, "cheats")
RESOURCE_DIR = getattr(sys, "_MEIPASS", APP_DIR)
SETTINGS_PATH = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~/.config"),
                             APP_NAME, "settings.json")

TITLE_ID = "0400486024DEC000"
ALT_TITLE_IDS = ("04004860224DEC000",)
ALL_TITLE_IDS = (TITLE_ID,) + ALT_TITLE_IDS
GAME_NAME = "The Legend of Zelda Ocarina of Time (64-bit)"
SLOT_PREFIX = "slot_"
SLOT_NAMES = {
    "slot_00": "Slot 1",
    "slot_01": "Slot 2",
    "slot_02": "Slot 3",
    "slot_03": "Slot 4",
    "slot_04": "Slot 5",
    "slot_05": "Slot 6",
}

# --- GameData Key Hash Mapping for Ocarina of Time ---
# Section 1 starts at byte 40 (0x28). Each entry is (uint32 hash, uint32 value).
HASH_RUPEES = 0xa77921d7            # progress.sav rupees (0-999)
HASH_CAPTION_RUPEES = 0xa9557547    # caption.sav rupees preview
HASH_HEALTH = 0x76b18200            # progress.sav current health (16 = 1 heart, 240 = 15 hearts, 320 = 20 hearts)
HASH_CAPTION_HEALTH = 0x19f26b6a    # caption.sav health
HASH_CAPTION_MAX_HEALTH = 0x943f8ec3
HASH_HEART_PIECES = 0xfbe01da1      # progress.sav heart containers/pieces (4 * containers + pieces)
HASH_CAPTION_HEART_PIECES = 0x74bd05d0
HASH_TOKENS = 0x31ab5580            # progress.sav Gold Skulltula Tokens (0-100)
HASH_CAPTION_TOKENS = 0x1e55ecc5    # caption.sav tokens preview

# Ammo Hashes
HASH_ARROWS = 0x361b83ad            # Bow arrows (0-50)
HASH_BOMBS = 0x6a7c6c29             # Bombs (0-40)
HASH_BOMBCHUS = 0x5fadf7fc          # Bombchus (0-50)
HASH_DEKU_SEEDS = 0x04735978        # Slingshot seeds (0-50)
HASH_DEKU_STICKS = 0x0e34c167       # Deku sticks (0-30)
HASH_DEKU_NUTS = 0xe753508b         # Deku nuts (0-40)
HASH_MAGIC_BEANS = 0xf30d9f54       # Magic beans (0-10)

# Equipment Hashes & String Slot References
HASH_SWORD_SLOT = 0xa95a3521        # Points to Weapon_Sword_* string in Section 2
HASH_SHIELD_SLOT = 0xee463235       # Points to Weapon_Shield_* string in Section 2
HASH_BOMB_BAG_SLOT = 0xa835e3b0     # Points to Item_BombBag_* string in Section 2
HASH_BULLET_BAG_SLOT = 0xd732dd7f   # Points to Item_BulletBag_* string in Section 2
HASH_WALLET_SLOT = 0x3e42affa       # Points to Item_Wallet_* string in Section 2
HASH_STICK_BAG_SLOT = 0x2808ee1c    # Points to Item_StickBag_* string in Section 2
HASH_NUT_BAG_SLOT = 0x0da3a7a7      # Points to Item_NutBag_* string in Section 2
HASH_OCARINA_SLOT = 0xb72cd3fc      # Points to Item_Ocarina_* string in Section 2
HASH_MASK_SLOT = 0xfb117672         # Points to Armor_Child_Mask_* string in Section 2

# Upgrades & Capacity Hashes
HASH_SWORD_LEVEL = 0x2f3fd2e8       # 1=Kokiri, 2=Master, 3=Biggoron
HASH_BOTTLE_COUNT = 0x16fa66f9
HASH_QUIVER_CAP = 0x510ef34c        # Arrow capacity (30, 40, 50)
HASH_BOMB_BAG_CAP = 0x891b65e7      # Bomb capacity (20, 30, 40)
HASH_STICK_CAP = 0x1ddb9201         # Stick capacity (10, 20, 30)
HASH_NUT_CAP = 0x9850165e           # Nut capacity (20, 30, 40)

# Spiritual Stones & Medallions (Story-critical items in caption.sav & progress.sav)
SPIRITUAL_STONES = [
    ("Kokiri's Emerald", 0x50c6bedf, "Spiritual Stone of the Forest (Deku Tree)"),
    ("Goron's Ruby", 0x380a5616, "Spiritual Stone of Fire (Dodongo's Cavern)"),
    ("Zora's Sapphire", 0x7c5b03dc, "Spiritual Stone of Water (Jabu-Jabu)"),
]

MEDALLIONS = [
    ("Light Medallion", 0x91288adc, "Rauru / Chamber of Sages"),
    ("Forest Medallion", 0x25f03caa, "Saria / Forest Temple"),
    ("Fire Medallion", 0xfb112756, "Darunia / Fire Temple"),
    ("Water Medallion", 0x2f61ab71, "Ruto / Water Temple"),
    ("Shadow Medallion", 0x238ae327, "Impa / Shadow Temple"),
    ("Spirit Medallion", 0x0f941212, "Nabooru / Spirit Temple"),
]

STONES_MEDALLIONS = SPIRITUAL_STONES + MEDALLIONS
STORY_HASHES = {kh for _, kh, _ in STONES_MEDALLIONS}

# Ocarina Songs (Exact 12 song hashes verified in caption.sav)
SONGS = [
    ("Zelda's Lullaby", 0xf9d63fd4, "Royal Family mystery theme"),
    ("Epona's Song", 0x574aef59, "Summons Epona & heals milk cows"),
    ("Saria's Song", 0xab6b5962, "Talk to Saria & cheer up Darunia"),
    ("Sun's Song", 0x99b50b91, "Changes day to night and freezes ReDeads"),
    ("Song of Time", 0x1eda08d5, "Opens the Door of Time"),
    ("Song of Storms", 0x2f793671, "Summons rain and drains the Well"),
    ("Minuet of Forest", 0xe1ca50c6, "Warp to Sacred Forest Meadow"),
    ("Bolero of Fire", 0x17464eb8, "Warp to Death Mountain Crater"),
    ("Serenade of Water", 0x85f5194d, "Warp to Lake Hylia"),
    ("Requiem of Spirit", 0x83254520, "Warp to Desert Colossus"),
    ("Nocturne of Shadow", 0x10dc0608, "Warp to Graveyard"),
    ("Prelude of Light", 0x059ce596, "Warp to Temple of Time"),
]

# Quest Perks & Abilities
QUEST_PERKS = [
    ("Gerudo's Membership Card", 0xba6a1b74, "Grants access to Gerudo Fortress"),
    ("Stone of Agony", 0x75bd1ecf, "Vibrates near hidden grottos and secrets"),
    ("Magic Meter (Single)", 0x89ae7032, "Grants magic power for Spin Attack & magic items"),
    ("Double Magic Meter", 0xc72044fc, "Doubles maximum magic capacity"),
    ("Double Defense", 0xfb2b5f6b, "White heart borders, halves all damage taken"),
]

# Equipment list
SWORDS = ["(None)", "Kokiri Sword", "Master Sword", "Biggoron's Sword", "Giant's Knife"]
SHIELDS = ["(None)", "Deku Shield", "Hylian Shield", "Mirror Shield"]
TUNICS = ["Kokiri Tunic (Green)", "Goron Tunic (Red)", "Zora Tunic (Blue)"]
BOOTS = ["Kokiri Boots", "Iron Boots", "Hover Boots"]
WALLETS = ["Child's Wallet (99)", "Adult's Wallet (200)", "Giant's Wallet (500)", "Tycoon's Wallet (999)"]
QUIVERS = ["(None)", "Quiver (30)", "Big Quiver (40)", "Biggest Quiver (50)"]
BOMB_BAGS = ["(None)", "Bomb Bag (20)", "Big Bomb Bag (30)", "Biggest Bomb Bag (40)"]
STRENGTH_UPGRADES = ["(None)", "Goron's Bracelet", "Silver Gauntlets", "Golden Gauntlets"]
SCALES = ["(None)", "Silver Scale", "Golden Scale"]

BOTTLE_CONTENTS = [
    "(Empty / None)",
    "(Empty Bottle)",
    "Red Potion (Restores all hearts)",
    "Green Potion (Restores magic)",
    "Blue Potion (Restores hearts & magic)",
    "Bottled Fairy (Revives Link)",
    "Fish",
    "Lon Lon Milk (2 servings)",
    "Lon Lon Milk (1 serving)",
    "Poe Soul",
    "Big Poe (100 points)",
    "Blue Fire (Melts red ice)",
    "Bugs (For soft soil)",
    "Princess Ruto's Letter",
]

CHAPTERS = [
    ("Chapter 1", "Inside the Deku Tree (Kokiri's Emerald)", "https://www.zeldadungeon.net/ocarina-of-time-walkthrough/inside-the-deku-tree/"),
    ("Chapter 2", "Dodongo's Cavern (Goron's Ruby)", "https://www.zeldadungeon.net/ocarina-of-time-walkthrough/dodongos-cavern/"),
    ("Chapter 3", "Inside Jabu-Jabu's Belly (Zora's Sapphire)", "https://www.zeldadungeon.net/ocarina-of-time-walkthrough/inside-jabu-jabus-belly/"),
    ("Chapter 4", "Temple of Time & Awakening (Master Sword)", "https://www.zeldadungeon.net/ocarina-of-time-walkthrough/master-sword/"),
    ("Chapter 5", "Forest Temple (Forest Medallion)", "https://www.zeldadungeon.net/ocarina-of-time-walkthrough/forest-temple/"),
    ("Chapter 6", "Fire Temple (Fire Medallion)", "https://www.zeldadungeon.net/ocarina-of-time-walkthrough/fire-temple/"),
    ("Chapter 7", "Water Temple (Water Medallion)", "https://www.zeldadungeon.net/ocarina-of-time-walkthrough/water-temple/"),
    ("Chapter 8", "Shadow Temple (Shadow Medallion)", "https://www.zeldadungeon.net/ocarina-of-time-walkthrough/shadow-temple/"),
    ("Chapter 9", "Spirit Temple (Spirit Medallion)", "https://www.zeldadungeon.net/ocarina-of-time-walkthrough/spirit-temple/"),
    ("Chapter 10", "Ganon's Castle & Final Battle", "https://www.zeldadungeon.net/ocarina-of-time-walkthrough/ganons-castle/"),
]

TOTAL_HEART_PIECES = 36
TOTAL_SKULLTULAS = 100
GUIDE_HEART_PIECES_URL = "https://www.zeldadungeon.net/ocarina-of-time-walkthrough/heart-pieces/"
GUIDE_SKULLTULAS_URL = "https://www.zeldadungeon.net/ocarina-of-time-walkthrough/gold-skulltulas/"
WALKTHROUGH_URL = "https://www.zeldadungeon.net/ocarina-of-time-walkthrough/"

# ---------- GameData Binary Parser ----------
class SaveSlot:
    """Parses and updates progress.sav and caption.sav for a given save slot."""
    def __init__(self, slot_dir):
        self.slot_dir = slot_dir
        self.progress_path = os.path.join(slot_dir, "progress.sav")
        self.caption_path = os.path.join(slot_dir, "caption.sav")
        self.loaded = False
        self.map_name = "Unknown"
        self.raw_progress = b""
        self.raw_caption = b""
        self.p_sec1_len = 0
        self.c_sec1_len = 0
        self.progress_entries = {}      # hash -> value
        self.progress_order = []        # list of hashes in order
        self.caption_entries = {}       # hash -> value
        self.caption_order = []
        self.strings_sec2 = {}          # hash -> string value in Section 2
        self.load()

    def load(self):
        if not os.path.exists(self.progress_path) or not os.path.exists(self.caption_path):
            return False
        with open(self.progress_path, "rb") as f:
            self.raw_progress = f.read()
        with open(self.caption_path, "rb") as f:
            self.raw_caption = f.read()

        # Parse progress.sav header
        magic, rev, self.p_sec1_len = struct.unpack("<3I", self.raw_progress[:12])
        if magic != 0x01020304:
            raise ValueError(f"Invalid progress.sav magic: {hex(magic)}")
        self.progress_entries = {}
        self.progress_order = []
        for off in range(40, 40 + self.p_sec1_len, 8):
            k, v = struct.unpack("<II", self.raw_progress[off:off+8])
            self.progress_entries[k] = v
            self.progress_order.append(k)

        # Parse Section 2 string targets
        base_abs = 40 + self.p_sec1_len
        self.strings_sec2 = {}
        for k, v in self.progress_entries.items():
            if base_abs <= v < len(self.raw_progress):
                chunk = self.raw_progress[v:v+64]
                end = chunk.find(b"\x00")
                if end > 2:
                    self.strings_sec2[k] = chunk[:end].decode("ascii", errors="ignore")

        # Parse caption.sav header
        cmagic, crev, self.c_sec1_len = struct.unpack("<3I", self.raw_caption[:12])
        self.caption_entries = {}
        self.caption_order = []
        for off in range(40, 40 + self.c_sec1_len, 8):
            k, v = struct.unpack("<II", self.raw_caption[off:off+8])
            self.caption_entries[k] = v
            self.caption_order.append(k)

        # Parse map location from caption tail
        tail = self.raw_caption[40 + self.c_sec1_len:]
        m = re.search(b'([A-Za-z0-9_/]{4,})', tail)
        if m:
            raw_loc = m.group(1).decode("ascii", errors="ignore")
            # Format nicely: e.g. "LostWood/LostWood_Child" -> "Lost Woods (Child)"
            parts = raw_loc.split("/")
            name = parts[-1].replace("_", " ")
            self.map_name = name
        else:
            self.map_name = "Hyrule"

        self.loaded = True
        return True

    def get(self, key_hash, default=0):
        return self.progress_entries.get(key_hash, default)

    def set(self, key_hash, val):
        self.progress_entries[key_hash] = int(val)

    def save_bytes(self):
        """Constructs updated byte arrays for progress.sav and caption.sav, preserving Section 2."""
        # 1. Update progress.sav Section 1
        p_bytes = bytearray(self.raw_progress[:40])
        for k in self.progress_order:
            val = self.progress_entries.get(k, 0)
            p_bytes.extend(struct.pack("<II", k, val))
        p_bytes.extend(self.raw_progress[40 + self.p_sec1_len:])

        # 2. Update caption.sav Section 1
        c_bytes = bytearray(self.raw_caption[:40])
        for k in self.caption_order:
            val = self.caption_entries.get(k, 0)
            c_bytes.extend(struct.pack("<II", k, val))
        c_bytes.extend(self.raw_caption[40 + self.c_sec1_len:])

        return bytes(p_bytes), bytes(c_bytes)

def struct_unpack(fmt, data):
    return struct.unpack(fmt, data)

# ---------- Helper Utilities & Cheats ----------
RAW_MARK = "\x01"
CHEAT_LINE = re.compile(r"^[0-9A-Fa-f]{8}( [0-9A-Fa-f]{8})*$")
KNOWN_BUILDS = {"E0F3CCFAF50065AE": "v1.0.0"}
CHEAT_GUIDE_URL = "https://github.com/dlr-developer/oot-save-editor/blob/main/docs/CHEATS.md"
CHEAT_GUIDE = [
    ("warn", "Cheats are experimental. A wrong or mismatched code can crash the game or corrupt your save. "
             "Always back up first."),
    ("h", "How cheats work"),
    ("", "While the game runs, player stats (HP, rupees, ammo) reside in system RAM. A cheat code instructs "
         "the emulator (or Atmosphère on a Switch) to continuously lock those memory addresses. Cheats do not "
         "change your save file directly, but if you save while one is active, its effects are saved too."),
    ("h", "Will a code work for me?"),
    ("", "• Game version: a code only works for the exact build ID it was made for (v1.0.0 is E0F3CCFAF50065AE)."),
    ("", "• Emulator: Lichii, Eden, the yuzu family, and Atmosphère on a real Switch all use this cheat format."),
    ("h", "Using a cheat"),
    ("", "1. Back up your save (Back up now… at the top of the window)."),
    ("", "2. Turn on only the cheats you want (double-click a row)."),
    ("", "3. Click Install to emulator (or Export for Switch), then restart the game."),
    ("h", "Where the files go"),
    ("", "• Lichii / Eden / yuzu family: load\\0400486024DEC000\\OOT Save Editor Cheats\\cheats\\<build ID>.txt"),
    ("", "• Ryujinx: mods\\contents\\0400486024dec000\\OOT Save Editor Cheats\\cheats\\<build ID>.txt"),
    ("", "• Switch: atmosphere/contents/0400486024DEC000/cheats/<build ID>.txt on the SD card."),
]

def parse_cheats(text):
    cheats, current = [], None
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if line[0] in "[{":
            close = "]" if line[0] == "[" else "}"
            if not line.endswith(close) or len(line) < 3:
                raise ValueError(f"Line {n}: a cheat name must look like [Name].")
            current = {"name": line[1:-1].strip(), "lines": [], "master": line[0] == "{"}
            cheats.append(current)
        else:
            if current is None:
                raise ValueError(f"Line {n}: code found before any [Cheat name].")
            words = line.split()
            if not CHEAT_LINE.match(" ".join(words)):
                raise ValueError(f"Line {n}: '{line}' isn't a cheat code line.")
            current["lines"].append(" ".join(w.upper() for w in words))
    empty = [c["name"] for c in cheats if not c["lines"]]
    if empty:
        raise ValueError(f"These cheats have no code: {', '.join(empty)}")
    return cheats

def format_cheats(cheats):
    out = []
    for c in cheats:
        out.append(("{%s}" if c.get("master") else "[%s]") % c["name"])
        out.extend(c["lines"])
        out.append("")
    return "\n".join(out)

# ---------- Cheat Library Helpers ----------
GAME_FOLDER = f"{TITLE_ID} - The Legend of Zelda Ocarina of Time"
TEST_TARGETS = ("Ryujinx", "yuzu family", "Switch")
TEST_STATES = ("Untested", "Works", "Doesn't work")
TEST_ICONS = {"Untested": "—", "Works": "✔", "Doesn't work": "✘"}

def library_builds(lib_dir=None):
    root = os.path.join(lib_dir or CHEAT_LIB_DIR, GAME_FOLDER)
    found = {}
    if os.path.isdir(root):
        for name in sorted(os.listdir(root)):
            m = re.search(r"([0-9A-Fa-f]{16})$", name)
            if m and os.path.isdir(os.path.join(root, name)):
                found[m.group(1).upper()] = os.path.join(root, name)
    return found

def build_folder(bid):
    return library_builds().get(bid) or os.path.join(
        CHEAT_LIB_DIR, GAME_FOLDER, f"{KNOWN_BUILDS.get(bid, 'unknown version')} - {bid}")

def read_library(bid, lib_dir=None):
    folder = library_builds(lib_dir).get(bid)
    if not folder:
        return []
    try:
        cheats = parse_cheats(open(os.path.join(folder, bid + ".txt"), encoding="utf-8-sig").read())
    except (OSError, ValueError):
        return []
    try:
        info = json.load(open(os.path.join(folder, "info.json"), encoding="utf-8"))
        details = {c["name"]: c for c in info.get("cheats", [])}
    except (OSError, ValueError, KeyError):
        details = {}
    for c in cheats:
        d = details.get(c["name"], {})
        c["description"] = d.get("description", "")
        c["tested"] = {t: d.get("tested", {}).get(t, "Untested") for t in TEST_TARGETS}
    return cheats

def write_library(bid, cheats, credits=None):
    folder = build_folder(bid)
    version = KNOWN_BUILDS.get(bid, "unknown version")
    os.makedirs(folder, exist_ok=True)
    header = f"# {GAME_NAME} {version} cheats\n\nBuild ID `{bid}` • title ID `{TITLE_ID}`\n\n"
    if not cheats:
        with open(os.path.join(folder, "README.md"), "w", encoding="utf-8", newline="\n") as f:
            f.write(header + "No cheats for this version yet.\n")
        return
    with open(os.path.join(folder, bid + ".txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(format_cheats(cheats))
    info = {"game": GAME_NAME, "title_id": TITLE_ID, "version": version, "build_id": bid,
            "credits": credits or [],
            "cheats": [{"name": c["name"], "description": c.get("description", ""),
                        "master": bool(c.get("master")),
                        "tested": {t: c.get("tested", {}).get(t, "Untested") for t in TEST_TARGETS}}
                       for c in cheats]}
    with open(os.path.join(folder, "info.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(info, f, indent=2, ensure_ascii=False)

def emulator_for(save_folder):
    if not save_folder:
        return None
    parts = os.path.normpath(save_folder).split(os.sep)
    low = [p.lower() for p in parts]
    for i in range(len(low) - 2):
        if low[i:i + 3] == ["bis", "user", "save"]:
            root = os.sep.join(parts[:i]) or os.sep
            title_dir = os.path.join(root, "mods", "contents", TITLE_ID.lower())
            return {"name": "Ryujinx", "root": root,
                    "cheat_dir": os.path.join(title_dir, "OOT Save Editor Cheats", "cheats"),
                    "enabled_file": os.path.join(title_dir, "cheats", "enabled.txt"),
                    "logs": [os.path.join(root, "Logs")]}
        if low[i:i + 3] == ["nand", "user", "save"]:
            root = os.sep.join(parts[:i]) or os.sep
            return {"name": os.path.basename(root) or "yuzu-based emulator", "root": root,
                    "cheat_dir": os.path.join(root, "load", TITLE_ID, "OOT Save Editor Cheats", "cheats"),
                    "enabled_file": None, "logs": [os.path.join(root, "log")]}
    return None

def detect_build_ids(emulator):
    found = []
    for folder in (emulator or {}).get("logs", []):
        logs = sorted(glob.glob(os.path.join(glob.escape(folder), "*.txt")) +
                      glob.glob(os.path.join(glob.escape(folder), "*.log")), key=os.path.getmtime, reverse=True)
        for path in logs[:10]:
            try:
                lines = open(path, encoding="utf-8", errors="ignore").read().splitlines()
            except OSError:
                continue
            for n, line in enumerate(lines):
                if any(tid in line.upper() for tid in ALL_TITLE_IDS) and "build_id=" in line:
                    m = re.search(r"build_id=([0-9A-Fa-f]{16,64})", line)
                    if m:
                        bid = m.group(1)[:16].upper()
                        if bid not in found:
                            found.append(bid)
    return found

def is_emulator_running():
    """Checks whether lichii, eden, yuzu, or ryujinx processes are actively running."""
    if sys.platform != "win32":
        return False
    try:
        out = subprocess.check_output('tasklist /FI "STATUS eq RUNNING" /FO CSV /NH', shell=True, text=True)
        low = out.lower()
        for name in ("lichii.exe", "eden.exe", "yuzu.exe", "suyu.exe", "sudachi.exe", "ryujinx.exe"):
            if name in low:
                return True
    except Exception:
        pass
    return False

# ---------- Themes & Palettes ----------
PALETTES = {
    "light": {"bg": "#f0f0f0", "surface": "#e6e6e6", "field": "#ffffff", "fg": "#000000", "muted": "#555555",
              "faint": "#888888", "border": "#c8c8c8", "hover": "#dcdcdc", "select": "#0078d7",
              "accent": "#0b5cad", "warn": "#b26a00", "banner": "#fff4e0", "tag_worn": "#0b5cad", "tag_key": "#6a4c93",
              "tag_none": "#999999", "tag_on": "#2e7d32", "tag_off": "#888888"},
    "dark": {"bg": "#1f2125", "surface": "#2b2e33", "field": "#26292e", "fg": "#e8e8e8", "muted": "#a9adb4",
             "faint": "#7d828a", "border": "#3d4148", "hover": "#353940", "select": "#2f5f9e",
             "accent": "#6cb4ff", "warn": "#ffb74d", "banner": "#3a3020", "tag_worn": "#6cb4ff", "tag_key": "#c7a8ff",
             "tag_none": "#6f747c", "tag_on": "#7fd88a", "tag_off": "#7d828a"},
}
THEMES = ("System", "Light", "Dark")

def system_prefers_dark():
    """True if the system is set to dark mode for apps (Windows, macOS, GNOME/KDE on Linux)."""
    if sys.platform == "darwin":
        try:
            out = subprocess.run(["defaults", "read", "-g", "AppleInterfaceStyle"],
                                 capture_output=True, text=True, timeout=2).stdout
            return "dark" in out.lower()
        except (OSError, subprocess.SubprocessError):
            return False
    if sys.platform != "win32":
        try:
            out = subprocess.run(["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
                                 capture_output=True, text=True, timeout=2).stdout
            if "dark" in out.lower():
                return True
        except (OSError, subprocess.SubprocessError):
            pass
        try:
            kde = open(os.path.expanduser("~/.config/kdeglobals"), encoding="utf-8", errors="ignore").read()
            return "colorscheme=" in kde.lower() and "dark" in kde.lower().split("colorscheme=", 1)[1].split("\n", 1)[0]
        except OSError:
            return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as key:
            return winreg.QueryValueEx(key, "AppsUseLightTheme")[0] == 0
    except OSError:
        return False

def open_folder(path):
    if sys.platform == "win32":
        os.startfile(path)
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", path])

def load_settings():
    try:
        with open(SETTINGS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}

def store_settings(settings):
    try:
        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except OSError:
        pass

# ---------- Save Directory Resolution ----------
def resolve_save_folder(folder):
    if not folder or not os.path.isdir(folder):
        return None
    # Check if folder directly has slot_00 or slot_01
    if any(os.path.isdir(os.path.join(folder, f"slot_{i:02d}")) for i in range(6)):
        return folder
    # Recursively check subdirectories up to 5 levels deep
    for root, dirs, files in os.walk(folder):
        if any(d.startswith("slot_") for d in dirs):
            if any(os.path.exists(os.path.join(root, d, "progress.sav")) for d in dirs if d.startswith("slot_")):
                return root
    return None

def candidate_roots():
    roots = []
    appdata = os.environ.get("APPDATA", "")
    home = os.path.expanduser("~")
    bases = [appdata, os.path.join(home, ".config"), os.path.join(home, ".local", "share")]
    for base in bases:
        if not base: continue
        for emu in ("eden", "yuzu", "suyu", "sudachi", "citron", "torzu"):
            roots.append(os.path.join(base, emu, "nand", "user", "save"))
        roots.append(os.path.join(base, "Ryujinx", "bis", "user", "save"))
    return [r for r in roots if os.path.isdir(r)]

def autodetect():
    for root in candidate_roots():
        for tid in ALL_TITLE_IDS:
            hits = glob.glob(os.path.join(glob.escape(root), "*", "*", tid))
            hits += glob.glob(os.path.join(glob.escape(root), "*", "*", tid.lower()))
            for h in hits:
                found = resolve_save_folder(h)
                if found:
                    return found
    return None

# ---------- Main GUI Editor Class ----------
class OOTEditor(tk.Tk):
    def __init__(self, folder=None):
        super().__init__()
        self.title(APP_NAME)
        self._set_icon()
        self.geometry("960x740")
        self.minsize(820, 560)
        self.settings = load_settings()
        self.root_dir = tk.StringVar()
        self.slot = tk.StringVar()
        self.slot_names = []
        self.active_slot = None
        self.orig_snapshot = {}
        self._sort = {}
        self.cheats = []
        self.emulator = None
        self._story_warned = False  # Track user confirmation for story items

        # Variables for tabs
        self.general_vars = {}
        self.equip_vars = {}
        self.ammo_vars = {}
        self.bottle_vars = {}
        self.quest_vars = {}
        self.song_vars = {}

        self._style()
        self._build_top()
        self._build_tabs()
        self.apply_theme()

        start = folder or self.settings.get("save_folder")
        start = resolve_save_folder(start) if start else None
        self.set_folder(start or autodetect())

    def _set_icon(self):
        icons = os.path.join(RESOURCE_DIR, "assets")
        try:
            if sys.platform == "win32":
                self.iconbitmap(default=os.path.join(icons, "icon.ico"))
            else:
                self._icon = tk.PhotoImage(file=os.path.join(icons, "icon.png"))
                self.iconphoto(True, self._icon)
        except (tk.TclError, OSError):
            pass

    def _style(self):
        self.style = ttk.Style(self)
        self.base_theme = self.style.theme_use()
        self.palette = PALETTES["light"]
        self._style_common()

    def _build_top(self):
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")

        # Save folder row
        ttk.Label(top, text="Save folder:").grid(row=0, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.root_dir, state="readonly").grid(row=0, column=1, sticky="ew", padx=4)
        fb = ttk.Frame(top)
        fb.grid(row=0, column=2, sticky="ew")
        ttk.Button(fb, text="Browse…", command=self.browse).pack(side="left")
        ttk.Button(fb, text="Auto-detect", command=self.redetect).pack(side="left", padx=(4, 0))

        # Slot row
        ttk.Label(top, text="Slot:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.slot_box = ttk.Combobox(top, textvariable=self.slot, state="readonly")
        self.slot_box.grid(row=1, column=1, sticky="ew", padx=4, pady=(6, 0))
        self.slot_box.bind("<<ComboboxSelected>>", lambda e: self.load_slot())
        btns = ttk.Frame(top)
        btns.grid(row=1, column=2, pady=(6, 0), sticky="ew")
        ttk.Button(btns, text="Reload", command=self.load_slot).pack(side="left")
        self.primary_button(btns, "Save changes", self.save).pack(side="left", padx=(4, 0))

        # Backups row
        bk = ttk.LabelFrame(top, text="Backups", padding=6)
        bk.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        ttk.Button(bk, text="Back up now…", command=self.backup_now).pack(side="left")
        ttk.Button(bk, text="Restore a backup…", command=self.restore_dialog).pack(side="left", padx=4)
        ttk.Button(bk, text="Open backups folder", command=self.open_backups).pack(side="left")
        self.backup_count = tk.StringVar()
        ttk.Label(bk, textvariable=self.backup_count, style="Muted.TLabel").pack(side="left", padx=10)

        self.theme_choice = tk.StringVar(value=self.settings.get("theme", "System"))
        theme = ttk.Combobox(bk, textvariable=self.theme_choice, values=THEMES, state="readonly", width=8)
        theme.pack(side="right")
        theme.bind("<<ComboboxSelected>>", self.on_theme_pick)
        ttk.Label(bk, text="Theme:").pack(side="right", padx=(0, 4))
        top.columnconfigure(1, weight=1)

        self.status = tk.StringVar(value="Close the game/emulator before saving or restoring.")
        self.status_lbl = ttk.Label(self, textvariable=self.status, style="Muted.TLabel", padding=(8, 0))
        self.status_lbl.pack(side="bottom", fill="x", pady=4)

    def _build_tabs(self):
        nb = self.nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=4)

        # 1. General & Stats Tab
        self._build_general_tab(nb)

        # 2. Equipment & Upgrades Tab
        self._build_equipment_tab(nb)

        # 3. Inventory & Bottles Tab
        self._build_inventory_tab(nb)

        # 4. Quest Status & Songs Tab
        self._build_quest_tab(nb)

        # 5. Walkthrough Tab
        self._build_walkthrough_tab(nb)

        # 6. Cheats Tab
        self._build_cheats_tab(nb)

        nb.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    # ---------- TAB 1: General & Stats ----------
    def _build_general_tab(self, nb):
        gen = ttk.Frame(nb, padding=12)
        nb.add(gen, text="General")

        # Rupees
        r = 0
        ttk.Label(gen, text="Rupees:").grid(row=r, column=0, sticky="w", pady=4)
        self.v_rupees = tk.StringVar(value="0")
        ttk.Spinbox(gen, from_=0, to=999, textvariable=self.v_rupees, width=12).grid(row=r, column=1, sticky="w", padx=8)
        ttk.Button(gen, text="Max", width=6, command=lambda: self.v_rupees.set("999")).grid(row=r, column=2, sticky="w")
        ttk.Label(gen, text="(0–999)", style="Faint.TLabel").grid(row=r, column=3, sticky="w", padx=(8, 0))

        # Hearts / Current Health
        r += 1
        ttk.Label(gen, text="Hearts (Health):").grid(row=r, column=0, sticky="w", pady=4)
        self.v_hearts = tk.StringVar(value="3")
        ttk.Spinbox(gen, from_=3, to=20, textvariable=self.v_hearts, width=12).grid(row=r, column=1, sticky="w", padx=8)
        ttk.Button(gen, text="Max", width=6, command=lambda: self.v_hearts.set("20")).grid(row=r, column=2, sticky="w")
        ttk.Label(gen, text="(3–20 hearts)", style="Faint.TLabel").grid(row=r, column=3, sticky="w", padx=(8, 0))

        # Max Heart Containers
        r += 1
        ttk.Label(gen, text="Max Heart Containers:").grid(row=r, column=0, sticky="w", pady=4)
        self.v_containers = tk.StringVar(value="3")
        ttk.Spinbox(gen, from_=3, to=20, textvariable=self.v_containers, width=12).grid(row=r, column=1, sticky="w", padx=8)
        ttk.Button(gen, text="Max", width=6, command=lambda: self.v_containers.set("20")).grid(row=r, column=2, sticky="w")
        ttk.Label(gen, text="(3–20 containers)", style="Faint.TLabel").grid(row=r, column=3, sticky="w", padx=(8, 0))

        # Pieces of Heart (0-3)
        r += 1
        ttk.Label(gen, text="Pieces of Heart:").grid(row=r, column=0, sticky="w", pady=4)
        self.v_heart_pieces = tk.StringVar(value="0")
        ttk.Spinbox(gen, from_=0, to=3, textvariable=self.v_heart_pieces, width=12).grid(row=r, column=1, sticky="w", padx=8)
        ttk.Label(gen, text="(0–3 towards next container)", style="Faint.TLabel").grid(row=r, column=3, sticky="w", padx=(8, 0))

        # Magic Meter
        r += 1
        ttk.Label(gen, text="Magic Meter:").grid(row=r, column=0, sticky="w", pady=4)
        self.v_magic = tk.StringVar(value="None")
        magic_box = ttk.Combobox(gen, textvariable=self.v_magic, state="readonly", width=18,
                                 values=["None", "Standard Magic", "Double Magic"])
        magic_box.grid(row=r, column=1, sticky="w", padx=8)

        # Gold Skulltula Tokens
        r += 1
        ttk.Label(gen, text="Gold Skulltula Tokens:").grid(row=r, column=0, sticky="w", pady=4)
        self.v_tokens = tk.StringVar(value="0")
        ttk.Spinbox(gen, from_=0, to=100, textvariable=self.v_tokens, width=12).grid(row=r, column=1, sticky="w", padx=8)
        ttk.Button(gen, text="Max", width=6, command=lambda: self.v_tokens.set("100")).grid(row=r, column=2, sticky="w")
        ttk.Label(gen, text="(0–100 tokens)", style="Faint.TLabel").grid(row=r, column=3, sticky="w", padx=(8, 0))

        # Double Defense
        r += 1
        self.v_double_defense = tk.BooleanVar(value=False)
        ttk.Checkbutton(gen, text="Double Defense (White Heart Outline)", variable=self.v_double_defense).grid(
            row=r, column=0, columnspan=3, sticky="w", pady=6)

        # Action Buttons
        r += 1
        ttk.Button(gen, text="Max All Stats", command=self.max_general).grid(
            row=r, column=1, sticky="w", padx=8, pady=(12, 0))

        # Info Box
        r += 1
        self.gen_info = tk.StringVar()
        ttk.Label(gen, textvariable=self.gen_info, style="Muted.TLabel", justify="left").grid(
            row=r, column=0, columnspan=4, sticky="w", pady=(20, 0))

    # ---------- TAB 2: Equipment & Gear ----------
    def _build_equipment_tab(self, nb):
        eq = ttk.Frame(nb, padding=12)
        nb.add(eq, text="Equipment")

        # Equipment Combos
        items = [
            ("Sword:", SWORDS, "sword"),
            ("Shield:", SHIELDS, "shield"),
            ("Tunic:", TUNICS, "tunic"),
            ("Boots:", BOOTS, "boots"),
            ("Wallet:", WALLETS, "wallet"),
            ("Quiver (Bow Capacity):", QUIVERS, "quiver"),
            ("Bomb Bag (Capacity):", BOMB_BAGS, "bomb_bag"),
            ("Strength (Gauntlets):", STRENGTH_UPGRADES, "strength"),
            ("Diving Scale:", SCALES, "scale"),
        ]

        for r, (label, choices, key) in enumerate(items):
            ttk.Label(eq, text=label).grid(row=r, column=0, sticky="w", pady=4)
            var = tk.StringVar(value=choices[0])
            box = ttk.Combobox(eq, textvariable=var, state="readonly", width=26, values=choices)
            box.grid(row=r, column=1, sticky="w", padx=10)
            self.equip_vars[key] = var

        ttk.Button(eq, text="Max Out All Equipment", command=self.max_equipment).grid(
            row=len(items), column=1, sticky="w", padx=10, pady=(14, 0))

        ttk.Label(eq, style="Muted.TLabel", wraplength=820, text=(
            "Equipping gear adjusts your inventory and abilities immediately upon loading your save. "
            "Selecting Master Sword, Biggoron's Sword, or specialized tunics allows Link to use them "
            "whenever appropriate in your quest.")).grid(
            row=len(items) + 1, column=0, columnspan=3, sticky="w", pady=(16, 0))

    # ---------- TAB 3: Inventory & Bottles ----------
    def _build_inventory_tab(self, nb):
        inv = ttk.Frame(nb, padding=12)
        nb.add(inv, text="Inventory")

        # Ammo section
        ammo_frame = ttk.LabelFrame(inv, text="Ammo & Consumables", padding=10)
        ammo_frame.grid(row=0, column=0, columnspan=4, sticky="ew")

        ammo_list = [
            ("Arrows:", 50, "arrows", self.v_rupees),
            ("Bombs:", 40, "bombs", None),
            ("Bombchus:", 50, "bombchus", None),
            ("Deku Seeds:", 50, "seeds", None),
            ("Deku Sticks:", 30, "sticks", None),
            ("Deku Nuts:", 40, "nuts", None),
            ("Magic Beans:", 10, "beans", None),
        ]

        for i, (label, max_val, key, _) in enumerate(ammo_list):
            row = i // 2
            col = (i % 2) * 3
            ttk.Label(ammo_frame, text=label).grid(row=row, column=col, sticky="w", padx=(10 if col else 0, 4), pady=3)
            v = tk.StringVar(value="0")
            ttk.Spinbox(ammo_frame, from_=0, to=max_val, textvariable=v, width=8).grid(
                row=row, column=col+1, sticky="w", padx=4)
            ttk.Button(ammo_frame, text="Max", width=5, command=lambda var=v, m=max_val: var.set(str(m))).grid(
                row=row, column=col+2, sticky="w")
            self.ammo_vars[key] = (v, max_val)

        ttk.Button(ammo_frame, text="Max All Ammo", command=self.max_ammo).grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(10, 0))

        # Bottles section
        bot_frame = ttk.LabelFrame(inv, text="Bottles", padding=10)
        bot_frame.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(12, 0))

        for b in range(1, 5):
            ttk.Label(bot_frame, text=f"Bottle {b}:").grid(row=b-1, column=0, sticky="w", pady=4)
            bv = tk.StringVar(value=BOTTLE_CONTENTS[0])
            box = ttk.Combobox(bot_frame, textvariable=bv, state="readonly", width=36, values=BOTTLE_CONTENTS)
            box.grid(row=b-1, column=1, sticky="w", padx=10)
            self.bottle_vars[f"bottle_{b}"] = bv

        ttk.Button(bot_frame, text="Fill All with Bottled Fairies", command=self.fairies_in_all_bottles).grid(
            row=4, column=1, sticky="w", padx=10, pady=(8, 0))

    # ---------- TAB 4: Quest Status & Songs ----------
    def _build_quest_tab(self, nb):
        qst = ttk.Frame(nb, padding=12)
        nb.add(qst, text="Quest items")

        # Spiritual Stones & Medallions
        sm_frame = ttk.LabelFrame(qst, text="Spiritual Stones & Medallions (Story Items ⚠)", padding=10)
        sm_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        for idx, (name, hash_key, desc) in enumerate(STONES_MEDALLIONS):
            var = tk.BooleanVar(value=False)
            cb = ttk.Checkbutton(sm_frame, text=f"{name} — {desc}", variable=var,
                                 command=lambda hk=hash_key, v=var: self._on_story_item_toggle(hk, v))
            cb.grid(row=idx, column=0, sticky="w", pady=2)
            self.quest_vars[hash_key] = var

        btn_row = ttk.Frame(sm_frame)
        btn_row.grid(row=len(STONES_MEDALLIONS), column=0, sticky="w", pady=(8, 0))
        ttk.Button(btn_row, text="Unlock All Stones & Medallions", command=self.unlock_all_stones).pack(side="left")

        # Ocarina Songs
        songs_frame = ttk.LabelFrame(qst, text="Ocarina Songs", padding=10)
        songs_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        for idx, (sname, shash, sdesc) in enumerate(SONGS):
            svar = tk.BooleanVar(value=False)
            scb = ttk.Checkbutton(songs_frame, text=f"{sname} ({sdesc})", variable=svar)
            scb.grid(row=idx, column=0, sticky="w", pady=2)
            self.song_vars[shash] = svar

        btn_row2 = ttk.Frame(songs_frame)
        btn_row2.grid(row=len(SONGS), column=0, sticky="w", pady=(8, 0))
        ttk.Button(btn_row2, text="Learn All Songs", command=self.learn_all_songs).pack(side="left")

        qst.columnconfigure(0, weight=1)
        qst.columnconfigure(1, weight=1)

    def _on_story_item_toggle(self, key_hash, var):
        """Intercepts story item changes and issues a confirmation warning."""
        if not self._story_warned:
            want = var.get()
            item_name = next((name for name, h, _ in STONES_MEDALLIONS if h == key_hash), "this story item")
            msg = (
                f"Spiritual Stones and Medallions are critical story items tied to game progression.\n\n"
                f"Adding or removing '{item_name}' can sequence-break your save file or cause progression glitches.\n\n"
                f"Change story items anyway?"
            )
            if messagebox.askyesno("Story Item Warning", msg, icon="warning", parent=self):
                self._story_warned = True
                self.refresh_walkthrough()
            else:
                # Revert change
                var.set(not want)
                return
        else:
            self.refresh_walkthrough()

    # ---------- TAB 5: Walkthrough & Collectibles ----------
    def _build_walkthrough_tab(self, nb):
        wk = ttk.Frame(nb, padding=12)
        nb.add(wk, text="Walkthrough")

        prog = ttk.LabelFrame(wk, text="Your progress (from this save)", padding=10)
        prog.grid(row=0, column=0, columnspan=6, sticky="ew")

        self.walk_now = tk.StringVar(value="Load a save slot to see your progress.")
        ttk.Label(prog, textvariable=self.walk_now, font=("Segoe UI", 11, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w")
        self.walk_btn = self.primary_button(prog, "Open this chapter's guide", self.open_current_chapter)
        self.walk_btn.grid(row=0, column=3, sticky="e", padx=(12, 0))

        # Heart Pieces progress bar
        ttk.Label(prog, text="Heart Pieces:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.hp_bar = ttk.Progressbar(prog, maximum=TOTAL_HEART_PIECES, length=260)
        self.hp_bar.grid(row=1, column=1, sticky="w", padx=8, pady=(8, 0))
        self.hp_text = tk.StringVar(value="0 / 36 found")
        ttk.Label(prog, textvariable=self.hp_text, style="Muted.TLabel").grid(row=1, column=2, sticky="w", pady=(8, 0))

        # Gold Skulltula Tokens progress bar
        ttk.Label(prog, text="Gold Skulltulas:").grid(row=2, column=0, sticky="w", pady=(4, 0))
        self.token_bar = ttk.Progressbar(prog, maximum=TOTAL_SKULLTULAS, length=260)
        self.token_bar.grid(row=2, column=1, sticky="w", padx=8, pady=(4, 0))
        self.token_text = tk.StringVar(value="0 / 100 found")
        ttk.Label(prog, textvariable=self.token_text, style="Muted.TLabel").grid(row=2, column=2, sticky="w", pady=(4, 0))
        prog.columnconfigure(2, weight=1)

        self.walk_tree = self._make_tree(wk, (("ch", "Chapter", 100), ("goal", "Goal / Dungeon", 340),
                                              ("status", "Status", 140), ("guide", "Walkthrough", 220)), row=1, height=8)
        self.walk_tree.bind("<Double-1>", lambda e: self.open_selected_chapter())

        row = ttk.Frame(wk)
        row.grid(row=2, column=0, columnspan=6, sticky="w", pady=(8, 0))
        ttk.Button(row, text="Open selected chapter guide", command=self.open_selected_chapter).pack(side="left")
        ttk.Button(row, text="Full Walkthrough (Zelda Dungeon)", command=lambda: webbrowser.open(WALKTHROUGH_URL)).pack(
            side="left", padx=6)
        ttk.Button(row, text="Heart Pieces Guide (36)", command=lambda: webbrowser.open(GUIDE_HEART_PIECES_URL)).pack(
            side="left")
        ttk.Button(row, text="Gold Skulltulas Guide (100)", command=lambda: webbrowser.open(GUIDE_SKULLTULAS_URL)).pack(
            side="left", padx=6)
        wk.columnconfigure(0, weight=1)

    # ---------- TAB 6: Cheats (Atmosphère / Emulator) ----------
    def _build_cheats_tab(self, nb):
        ct = ttk.Frame(nb, padding=12)
        nb.add(ct, text="Cheats")

        info_box = ttk.LabelFrame(ct, text="Cheat engine status", padding=8)
        info_box.pack(fill="x")
        self.cheat_status = tk.StringVar(value="Detecting emulator & cheats…")
        ttk.Label(info_box, textvariable=self.cheat_status).pack(side="left")
        ttk.Button(info_box, text="Refresh", command=self.refresh_cheats).pack(side="right")

        self.cheat_tree = self._make_tree(
            ct, (("on", "On", 46), ("name", "Cheat", 280), ("tested", "Tested", 120),
                 ("desc", "Description", 360)), row=None, height=12)
        self.cheat_tree.bind("<Double-1>", lambda e: self.toggle_cheats())

        crow = ttk.Frame(ct)
        crow.pack(fill="x")
        ttk.Button(crow, text="Install to emulator", command=self.install_cheats).pack(side="left")
        ttk.Button(crow, text="Export for Switch (Atmosphère)", command=self.export_cheats).pack(side="left", padx=6)
        ttk.Button(crow, text="Uninstall cheats", command=self.uninstall_cheats).pack(side="left")
        ttk.Button(crow, text="Open cheat folder", command=self.open_cheat_folder).pack(side="left", padx=6)
        ttk.Button(crow, text="Cheat guide & help", command=self.show_cheat_guide).pack(side="right")

    def _make_tree(self, parent, columns, row=None, height=10):
        frame = ttk.Frame(parent)
        if row is not None:
            frame.grid(row=row, column=0, columnspan=6, sticky="nsew", pady=4)
        else:
            frame.pack(fill="both", expand=True)

        cols = [c[0] for c in columns]
        tree = ttk.Treeview(frame, columns=cols, show="headings", height=height, selectmode="extended")
        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        for cid, title, width in columns:
            tree.heading(cid, text=title, command=lambda c=cid, t=tree: self.sort_by(t, c))
            tree.column(cid, width=width, stretch=True)

        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        return tree

    # ---------- Navigation & Save Loading ----------
    def set_folder(self, folder):
        folder = resolve_save_folder(folder)
        if not folder:
            self.root_dir.set("")
            self.slot_box.configure(values=[])
            self.slot.set("")
            self.active_slot = None
            self.status.set("No save folder found. Click Browse or Auto-detect.")
            return

        self.root_dir.set(folder)
        self.settings["save_folder"] = folder
        store_settings(self.settings)
        self.refresh_slots()
        self.update_backup_count()
        self.detect_cheat_target()

    def browse(self):
        f = filedialog.askdirectory(title="Choose save directory or emulator NAND folder")
        if f:
            self.set_folder(f)

    def redetect(self):
        f = autodetect()
        if f:
            self.set_folder(f)
            self.status.set(f"Auto-detected save folder: {f}")
        else:
            messagebox.showinfo("Auto-detect", "Could not locate standard save directories for Lichii/Eden/Yuzu.")

    def refresh_slots(self):
        f = self.root_dir.get()
        if not f or not os.path.isdir(f):
            return
        slots = []
        for i in range(6):
            sname = f"slot_{i:02d}"
            sdir = os.path.join(f, sname)
            if os.path.isdir(sdir) and os.path.exists(os.path.join(sdir, "progress.sav")):
                slots.append(sname)

        self.slot_names = slots
        display_names = [f"{SLOT_NAMES.get(s, s)} ({s})" for s in slots]
        self.slot_box.configure(values=display_names)
        if slots:
            # Prefer slot_03 or first slot
            def_idx = 3 if len(slots) > 3 else 0
            self.slot_box.current(def_idx)
            self.load_slot()

    def load_slot(self):
        idx = self.slot_box.current()
        if idx < 0 or idx >= len(self.slot_names):
            return
        sdir = self.slot_names[idx]
        slot_path = os.path.join(self.root_dir.get(), sdir)
        try:
            self.active_slot = SaveSlot(slot_path)
        except Exception as e:
            messagebox.showerror("Load failed", str(e))
            return

        s = self.active_slot

        # Populate General Tab
        rupees = s.get(HASH_RUPEES, 0)
        self.v_rupees.set(str(rupees))
        health = s.get(HASH_HEALTH, 48)
        self.v_hearts.set(str(max(3, min(20, health // 16))))
        pieces_data = s.get(HASH_HEART_PIECES, 12)
        containers = pieces_data // 4
        pieces = pieces_data % 4
        self.v_containers.set(str(max(3, min(20, containers))))
        self.v_heart_pieces.set(str(pieces))
        tokens = s.get(HASH_TOKENS, 0)
        self.v_tokens.set(str(tokens))

        # Magic Meter & Double Defense
        has_double_magic = bool(s.caption_entries.get(0xc72044fc, 0))
        has_magic = bool(s.caption_entries.get(0x89ae7032, 0)) or has_double_magic
        self.v_magic.set("Double Magic" if has_double_magic else ("Standard Magic" if has_magic else "None"))
        self.v_double_defense.set(bool(s.caption_entries.get(0xfb2b5f6b, 0)))

        # Populate Ammo (strictly read from save, fallback to 0)
        self.ammo_vars["arrows"][0].set(str(s.get(HASH_ARROWS, 0)))
        self.ammo_vars["bombs"][0].set(str(s.get(HASH_BOMBS, 0)))
        self.ammo_vars["bombchus"][0].set(str(s.get(HASH_BOMBCHUS, 0)))
        self.ammo_vars["seeds"][0].set(str(s.get(HASH_DEKU_SEEDS, 0)))
        self.ammo_vars["sticks"][0].set(str(s.get(HASH_DEKU_STICKS, 0)))
        self.ammo_vars["nuts"][0].set(str(s.get(HASH_DEKU_NUTS, 0)))
        self.ammo_vars["beans"][0].set(str(s.get(HASH_MAGIC_BEANS, 0)))

        # Populate Equipment & Upgrades
        sw_str = s.strings_sec2.get(0xa95a3521, "")
        if "Master" in sw_str: sw = "Master Sword"
        elif "Biggoron" in sw_str: sw = "Biggoron's Sword"
        elif "Kokiri" in sw_str: sw = "Kokiri Sword"
        elif "Giant" in sw_str: sw = "Giant's Knife"
        else: sw = "(None)"
        self.equip_vars["sword"].set(sw)

        sh_str = s.strings_sec2.get(0xee463235, "")
        if "Deku" in sh_str: sh = "Deku Shield"
        elif "Hylian" in sh_str: sh = "Hylian Shield"
        elif "Mirror" in sh_str: sh = "Mirror Shield"
        else: sh = "(None)"
        self.equip_vars["shield"].set(sh)

        self.equip_vars["tunic"].set(TUNICS[0]) # Kokiri Tunic
        self.equip_vars["boots"].set(BOOTS[0])   # Kokiri Boots

        w_str = s.strings_sec2.get(0x3e42affa, "")
        if "Large" in w_str: w = WALLETS[2]
        elif "Giant" in w_str: w = WALLETS[3]
        elif "Medium" in w_str: w = WALLETS[1]
        elif "Small" in w_str: w = WALLETS[0]
        else: w = WALLETS[2] if rupees > 200 else (WALLETS[1] if rupees > 99 else WALLETS[0])
        self.equip_vars["wallet"].set(w)

        bb_str = s.strings_sec2.get(0xa835e3b0, "")
        if "Large" in bb_str: bb = BOMB_BAGS[3]
        elif "Medium" in bb_str: bb = BOMB_BAGS[2]
        elif "Small" in bb_str: bb = BOMB_BAGS[1]
        else: bb = BOMB_BAGS[0]
        self.equip_vars["bomb_bag"].set(bb)

        q_found = any("Quiver" in val for val in s.strings_sec2.values())
        self.equip_vars["quiver"].set(QUIVERS[1] if q_found else QUIVERS[0])

        st_found = next((val for val in s.strings_sec2.values() if any(x in val for x in ("Bracelet", "Gauntlet"))), None)
        if st_found:
            st = STRENGTH_UPGRADES[3] if "Gold" in st_found else (STRENGTH_UPGRADES[2] if "Silver" in st_found else STRENGTH_UPGRADES[1])
        else:
            st = STRENGTH_UPGRADES[0]
        self.equip_vars["strength"].set(st)

        sc_found = next((val for val in s.strings_sec2.values() if "Scale" in val), None)
        if sc_found:
            sc = SCALES[2] if "Gold" in sc_found else SCALES[1]
        else:
            sc = SCALES[0]
        self.equip_vars["scale"].set(sc)

        # Populate Bottles (default empty unless verified)
        for b in range(1, 5):
            self.bottle_vars[f"bottle_{b}"].set(BOTTLE_CONTENTS[0])

        # Populate Quest Items
        # Spiritual Stones (Child Link with Ocarina of Time and Water Stone has collected the 3 stones)
        has_sapphire = (0x0f4e78bc in s.strings_sec2) or bool(s.caption_entries.get(0x7c5b03dc, 0))
        has_emerald = bool(s.caption_entries.get(0x50c6bedf, 0)) or has_sapphire
        has_ruby = bool(s.caption_entries.get(0x380a5616, 0)) or has_sapphire

        self.quest_vars[0x50c6bedf].set(has_emerald)
        self.quest_vars[0x380a5616].set(has_ruby)
        self.quest_vars[0x7c5b03dc].set(has_sapphire)

        # Medallions (Only unlocked if Link has awakened as Adult Link / pulled Master Sword)
        is_adult_unlocked = ("Master" in sw_str) or ("Adult" in s.map_name)
        for _, kh, _ in MEDALLIONS:
            if kh in self.quest_vars:
                val = bool(s.caption_entries.get(kh, 0)) and is_adult_unlocked
                self.quest_vars[kh].set(val)

        # Populate Songs (read from caption_entries, default False)
        for sname, shash, _ in SONGS:
            if shash in self.song_vars:
                self.song_vars[shash].set(bool(s.caption_entries.get(shash, 0)))

        # Walkthrough progress
        self.refresh_walkthrough()

        # Update info text
        self.gen_info.set(
            f"Location: {s.map_name}\n"
            f"Slot: {SLOT_NAMES.get(sdir, sdir)} ({sdir})\n"
            f"Gold Skulltulas: {s.get(HASH_TOKENS, 0)} / {TOTAL_SKULLTULAS}\n"
            f"Heart Pieces: {min(TOTAL_HEART_PIECES, s.get(HASH_HEART_PIECES, 0))} / {TOTAL_HEART_PIECES}\n"
            f"Status: Safe to edit (close emulator before saving)"
        )
        self.status.set(f"Loaded {SLOT_NAMES.get(sdir, sdir)}. Close emulator before saving.")
        self.snapshot_current()

    def snapshot_current(self):
        """Records state so we can display exact diffs on save."""
        self.orig_snapshot = {
            "rupees": self.v_rupees.get(),
            "hearts": self.v_hearts.get(),
            "containers": self.v_containers.get(),
            "heart_pieces": self.v_heart_pieces.get(),
            "tokens": self.v_tokens.get(),
            "magic": self.v_magic.get(),
            "double_defense": self.v_double_defense.get(),
            "sword": self.equip_vars["sword"].get(),
            "shield": self.equip_vars["shield"].get(),
            "wallet": self.equip_vars["wallet"].get(),
            "quiver": self.equip_vars["quiver"].get(),
            "bomb_bag": self.equip_vars["bomb_bag"].get(),
            "strength": self.equip_vars["strength"].get(),
            "scale": self.equip_vars["scale"].get(),
            "arrows": self.ammo_vars["arrows"][0].get(),
            "bombs": self.ammo_vars["bombs"][0].get(),
            "bombchus": self.ammo_vars["bombchus"][0].get(),
            "seeds": self.ammo_vars["seeds"][0].get(),
            "sticks": self.ammo_vars["sticks"][0].get(),
            "nuts": self.ammo_vars["nuts"][0].get(),
            "beans": self.ammo_vars["beans"][0].get(),
        }

    def max_general(self):
        self.v_rupees.set("999")
        self.v_hearts.set("20")
        self.v_containers.set("20")
        self.v_heart_pieces.set("0")
        self.v_magic.set("Double Magic")
        self.v_tokens.set("100")
        self.v_double_defense.set(True)
        self.status.set("Maxed all general stats (not saved yet).")

    def max_equipment(self):
        self.equip_vars["sword"].set(SWORDS[3])          # Biggoron's Sword
        self.equip_vars["shield"].set(SHIELDS[3])        # Mirror Shield
        self.equip_vars["wallet"].set(WALLETS[3])        # Tycoon's Wallet
        self.equip_vars["quiver"].set(QUIVERS[3])        # Biggest Quiver (50)
        self.equip_vars["bomb_bag"].set(BOMB_BAGS[3])    # Biggest Bomb Bag (40)
        self.equip_vars["strength"].set(STRENGTH_UPGRADES[3]) # Golden Gauntlets
        self.equip_vars["scale"].set(SCALES[2])          # Golden Scale
        self.status.set("Maxed all equipment & upgrades (not saved yet).")

    def max_ammo(self):
        for k, (v, m) in self.ammo_vars.items():
            v.set(str(m))
        self.status.set("Maxed all ammo & consumables (not saved yet).")

    def fairies_in_all_bottles(self):
        for b in range(1, 5):
            self.bottle_vars[f"bottle_{b}"].set("Bottled Fairy (Revives Link)")
        self.status.set("Put Bottled Fairies in all bottles (not saved yet).")

    def unlock_all_stones(self):
        if not self._story_warned:
            msg = (
                "Spiritual Stones and Medallions are critical story items tied to game progression.\n\n"
                "Unlocking all story items at once can sequence-break your save or mark dungeons as completed.\n\n"
                "Unlock all story items anyway?"
            )
            if not messagebox.askyesno("Story Item Warning", msg, icon="warning", parent=self):
                return
            self._story_warned = True

        for _, kh, _ in STONES_MEDALLIONS:
            if kh in self.quest_vars:
                self.quest_vars[kh].set(True)
        self.refresh_walkthrough()
        self.status.set("Unlocked all Spiritual Stones & Medallions.")

    def learn_all_songs(self):
        for sname, shash, _ in SONGS:
            if shash in self.song_vars:
                self.song_vars[shash].set(True)
        self.status.set("Learned all 12 Ocarina Songs.")

    def refresh_walkthrough(self):
        self.walk_tree.delete(*self.walk_tree.get_children())
        if not self.active_slot:
            return

        s = self.active_slot
        # Accurately compute progress from quest vars in this slot
        has_emerald = self.quest_vars[0x50c6bedf].get() if 0x50c6bedf in self.quest_vars else False
        has_ruby = self.quest_vars[0x380a5616].get() if 0x380a5616 in self.quest_vars else False
        has_sapphire = self.quest_vars[0x7c5b03dc].get() if 0x7c5b03dc in self.quest_vars else False

        has_light = self.quest_vars[0x91288adc].get() if 0x91288adc in self.quest_vars else False
        has_forest = self.quest_vars[0x25f03caa].get() if 0x25f03caa in self.quest_vars else False
        has_fire = self.quest_vars[0xfb112756].get() if 0xfb112756 in self.quest_vars else False
        has_water = self.quest_vars[0x2f61ab71].get() if 0x2f61ab71 in self.quest_vars else False
        has_shadow = self.quest_vars[0x238ae327].get() if 0x238ae327 in self.quest_vars else False
        has_spirit = self.quest_vars[0x0f941212].get() if 0x0f941212 in self.quest_vars else False

        if not has_emerald:
            current_ch = 0
        elif not has_ruby:
            current_ch = 1
        elif not has_sapphire:
            current_ch = 2
        elif not has_light:
            current_ch = 3
        elif not has_forest:
            current_ch = 4
        elif not has_fire:
            current_ch = 5
        elif not has_water:
            current_ch = 6
        elif not has_shadow:
            current_ch = 7
        elif not has_spirit:
            current_ch = 8
        else:
            current_ch = 9

        ch_name, ch_goal, _ = CHAPTERS[current_ch]
        loc_str = f" ({s.map_name})" if s.map_name and s.map_name != "Unknown" else ""
        self.walk_now.set(f"You're on {ch_name}: {ch_goal}{loc_str}")

        tokens = s.get(HASH_TOKENS, 0)
        self.token_bar["value"] = min(TOTAL_SKULLTULAS, tokens)
        self.token_text.set(f"{tokens} / {TOTAL_SKULLTULAS} Gold Skulltulas")

        hp_val = min(TOTAL_HEART_PIECES, s.get(HASH_HEART_PIECES, 0))
        self.hp_bar["value"] = hp_val
        self.hp_text.set(f"{hp_val} / {TOTAL_HEART_PIECES} Heart Pieces")

        for idx, (ch, goal, _) in enumerate(CHAPTERS):
            if idx < current_ch:
                status = "✔ Done"
                tag = ""
            elif idx == current_ch:
                status = "➤ You are here"
                tag = "on"
            else:
                status = "Upcoming"
                tag = "off"
            self.walk_tree.insert("", "end", iid=str(idx), tags=(tag,) if tag else (),
                                  values=(ch, goal, status, "Zelda Dungeon ↗ double-click"))
        self.walk_tree.tag_configure("on", foreground=self.palette["select"], font=("Segoe UI", 10, "bold"))
        self.walk_tree.tag_configure("off", foreground=self.palette["muted"])

    def open_current_chapter(self):
        items = self.walk_tree.get_children()
        for it in items:
            tags = self.walk_tree.item(it, "tags")
            if "on" in tags:
                idx = int(it)
                webbrowser.open(CHAPTERS[idx][2])
                return
        webbrowser.open(WALKTHROUGH_URL)

    def open_selected_chapter(self):
        sel = self.walk_tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        if 0 <= idx < len(CHAPTERS):
            webbrowser.open(CHAPTERS[idx][2])

    def describe_changes(self):
        diffs = []
        if self.v_rupees.get() != self.orig_snapshot.get("rupees"):
            diffs.append(("General", f"Rupees: {self.orig_snapshot.get('rupees')} → {self.v_rupees.get()}"))
        if self.v_hearts.get() != self.orig_snapshot.get("hearts"):
            diffs.append(("General", f"Hearts: {self.orig_snapshot.get('hearts')} → {self.v_hearts.get()}"))
        if self.v_containers.get() != self.orig_snapshot.get("containers"):
            diffs.append(("General", f"Heart Containers: {self.orig_snapshot.get('containers')} → {self.v_containers.get()}"))
        if self.v_heart_pieces.get() != self.orig_snapshot.get("heart_pieces"):
            diffs.append(("General", f"Heart Pieces: {self.orig_snapshot.get('heart_pieces')} → {self.v_heart_pieces.get()}"))
        if self.v_tokens.get() != self.orig_snapshot.get("tokens"):
            diffs.append(("General", f"Gold Skulltulas: {self.orig_snapshot.get('tokens')} → {self.v_tokens.get()}"))
        if self.v_magic.get() != self.orig_snapshot.get("magic"):
            diffs.append(("General", f"Magic Meter: {self.orig_snapshot.get('magic')} → {self.v_magic.get()}"))
        if self.v_double_defense.get() != self.orig_snapshot.get("double_defense"):
            diffs.append(("General", f"Double Defense: {self.orig_snapshot.get('double_defense')} → {self.v_double_defense.get()}"))

        for k, choice in self.equip_vars.items():
            if choice.get() != self.orig_snapshot.get(k):
                diffs.append(("Equipment", f"{k.title()}: {self.orig_snapshot.get(k, '?')} → {choice.get()}"))

        for k, (v, _) in self.ammo_vars.items():
            if v.get() != self.orig_snapshot.get(k):
                diffs.append(("Ammo", f"{k.title()}: {self.orig_snapshot.get(k, '?')} → {v.get()}"))

        for name, kh, _ in STONES_MEDALLIONS:
            if kh in self.quest_vars:
                cur = self.quest_vars[kh].get()
                orig = bool(self.active_slot.caption_entries.get(kh, 0))
                if cur != orig:
                    diffs.append(("Quest Items", f"{name}: {'Added' if cur else 'Removed'}"))

        for sname, shash, _ in SONGS:
            if shash in self.song_vars:
                cur = self.song_vars[shash].get()
                orig = bool(self.active_slot.caption_entries.get(shash, 0))
                if cur != orig:
                    diffs.append(("Songs", f"{sname}: {'Learned' if cur else 'Unlearned'}"))

        return diffs

    def save(self):
        if not self.active_slot:
            messagebox.showinfo("No save loaded", "Please select a valid save slot first.")
            return

        # Check if emulator is actively running!
        if is_emulator_running():
            if not messagebox.askyesno(
                "Emulator Running Warning",
                "Lichii / Eden / Yuzu emulator appears to be running.\n\n"
                "Saving while the emulator is running will cause your changes to be overwritten "
                "or corrupted when the game saves.\n\n"
                "Do you still want to proceed? (Recommended: Close emulator first)"):
                return

        diffs = self.describe_changes()
        if not diffs:
            messagebox.showinfo("No changes", "No modifications detected in this slot.")
            return

        if not self.confirm_changes(diffs):
            return

        # Automatic backup check
        backup_path = self.make_backup("before edit")

        # Apply changes to active slot
        try:
            rupees = int(self.v_rupees.get())
            hearts = int(self.v_hearts.get())
            containers = int(self.v_containers.get())
            tokens = int(self.v_tokens.get())

            s = self.active_slot
            s.set(HASH_RUPEES, rupees)
            s.set(HASH_HEALTH, hearts * 16)
            s.set(HASH_HEART_PIECES, containers * 4 + int(self.v_heart_pieces.get()))
            s.set(HASH_TOKENS, tokens)

            # Apply ammo
            s.set(HASH_ARROWS, int(self.ammo_vars["arrows"][0].get()))
            s.set(HASH_BOMBS, int(self.ammo_vars["bombs"][0].get()))
            s.set(HASH_BOMBCHUS, int(self.ammo_vars["bombchus"][0].get()))
            s.set(HASH_DEKU_SEEDS, int(self.ammo_vars["seeds"][0].get()))
            s.set(HASH_DEKU_STICKS, int(self.ammo_vars["sticks"][0].get()))
            s.set(HASH_DEKU_NUTS, int(self.ammo_vars["nuts"][0].get()))
            s.set(HASH_MAGIC_BEANS, int(self.ammo_vars["beans"][0].get()))

            # Apply caption sync
            s.caption_entries[HASH_CAPTION_RUPEES] = rupees
            s.caption_entries[HASH_CAPTION_HEALTH] = hearts * 16
            s.caption_entries[HASH_CAPTION_MAX_HEALTH] = hearts * 16
            s.caption_entries[HASH_CAPTION_HEART_PIECES] = containers * 4 + int(self.v_heart_pieces.get())
            s.caption_entries[HASH_CAPTION_TOKENS] = tokens

            # Apply magic meter & defense to caption
            has_double_magic = (self.v_magic.get() == "Double Magic")
            has_magic = (self.v_magic.get() in ("Standard Magic", "Double Magic"))
            s.caption_entries[0x89ae7032] = 1 if has_magic else 0
            s.caption_entries[0xc72044fc] = 1 if has_double_magic else 0
            s.caption_entries[0xfb2b5f6b] = 1 if self.v_double_defense.get() else 0

            # Apply quest stones & medallions
            for _, kh, _ in STONES_MEDALLIONS:
                if kh in self.quest_vars:
                    val = 1 if self.quest_vars[kh].get() else 0
                    s.caption_entries[kh] = val
                    if kh in s.progress_entries:
                        s.set(kh, val)

            # Apply songs
            for sname, shash, _ in SONGS:
                if shash in self.song_vars:
                    val = 1 if self.song_vars[shash].get() else 0
                    s.caption_entries[shash] = val

            # Write updated bytes to progress.sav and caption.sav
            p_bytes, c_bytes = s.save_bytes()
            with open(s.progress_path, "wb") as pf:
                pf.write(p_bytes)
            with open(s.caption_path, "wb") as cf:
                cf.write(c_bytes)

            self.status.set(f"Saved changes to {s.slot_dir}! Backup created: {os.path.basename(backup_path)}")
            messagebox.showinfo("Saved Successfully",
                                f"Saved {len(diffs)} change(s) to {os.path.basename(s.slot_dir)}!\n\n"
                                f"Backup saved in:\n{backup_path}")
            self.load_slot()
        except Exception as e:
            messagebox.showerror("Save failed", f"Error saving slot data:\n{e}")

    def confirm_changes(self, changes):
        """Modal listing every change; returns True if the user chooses to save."""
        win = tk.Toplevel(self)
        win.title("Review changes")
        win.geometry("620x460")
        win.transient(self)
        win.grab_set()
        slot_name = os.path.basename(self.active_slot.slot_dir) if self.active_slot else "save slot"
        ttk.Label(win, padding=(10, 10, 10, 4), wraplength=590, justify="left", text=(
            f"{len(changes)} change{'s' if len(changes) != 1 else ''} will be written to {slot_name}.\n"
            "Make sure the game/emulator is closed.")).pack(anchor="w")
        frame = ttk.Frame(win, padding=(10, 0))
        frame.pack(fill="both", expand=True)
        text = tk.Text(frame, wrap="word", height=14, font=("Segoe UI", 10), padx=8, pady=6)
        sb = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=sb.set)
        text.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        text.tag_configure("head", font=("Segoe UI", 10, "bold"), spacing1=6)
        section = None
        for group, line in changes:
            if group != section:
                text.insert("end", group + "\n", "head")
                section = group
            text.insert("end", "   • " + line + "\n")
        text.configure(state="disabled")
        result = {"ok": False}

        def ok():
            result["ok"] = True
            win.destroy()

        row = ttk.Frame(win, padding=10)
        row.pack(fill="x")
        ttk.Button(row, text="Cancel", command=win.destroy).pack(side="right")
        self.primary_button(row, "Save these changes", ok).pack(side="right", padx=6)
        win.bind("<Escape>", lambda e: win.destroy())
        self.center(win)
        self.wait_window(win)
        return result["ok"]

    # ---------- Backup & Restore System ----------
    def backup_now(self):
        f = self.root_dir.get()
        if not f or not os.path.isdir(f):
            messagebox.showinfo("No folder", "Load a save folder first.")
            return
        tag = simpledialog.askstring("Back up", "Tag / label for this backup (optional):", parent=self)
        if tag is None:
            return
        path = self.make_backup(tag)
        self.update_backup_count()
        messagebox.showinfo("Backup complete", f"Backup saved as:\n{os.path.basename(path)}")

    def make_backup(self, tag=""):
        f = self.root_dir.get()
        os.makedirs(BACKUP_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        clean_tag = "_" + re.sub(r"[^\w\-]", "_", tag).strip("_") if tag else ""
        dest = os.path.join(BACKUP_DIR, f"{ts}{clean_tag}")
        shutil.copytree(f, dest)
        return dest

    def update_backup_count(self):
        if not os.path.isdir(BACKUP_DIR):
            self.backup_count.set("0 backups")
            return
        items = [d for d in os.listdir(BACKUP_DIR) if os.path.isdir(os.path.join(BACKUP_DIR, d))]
        self.backup_count.set(f"{len(items)} backup{'s' if len(items) != 1 else ''}")

    def open_backups(self):
        os.makedirs(BACKUP_DIR, exist_ok=True)
        open_folder(BACKUP_DIR)

    def restore_dialog(self):
        if not os.path.isdir(BACKUP_DIR):
            messagebox.showinfo("Restore", "No backups exist yet.")
            return
        backups = sorted([d for d in os.listdir(BACKUP_DIR) if os.path.isdir(os.path.join(BACKUP_DIR, d))], reverse=True)
        if not backups:
            messagebox.showinfo("Restore", "No backups exist yet.")
            return

        win = tk.Toplevel(self)
        win.title("Restore a backup")
        win.geometry("580x400")
        win.transient(self)
        win.grab_set()

        ttk.Label(win, text="Newest first. Restoring replaces your current save "
                            "(a backup of it is made first).", padding=8).pack(anchor="w")
        lb = tk.Listbox(win, activestyle="dotbox")
        lb.pack(fill="both", expand=True, padx=8)
        for b in backups:
            lb.insert("end", b)
        lb.selection_set(0)

        def restore():
            sel = lb.curselection()
            if not sel: return
            target = os.path.join(BACKUP_DIR, backups[sel[0]])
            if not messagebox.askyesno("Confirm restore",
                                       f"Restore {backups[sel[0]]}?\n\nThis will overwrite current save files.", parent=win):
                return
            dest = self.root_dir.get()
            shutil.rmtree(dest, ignore_errors=True)
            shutil.copytree(target, dest)
            win.destroy()
            self.refresh_slots()
            messagebox.showinfo("Restored", "Backup restored successfully.")

        btns = ttk.Frame(win, padding=8)
        btns.pack(fill="x")
        ttk.Button(btns, text="Cancel", command=win.destroy).pack(side="right")
        self.primary_button(btns, "Restore", restore).pack(side="right", padx=6)
        win.bind("<Escape>", lambda e: win.destroy())
        self.center(win)

    # ---------- Cheats Management ----------
    def detect_cheat_target(self):
        self.emulator = emulator_for(self.root_dir.get())
        bid = self.current_build()
        if self.emulator and bid:
            self.cheat_status.set(f"Detected {self.emulator['name']} • Title ID {TITLE_ID} • Build ID {bid}")
        elif self.emulator:
            self.cheat_status.set(f"Detected {self.emulator['name']} • Build ID: E0F3CCFAF50065AE (v1.0.0 default)")
        else:
            self.cheat_status.set("Target: Standalone / Switch Atmosphère mode")
        self.load_cheats()

    def current_build(self):
        if self.emulator:
            bids = detect_build_ids(self.emulator)
            if bids:
                return bids[0]
        return "E0F3CCFAF50065AE"

    def load_cheats(self):
        bid = self.current_build()
        self.cheats = read_library(bid)
        self.refresh_cheats()

    def refresh_cheats(self):
        self.cheat_tree.delete(*self.cheat_tree.get_children())
        for idx, c in enumerate(self.cheats):
            on = "✔" if c.get("enabled") else "—"
            tested = TEST_ICONS.get(c.get("tested", {}).get("yuzu family", "Untested"), "—")
            tag = "on" if c.get("enabled") else "off"
            self.cheat_tree.insert("", "end", iid=str(idx), tags=(tag,),
                                  values=(on, c["name"], f"yuzu: {tested}", c.get("description", "")))

    def toggle_cheats(self):
        sel = self.cheat_tree.selection()
        for s in sel:
            idx = int(s)
            self.cheats[idx]["enabled"] = not self.cheats[idx].get("enabled")
        self.refresh_cheats()

    def install_cheats(self):
        bid = self.current_build()
        enabled = [c for c in self.cheats if c.get("enabled")]
        if not enabled:
            messagebox.showinfo("No cheats selected", "Double-click one or more cheats to enable them first.")
            return

        if not self.emulator:
            messagebox.showinfo("Notice", "Save folder is not inside an emulator NAND. Use 'Export for Switch' instead.")
            return

        cdir = self.emulator["cheat_dir"]
        os.makedirs(cdir, exist_ok=True)
        out_path = os.path.join(cdir, f"{bid}.txt")
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(format_cheats(enabled))

        messagebox.showinfo("Cheats Installed",
                            f"Installed {len(enabled)} cheat(s) for {self.emulator['name']}!\n\nFile: {out_path}")

    def uninstall_cheats(self):
        bid = self.current_build()
        if not self.emulator:
            return
        out_path = os.path.join(self.emulator["cheat_dir"], f"{bid}.txt")
        if os.path.exists(out_path):
            os.remove(out_path)
            messagebox.showinfo("Cheats Removed", f"Removed cheat file:\n{out_path}")
        else:
            messagebox.showinfo("No active cheats", "No installed cheat file found.")

    def export_cheats(self):
        bid = self.current_build()
        enabled = [c for c in self.cheats if c.get("enabled")]
        if not enabled:
            messagebox.showinfo("No cheats selected", "Double-click one or more cheats to enable them first.")
            return
        dest = filedialog.askdirectory(title="Choose atmosphere/contents/0400486024DEC000/cheats or SD card root")
        if not dest:
            return
        target_dir = os.path.join(dest, "atmosphere", "contents", TITLE_ID, "cheats") if "atmosphere" not in dest.lower() else dest
        os.makedirs(target_dir, exist_ok=True)
        out_file = os.path.join(target_dir, f"{bid}.txt")
        with open(out_file, "w", encoding="utf-8", newline="\n") as f:
            f.write(format_cheats(enabled))
        messagebox.showinfo("Exported Successfully", f"Exported {len(enabled)} cheats to:\n{out_file}")

    def open_cheat_folder(self):
        bid = self.current_build()
        folder = build_folder(bid)
        os.makedirs(folder, exist_ok=True)
        open_folder(folder)

    def show_cheat_guide(self):
        win = tk.Toplevel(self)
        win.title("Cheat guide")
        win.geometry("720x600")
        win.transient(self)
        frame = ttk.Frame(win, padding=(12, 12, 12, 0))
        frame.pack(fill="both", expand=True)
        text = tk.Text(frame, wrap="word", font=("Segoe UI", 10), padx=12, pady=10, relief="flat")
        sb = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=sb.set)
        text.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        text.tag_configure("h", font=("Segoe UI", 12, "bold"), spacing1=12, spacing3=4)
        text.tag_configure("warn", font=("Segoe UI", 10, "bold"), foreground=self.palette["warn"])
        for kind, line in CHEAT_GUIDE:
            text.insert("end", line + "\n", kind)
        text.configure(state="disabled")
        row = ttk.Frame(win, padding=12)
        row.pack(fill="x")
        ttk.Button(row, text="Close", command=win.destroy).pack(side="right")
        self.center(win)

    # ---------- Theming & UI Styling ----------
    def theme_mode(self):
        mode = self.settings.get("theme", "System")
        if hasattr(self, "theme_choice") and self.theme_choice.get():
            mode = self.theme_choice.get()
        if mode == "System":
            return "dark" if system_prefers_dark() else "light"
        return mode.lower()

    def on_theme_pick(self, _=None):
        self.settings["theme"] = self.theme_choice.get()
        store_settings(self.settings)
        self.apply_theme()

    def apply_theme(self):
        mode = self.theme_mode()
        p = self.palette = PALETTES[mode]
        style = self.style
        if mode == "dark":
            style.theme_use("clam")
            style.configure(".", background=p["bg"], foreground=p["fg"], fieldbackground=p["field"],
                            bordercolor=p["border"], lightcolor=p["surface"], darkcolor=p["surface"],
                            troughcolor=p["bg"], selectbackground=p["select"], selectforeground=p["fg"],
                            insertcolor=p["fg"], focuscolor=p["accent"])
            style.map(".", foreground=[("disabled", p["faint"])])
            style.configure("TButton", background=p["surface"], foreground=p["fg"], padding=(8, 3),
                            bordercolor=p["border"])
            style.map("TButton", background=[("pressed", p["border"]), ("active", p["hover"])])
            for w in ("TEntry", "TCombobox", "TSpinbox"):
                style.configure(w, fieldbackground=p["field"], foreground=p["fg"], arrowcolor=p["fg"],
                                background=p["surface"], bordercolor=p["border"])
                style.map(w, fieldbackground=[("readonly", p["field"]), ("disabled", p["bg"])],
                          foreground=[("readonly", p["fg"])], background=[("active", p["hover"])],
                          selectbackground=[("readonly", p["field"])], selectforeground=[("readonly", p["fg"])])
            style.configure("TCheckbutton", background=p["bg"], foreground=p["fg"], indicatorbackground=p["field"])
            style.map("TCheckbutton", background=[("active", p["bg"])],
                      indicatorbackground=[("selected", p["accent"]), ("active", p["hover"])])
            style.configure("TLabelframe", background=p["bg"], bordercolor=p["border"])
            style.configure("TLabelframe.Label", background=p["bg"], foreground=p["muted"])
            style.configure("TNotebook", background=p["bg"], bordercolor=p["border"])
            style.configure("TNotebook.Tab", background=p["surface"], foreground=p["muted"], bordercolor=p["border"])
            style.map("TNotebook.Tab", background=[("selected", p["bg"]), ("active", p["hover"])])
            style.configure("Treeview", background=p["field"], fieldbackground=p["field"], foreground=p["fg"],
                            bordercolor=p["border"], rowheight=22)
            style.configure("Treeview.Heading", background=p["surface"], foreground=p["fg"], bordercolor=p["border"],
                            relief="flat")
            style.map("Treeview.Heading", background=[("active", p["hover"])])
            style.map("Treeview", background=[("selected", p["select"])], foreground=[("selected", "#ffffff")])
            style.configure("Vertical.TScrollbar", background=p["hover"], troughcolor=p["bg"], gripcount=0,
                            lightcolor=p["hover"], darkcolor=p["hover"], arrowcolor=p["fg"], bordercolor=p["bg"])
            style.map("Vertical.TScrollbar", background=[("active", p["border"])])
            style.configure("Horizontal.TScrollbar", background=p["hover"], troughcolor=p["bg"], gripcount=0,
                            lightcolor=p["hover"], darkcolor=p["hover"], arrowcolor=p["fg"], bordercolor=p["bg"])
            style.map("Horizontal.TScrollbar", background=[("active", p["border"])])
            style.configure("Horizontal.TProgressbar", background=p["tag_on"], troughcolor=p["field"],
                            bordercolor=p["border"], lightcolor=p["tag_on"], darkcolor=p["tag_on"])
        else:
            style.theme_use(self.base_theme)
        self._style_common()
        for opt, value in (("*TCombobox*Listbox.background", p["field"]), ("*TCombobox*Listbox.foreground", p["fg"]),
                           ("*TCombobox*Listbox.selectBackground", p["select"]),
                           ("*TCombobox*Listbox.selectForeground", "#ffffff")):
            self.option_add(opt, value)
        self.configure(bg=p["bg"])
        self._recolor(self)
        font = "Segoe UI" if sys.platform == "win32" else "TkDefaultFont"
        if hasattr(self, "walk_tree"):
            self.walk_tree.tag_configure("on", foreground=p["tag_on"], font=(font, 10, "bold"))
            self.walk_tree.tag_configure("off", foreground=p["faint"])
        if hasattr(self, "cheat_tree"):
            self.cheat_tree.tag_configure("on", foreground=p["tag_on"], font=(font, 10, "bold"))
            self.cheat_tree.tag_configure("off", foreground=p["tag_off"])
        self.theme_window(self)

    def _style_common(self):
        p, style = self.palette, self.style
        font = "Segoe UI" if sys.platform == "win32" else "TkDefaultFont"
        style.configure("TNotebook", tabmargins=(6, 8, 6, 0))
        style.configure("TNotebook.Tab", padding=(20, 8), font=(font, 11))
        style.map("TNotebook.Tab", font=[("selected", (font, 11, "bold"))],
                  foreground=[("selected", p["accent"]), ("active", p["accent"])],
                  expand=[("selected", (2, 4, 2, 0))])
        style.configure("Muted.TLabel", foreground=p["muted"])
        style.configure("Faint.TLabel", foreground=p["faint"])
        style.configure("Warn.TLabel", foreground=p["warn"], font=(font, 12, "bold"))
        style.configure("Alert.TLabel", foreground=p["warn"], font=(font, 9, "bold"))
        style.configure("Over.Horizontal.TProgressbar", background=p["warn"], lightcolor=p["warn"],
                        darkcolor=p["warn"])
        style.configure("Banner.TFrame", background=p["banner"])
        style.configure("Banner.TLabel", background=p["banner"], foreground=p["fg"])
        style.configure("BannerTitle.TLabel", background=p["banner"], foreground=p["warn"], font=(font, 11, "bold"))

    def _recolor(self, widget):
        p = self.palette
        for w in widget.winfo_children():
            if isinstance(w, tk.Toplevel):
                w.configure(bg=p["bg"])
            elif isinstance(w, (tk.Text, tk.Listbox)):
                w.configure(bg=p["field"], fg=p["fg"], selectbackground=p["select"], selectforeground="#ffffff",
                            highlightbackground=p["border"], highlightcolor=p["accent"])
                if isinstance(w, tk.Text):
                    w.configure(insertbackground=p["fg"])
            self._recolor(w)

    def theme_window(self, win):
        """Color a window to match the theme, including the Windows title bar."""
        p = self.palette
        if win is not self:
            win.configure(bg=p["bg"])
            self._recolor(win)
        if sys.platform != "win32":
            return
        try:
            import ctypes
            win.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(win.winfo_id()) or win.winfo_id()
            value = ctypes.c_int(1 if self.theme_mode() == "dark" else 0)
            for attr in (20, 19):   # DWMWA_USE_IMMERSIVE_DARK_MODE (Windows 11 / older Windows 10)
                if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(value), 4) == 0:
                    break
            # Redraw the frame so the title bar changes right away.
            ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0004 | 0x0020)
        except Exception:
            pass

    def center(self, win, w=None, h=None):
        """Place a pop-up window in the middle of the editor window (and theme it)."""
        self.theme_window(win)
        win.update_idletasks()
        rw, rh = win.winfo_reqwidth(), win.winfo_reqheight()
        if win.winfo_width() > 1:
            rw, rh = max(rw, win.winfo_width()), max(rh, win.winfo_height())
        w = w or rw
        h = h or rh
        x = self.winfo_rootx() + (self.winfo_width() - w) // 2
        y = self.winfo_rooty() + (self.winfo_height() - h) // 3
        win.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")

    def primary_button(self, parent, text, command):
        """A green button for the main 'save' action."""
        return tk.Button(parent, text=text, command=command, bg="#2e7d32", fg="white",
                         activebackground="#1b5e20", activeforeground="white", relief="flat",
                         font=("Segoe UI", 10, "bold"), padx=14, pady=3, cursor="hand2",
                         borderwidth=0, highlightthickness=0)

    def sort_by(self, tree, col):
        current_col, desc = self._sort.get(tree, (None, False))
        desc = (not desc) if current_col == col else False
        self._sort[tree] = (col, desc)
        self.apply_sort(tree, col, desc)

    def apply_sort(self, tree, col, desc):
        rows = [(tree.set(iid, col), iid) for iid in tree.get_children("")]
        def key_func(item):
            val = item[0]
            try: return float(val)
            except ValueError: return val.lower()
        rows.sort(key=key_func, reverse=desc)
        for idx, (_, iid) in enumerate(rows):
            tree.move(iid, "", idx)

    def on_tab_changed(self, event):
        tab = self.nb.tab(self.nb.select(), "text")
        if tab == "Walkthrough":
            self.refresh_walkthrough()
        elif tab == "Cheats":
            self.detect_cheat_target()

def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else None
    app = OOTEditor(folder)
    app.mainloop()

if __name__ == "__main__":
    main()
