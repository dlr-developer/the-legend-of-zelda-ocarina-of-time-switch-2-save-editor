"""The Legend of Zelda: Ocarina of Time (64-bit) (Switch 2 / NX2) save editor.

Works with saves from Lichii, Eden, Yuzu, Suyu, Sudachi, Citron, Torzu, Ryujinx,
and saves dumped from a Nintendo Switch 2 running Atmosphere.

Save files use Nintendo's modern GameData container (magic 0x01020304, revision 0x002d80eb)
with 32-bit MurmurHash3 key-value pairs in progress.sav (fixed header end 0x175D8)
and slot metadata in caption.sav (fixed header end 0x2A0).
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
from datetime import datetime
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import NamedTuple

from app_paths import (
    APP_NAME,
    APP_DIR,
    RESOURCE_DIR,
    USER_DATA_DIR,
    LEGACY_DATA_DIR,
    SETTINGS_PATH,
    BACKUP_DIR,
    CHEAT_LIB_DIR,
    get_user_data_dir,
    get_legacy_data_dir,
)

APP_VERSION = "1.0.0"

TITLE_ID = "0400486024DEC000"
ALT_TITLE_IDS = ("04004860224DEC000",)
ALL_TITLE_IDS = (TITLE_ID,) + ALT_TITLE_IDS
GAME_NAME = "The Legend of Zelda Ocarina of Time (64-bit)"
SLOT_PREFIX = "slot_"

HEADER_END_PROGRESS = 0x175D8
HEADER_END_CAPTION = 0x2A0

# Load official Switch 2 GameData Schema
SCHEMA_PATH = os.path.join(RESOURCE_DIR, "script0.json")
if not os.path.exists(SCHEMA_PATH):
    alt_path = os.path.join(APP_DIR, "script0.json")
    if os.path.exists(alt_path):
        SCHEMA_PATH = alt_path

try:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        CATALOG = json.load(f)
except Exception:
    CATALOG = {"inventory": [], "registrations": [], "fields": []}

# Official Wallets (Switch 2 GameData)
WALLETS = [
    {"id": "Item_Wallet_Small", "stock": 0x1D74617E, "limit": 200, "label": "Kokiri Wallet (200 Rupees)"},
    {"id": "Item_Wallet_Medium", "stock": 0x2D2C874B, "limit": 500, "label": "Adult's Wallet (500 Rupees)"},
    {"id": "Item_Wallet_Large", "stock": 0xAFA4BB52, "limit": 1000, "label": "Giant's Wallet (1000 Rupees)"},
]

# Capacity Groups & Tiers (Switch 2 GameData)
CAPACITY_GROUPS = [
    {
        "id": "seeds", "label": "Deku Seed Bag", "hash": 0xAE8CC742, "nameHash": 0xD732DD7F, "actor": "Item_BulletBag",
        "tiers": [(30, 0xDC52ACAF), (40, 0x9A30A9E5), (50, 0x7B9673F5)],
        "labels": ["Deku-Seed Bag (30)", "Bigger Deku-Seed Bag (40)", "Biggest Deku-Seed Bag (50)"]
    },
    {
        "id": "nuts", "label": "Deku Nut Bag", "hash": 0x735B00F7, "nameHash": 0x0DA3A7A7, "actor": "Item_NutBag",
        "tiers": [(20, 0x19B80DBC), (30, 0xEAA1785E), (40, 0xD60E4B23)],
        "labels": ["Deku-Nut Bag (20)", "Bigger Deku-Nut Bag (30)", "Biggest Deku-Nut Bag (40)"]
    },
    {
        "id": "sticks", "label": "Deku Stick Bag", "hash": 0x457616B0, "nameHash": 0x2808EE1C, "actor": "Item_StickBag",
        "tiers": [(10, 0x2FE6AB1A), (20, 0x41DB7AB5), (30, 0x48E53698)],
        "labels": ["Deku-Stick Bag (10)", "Bigger Deku-Stick Bag (20)", "Biggest Deku-Stick Bag (30)"]
    },
    {
        "id": "bombs", "label": "Bomb Bag", "hash": 0xE753508B, "nameHash": 0xA835E3B0, "actor": "Item_BombBag",
        "tiers": [(20, 0xB0A1BF51), (30, 0xE5FF45AA), (40, 0xBD3CA2C6)],
        "labels": ["Bomb Bag (20)", "Bigger Bomb Bag (30)", "Biggest Bomb Bag (40)"]
    },
    {
        "id": "arrows", "label": "Quiver", "hash": 0x418DB791, "nameHash": None, "actor": "Item_Quiver",
        "tiers": [(30, 0xA8C3E1FB), (40, 0x3BB370E1), (50, 0xD331C7DA)],
        "labels": ["Quiver (30)", "Bigger Quiver (40)", "Biggest Quiver (50)"]
    },
]

# Ammo & Consumables (Switch 2 GameData)
SUPPLIES = [
    {"id": "seeds", "label": "Deku Seeds", "stock": 0x5FADF7FC, "group": "seeds"},
    {"id": "nuts", "label": "Deku Nuts", "stock": 0xF30D9F54, "group": "nuts"},
    {"id": "sticks", "label": "Deku Sticks", "stock": 0xB9494411, "group": "sticks"},
    {"id": "arrows", "label": "Arrows", "stock": 0x518EC74B, "group": "arrows"},
    {"id": "bombs", "label": "Bombs", "stock": 0xDB1BCD4F, "group": "bombs"},
    {"id": "bombchu", "label": "Bombchus", "stock": 0xDF7C517A, "max": 30},
    {"id": "beans", "label": "Magic Beans", "stock": 0xB003124D, "max": 10},
    {"id": "scrub", "label": "Business Scrub Seeds", "stock": 0x600E29EB, "max": 30},
    {"id": "skulltulas", "label": "Gold Skulltula Tokens", "stock": 0x04735978, "max": 100},
    {"id": "heartPieces", "label": "Pieces of Heart", "stock": 0x51EC97B3, "max": 3},
]

# Dungeon Small Keys
SMALL_KEYS = [
    {"id": "well", "label": "Bottom of the Well", "stock": 0x7DD79D10, "max": 2},
    {"id": "forest", "label": "Forest Temple", "stock": 0x90237092, "max": 5},
    {"id": "fire", "label": "Fire Temple", "stock": 0x1DF11487, "max": 7},
    {"id": "water", "label": "Water Temple", "stock": 0x877BDCEE, "max": 4},
    {"id": "shadow", "label": "Shadow Temple", "stock": 0x5EDDA9E3, "max": 5},
    {"id": "spirit", "label": "Spirit Temple", "stock": 0x79EEEC8E, "max": 5},
    {"id": "fortress", "label": "Gerudo Fortress", "stock": 0x3A28B6A4, "max": 4},
    {"id": "training", "label": "Gerudo Proving Grounds", "stock": 0xEA9786F5, "max": 8},
    {"id": "castle", "label": "Ganondorf's Castle", "stock": 0xFBFD2910, "max": 1},
]

# 5 Bottle Slots [stock, valid, content]
BOTTLE_SLOTS = [
    [0xD53CE3A7, 0xF39CE410, 0x7D48DF76],
    [0xFCA29A04, 0x000FF6EA, 0x1EDD164A],
    [0x893216A1, 0xF63B1194, 0xB80C70A8],
    [0x5324F9D3, 0xB7F052CE, 0xE4C1B1FC],
    [0xC92B16BE, 0xE27B136D, 0x365E1953],
]
EMPTY_BOTTLE = 0xBE69DE49

BOTTLE_CONTENTS = [
    ("Empty Bottle", 0xBE69DE49),
    ("Red Potion (Restores Health)", 0xEABA6067),
    ("Green Potion (Restores Magic)", 0x049D37C1),
    ("Blue Potion (Restores Health & Magic)", 0xF383D6E5),
    ("Bottled Fairy (Revives Link)", 0x6F49E357),
    ("Fish", 0x1E834EF8),
    ("Blue Fire", 0x1C293517),
    ("Bugs", 0x74D62ECB),
    ("Poe", 0x02084F9E),
    ("Big Poe", 0xCDC21471),
    ("Zelda's Letter (Ruto's Letter)", 0x0F24E808),
    ("Lon Lon Milk", 0x73356827),
    ("Lon Lon Milk (Half)", 0xEEF6E4B0),
]
BOTTLE_ID_TO_NAME = {h: label for label, h in BOTTLE_CONTENTS}
BOTTLE_NAME_TO_ID = {label: h for label, h in BOTTLE_CONTENTS}

# Hashes for Vitals & Wallet
KEY_RUPEES = 0xA77921D7
KEY_LIMIT = 0xE0010A50
KEY_WALLET = 0x3E42AFFA
KEY_PREVIEW_RUPEES = 0xA9557547

# Vitals scaling: hearts x4 (quarter-hearts), magic x10 (tenths)
HASH_PROG_HEARTS = 0x31AB5580
HASH_CAPT_HEARTS = 0x1E55ECC5
HASH_PROG_MAX_HEARTS = 0xFBE01DA1
HASH_CAPT_MAX_HEARTS = 0x74BD05D0

HASH_PROG_MAGIC = 0x76B18200
HASH_CAPT_MAGIC = 0x19F26B6A
HASH_PROG_MAX_MAGIC = 0x12D63A97
HASH_CAPT_MAX_MAGIC = 0x943F8EC3

BLESSING_MP_STANDARD = 0x5E671D92
BLESSING_MP_DOUBLE = 0x5F043856
BLESSING_DEFENSE_DOUBLE = 0x9A826FAB

# Section 2 String Target Hashes (64-byte blocks)
HASH_SWORD_SLOT = 0xA95A3521
HASH_SHIELD_SLOT = 0xEE463235
HASH_OCARINA_SLOT = 0xB72CD3FC
HASH_MASK_SLOT = 0x59D9C7B3

# Equipment
SWORDS = [
    ("Kokiri Sword", 0xEEB495B9, "Weapon_Sword_Kokiri"),
    ("Master Sword", 0xF1C45294, "Weapon_Sword_Master"),
    ("Biggoron's Sword", 0xB0B3E399, "Weapon_Sword_Biggoron"),
    ("Giant's Knife", 0x396A5C02, "Weapon_Sword_Giant"),
]

SHIELDS = [
    ("Deku Shield", 0x7CA64F23, "Weapon_Shield_Deku"),
    ("Hylian Shield", 0x08BEFD3A, "Weapon_Shield_Hylian"),
    ("Mirror Shield", 0xF58E0E2F, "Weapon_Shield_Mirror"),
]

TUNICS = [
    ("Kokiri Tunic", 0x84BA0D24, "Armor_Adult_Normal"),
    ("Goron Tunic", 0x21ECBD19, "Armor_Adult_Goron"),
    ("Zora Tunic", 0xB816AF94, "Armor_Adult_Zora"),
]

BOOTS = [
    ("Kokiri Boots", 0x00000000, "Default Boots"),
    ("Iron Boots", 0x2BAD189A, "Armor_Adult_HeavyBoot"),
    ("Hover Boots", 0xC9220366, "Armor_Adult_HoverBoot"),
]

GAUNTLETS = [
    ("None", 0x00000000),
    ("Goron's Bracelet", 0xD1317941),
    ("Silver Gauntlets", 0x0012B8C0),
    ("Golden Gauntlets", 0x40AE1183),
]

DIVING_SCALES = [
    ("Default (1 meter)", 0x00000000),
    ("Silver Scale (6 meters)", 0x1240044B),
    ("Golden Scale (8 meters)", 0x4AEB140A),
]

# Special Items, Tools & Spells
DUNGEON_TOOLS_BASE = [
    ("Fairy Slingshot", 0x80D34CE9, "Child weapon using Deku Seeds"),
    ("Boomerang", 0xA1D76D31, "Retrieves items and stuns enemies"),
    ("Fairy Bow", 0x938D56BF, "Adult weapon for shooting arrows"),
    ("Megaton Hammer", 0x1AAFDB66, "Heavy blunt weapon for crushing rocks"),
    ("Lens of Truth", 0x49D1C374, "Reveals hidden passages and illusions"),
]

HOOKSHOT_CHOICES = ["None", "Hookshot", "Longshot"]

MAGIC_SPELLS = [
    ("Din's Fire", 0xB796C16D, "Expands a fiery sphere that burns enemies"),
    ("Farore's Wind", 0x47F2CA87, "Creates a return warp point inside dungeons"),
    ("Nayru's Love", 0xF0828CD0, "Creates a protective crystalline shield"),
]

MAGIC_ARROWS = [
    ("Fire Arrow", 0x5E529AB9, "Shoots fiery arrows that melt ice"),
    ("Ice Arrow", 0x40735A8D, "Freezes enemies in solid blocks of ice"),
    ("Light Arrow", 0xBFB285C8, "Pierces evil with radiant divine magic"),
]

MAGIC_POWERS = [
    ("Fairy Ocarina", 0xB7DF60F1, "Saria's parting gift to Link"),
    ("Ocarina of Time", 0x54E2A3D1, "Legendary royal instrument"),
    ("Stone of Agony (Echo Gem)", 0xF3B14CE2, "Resonates near secrets and hidden holes"),
    ("Gerudo Pass", 0xFEB4D56B, "Permits free travel in the Gerudo Fortress"),
]

# Happy Mask Shop (Only one active at a time)
MASK_CHOICES = [
    "None", "Keaton Mask", "Skull Mask", "Spooky Mask", "Bunny Hood",
    "Mask of Truth", "Goron Mask", "Zora Mask", "Gerudo Mask"
]

MASK_MAP = {
    "Keaton Mask": (0xB5C10899, "Armor_Child_Mask_Keaton"),
    "Skull Mask": (0x47B2D775, "Armor_Child_Mask_Skull"),
    "Spooky Mask": (0xF046629E, "Armor_Child_Mask_Spooky"),
    "Bunny Hood": (0x7E607033, "Armor_Child_Mask_Bunny"),
    "Mask of Truth": (0x96459CD3, "Armor_Child_Mask_Truth"),
    "Goron Mask": (0xFC508DA7, "Armor_Child_Mask_Goron"),
    "Zora Mask": (0x924E9A46, "Armor_Child_Mask_Zora"),
    "Gerudo Mask": (0x0E94A8DF, "Armor_Child_Mask_Gerudo"),
}

# Child Quest Items (Only one active at a time)
CHILD_QUEST_CHOICES = ["None", "Weird Egg", "Zelda's Letter"]
CHILD_QUEST_MAP = {
    "Weird Egg": 0x24596E8E,
    "Zelda's Letter": 0x6BE5C3B0,
}

# Adult Trading Sequence (Biggoron's Sword - Only one active at a time)
ADULT_TRADE_CHOICES = [
    "None", "Pocket Egg", "Pocket Cucco", "Cojiro", "Odd Mushroom", "Odd Poultice",
    "Poacher's Saw", "Broken Goron Sword", "Prescription", "Eyeball Frog",
    "Specialty Eye Drops", "Biggoron Receipt"
]
ADULT_TRADE_MAP = {
    "Pocket Egg": 0x07F10AAF,
    "Pocket Cucco": 0x0165E7CA,
    "Cojiro": 0x51D89EF0,
    "Odd Mushroom": 0x07DE3E6F,
    "Odd Poultice": 0x58C9BC78,
    "Poacher's Saw": 0xA862D276,
    "Broken Goron Sword": 0x2815C82A,
    "Prescription": 0x897CF7EB,
    "Eyeball Frog": 0x919EA324,
    "Specialty Eye Drops": 0x5C41A6B1,
    "Biggoron Receipt": 0xDED8E8D3,
}

BOTTLE_CHOICES = ["(Not Acquired / Locked)"] + [c[0] for c in BOTTLE_CONTENTS]

# Spiritual Stones & Medallions (Story progression items)
SPIRITUAL_STONES = [
    ("Kokiri's Emerald", 0xCBD1E58C, "Great Deku Tree's Forest Spiritual Stone"),
    ("Goron's Ruby", 0x7D69AD47, "Darunia's Fire Spiritual Stone"),
    ("Zora's Sapphire", 0xB8E3BF45, "Princess Ruto's Water Engagement Stone"),
]

MEDALLIONS = [
    ("Light Medallion", 0x235C7D9A, "Awakens Rauru, Sage of Light"),
    ("Forest Medallion", 0x692D57CB, "Awakens Saria, Sage of Forest"),
    ("Fire Medallion", 0x5CE254A6, "Awakens Darunia, Sage of Fire"),
    ("Water Medallion", 0x0151A68F, "Awakens Ruto, Sage of Water"),
    ("Shadow Medallion", 0x204D2063, "Awakens Impa, Sage of Shadow"),
    ("Spirit Medallion", 0x0C7A5FD0, "Awakens Nabooru, Sage of Spirit"),
]

STONES_MEDALLIONS = SPIRITUAL_STONES + MEDALLIONS

# 12 Ocarina Songs (Exact bitfield at 0x628BE485 and official event hashes)
SONGS = [
    ("Zelda's Lullaby", 0, 0x01C20002, 0x2CD669E8, "Opens Royal Tomb & unlocks Darunia's chamber"),
    ("Epona's Song", 1, None, 0xDB8433F7, "Summons Epona & heals milk cows"),
    ("Saria's Song", 2, 0xD3F8BFCC, 0x3A33F18D, "Talk to Saria & cheer up Darunia"),
    ("Song of Time", 3, None, 0xBE4E744F, "Opens the Door of Time"),
    ("Sun's Song", 4, 0x4B415FBB, None, "Changes day to night and freezes ReDeads"),
    ("Song of Storms", 5, 0x2B39DD4F, 0x9E1EFBA1, "Summons rain and drains the Well"),
    ("Minuet of Forest", 6, 0xDC0A0B54, None, "Warps to Sacred Forest Meadow"),
    ("Bolero of Fire", 7, 0x49041AB9, None, "Warps to Death Mountain Crater"),
    ("Serenade of Water", 8, 0x3FA63986, None, "Warps to Lake Hylia"),
    ("Requiem of Spirit", 9, 0x802A36A8, None, "Warps to Desert Colossus"),
    ("Nocturne of Shadow", 10, 0xC2FB95F4, None, "Warps to Kakariko Graveyard"),
    ("Prelude of Light", 11, None, 0xEF7B5505, "Warps to Temple of Time"),
]

HASH_SONG_MASK = 0x628BE485

# Story Chapters
CHAPTERS = [
    ("Chapter 1", "Inside the Deku Tree (Kokiri's Emerald)"),
    ("Chapter 2", "Dodongo's Cavern (Goron's Ruby)"),
    ("Chapter 3", "Inside Jabu-Jabu's Belly (Zora's Sapphire)"),
    ("Chapter 4", "Temple of Time & Awakening (Master Sword)"),
    ("Chapter 5", "Forest Temple (Forest Medallion)"),
    ("Chapter 6", "Fire Temple (Fire Medallion)"),
    ("Chapter 7", "Water Temple (Water Medallion)"),
    ("Chapter 8", "Shadow Temple (Shadow Medallion)"),
    ("Chapter 9", "Spirit Temple (Spirit Medallion)"),
    ("Chapter 10", "Ganon's Castle & Final Battle"),
]

TOTAL_HEART_PIECES = 36
TOTAL_SKULLTULAS = 100


# ---------- GameData Binary Parser ----------
class SaveSlot:
    """In-place binary parser and modifier for Switch 2 GameData containers.
    Preserves exact fixed header ends (0x175D8 progress, 0x2A0 caption) and file sizes.
    """
    def __init__(self, slot_dir):
        self.slot_dir = slot_dir
        self.progress_path = os.path.join(slot_dir, "progress.sav")
        self.caption_path = os.path.join(slot_dir, "caption.sav")
        self.p_bytes = bytearray()
        self.c_bytes = bytearray()
        self.p_fields = {}
        self.c_fields = {}
        self.map_name = "Hyrule"
        self.loaded = False
        self.load()

    def load(self):
        if not os.path.exists(self.progress_path) or not os.path.exists(self.caption_path):
            return False

        with open(self.progress_path, "rb") as f:
            self.p_bytes = bytearray(f.read())
        with open(self.caption_path, "rb") as f:
            self.c_bytes = bytearray(f.read())

        if len(self.p_bytes) < HEADER_END_PROGRESS:
            raise ValueError(f"progress.sav too short: {len(self.p_bytes)} < {HEADER_END_PROGRESS}")

        magic, ver, hend = struct.unpack_from("<III", self.p_bytes, 0)
        if magic != 0x01020304 or ver != 0x002D80EB or hend != HEADER_END_PROGRESS:
            raise ValueError(f"progress.sav format mismatch (magic={hex(magic)}, ver={hex(ver)}, hend={hex(hend)})")

        self.p_fields = {}
        for o in range(40, HEADER_END_PROGRESS, 8):
            h = struct.unpack_from("<I", self.p_bytes, o)[0]
            if h != 0:
                self.p_fields[h] = o + 4

        if len(self.c_bytes) < HEADER_END_CAPTION:
            raise ValueError(f"caption.sav too short: {len(self.c_bytes)} < {HEADER_END_CAPTION}")

        cmagic, cver, chend = struct.unpack_from("<III", self.c_bytes, 0)
        if cmagic != 0x01020304 or cver != 0x002D80EB or chend != HEADER_END_CAPTION:
            raise ValueError(f"caption.sav format mismatch (magic={hex(cmagic)}, ver={hex(cver)}, hend={hex(chend)})")

        self.c_fields = {}
        for o in range(40, HEADER_END_CAPTION, 8):
            h = struct.unpack_from("<I", self.c_bytes, o)[0]
            if h != 0:
                self.c_fields[h] = o + 4

        loc_str = self.get_caption_string(0xCCCC6CD, 64) or self.get_caption_string(0xF74E0E8E, 64)
        if loc_str:
            parts = loc_str.split("/")
            self.map_name = parts[-1].replace("_", " ")
        else:
            self.map_name = "Hyrule"

        self.loaded = True
        return True

    def get(self, h, default=0):
        if h in self.p_fields:
            return struct.unpack_from("<i", self.p_bytes, self.p_fields[h])[0]
        return default

    def set(self, h, val):
        if h in self.p_fields:
            struct.pack_into("<i", self.p_bytes, self.p_fields[h], int(val))

    def get_u32(self, h, default=0):
        if h in self.p_fields:
            return struct.unpack_from("<I", self.p_bytes, self.p_fields[h])[0]
        return default

    def set_u32(self, h, val):
        if h in self.p_fields:
            struct.pack_into("<I", self.p_bytes, self.p_fields[h], int(val) & 0xFFFFFFFF)

    def get_c(self, h, default=0):
        if h in self.c_fields:
            return struct.unpack_from("<i", self.c_bytes, self.c_fields[h])[0]
        return default

    def set_c(self, h, val):
        if h in self.c_fields:
            struct.pack_into("<i", self.c_bytes, self.c_fields[h], int(val))

    def get_string(self, h, length=64):
        if h not in self.p_fields:
            return ""
        off = self.get_u32(h)
        if off < HEADER_END_PROGRESS or off > len(self.p_bytes) - length:
            return ""
        raw = bytes(self.p_bytes[off:off+length])
        nul = raw.find(b"\x00")
        if nul >= 0:
            raw = raw[:nul]
        return raw.decode("utf-8", errors="replace")

    def set_string(self, h, text, length=64):
        if h not in self.p_fields:
            return
        off = self.get_u32(h)
        if off < HEADER_END_PROGRESS or off > len(self.p_bytes) - length:
            return
        self.p_bytes[off:off+length] = b"\x00" * length
        raw = text.encode("utf-8")[:length-1]
        self.p_bytes[off:off+len(raw)] = raw

    def get_caption_string(self, h, length=64):
        if h not in self.c_fields:
            return ""
        off = struct.unpack_from("<I", self.c_bytes, self.c_fields[h])[0]
        if off < HEADER_END_CAPTION or off > len(self.c_bytes) - length:
            return ""
        raw = bytes(self.c_bytes[off:off+length])
        nul = raw.find(b"\x00")
        if nul >= 0:
            raw = raw[:nul]
        return raw.decode("utf-8", errors="replace")

    def save_to_files(self):
        with open(self.progress_path, "wb") as f:
            f.write(self.p_bytes)
        with open(self.caption_path, "wb") as f:
            f.write(self.c_bytes)


def register_all_owned_inventory(s):
    """Automatically synchronizes all 105 official acquisition and related flags
    matching Traiver's reverse-engineered registerInventory logic.
    """
    count = 0
    for stocks, acquired, related, name in CATALOG.get("registrations", []):
        has_any = any(s.get(h, 0) > 0 for h in stocks)
        if has_any:
            if acquired in s.p_fields and s.get(acquired, 0) == 0:
                s.set(acquired, 1)
                count += 1
            if related and related in s.p_fields and s.get(related, 0) == 0:
                s.set(related, 1)
                count += 1
    return count


# ---------- Helper Utilities & Cheats ----------
RAW_MARK = "\x01"
CHEAT_LINE = re.compile(r"^[0-9A-Fa-f]{8}( [0-9A-Fa-f]{8})*$")
KNOWN_BUILDS = {"E0F3CCFAF50065AE": "v1.0.0"}
CHEAT_GUIDE_URL = "https://github.com/dlr-developer/the-legend-of-zelda-ocarina-of-time-switch-2-save-editor/blob/main/docs/CHEATS.md"
CHEAT_GUIDE = [
    ("warn", "Cheats are experimental. A wrong or mismatched code can crash the game or corrupt your save. "
             "Always back up first."),
    ("h", "How cheats work"),
    ("", "While the game runs, player stats (HP, rupees, ammo) reside in system RAM. A cheat code instructs "
         "the emulator (or Atmosphere on a Switch 2) to continuously lock those memory addresses. Cheats do not "
         "change your save file directly, but if you save while one is active, its effects are saved too."),
    ("h", "Will a code work for me?"),
    ("", "- Game version: a code only works for the exact build ID it was made for (v1.0.0 is E0F3CCFAF50065AE)."),
    ("", "- Emulator: Lichii, Eden, the yuzu family, and Atmosphere on a real Switch 2 all use this cheat format."),
    ("h", "Using a cheat"),
    ("", "1. Back up your save (Back up now button at the top of the window)."),
    ("", "2. Turn on only the cheats you want (double-click a row)."),
    ("", "3. Click Install to emulator (or Export for Switch 2), then restart the game."),
    ("h", "Where the files go"),
    ("", "- Lichii / Eden / yuzu family: load\\0400486024DEC000\\OOT Save Editor Cheats\\cheats\\<build ID>.txt"),
    ("", "- Ryujinx: mods\\contents\\0400486024dec000\\OOT Save Editor Cheats\\cheats\\<build ID>.txt"),
    ("", "- Switch 2: atmosphere/contents/0400486024DEC000/cheats/<build ID>.txt on the SD card."),
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
TEST_TARGETS = ("Ryujinx", "yuzu family", "Switch 2")
TEST_STATES = ("Untested", "Works", "Doesn't work")

def seed_cheat_library(user_cheat_dir=None, resource_cheat_dir=None):
    """Seed USER_DATA_DIR/cheats by copying missing files from RESOURCE_DIR/cheats (never overwrite)."""
    u_dir = user_cheat_dir or CHEAT_LIB_DIR
    r_dir = resource_cheat_dir or os.path.join(RESOURCE_DIR, "cheats")
    if not os.path.isdir(r_dir) or os.path.normpath(r_dir) == os.path.normpath(u_dir):
        return 0
    copied = 0
    for root, dirs, files in os.walk(r_dir):
        rel = os.path.relpath(root, r_dir)
        dst_root = os.path.join(u_dir, rel)
        for f in files:
            dst_file = os.path.join(dst_root, f)
            if not os.path.exists(dst_file):
                os.makedirs(dst_root, exist_ok=True)
                shutil.copy2(os.path.join(root, f), dst_file)
                copied += 1
    return copied

def library_builds(lib_dir=None):
    if lib_dir is not None:
        root = os.path.join(lib_dir, GAME_FOLDER)
        found = {}
        if os.path.isdir(root):
            for name in sorted(os.listdir(root)):
                m = re.search(r"([0-9A-Fa-f]{16})$", name)
                if m and os.path.isdir(os.path.join(root, name)):
                    found[m.group(1).upper()] = os.path.join(root, name)
        return found

    # When lib_dir is None, combine bundled fallback with user library
    found = {}
    res_cheats = os.path.join(RESOURCE_DIR, "cheats")
    if os.path.isdir(res_cheats) and os.path.normpath(res_cheats) != os.path.normpath(CHEAT_LIB_DIR):
        found.update(library_builds(res_cheats))
    found.update(library_builds(CHEAT_LIB_DIR))
    return found

def build_folder(bid):
    # App-written cheats always live in CHEAT_LIB_DIR (USER_DATA_DIR/cheats)
    user_builds = library_builds(CHEAT_LIB_DIR)
    return user_builds.get(bid) or os.path.join(
        CHEAT_LIB_DIR, GAME_FOLDER, f"{KNOWN_BUILDS.get(bid, 'unknown version')} - {bid}")

def read_library(bid, lib_dir=None):
    if lib_dir is None:
        seed_cheat_library()
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
    seed_cheat_library()
    folder = build_folder(bid)
    version = KNOWN_BUILDS.get(bid, "unknown version")
    os.makedirs(folder, exist_ok=True)
    header = f"# {GAME_NAME} {version} cheats\n\nBuild ID `{bid}` - title ID `{TITLE_ID}`\n\n"
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
        out = subprocess.check_output('tasklist /FO CSV /NH', shell=True, text=True)
        low = out.lower()
        for name in ("lichii.exe", "eden.exe", "yuzu.exe", "suyu.exe", "sudachi.exe", "ryujinx.exe"):
            if name in low:
                return True
    except Exception:
        pass
    return False

# ---------- Themes & Palettes ----------
PALETTES = {
    "light": {"bg": "#f4f5f7", "surface": "#ffffff", "field": "#ffffff", "fg": "#1e2229", "muted": "#5c6470",
              "faint": "#8a92a0", "border": "#d2d6dc", "hover": "#e6e8eb", "select": "#1976d2",
              "accent": "#0066cc", "warn": "#d97706", "banner": "#fff8e1", "tag_worn": "#1976d2", "tag_key": "#7c3aed",
              "tag_none": "#999999", "tag_on": "#2e7d32", "tag_off": "#888888", "tag_changed": "#d97706"},
    "dark": {"bg": "#1f2125", "surface": "#2b2e33", "field": "#26292e", "fg": "#e8e8e8", "muted": "#a9adb4",
             "faint": "#7d828a", "border": "#3d4148", "hover": "#353940", "select": "#2f5f9e",
             "accent": "#6cb4ff", "warn": "#ffb74d", "banner": "#3a3020", "tag_worn": "#6cb4ff", "tag_key": "#c7a8ff",
             "tag_none": "#6f747c", "tag_on": "#7fd88a", "tag_off": "#7d828a", "tag_changed": "#ffb74d"},
}
THEMES = ("System", "Light", "Dark")

def system_prefers_dark():
    """True if system is set to dark mode for apps."""
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

def load_settings(path=None):
    target_path = path or SETTINGS_PATH
    try:
        with open(target_path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def store_settings(settings, path=None):
    target_path = path or SETTINGS_PATH
    try:
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except OSError:
        pass


class LegacyMigrationCounts(NamedTuple):
    """Result counts from legacy user data folder migration."""
    backups: int = 0
    cheats: int = 0
    guides: int = 0
    settings: int = 0

    @property
    def total(self) -> int:
        return self.backups + self.cheats + self.guides + self.settings


def _cleanup_staging_path(path):
    """Safely remove a staging directory or file if it exists."""
    if os.path.lexists(path):
        if os.path.isdir(path) and not os.path.islink(path):
            shutil.rmtree(path, ignore_errors=True)
        else:
            try:
                os.remove(path)
            except OSError:
                pass


def cleanup_staging_items(folder):
    """Remove stale staging folders and files (matching *.partial*) under folder.

    Only ever deletes staging items whose names contain '.partial', never anything else.
    """
    if not folder or not os.path.isdir(folder):
        return
    try:
        for root, dirs, files in os.walk(folder, topdown=True):
            for d in list(dirs):
                if ".partial" in d:
                    shutil.rmtree(os.path.join(root, d), ignore_errors=True)
                    dirs.remove(d)
            for f in files:
                if ".partial" in f:
                    try:
                        os.remove(os.path.join(root, f))
                    except OSError:
                        pass
    except OSError:
        pass


def list_backups(backup_dir):
    """List valid backup directory names in backup_dir, sorted descending, skipping staging folders."""
    if not backup_dir or not os.path.isdir(backup_dir):
        return []
    try:
        entries = os.listdir(backup_dir)
    except OSError:
        return []
    return sorted(
        [
            d for d in entries
            if ".partial" not in d and os.path.isdir(os.path.join(backup_dir, d))
        ],
        reverse=True,
    )


def safe_copy(src, dst):
    """Safely copy a directory or file using a per-process .partial-<pid> staging location, replacing atomically to dst on success.

    Leaves no half-copied data under dst if copying fails, cleans up stale staging if present,
    never modifies or deletes any files in src, and discards staging if dst appeared concurrently.
    """
    if not os.path.exists(src):
        return False
    if os.path.exists(dst):
        return False

    partial = f"{dst}.partial-{os.getpid()}"
    _cleanup_staging_path(partial)

    os.makedirs(os.path.dirname(dst), exist_ok=True)

    if os.path.isdir(src):
        try:
            # copy_function is passed explicitly so it is resolved at call time (copytree's default is
            # bound at import, which would hide test doubles for shutil.copy2).
            shutil.copytree(src, partial, copy_function=shutil.copy2)
            if os.path.exists(dst):
                _cleanup_staging_path(partial)
                return False
            os.replace(partial, dst)
        except OSError:
            if os.path.exists(dst):
                _cleanup_staging_path(partial)
                return False
            _cleanup_staging_path(partial)
            raise
        return True
    else:
        try:
            shutil.copy2(src, partial)
            if os.path.exists(dst):
                _cleanup_staging_path(partial)
                return False
            os.replace(partial, dst)
        except OSError:
            if os.path.exists(dst):
                _cleanup_staging_path(partial)
                return False
            _cleanup_staging_path(partial)
            raise
        return True


def migrate_legacy_user_data(legacy_dir=None, user_data_dir=None, settings=None, app_dir=None):
    """Migrate settings, backups, cheats, and guides from legacy data folder into user_data_dir once."""
    l_dir = legacy_dir or LEGACY_DATA_DIR
    u_dir = user_data_dir or USER_DATA_DIR
    a_dir = app_dir or APP_DIR
    new_settings_path = os.path.join(u_dir, "settings.json")
    sets = settings if settings is not None else load_settings(new_settings_path)

    # In portable mode, skip legacy migration so portable installs do not pull data from the PC
    if os.path.exists(os.path.join(a_dir, "portable.txt")):
        return LegacyMigrationCounts()
    if u_dir and os.path.exists(os.path.join(os.path.dirname(u_dir), "portable.txt")):
        return LegacyMigrationCounts()

    if not os.path.isdir(l_dir):
        return LegacyMigrationCounts()
    if os.path.normpath(l_dir) == os.path.normpath(u_dir):
        return LegacyMigrationCounts()
    if sets.get("migrated_from_legacy_dir") == l_dir:
        return LegacyMigrationCounts()

    os.makedirs(u_dir, exist_ok=True)
    failures = 0

    # Clean stale staging items in destination folders before migrating
    for dest_folder in (os.path.join(u_dir, "backups"), os.path.join(u_dir, "cheats"), os.path.join(u_dir, "guides")):
        cleanup_staging_items(dest_folder)

    # 1. settings.json (only if new one does not exist)
    migrated_settings = 0
    old_settings_path = os.path.join(l_dir, "settings.json")
    if os.path.isfile(old_settings_path) and not os.path.exists(new_settings_path):
        try:
            with open(old_settings_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                for k, v in loaded.items():
                    if k not in sets:
                        sets[k] = v
            if safe_copy(old_settings_path, new_settings_path):
                migrated_settings = 1
        except OSError:
            failures += 1
        except Exception:
            pass

    # 2. backups/* folders
    migrated_backups = 0
    old_backups = os.path.join(l_dir, "backups")
    new_backups = os.path.join(u_dir, "backups")
    if os.path.isdir(old_backups):
        os.makedirs(new_backups, exist_ok=True)
        for item in sorted(os.listdir(old_backups)):
            s_item = os.path.join(old_backups, item)
            d_item = os.path.join(new_backups, item)
            if os.path.isdir(s_item) and not os.path.exists(d_item):
                try:
                    if safe_copy(s_item, d_item):
                        migrated_backups += 1
                except OSError:
                    failures += 1

    # 3. cheats/* files
    migrated_cheats = 0
    old_cheats = os.path.join(l_dir, "cheats")
    new_cheats = os.path.join(u_dir, "cheats")
    if os.path.isdir(old_cheats):
        for root, dirs, files in os.walk(old_cheats):
            rel = os.path.relpath(root, old_cheats)
            dst_root = os.path.join(new_cheats, rel)
            for f in files:
                s_file = os.path.join(root, f)
                d_file = os.path.join(dst_root, f)
                if not os.path.exists(d_file):
                    try:
                        if safe_copy(s_file, d_file):
                            migrated_cheats += 1
                    except OSError:
                        failures += 1

    # 4. guides/* files
    migrated_guides = 0
    old_guides = os.path.join(l_dir, "guides")
    new_guides = os.path.join(u_dir, "guides")
    if os.path.isdir(old_guides):
        for root, dirs, files in os.walk(old_guides):
            rel = os.path.relpath(root, old_guides)
            dst_root = os.path.join(new_guides, rel)
            for f in files:
                s_file = os.path.join(root, f)
                d_file = os.path.join(dst_root, f)
                if not os.path.exists(d_file):
                    try:
                        if safe_copy(s_file, d_file):
                            migrated_guides += 1
                    except OSError:
                        failures += 1

    if failures == 0:
        sets["migrated_from_legacy_dir"] = l_dir
        store_settings(sets, path=new_settings_path)
    else:
        sets.pop("migrated_from_legacy_dir", None)
        store_settings(sets, path=new_settings_path)

    return LegacyMigrationCounts(
        backups=migrated_backups,
        cheats=migrated_cheats,
        guides=migrated_guides,
        settings=migrated_settings,
    )


def migrate_user_data(app_dir=None, user_data_dir=None, settings=None):
    """Migrate legacy backups and user-written cheats from app_dir to user_data_dir once."""
    a_dir = app_dir or APP_DIR
    u_dir = user_data_dir or USER_DATA_DIR
    new_settings_path = os.path.join(u_dir, "settings.json")
    sets = settings if settings is not None else load_settings(new_settings_path)

    if os.path.normpath(a_dir) == os.path.normpath(u_dir):
        return 0, 0
    if sets.get("backups_migrated_from") == a_dir:
        return 0, 0

    failures = 0

    # Clean stale staging items in destination folders before migrating
    for dest_folder in (os.path.join(u_dir, "backups"), os.path.join(u_dir, "cheats")):
        cleanup_staging_items(dest_folder)

    migrated_backups = 0
    old_backups = os.path.join(a_dir, "backups")
    new_backups = os.path.join(u_dir, "backups")
    if os.path.isdir(old_backups):
        os.makedirs(new_backups, exist_ok=True)
        for item in sorted(os.listdir(old_backups)):
            s_item = os.path.join(old_backups, item)
            d_item = os.path.join(new_backups, item)
            if os.path.isdir(s_item) and not os.path.exists(d_item):
                try:
                    if safe_copy(s_item, d_item):
                        migrated_backups += 1
                except OSError:
                    failures += 1

    migrated_cheats = 0
    old_cheats = os.path.join(a_dir, "cheats")
    new_cheats = os.path.join(u_dir, "cheats")
    if os.path.isdir(old_cheats):
        for root, dirs, files in os.walk(old_cheats):
            rel = os.path.relpath(root, old_cheats)
            dst_root = os.path.join(new_cheats, rel)
            for f in files:
                s_file = os.path.join(root, f)
                d_file = os.path.join(dst_root, f)
                if not os.path.exists(d_file):
                    try:
                        if safe_copy(s_file, d_file):
                            migrated_cheats += 1
                    except OSError:
                        failures += 1

    if failures == 0:
        sets["backups_migrated_from"] = a_dir
        store_settings(sets, path=new_settings_path)
    else:
        sets.pop("backups_migrated_from", None)
        store_settings(sets, path=new_settings_path)

    return migrated_backups, migrated_cheats

# ---------- Save Directory Resolution ----------
def resolve_save_folder(folder):
    if not folder or not os.path.isdir(folder):
        return None
    if any(os.path.isdir(os.path.join(folder, f"slot_{i:02d}")) for i in range(6)):
        return folder
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


def compute_adaptive_geometry(screen_w, screen_h, needed_w, needed_h):
    """Compute adaptive window geometry and minsize clamped to 92% of screen."""
    floor_w, floor_h = 1060, 780
    cap_w = int(screen_w * 0.92)
    cap_h = int(screen_h * 0.92)
    final_w = min(max(floor_w, needed_w), cap_w)
    final_h = min(max(floor_h, needed_h), cap_h)
    min_w = min(920, final_w)
    min_h = min(620, final_h)
    return final_w, final_h, min_w, min_h


# ---------- Main GUI Editor Class ----------
class OOTEditor(tk.Tk):
    def __init__(self, folder=None):
        super().__init__()
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self._set_icon()
        self.geometry("1060x780")
        self.minsize(920, 620)
        self.app_dir = APP_DIR
        self.user_data_dir = USER_DATA_DIR
        self.legacy_data_dir = LEGACY_DATA_DIR
        self.resource_dir = RESOURCE_DIR

        # Safe migration of legacy data folder BEFORE load_settings(),
        # ensuring migrated settings (e.g. theme) are loaded and applied on first launch.
        self._legacy_migration_counts = None
        self._legacy_migration_error = None
        if not os.path.exists(os.path.join(self.app_dir, "portable.txt")):
            try:
                self._legacy_migration_counts = migrate_legacy_user_data(
                    self.legacy_data_dir, self.user_data_dir, app_dir=self.app_dir
                )
            except Exception as e:
                self._legacy_migration_error = str(e)

        self.settings = load_settings()

        self._app_migration_bks = 0
        self._app_migration_error = None
        try:
            self._app_migration_bks, _ = migrate_user_data(self.app_dir, self.user_data_dir, self.settings)
        except Exception as e:
            self._app_migration_error = str(e)

        self.root_dir = tk.StringVar()
        self.slot = tk.StringVar()
        self.slot_names = []
        self.active_slot = None
        self.orig_snapshot = {}
        self._sort = {}
        self.cheats = []
        self.emulator = None
        self._story_warned = False

        # General Tab Variables
        self.v_rupees = tk.StringVar(value="0")
        self.v_hearts = tk.StringVar(value="3")
        self.v_boss_containers = tk.StringVar(value="0")
        self.v_heart_pieces_total = tk.StringVar(value="0")
        self.v_heart_pieces_held = tk.StringVar(value="0")
        self.v_hearts_from_pieces = tk.StringVar(value="0")
        self.v_hp = tk.StringVar(value="12")
        self.v_hp_status = tk.StringVar(value="3 Full Hearts (12 Quarters)")
        self.v_magic = tk.StringVar(value="None")
        self.v_magic_points = tk.StringVar(value="0")
        self.v_magic_status = tk.StringVar(value="0 / 0 MP")
        self.v_tokens = tk.StringVar(value="0")
        self.v_double_defense = tk.BooleanVar(value=False)

        # Equipment Variables
        self.equip_vars = {}
        self.owned_swords = {}
        self.owned_shields = {}
        self.owned_tunics = {}
        self.owned_boots = {}

        # Ammo, Bottles, Special, Quest, Songs
        self.ammo_vars = {}
        self.bottle_vars = {}
        self.special_item_vars = {}
        self.quest_vars = {}
        self.song_vars = {}

        # Mutually exclusive & single active item vars
        self.hookshot_var = tk.StringVar(value="None")
        self.active_mask_var = tk.StringVar(value="None")
        self.child_quest_var = tk.StringVar(value="None")
        self.adult_trade_var = tk.StringVar(value="None")
        self.prev_bottle_selections = {}
        self.key_vars = {}

        # Progress Flags & Field Inspector vars
        self.flag_changes = {}
        self.flag_tree = None
        self.flag_search_var = tk.StringVar(value="")
        self.flag_category_var = tk.StringVar(value="All Categories")
        self.flag_status_var = tk.StringVar(value="All States")
        self.flag_count_lbl = tk.StringVar(value="0 flags")

        self.inspector_tree = None
        self.inspector_search_var = tk.StringVar(value="")
        self.inspector_only_named_var = tk.BooleanVar(value=True)
        self.inspector_type_var = tk.StringVar(value="All Types")
        self.inspector_count_lbl = tk.StringVar(value="0 fields")

        self._style()
        self._build_top()
        self._build_tabs()
        self.apply_theme()
        self._set_adaptive_geometry()

        start = folder or self.settings.get("save_folder")
        start = resolve_save_folder(start) if start else None
        self.set_folder(start or autodetect())

        # Display deferred migration status messages
        if self._legacy_migration_error:
            self.status.set(f"Legacy migration failed: {self._legacy_migration_error}")
        elif self._legacy_migration_counts and self._legacy_migration_counts.total > 0:
            parts = []
            if self._legacy_migration_counts.backups:
                cnt = self._legacy_migration_counts.backups
                parts.append(f"{cnt} backup{'s' if cnt != 1 else ''}")
            if self._legacy_migration_counts.cheats:
                cnt = self._legacy_migration_counts.cheats
                parts.append(f"{cnt} cheat file{'s' if cnt != 1 else ''}")
            if self._legacy_migration_counts.guides:
                cnt = self._legacy_migration_counts.guides
                parts.append(f"{cnt} guide file{'s' if cnt != 1 else ''}")
            if self._legacy_migration_counts.settings:
                parts.append("settings")
            self.status.set(f"Migrated {', '.join(parts)} from legacy data folder.")
            self.update_backup_count()
        elif self._app_migration_error:
            self.status.set(f"Backup migration failed: {self._app_migration_error}")
        elif self._app_migration_bks > 0:
            self.status.set(f"Migrated {self._app_migration_bks} backup{'s' if self._app_migration_bks != 1 else ''} to user data folder.")
            self.update_backup_count()

    def _set_adaptive_geometry(self):
        self.update_idletasks()
        max_tab_w = 0
        max_tab_h = 0
        for tab_id in self.notebook.tabs():
            tab_widget = self.nametowidget(tab_id)
            max_tab_w = max(max_tab_w, tab_widget.winfo_reqwidth())
            max_tab_h = max(max_tab_h, tab_widget.winfo_reqheight())

        pad_w = 32
        pad_h = 36
        if hasattr(self, "_top_frame") and self._top_frame:
            pad_h += self._top_frame.winfo_reqheight()
        else:
            pad_h += 130
        if hasattr(self, "_bot_frame") and self._bot_frame:
            pad_h += self._bot_frame.winfo_reqheight()
        else:
            pad_h += 30

        top_req_w = self._top_frame.winfo_reqwidth() if (hasattr(self, "_top_frame") and self._top_frame) else 0
        needed_w = max(max_tab_w + pad_w, top_req_w + 20)
        needed_h = max_tab_h + pad_h

        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()

        final_w, final_h, min_w, min_h = compute_adaptive_geometry(
            screen_w, screen_h, needed_w, needed_h
        )

        pos_x = max(0, (screen_w - final_w) // 2)
        pos_y = max(0, (screen_h - final_h) // 2)

        self.geometry(f"{final_w}x{final_h}+{pos_x}+{pos_y}")
        self.minsize(min_w, min_h)

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
        top = self._top_frame = ttk.Frame(self, padding=8)
        top.pack(fill="x")

        # Save folder row
        ttk.Label(top, text="Save folder:").grid(row=0, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.root_dir, state="readonly").grid(row=0, column=1, sticky="ew", padx=4)
        fb = ttk.Frame(top)
        fb.grid(row=0, column=2, sticky="ew")
        ttk.Button(fb, text="Browse...", command=self.browse).pack(side="left")
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

        bk_controls = ttk.Frame(bk)
        bk_controls.pack(fill="x", expand=True)

        ttk.Button(bk_controls, text="Back up now...", command=self.backup_now).pack(side="left")
        ttk.Button(bk_controls, text="Restore a backup...", command=self.restore_dialog).pack(side="left", padx=4)
        ttk.Button(bk_controls, text="Open backups folder", command=self.open_backups).pack(side="left")
        self.backup_count = tk.StringVar()
        ttk.Label(bk_controls, textvariable=self.backup_count, style="Muted.TLabel").pack(side="left", padx=(10, 4))

        # Theme selector prominently placed in Backups frame (matching SMRPG)
        self.theme_choice = tk.StringVar(value=self.settings.get("theme", "System"))
        theme_cb = ttk.Combobox(bk_controls, textvariable=self.theme_choice, values=THEMES, state="readonly", width=8)
        theme_cb.pack(side="right")
        theme_cb.bind("<<ComboboxSelected>>", self.on_theme_pick)
        ttk.Label(bk_controls, text="Theme:").pack(side="right", padx=(0, 4))

        # In-Game Interactive Pause Menu Button (on the left side of Theme selector)
        self.pause_menu_button = ttk.Button(bk_controls, text="Switch 2 Pause Menu 🎮", command=self.switch_to_texture_view)
        self.pause_menu_button.pack(side="right", padx=(0, 16))

        # Full backups path moved to its own row under buttons so it never squeezes the Pause Menu button
        self.backups_path_label = ttk.Label(bk, text=f"({os.path.join(self.user_data_dir, 'backups')})", style="Faint.TLabel", wraplength=1000)
        self.backups_path_label.pack(fill="x", anchor="w", pady=(4, 0))

        top.columnconfigure(1, weight=1)

    def _build_tabs(self):
        self.view_container = ttk.Frame(self)
        self.view_container.pack(fill="both", expand=True)

        # Standard Editor View Frame
        self.standard_view_frame = ttk.Frame(self.view_container)
        self.standard_view_frame.pack(fill="both", expand=True)

        nb = self.notebook = ttk.Notebook(self.standard_view_frame)
        nb.pack(fill="both", expand=True, padx=8, pady=(4, 0))
        self._build_general_tab(nb)
        self._build_equipment_inventory_tab(nb)
        self._build_quest_tab(nb)
        self._build_progress_inspector_tab(nb)
        self._build_guides_tab(nb)
        self._build_cheats_tab(nb)

        # Bottom status bar
        bot = self._bot_frame = ttk.Frame(self.standard_view_frame, padding=(8, 4))
        bot.pack(fill="x")
        self.status = tk.StringVar(value="Select a save slot to begin editing.")
        ttk.Label(bot, textvariable=self.status, style="Muted.TLabel").pack(side="left")
        nb.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        self.texture_view_frame = None

    def switch_to_texture_view(self):
        try:
            from oot_pause_menu import OOTTextureMenuFrame
            if not self.active_slot:
                messagebox.showinfo("No Slot Selected", "Please select and load a save slot first.", parent=self)
                return
            self.standard_view_frame.pack_forget()
            if self.texture_view_frame is None:
                self.texture_view_frame = OOTTextureMenuFrame(self.view_container, self)
            self.texture_view_frame.pack(fill="both", expand=True)
            self.texture_view_frame.refresh_visuals()
        except Exception as e:
            messagebox.showerror("Error Switching View", f"Could not launch In-Game Texture View:\n{str(e)}", parent=self)

    def switch_to_standard_view(self):
        if self.texture_view_frame:
            self.texture_view_frame.pack_forget()
        self.standard_view_frame.pack(fill="both", expand=True)
        self.load_slot()

    # ---------- TAB 1: General & Stats ----------
    def _build_general_tab(self, nb):
        gen = ttk.Frame(nb, padding=12)
        nb.add(gen, text="General")

        # Wealth & Skulltulas
        w_frame = ttk.LabelFrame(gen, text="Rupees & Gold Skulltulas", padding=10)
        w_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(w_frame, text="Rupees:").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Spinbox(w_frame, from_=0, to=1000, textvariable=self.v_rupees, width=10).grid(row=0, column=1, sticky="w", padx=8)
        ttk.Button(w_frame, text="Max", width=5, command=self._max_rupees_to_wallet).grid(row=0, column=2, sticky="w")
        ttk.Label(w_frame, text="(Wallet determines maximum: 200, 500, or 1000)", style="Faint.TLabel").grid(row=0, column=3, sticky="w", padx=(8, 0))

        ttk.Label(w_frame, text="Gold Skulltula Tokens:").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Spinbox(w_frame, from_=0, to=100, textvariable=self.v_tokens, width=10).grid(row=1, column=1, sticky="w", padx=8)
        ttk.Button(w_frame, text="Max", width=5, command=lambda: self.v_tokens.set("100")).grid(row=1, column=2, sticky="w")
        ttk.Label(w_frame, text="(0-100 tokens collected for the House of Skulltula)", style="Faint.TLabel").grid(row=1, column=3, sticky="w", padx=(8, 0))

        # Health & Hearts
        h_frame = ttk.LabelFrame(gen, text="Health & Hearts System (Quarter-Heart Precision)", padding=10)
        h_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(h_frame, text="Boss Heart Containers:").grid(row=0, column=0, sticky="w", pady=3)
        sb_boss = ttk.Spinbox(h_frame, from_=0, to=8, textvariable=self.v_boss_containers, width=10,
                              command=self._recalc_hearts_from_components)
        sb_boss.grid(row=0, column=1, sticky="w", padx=8)
        sb_boss.bind("<KeyRelease>", lambda e: self._recalc_hearts_from_components())
        ttk.Button(h_frame, text="Max (8)", width=8, command=self._max_boss_containers).grid(row=0, column=2, sticky="w")
        ttk.Label(h_frame, text="(Main dungeon bosses: Deku Tree, Dodongo, Jabu-Jabu, 5 Temples)",
                  style="Faint.TLabel").grid(row=0, column=3, sticky="w", padx=(8, 0))

        ttk.Label(h_frame, text="Heart Pieces Found:").grid(row=1, column=0, sticky="w", pady=3)
        sb_pieces = ttk.Spinbox(h_frame, from_=0, to=36, textvariable=self.v_heart_pieces_total, width=10,
                                command=self._recalc_hearts_from_components)
        sb_pieces.grid(row=1, column=1, sticky="w", padx=8)
        sb_pieces.bind("<KeyRelease>", lambda e: self._recalc_hearts_from_components())
        ttk.Button(h_frame, text="Max (36)", width=8, command=self._max_heart_pieces).grid(row=1, column=2, sticky="w")

        ttk.Label(h_frame, text="Total Maximum Hearts:").grid(row=2, column=0, sticky="w", pady=3)
        sb_hearts = ttk.Spinbox(h_frame, from_=3, to=20, textvariable=self.v_hearts, width=10,
                                command=self._on_total_hearts_change)
        sb_hearts.grid(row=2, column=1, sticky="w", padx=8)
        sb_hearts.bind("<KeyRelease>", lambda e: self._on_total_hearts_change())
        ttk.Button(h_frame, text="Max (20)", width=8, command=self._max_hearts_to_20).grid(row=2, column=2, sticky="w")
        ttk.Label(h_frame, text="Starting (3) + Boss Containers + (Pieces // 4)",
                  style="Faint.TLabel").grid(row=2, column=3, sticky="w", padx=(8, 0))

        ttk.Label(h_frame, text="Current Health (Quarter-Hearts):").grid(row=3, column=0, sticky="w", pady=3)
        sb_hp = ttk.Spinbox(h_frame, from_=1, to=80, textvariable=self.v_hp, width=10,
                            command=self._on_hp_change)
        sb_hp.grid(row=3, column=1, sticky="w", padx=8)
        sb_hp.bind("<KeyRelease>", lambda e: self._on_hp_change())

        hp_btns = ttk.Frame(h_frame)
        hp_btns.grid(row=3, column=2, columnspan=2, sticky="w")
        ttk.Button(hp_btns, text="Heal to Full", command=self.heal_link).pack(side="left")
        ttk.Button(hp_btns, text="Set Critical (1/4 Heart)", command=self.set_critical_health).pack(side="left", padx=(4, 0))

        ttk.Label(h_frame, textvariable=self.v_hp_status, style="Muted.TLabel",
                  font=("Segoe UI", 9, "bold")).grid(row=4, column=1, columnspan=3, sticky="w", pady=(2, 4))

        ttk.Checkbutton(h_frame, text="Double Defense (White Heart Outline - Halved damage from Great Fairy)",
                        variable=self.v_double_defense).grid(row=5, column=0, columnspan=4, sticky="w", pady=(4, 0))

        # Magic Meter
        m_frame = ttk.LabelFrame(gen, text="Magic Meter & Powers", padding=10)
        m_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(m_frame, text="Magic Meter Level:").grid(row=0, column=0, sticky="w", pady=3)
        m_box = ttk.Combobox(m_frame, textvariable=self.v_magic, state="readonly", width=34,
                              values=["None", "Standard Magic Meter (24 MP)", "Double Magic Meter (48 MP)"])
        m_box.grid(row=0, column=1, sticky="w", padx=8)
        m_box.bind("<<ComboboxSelected>>", self._on_magic_level_change)

        ttk.Label(m_frame, text="Current Magic (MP):").grid(row=1, column=0, sticky="w", pady=3)
        sb_mp = ttk.Spinbox(m_frame, from_=0, to=48, textvariable=self.v_magic_points, width=10,
                            command=self._on_mp_change)
        sb_mp.grid(row=1, column=1, sticky="w", padx=8)
        sb_mp.bind("<KeyRelease>", lambda e: self._on_mp_change())
        ttk.Button(m_frame, text="Refill Magic", command=self.refill_magic).grid(row=1, column=2, sticky="w")

        ttk.Label(m_frame, textvariable=self.v_magic_status, style="Muted.TLabel",
                  font=("Segoe UI", 9, "bold")).grid(row=2, column=1, columnspan=2, sticky="w", pady=(2, 0))

        bot_btns = ttk.Frame(gen)
        bot_btns.pack(fill="x", pady=(6, 0))
        self.primary_button(bot_btns, "Max All General Stats", self.max_general).pack(side="left")

        self.gen_info = tk.StringVar()
        ttk.Label(gen, textvariable=self.gen_info, style="Muted.TLabel", justify="left", wraplength=800).pack(
            anchor="w", pady=(12, 0))

    def _max_boss_containers(self):
        self.v_boss_containers.set("8")
        self._recalc_hearts_from_components()

    def _max_heart_pieces(self):
        self.v_heart_pieces_total.set("36")
        self._recalc_hearts_from_components()

    def _recalc_hearts_from_components(self):
        try:
            total_pieces = int(self.v_heart_pieces_total.get() or 0)
        except ValueError:
            total_pieces = 0
        total_pieces = max(0, min(36, total_pieces))
        pieces_hearts = total_pieces // 4
        held = total_pieces % 4
        self.v_hearts_from_pieces.set(str(pieces_hearts))
        self.v_heart_pieces_held.set(str(held))

        try:
            boss = int(self.v_boss_containers.get() or 0)
        except ValueError:
            boss = 0
        boss = max(0, min(8, boss))
        tot_hearts = 3 + boss + pieces_hearts
        tot_hearts = max(3, min(20, tot_hearts))
        self.v_hearts.set(str(tot_hearts))

        max_hp = tot_hearts * 4
        try:
            cur_hp = int(self.v_hp.get() or max_hp)
        except ValueError:
            cur_hp = max_hp
        if cur_hp > max_hp or cur_hp <= 0:
            cur_hp = max_hp
            self.v_hp.set(str(cur_hp))
        self._update_hp_display()

    def _on_total_hearts_change(self):
        try:
            tot = int(self.v_hearts.get() or 3)
        except ValueError:
            tot = 3
        tot = max(3, min(20, tot))
        max_hp = tot * 4
        try:
            cur_hp = int(self.v_hp.get() or max_hp)
        except ValueError:
            cur_hp = max_hp
        if cur_hp > max_hp or cur_hp <= 0:
            self.v_hp.set(str(max_hp))
        self._update_hp_display()

    def _on_hp_change(self):
        try:
            tot = int(self.v_hearts.get() or 3)
            cur = int(self.v_hp.get() or (tot * 4))
        except ValueError:
            return
        cur = max(1, min(tot * 4, cur))
        self.v_hp.set(str(cur))
        self._update_hp_display()

    def _update_hp_display(self):
        try:
            tot = int(self.v_hearts.get() or 3)
            cur = int(self.v_hp.get() or (tot * 4))
            tot_pieces = int(self.v_heart_pieces_total.get() or 0)
        except ValueError:
            return
        full_hearts = cur / 4.0
        held_pieces = tot_pieces % 4
        needed = 4 - held_pieces if held_pieces > 0 else 4
        self.v_hp_status.set(f"{full_hearts:.2f} / {tot} Hearts ({cur} / {tot * 4} Quarters) | {held_pieces}/4 pieces held towards next heart")

    def heal_link(self):
        try:
            tot = int(self.v_hearts.get() or 3)
        except ValueError:
            tot = 3
        self.v_hp.set(str(tot * 4))
        self._update_hp_display()
        self.status.set("Link restored to full health.")

    def set_critical_health(self):
        self.v_hp.set("1")
        self._update_hp_display()
        self.status.set("Link set to 1 quarter-heart (Critical).")

    def _max_hearts_to_20(self):
        self.v_boss_containers.set("8")
        self.v_heart_pieces_total.set("36")
        self._recalc_hearts_from_components()
        self.heal_link()

    def _max_rupees_to_wallet(self):
        w_choice = self.equip_vars.get("wallet", tk.StringVar(value=WALLETS[1]["label"])).get()
        target = 500
        for w in WALLETS:
            if w["id"] in w_choice or str(w["limit"]) in w_choice:
                target = w["limit"]
                break
        self.v_rupees.set(str(target))
        self.status.set(f"Rupees maxed to {target} (wallet limit).")

    def _on_magic_level_change(self, event=None):
        lvl = self.v_magic.get()
        if "Double" in lvl:
            max_mp = 48
        elif "Standard" in lvl:
            max_mp = 24
        else:
            max_mp = 0
        try:
            cur = float(self.v_magic_points.get() or 0)
        except ValueError:
            cur = 0
        cur = min(cur, max_mp)
        self.v_magic_points.set(str(int(cur)))
        self._update_magic_display()

    def _on_mp_change(self):
        lvl = self.v_magic.get()
        max_mp = 48 if "Double" in lvl else (24 if "Standard" in lvl else 0)
        try:
            cur = float(self.v_magic_points.get() or 0)
        except ValueError:
            cur = 0
        cur = max(0, min(max_mp, cur))
        self.v_magic_points.set(str(int(cur)))
        self._update_magic_display()

    def refill_magic(self):
        lvl = self.v_magic.get()
        if lvl == "None":
            self.v_magic.set("Standard Magic Meter (24 MP)")
            self.v_magic_points.set("24")
        elif "Double" in lvl:
            self.v_magic_points.set("48")
        else:
            self.v_magic_points.set("24")
        self._update_magic_display()
        self.status.set("Magic points refilled.")

    def _update_magic_display(self):
        lvl = self.v_magic.get()
        max_mp = 48 if "Double" in lvl else (24 if "Standard" in lvl else 0)
        cur = self.v_magic_points.get()
        self.v_magic_status.set(f"{cur} / {max_mp} MP")

    # ---------- TAB 2: Equipment & Inventory ----------
    def _build_equipment_inventory_tab(self, nb):
        ei = ttk.Frame(nb, padding=10)
        nb.add(ei, text="Equipment & Inventory")

        main_grid = ttk.Frame(ei)
        main_grid.pack(fill="both", expand=True)

        col1 = ttk.Frame(main_grid)
        col1.pack(side="left", fill="both", expand=True, padx=(0, 6))

        col2 = ttk.Frame(main_grid)
        col2.pack(side="left", fill="both", expand=True, padx=6)

        col3 = ttk.Frame(main_grid)
        col3.pack(side="left", fill="both", expand=True, padx=(6, 0))

        # =====================================================================
        # COLUMN 1: Gear Storage, Equipped Gear & Ammo
        # =====================================================================
        # 1. Owned Equipment Storage
        store_frame = ttk.LabelFrame(col1, text="Owned Equipment Storage", padding=6)
        store_frame.pack(fill="x", pady=(0, 6))

        ttk.Label(store_frame, text="Swords:", font=("Segoe UI", 8, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 4))
        ttk.Label(store_frame, text="Shields:", font=("Segoe UI", 8, "bold")).grid(row=0, column=1, sticky="w", padx=(0, 4))
        ttk.Label(store_frame, text="Tunics:", font=("Segoe UI", 8, "bold")).grid(row=0, column=2, sticky="w", padx=(0, 4))
        ttk.Label(store_frame, text="Boots:", font=("Segoe UI", 8, "bold")).grid(row=0, column=3, sticky="w")

        swords_list = [("Kokiri", "Kokiri Sword"), ("Master", "Master Sword"), ("Biggoron", "Biggoron's Sword")]
        for r_idx, (lbl, s_key) in enumerate(swords_list, 1):
            v = tk.BooleanVar(value=False)
            cb = ttk.Checkbutton(store_frame, text=lbl, variable=v, command=self._sync_equipped_options)
            cb.grid(row=r_idx, column=0, sticky="w", padx=(0, 4), pady=1)
            self.owned_swords[s_key] = v

        shields_list = [("Deku", "Deku Shield"), ("Hylian", "Hylian Shield"), ("Mirror", "Mirror Shield")]
        for r_idx, (lbl, sh_key) in enumerate(shields_list, 1):
            v = tk.BooleanVar(value=False)
            cb = ttk.Checkbutton(store_frame, text=lbl, variable=v, command=self._sync_equipped_options)
            cb.grid(row=r_idx, column=1, sticky="w", padx=(0, 4), pady=1)
            self.owned_shields[sh_key] = v

        tunics_list = [("Kokiri", "Kokiri Tunic"), ("Goron", "Goron Tunic"), ("Zora", "Zora Tunic")]
        for r_idx, (lbl, t_key) in enumerate(tunics_list, 1):
            v = tk.BooleanVar(value=False)
            cb = ttk.Checkbutton(store_frame, text=lbl, variable=v, command=self._sync_equipped_options)
            cb.grid(row=r_idx, column=2, sticky="w", padx=(0, 4), pady=1)
            self.owned_tunics[t_key] = v

        boots_list = [("Kokiri", "Kokiri Boots"), ("Iron", "Iron Boots"), ("Hover", "Hover Boots")]
        for r_idx, (lbl, b_key) in enumerate(boots_list, 1):
            v = tk.BooleanVar(value=False)
            cb = ttk.Checkbutton(store_frame, text=lbl, variable=v, command=self._sync_equipped_options)
            cb.grid(row=r_idx, column=3, sticky="w", pady=1)
            self.owned_boots[b_key] = v

        ttk.Button(store_frame, text="Unlock All Equipment", command=self.unlock_all_stored_equipment).grid(
            row=5, column=0, columnspan=4, sticky="w", pady=(4, 0))

        # 2. Currently Equipped Gear
        equip_frame = ttk.LabelFrame(col1, text="Currently Equipped Gear", padding=6)
        equip_frame.pack(fill="x", pady=(0, 6))

        equip_items = [
            ("Sword:", [s[0] for s in SWORDS if s[0] != "Giant's Knife"], "sword"),
            ("Shield:", [s[0] for s in SHIELDS], "shield"),
            ("Tunic:", [t[0] for t in TUNICS], "tunic"),
            ("Boots:", [b[0] for b in BOOTS], "boots"),
        ]
        self.equipped_combos = {}
        for idx, (lbl, choices, key) in enumerate(equip_items):
            row = idx // 2
            col = (idx % 2) * 2
            ttk.Label(equip_frame, text=lbl).grid(row=row, column=col, sticky="w", padx=(6 if col else 0, 2), pady=2)
            var = tk.StringVar(value=choices[0])
            box_w = max(len(str(c)) for c in choices) + 2
            box = ttk.Combobox(equip_frame, textvariable=var, state="readonly", width=box_w, values=choices)
            box.grid(row=row, column=col+1, sticky="w", pady=2)
            self.equip_vars[key] = var
            self.equipped_combos[key] = box

        # 3. Ammo & Consumables
        ammo_frame = ttk.LabelFrame(col1, text="Ammo & Consumables", padding=6)
        ammo_frame.pack(fill="x", pady=(0, 6))

        self.ammo_labels = {}
        ammo_list = [
            ("Arrows", 50, "arrows"),
            ("Bombs", 40, "bombs"),
            ("Bombchus", 30, "bombchus"),
            ("Deku Seeds", 50, "seeds"),
            ("Deku Sticks", 30, "sticks"),
            ("Deku Nuts", 40, "nuts"),
            ("Magic Beans", 10, "beans"),
            ("Scrub Seeds", 30, "scrub"),
        ]

        for i, (label_base, max_val, key) in enumerate(ammo_list):
            row = i // 2
            col = (i % 2) * 3
            lbl_var = tk.StringVar(value=f"{label_base}:")
            self.ammo_labels[key] = (lbl_var, label_base)
            ttk.Label(ammo_frame, textvariable=lbl_var).grid(row=row, column=col, sticky="w", padx=(6 if col else 0, 2), pady=2)
            v = tk.StringVar(value="0")
            sb = ttk.Spinbox(ammo_frame, from_=0, to=max_val, textvariable=v, width=4)
            sb.grid(row=row, column=col+1, sticky="w", padx=2)
            ttk.Button(ammo_frame, text="Max", width=5, command=lambda var=v, k=key: self._max_single_ammo(var, k)).grid(
                row=row, column=col+2, sticky="w", padx=(2, 0))
            self.ammo_vars[key] = (v, max_val, sb)

        ttk.Button(ammo_frame, text="Max All Ammo", command=self.max_ammo).grid(
            row=4, column=0, columnspan=6, sticky="w", pady=(3, 0))

        # =====================================================================
        # COLUMN 2: Upgrades, Capacities & Bottles
        # =====================================================================
        upg_frame = ttk.LabelFrame(col2, text="Upgrades & Capacities", padding=6)
        upg_frame.pack(fill="x", pady=(0, 6))

        capacity_items = [
            ("Strength (Gauntlets):", [g[0] for g in GAUNTLETS], "strength"),
            ("Diving Scale:", [s[0] for s in DIVING_SCALES], "scale"),
            ("Wallet:", [w["label"] for w in WALLETS], "wallet"),
            ("Quiver:", ["None", "Quiver (30)", "Bigger Quiver (40)", "Biggest Quiver (50)"], "quiver"),
            ("Bomb Bag:", ["None", "Bomb Bag (20)", "Bigger Bomb Bag (30)", "Biggest Bomb Bag (40)"], "bomb_bag"),
            ("Deku-Stick Bag:", ["Deku-Stick Bag (10)", "Bigger Deku-Stick Bag (20)", "Biggest Deku-Stick Bag (30)"], "stick_bag"),
            ("Deku-Nut Bag:", ["Deku-Nut Bag (20)", "Bigger Deku-Nut Bag (30)", "Biggest Deku-Nut Bag (40)"], "nut_bag"),
            ("Deku-Seed Bag:", ["Deku-Seed Bag (30)", "Bigger Deku-Seed Bag (40)", "Biggest Deku-Seed Bag (50)"], "bullet_bag"),
        ]

        for idx, (lbl, choices, key) in enumerate(capacity_items):
            ttk.Label(upg_frame, text=lbl).grid(row=idx, column=0, sticky="w", pady=2)
            var = tk.StringVar(value=choices[0])
            box_w = max(len(str(c)) for c in choices) + 2
            box = ttk.Combobox(upg_frame, textvariable=var, state="readonly", width=box_w, values=choices)
            box.grid(row=idx, column=1, sticky="w", padx=(4, 0), pady=2)
            box.bind("<<ComboboxSelected>>", lambda e, k=key: self._on_bag_or_capacity_changed(k))
            self.equip_vars[key] = var

        # Bottles (5 Bottles - Direct Dropdown Unlocking)
        bot_frame = ttk.LabelFrame(col2, text="Bottles (Direct Dropdown Unlocking)", padding=6)
        bot_frame.pack(fill="x", pady=(0, 6))

        bottle_w = max(len(str(c)) for c in BOTTLE_CHOICES) + 2
        for b in range(1, 6):
            ttk.Label(bot_frame, text=f"Bottle {b}:").grid(row=b-1, column=0, sticky="w", pady=2)
            bv = tk.StringVar(value=BOTTLE_CHOICES[0])
            box = ttk.Combobox(bot_frame, textvariable=bv, state="readonly", width=bottle_w, values=BOTTLE_CHOICES)
            box.grid(row=b-1, column=1, sticky="w", padx=(4, 0), pady=2)
            box.bind("<<ComboboxSelected>>", lambda e, b_num=b: self._on_bottle_selected(b_num))
            self.bottle_vars[f"bottle_{b}"] = bv
            self.prev_bottle_selections[f"bottle_{b}"] = BOTTLE_CHOICES[0]

        ttk.Button(bot_frame, text="Fill All with Fairies", command=self.fairies_in_all_bottles).grid(
            row=5, column=0, columnspan=2, sticky="w", pady=(3, 0))

        # =====================================================================
        # COLUMN 3: Dungeon Tools, Spells & Active Mask (FULLY VERTICAL!)
        # =====================================================================
        spec_frame = ttk.LabelFrame(col3, text="Dungeon Tools, Spells & Mask", padding=6)
        spec_frame.pack(fill="both", expand=True)

        # Dungeon Tools (Vertical list)
        ttk.Label(spec_frame, text="Dungeon Tools:", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 2))
        for name, kh, desc in DUNGEON_TOOLS_BASE:
            v = tk.BooleanVar(value=False)
            cb = ttk.Checkbutton(spec_frame, text=name, variable=v)
            cb.pack(anchor="w", pady=1)
            self.special_item_vars[kh] = (v, name)

        # Hookshot Upgrade (Single vertical row)
        hs_row = ttk.Frame(spec_frame)
        hs_row.pack(fill="x", pady=(3, 4))
        ttk.Label(hs_row, text="Hookshot:", font=("Segoe UI", 8, "bold")).pack(side="left", padx=(0, 4))
        hs_w = max(len(str(c)) for c in HOOKSHOT_CHOICES) + 2
        hs_box = ttk.Combobox(hs_row, textvariable=self.hookshot_var, state="readonly", width=hs_w, values=HOOKSHOT_CHOICES)
        hs_box.pack(side="left")

        # Magic Spells & Powers (Vertical list)
        ttk.Label(spec_frame, text="Magic Spells & Powers:", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(4, 2))
        for name, kh, desc in (MAGIC_SPELLS + MAGIC_ARROWS + MAGIC_POWERS):
            v = tk.BooleanVar(value=False)
            cb = ttk.Checkbutton(spec_frame, text=name, variable=v)
            cb.pack(anchor="w", pady=1)
            self.special_item_vars[kh] = (v, name)

        # Active Mask (Vertical row)
        m_row = ttk.Frame(spec_frame)
        m_row.pack(fill="x", pady=(4, 4))
        ttk.Label(m_row, text="Mask:", font=("Segoe UI", 8, "bold")).pack(side="left", padx=(0, 4))
        mask_w = max(len(str(c)) for c in MASK_CHOICES) + 2
        mask_box = ttk.Combobox(m_row, textvariable=self.active_mask_var, state="readonly", width=mask_w, values=MASK_CHOICES)
        mask_box.pack(side="left")

        # Quick Action Buttons
        sp_btns = ttk.Frame(spec_frame)
        sp_btns.pack(fill="x", pady=(4, 0))
        ttk.Button(sp_btns, text="Tools", command=self.unlock_all_weapons_tools, width=6).pack(side="left", padx=(0, 2))
        ttk.Button(sp_btns, text="Spells", command=self.unlock_all_spells, width=6).pack(side="left", padx=2)
        ttk.Button(sp_btns, text="All", command=self.unlock_all_special_items, width=5).pack(side="left", padx=2)

        # Bottom row across full width
        ei_bot = ttk.Frame(ei)
        ei_bot.pack(fill="x", pady=(6, 0))
        self.primary_button(ei_bot, "Max All Equipment & Upgrades", self.max_equipment).pack(side="left")

    def _sync_equipped_options(self):
        for category, combo_key, var_dict, default_val in [
            ("sword", "sword", self.owned_swords, "Kokiri Sword"),
            ("shield", "shield", self.owned_shields, "Deku Shield"),
            ("tunic", "tunic", self.owned_tunics, "Kokiri Tunic"),
            ("boots", "boots", self.owned_boots, "Kokiri Boots"),
        ]:
            available = [name for name, var in var_dict.items() if var.get()]
            if not available:
                available = [default_val]
            combo = self.equipped_combos.get(combo_key)
            if combo:
                combo.configure(values=available)
                cur = self.equip_vars[combo_key].get()
                if cur not in available:
                    self.equip_vars[combo_key].set(available[0])

    def unlock_all_stored_equipment(self):
        for d in (self.owned_swords, self.owned_shields, self.owned_tunics, self.owned_boots):
            for v in d.values():
                v.set(True)
        self._sync_equipped_options()
        self.status.set("Unlocked and stored all weapons, shields, tunics and boots in Link's inventory.")

    def _on_bag_or_capacity_changed(self, key):
        if key == "quiver" and "arrows" in self.ammo_vars:
            q_choice = self.equip_vars["quiver"].get()
            q_cap = 50 if "50" in q_choice else (40 if "40" in q_choice else (30 if "30" in q_choice else 0))
            v, _, sb = self.ammo_vars["arrows"]
            sb.configure(to=max(1, q_cap) if q_cap else 0)
            self.ammo_labels["arrows"][0].set(f"Arrows (Cap {q_cap}):" if q_cap else "Arrows (No Bow):")
            if int(v.get() or 0) > q_cap:
                v.set(str(q_cap))
        elif key == "bomb_bag" and "bombs" in self.ammo_vars:
            bb_choice = self.equip_vars["bomb_bag"].get()
            bb_cap = 40 if "40" in bb_choice else (30 if "30" in bb_choice else (20 if "20" in bb_choice else 0))
            v, _, sb = self.ammo_vars["bombs"]
            sb.configure(to=max(1, bb_cap) if bb_cap else 0)
            self.ammo_labels["bombs"][0].set(f"Bombs (Cap {bb_cap}):" if bb_cap else "Bombs (No Bag):")
            if int(v.get() or 0) > bb_cap:
                v.set(str(bb_cap))
        elif key == "stick_bag" and "sticks" in self.ammo_vars:
            sb_choice = self.equip_vars["stick_bag"].get()
            sb_cap = 30 if "30" in sb_choice else (20 if "20" in sb_choice else 10)
            v, _, sb = self.ammo_vars["sticks"]
            sb.configure(to=sb_cap)
            self.ammo_labels["sticks"][0].set(f"Deku Sticks (Cap {sb_cap}):")
            if int(v.get() or 0) > sb_cap:
                v.set(str(sb_cap))
        elif key == "nut_bag" and "nuts" in self.ammo_vars:
            nb_choice = self.equip_vars["nut_bag"].get()
            nb_cap = 40 if "40" in nb_choice else (30 if "30" in nb_choice else 20)
            v, _, sb = self.ammo_vars["nuts"]
            sb.configure(to=nb_cap)
            self.ammo_labels["nuts"][0].set(f"Deku Nuts (Cap {nb_cap}):")
            if int(v.get() or 0) > nb_cap:
                v.set(str(nb_cap))
        elif key == "bullet_bag" and "seeds" in self.ammo_vars:
            bul_choice = self.equip_vars["bullet_bag"].get()
            bul_cap = 50 if "50" in bul_choice else (40 if "40" in bul_choice else 30)
            v, _, sb = self.ammo_vars["seeds"]
            sb.configure(to=bul_cap)
            self.ammo_labels["seeds"][0].set(f"Deku Seeds (Cap {bul_cap}):")
            if int(v.get() or 0) > bul_cap:
                v.set(str(bul_cap))

    def _on_bottle_selected(self, b_num):
        k = f"bottle_{b_num}"
        cur = self.bottle_vars[k].get()
        prev = self.prev_bottle_selections.get(k, "(Not Acquired / Locked)")
        if "Ruto's Letter" in cur:
            msg = (
                "Ruto's Letter in a bottle can only be used once at the time of opening "
                "the path to Jabu-Jabu's Belly (by presenting it to King Zora).\n\n"
                "Once that conversation is done, the letter is no longer needed. If you have "
                "already moved King Zora, this letter CANNOT be discarded or emptied, "
                "permanently locking this bottle slot!\n\n"
                "Are you sure you want to put Ruto's Letter into this bottle?"
            )
            if not messagebox.askyesno("Ruto's Letter Warning", msg, icon="warning", parent=self):
                self.bottle_vars[k].set(prev)
                return
        self.prev_bottle_selections[k] = self.bottle_vars[k].get()

    def _max_single_ammo(self, var, key):
        if key == "arrows":
            q_choice = self.equip_vars.get("quiver", tk.StringVar(value="Quiver (30)")).get()
            q_cap = 50 if "50" in q_choice else (40 if "40" in q_choice else (30 if "30" in q_choice else 0))
            var.set(str(q_cap))
        elif key == "bombs":
            bb_choice = self.equip_vars.get("bomb_bag", tk.StringVar(value="Bomb Bag (20)")).get()
            bb_cap = 40 if "40" in bb_choice else (30 if "30" in bb_choice else (20 if "20" in bb_choice else 0))
            var.set(str(bb_cap))
        elif key == "sticks":
            sb_choice = self.equip_vars.get("stick_bag", tk.StringVar(value="Deku-Stick Bag (10)")).get()
            sb_cap = 30 if "30" in sb_choice else (20 if "20" in sb_choice else 10)
            var.set(str(sb_cap))
        elif key == "nuts":
            nb_choice = self.equip_vars.get("nut_bag", tk.StringVar(value="Deku-Nut Bag (20)")).get()
            nb_cap = 40 if "40" in nb_choice else (30 if "30" in nb_choice else 20)
            var.set(str(nb_cap))
        elif key == "seeds":
            bul_choice = self.equip_vars.get("bullet_bag", tk.StringVar(value="Deku-Seed Bag (30)")).get()
            bul_cap = 50 if "50" in bul_choice else (40 if "40" in bul_choice else 30)
            var.set(str(bul_cap))
        elif key == "beans":
            var.set("10")
        elif key == "scrub":
            var.set("30")
        elif key == "bombchus":
            var.set("30")

    def unlock_all_weapons_tools(self):
        for name, kh, _ in DUNGEON_TOOLS_BASE:
            if kh in self.special_item_vars:
                self.special_item_vars[kh][0].set(True)
        self.hookshot_var.set("Longshot")
        self.status.set("Unlocked all dungeon weapons & tools (upgraded to Longshot).")

    def unlock_all_spells(self):
        for name, kh, _ in (MAGIC_SPELLS + MAGIC_ARROWS + MAGIC_POWERS):
            if kh in self.special_item_vars:
                self.special_item_vars[kh][0].set(True)
        self.status.set("Unlocked all Great Fairy spells & magic powers.")

    def complete_adult_trade_quest(self):
        self.adult_trade_var.set("Biggoron Receipt")
        self.status.set("Completed Biggoron Sword trade quest (Claim Check / Receipt).")

    def unlock_all_special_items(self):
        self.unlock_all_weapons_tools()
        self.unlock_all_spells()
        self.active_mask_var.set("Mask of Truth")
        self.status.set("Unlocked all weapons, tools, spells, and Mask of Truth.")

    # ---------- TAB 3: Quest Items ----------
    def _build_quest_tab(self, nb):
        qst = ttk.Frame(nb, padding=10)
        nb.add(qst, text="Quest items")

        main_grid = ttk.Frame(qst)
        main_grid.pack(fill="both", expand=True)

        col1 = ttk.Frame(main_grid)
        col1.pack(side="left", fill="both", expand=True, padx=(0, 6))

        col2 = ttk.Frame(main_grid)
        col2.pack(side="left", fill="both", expand=True, padx=4)

        col3 = ttk.Frame(main_grid)
        col3.pack(side="left", fill="both", expand=True, padx=(6, 0))

        # =====================================================================
        # COLUMN 1: Spiritual Stones & Medallions
        # =====================================================================
        sm_frame = ttk.LabelFrame(col1, text="Spiritual Stones & Medallions", padding=8)
        sm_frame.pack(fill="both", expand=True)

        for idx, (name, hash_key, desc) in enumerate(STONES_MEDALLIONS):
            var = tk.BooleanVar(value=False)
            cb = ttk.Checkbutton(sm_frame, text=f"{name} - {desc}", variable=var,
                                 command=lambda hk=hash_key, v=var: self._on_story_item_toggle(hk, v))
            cb.grid(row=idx, column=0, sticky="w", pady=1)
            self.quest_vars[hash_key] = var

        btn_row = ttk.Frame(sm_frame)
        btn_row.grid(row=len(STONES_MEDALLIONS), column=0, sticky="w", pady=(8, 0))
        ttk.Button(btn_row, text="Unlock All Stones & Medallions", command=self.unlock_all_stones).pack(side="left")

        # =====================================================================
        # COLUMN 2: Ocarina Songs (12)
        # =====================================================================
        songs_frame = ttk.LabelFrame(col2, text="Ocarina Songs (12)", padding=8)
        songs_frame.pack(fill="both", expand=True)

        for idx, (sname, bit_idx, isget_h, event_h, sdesc) in enumerate(SONGS):
            svar = tk.BooleanVar(value=False)
            scb = ttk.Checkbutton(songs_frame, text=f"{sname} ({sdesc})", variable=svar)
            scb.grid(row=idx, column=0, sticky="w", pady=1)
            self.song_vars[bit_idx] = svar

        btn_row2 = ttk.Frame(songs_frame)
        btn_row2.grid(row=len(SONGS), column=0, sticky="w", pady=(8, 0))
        ttk.Button(btn_row2, text="Learn All Songs", command=self.learn_all_songs).pack(side="left")

        # =====================================================================
        # COLUMN 3: Quest Sequences & Dungeon Small Keys
        # =====================================================================
        # Quest Sequences
        seq_frame = ttk.LabelFrame(col3, text="Quest & Trading Sequences", padding=8)
        seq_frame.pack(fill="x", pady=(0, 6))

        ttk.Label(seq_frame, text="Child Quest Item:", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 1))
        child_hint = ttk.Label(seq_frame, text="(Link carries one child item/mask at a time)", style="Faint.TLabel", wraplength=280)
        child_hint.grid(row=1, column=0, sticky="w", pady=(0, 2))
        self.child_quest_combo = ttk.Combobox(seq_frame, textvariable=self.child_quest_var, state="readonly",
                                              values=CHILD_QUEST_CHOICES, width=28)
        self.child_quest_combo.grid(row=2, column=0, sticky="w", pady=(0, 6))

        ttk.Label(seq_frame, text="Adult Trading Sequence (Biggoron):", font=("Segoe UI", 9, "bold")).grid(row=3, column=0, sticky="w", pady=(0, 1))
        trade_hint = ttk.Label(seq_frame, text="(Sequential trade items from Pocket Egg to Claim Check)", style="Faint.TLabel", wraplength=280)
        trade_hint.grid(row=4, column=0, sticky="w", pady=(0, 2))
        self.adult_trade_combo = ttk.Combobox(seq_frame, textvariable=self.adult_trade_var, state="readonly",
                                              values=ADULT_TRADE_CHOICES, width=30)
        self.adult_trade_combo.grid(row=5, column=0, sticky="w", pady=(0, 4))

        def _update_seq_wraplength(event):
            w = max(180, event.width - 20)
            child_hint.configure(wraplength=w)
            trade_hint.configure(wraplength=w)

        seq_frame.bind("<Configure>", _update_seq_wraplength)

        seq_btns = ttk.Frame(seq_frame)
        seq_btns.grid(row=6, column=0, sticky="w", pady=(2, 0))
        ttk.Button(seq_btns, text="Complete Adult Trade Quest", command=self.complete_adult_trade_quest).pack(side="left")

        # Dungeon Small Keys (laid out one key per row so every tab fits without cut-offs)
        keys_frame = ttk.LabelFrame(col3, text="Dungeon Small Keys", padding=6)
        keys_frame.pack(fill="both", expand=True)

        for idx, k in enumerate(SMALL_KEYS):
            ttk.Label(keys_frame, text=f"{k['label']}:").grid(row=idx, column=0, sticky="w", pady=1)
            v = tk.StringVar(value="0")
            sb = ttk.Spinbox(keys_frame, from_=0, to=k["max"], textvariable=v, width=3)
            sb.grid(row=idx, column=1, sticky="w", padx=4, pady=1)
            ttk.Button(keys_frame, text=f"Max ({k['max']})", width=7, command=lambda var=v, m=k["max"]: var.set(str(m))).grid(
                row=idx, column=2, sticky="w", pady=1)
            self.key_vars[k["id"]] = (v, k["max"], sb, k["stock"], k["label"])

        key_btn_row = ttk.Frame(keys_frame)
        key_btn_row.grid(row=len(SMALL_KEYS), column=0, columnspan=3, sticky="w", pady=(6, 0))
        ttk.Button(key_btn_row, text="Max All Dungeon Keys", command=self.max_keys).pack(side="left")

    def max_keys(self):
        for k in SMALL_KEYS:
            if k["id"] in self.key_vars:
                self.key_vars[k["id"]][0].set(str(k["max"]))
        self.status.set("Maxed all dungeon small keys (not saved yet).")

    # ---------- TAB 4: Progress & Inspector ----------
    def _build_progress_inspector_tab(self, nb):
        pi = ttk.Frame(nb, padding=8)
        nb.add(pi, text="Progress & Inspector")

        sub_nb = ttk.Notebook(pi)
        sub_nb.pack(fill="both", expand=True)
        self.progress_sub_nb = sub_nb

        self._build_story_progress_subtab(sub_nb)
        self._build_progress_flags_subtab(sub_nb)
        self._build_field_inspector_subtab(sub_nb)
        sub_nb.select(0)

    def _build_story_progress_subtab(self, sub_nb):
        story_frame = ttk.Frame(sub_nb, padding=8)
        sub_nb.add(story_frame, text="Story Progress")

        prog_box = ttk.LabelFrame(story_frame, text="Main Storyline Progression", padding=8)
        prog_box.pack(fill="both", expand=True)

        cols = ("chapter", "dungeon", "status")
        self.walk_tree = ttk.Treeview(prog_box, columns=cols, show="headings", height=10)
        self.walk_tree.heading("chapter", text="Chapter", anchor="w")
        self.walk_tree.heading("dungeon", text="Main Objective & Boss", anchor="w")
        self.walk_tree.heading("status", text="Save Status", anchor="center")

        self.walk_tree.column("chapter", width=120, stretch=False)
        self.walk_tree.column("dungeon", width=500)
        self.walk_tree.column("status", width=160, anchor="center")
        self.walk_tree.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(prog_box, orient="vertical", command=self.walk_tree.yview)
        sb.pack(side="right", fill="y")
        self.walk_tree.configure(yscrollcommand=sb.set)
        return story_frame

    def _build_progress_flags_subtab(self, sub_nb):
        f_frame = ttk.Frame(sub_nb, padding=8)
        sub_nb.add(f_frame, text="Progress Flags")

        top = ttk.Frame(f_frame)
        top.pack(fill="x", pady=(0, 6))

        ttk.Label(top, text="Search:").pack(side="left", padx=(0, 4))
        e_search = ttk.Entry(top, textvariable=self.flag_search_var, width=22)
        e_search.pack(side="left", padx=(0, 8))
        e_search.bind("<KeyRelease>", lambda e: self.populate_flags())

        ttk.Label(top, text="Category:").pack(side="left", padx=(0, 4))
        c_cat = ttk.Combobox(top, textvariable=self.flag_category_var, state="readonly", width=18,
                             values=["All Categories", "Events & Cutscenes", "Dialogue & Navi Hints", "Other Flags"])
        c_cat.pack(side="left", padx=(0, 8))
        c_cat.bind("<<ComboboxSelected>>", lambda e: self.populate_flags())

        ttk.Label(top, text="Status:").pack(side="left", padx=(0, 4))
        c_stat = ttk.Combobox(top, textvariable=self.flag_status_var, state="readonly", width=16,
                              values=["All States", "Set in Save (True)", "Unset in Save (False)", "Changed / Pending"])
        c_stat.pack(side="left", padx=(0, 8))
        c_stat.bind("<<ComboboxSelected>>", lambda e: self.populate_flags())

        ttk.Button(top, text="Toggle Flag", command=self.toggle_selected_flag).pack(side="left", padx=2)
        ttk.Button(top, text="Revert Flag", command=self.revert_selected_flag).pack(side="left", padx=2)
        ttk.Button(top, text="Reset All", command=self.reset_all_flags).pack(side="left", padx=2)

        ttk.Label(top, textvariable=self.flag_count_lbl, style="Muted.TLabel").pack(side="right")

        tree_frame = ttk.Frame(f_frame)
        tree_frame.pack(fill="both", expand=True)

        cols = ("name", "hash", "initial", "current", "category")
        self.flag_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=16)
        self.flag_tree.heading("name", text="Flag Name", anchor="w", command=lambda: self.sort_by(self.flag_tree, "name"))
        self.flag_tree.heading("hash", text="MurmurHash3", anchor="center", command=lambda: self.sort_by(self.flag_tree, "hash"))
        self.flag_tree.heading("initial", text="Initial in Save", anchor="center", command=lambda: self.sort_by(self.flag_tree, "initial"))
        self.flag_tree.heading("current", text="Current Value", anchor="center", command=lambda: self.sort_by(self.flag_tree, "current"))
        self.flag_tree.heading("category", text="Category", anchor="center", command=lambda: self.sort_by(self.flag_tree, "category"))

        self.flag_tree.column("name", width=420)
        self.flag_tree.column("hash", width=110, anchor="center")
        self.flag_tree.column("initial", width=110, anchor="center")
        self.flag_tree.column("current", width=110, anchor="center")
        self.flag_tree.column("category", width=110, anchor="center")
        self.flag_tree.pack(side="left", fill="both", expand=True)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.flag_tree.yview)
        vsb.pack(side="right", fill="y")
        self.flag_tree.configure(yscrollcommand=vsb.set)

        self.flag_tree.bind("<Double-1>", lambda e: self.toggle_selected_flag())

    def _build_field_inspector_subtab(self, sub_nb):
        i_frame = ttk.Frame(sub_nb, padding=8)
        sub_nb.add(i_frame, text="Field Inspector (READ ONLY)")

        top = ttk.Frame(i_frame)
        top.pack(fill="x", pady=(0, 6))

        ttk.Label(top, text="Search:").pack(side="left", padx=(0, 4))
        e_search = ttk.Entry(top, textvariable=self.inspector_search_var, width=22)
        e_search.pack(side="left", padx=(0, 8))
        e_search.bind("<KeyRelease>", lambda e: self.populate_inspector())

        cb_named = ttk.Checkbutton(top, text="Named fields only", variable=self.inspector_only_named_var,
                                   command=self.populate_inspector)
        cb_named.pack(side="left", padx=(0, 8))

        ttk.Label(top, text="Type:").pack(side="left", padx=(0, 4))
        type_values = ["All Types"] + CATALOG.get("types", [])
        c_type = ttk.Combobox(top, textvariable=self.inspector_type_var, state="readonly", width=14,
                              values=type_values)
        c_type.pack(side="left", padx=(0, 8))
        c_type.bind("<<ComboboxSelected>>", lambda e: self.populate_inspector())

        ttk.Label(top, textvariable=self.inspector_count_lbl, style="Muted.TLabel").pack(side="right")

        tree_frame = ttk.Frame(i_frame)
        tree_frame.pack(fill="both", expand=True)

        cols = ("name", "hash", "type", "value")
        self.inspector_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=16)
        self.inspector_tree.heading("name", text="Field Name", anchor="w", command=lambda: self.sort_by(self.inspector_tree, "name"))
        self.inspector_tree.heading("hash", text="MurmurHash3", anchor="center", command=lambda: self.sort_by(self.inspector_tree, "hash"))
        self.inspector_tree.heading("type", text="Type", anchor="center", command=lambda: self.sort_by(self.inspector_tree, "type"))
        self.inspector_tree.heading("value", text="Current Value (Read-Only)", anchor="w", command=lambda: self.sort_by(self.inspector_tree, "value"))

        self.inspector_tree.column("name", width=380)
        self.inspector_tree.column("hash", width=120, anchor="center")
        self.inspector_tree.column("type", width=110, anchor="center")
        self.inspector_tree.column("value", width=360)
        self.inspector_tree.pack(side="left", fill="both", expand=True)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.inspector_tree.yview)
        vsb.pack(side="right", fill="y")
        self.inspector_tree.configure(yscrollcommand=vsb.set)

    def _get_flag_category(self, name):
        if name.startswith("HavePlayedEvent."):
            return "event"
        elif any(name.startswith(p) for p in ("HaveTalked", "HavePlayedNavi", "HaveTalk")):
            return "talk"
        return "other"

    def populate_flags(self):
        if not self.flag_tree:
            return
        self.flag_tree.delete(*self.flag_tree.get_children())
        if not self.active_slot:
            self.flag_count_lbl.set("0 flags")
            return

        search = self.flag_search_var.get().strip().lower()
        cat_filter = self.flag_category_var.get()
        cat_key = "event" if "Event" in cat_filter else ("talk" if "Talk" in cat_filter else ("other" if "Other" in cat_filter else "all"))
        status_filter = self.flag_status_var.get()
        stat_key = "set" if "Set in" in status_filter else ("unset" if "Unset in" in status_filter else ("changed" if "Changed" in status_filter else "all"))

        s = self.active_slot
        types = CATALOG.get("types", [])
        fields = CATALOG.get("fields", [])

        visible_count = 0
        changed_count = len(self.flag_changes)

        for item in fields:
            h = item[0]
            tid = item[1]
            name = item[2] if len(item) > 2 else ""
            if not name or tid >= len(types) or types[tid] != "Bool" or h not in s.p_fields:
                continue

            orig_val = bool(s.get(h, 0))
            cur_val = self.flag_changes.get(h, orig_val)
            cat = self._get_flag_category(name)

            if search:
                h_hex = f"0x{h:08X}".lower()
                if search not in name.lower() and search not in h_hex:
                    continue

            if cat_key != "all" and cat != cat_key:
                continue

            if stat_key == "set" and not cur_val:
                continue
            elif stat_key == "unset" and cur_val:
                continue
            elif stat_key == "changed" and h not in self.flag_changes:
                continue

            is_changed = (h in self.flag_changes)
            tags = ("changed",) if is_changed else (("on",) if cur_val else ("off",))
            cat_label = "Event" if cat == "event" else ("Talk" if cat == "talk" else "Other")

            self.flag_tree.insert(
                "", "end", iid=str(h),
                values=(name, f"0x{h:08X}", "Set (True)" if orig_val else "Unset (False)",
                        "Set (True)" if cur_val else "Unset (False)", cat_label),
                tags=tags
            )
            visible_count += 1

        self.flag_count_lbl.set(f"{visible_count} flags displayed ({changed_count} edited)")

    def toggle_selected_flag(self):
        if not self.flag_tree or not self.active_slot:
            return
        sel = list(self.flag_tree.selection())
        if not sel:
            return
        for item_id in sel:
            try:
                h = int(item_id)
            except ValueError:
                continue
            orig_val = bool(self.active_slot.get(h, 0))
            cur_val = self.flag_changes.get(h, orig_val)
            new_val = not cur_val
            if new_val == orig_val:
                self.flag_changes.pop(h, None)
            else:
                self.flag_changes[h] = new_val
        self.populate_flags()
        valid_sel = [i for i in sel if self.flag_tree.exists(i)]
        if valid_sel:
            self.flag_tree.selection_set(valid_sel)

    def revert_selected_flag(self):
        if not self.flag_tree:
            return
        sel = list(self.flag_tree.selection())
        if not sel:
            return
        for item_id in sel:
            try:
                h = int(item_id)
            except ValueError:
                continue
            self.flag_changes.pop(h, None)
        self.populate_flags()
        valid_sel = [i for i in sel if self.flag_tree.exists(i)]
        if valid_sel:
            self.flag_tree.selection_set(valid_sel)

    def reset_all_flags(self):
        if not self.flag_changes:
            return
        if messagebox.askyesno("Reset Flags", "Revert all modified progress flags back to original save state?", parent=self):
            self.flag_changes.clear()
            self.populate_flags()

    def populate_inspector(self):
        if not self.inspector_tree:
            return
        self.inspector_tree.delete(*self.inspector_tree.get_children())
        if not self.active_slot:
            self.inspector_count_lbl.set("0 fields")
            return

        search = self.inspector_search_var.get().strip().lower()
        only_named = self.inspector_only_named_var.get()
        type_filter = self.inspector_type_var.get()

        s = self.active_slot
        types = CATALOG.get("types", [])
        fields = CATALOG.get("fields", [])

        visible_count = 0
        max_rows = 1500

        for item in fields:
            h = item[0]
            tid = item[1]
            name = item[2] if len(item) > 2 else ""
            t_name = types[tid] if tid < len(types) else "Unknown"

            if only_named and not name:
                continue

            if type_filter != "All Types" and t_name != type_filter:
                continue

            display_name = name or f"0x{h:08X}"
            h_hex = f"0x{h:08X}"

            if search:
                if search not in display_name.lower() and search not in h_hex.lower() and search not in t_name.lower():
                    continue

            val_str = self.format_field_value(s, h, t_name)
            if search and search not in display_name.lower() and search not in h_hex.lower() and search not in t_name.lower():
                if search not in val_str.lower():
                    continue

            self.inspector_tree.insert(
                "", "end",
                values=(display_name, h_hex, t_name, val_str)
            )
            visible_count += 1
            if not search and visible_count >= max_rows:
                break

        total_fields = len(fields)
        if visible_count >= max_rows and not search:
            self.inspector_count_lbl.set(f"Showing first {visible_count} of {total_fields} fields (type search to filter)")
        else:
            self.inspector_count_lbl.set(f"{visible_count} of {total_fields} fields displayed")

    def format_field_value(self, s, h, t_name):
        if h not in s.p_fields:
            return "<not in progress.sav>"
        val_off = s.p_fields[h]
        raw_u32 = struct.unpack_from("<I", s.p_bytes, val_off)[0]
        raw_i32 = struct.unpack_from("<i", s.p_bytes, val_off)[0]

        if t_name == "Bool":
            return "true" if raw_u32 == 1 else ("false" if raw_u32 == 0 else f"0x{raw_u32:08X}")
        elif t_name == "Int":
            return str(raw_i32)
        elif t_name == "UInt":
            return str(raw_u32)
        elif t_name == "Float":
            f_val = struct.unpack_from("<f", s.p_bytes, val_off)[0]
            return f"{f_val:.4f}"
        elif t_name in ("Enum", "Unknown"):
            return f"0x{raw_u32:08X}"
        elif t_name in ("String32", "String64"):
            length = 32 if t_name == "String32" else 64
            off = raw_u32
            if off < HEADER_END_PROGRESS or off > len(s.p_bytes) - length:
                return f"Offset 0x{raw_u32:08X}"
            chunk = s.p_bytes[off:off+length]
            nul = chunk.find(b"\x00")
            if nul >= 0:
                chunk = chunk[:nul]
            return chunk.decode("utf-8", errors="replace") or '""'
        elif t_name == "Vector3":
            off = raw_u32
            if off < HEADER_END_PROGRESS or off > len(s.p_bytes) - 12:
                return f"Offset 0x{raw_u32:08X}"
            x, y, z = struct.unpack_from("<3f", s.p_bytes, off)
            return f"({x:.2f}, {y:.2f}, {z:.2f})"
        elif "Array" in t_name:
            off = raw_u32
            if off < HEADER_END_PROGRESS or off > len(s.p_bytes) - 4:
                return f"Array at 0x{raw_u32:08X}"
            arr_size = struct.unpack_from("<I", s.p_bytes, off)[0]
            stride = 8 if "64" in t_name else 4
            vals = []
            for i in range(min(arr_size, 6)):
                item_off = off + 4 + i * stride
                if item_off + stride <= len(s.p_bytes):
                    if "Float" in t_name:
                        fv = struct.unpack_from("<f", s.p_bytes, item_off)[0]
                        vals.append(f"{fv:.2f}")
                    elif "Int" in t_name:
                        iv = struct.unpack_from("<i", s.p_bytes, item_off)[0]
                        vals.append(str(iv))
                    elif "Bool" in t_name:
                        bv = (struct.unpack_from("<I", s.p_bytes, off + 4 + 4 * (i // 32))[0] >> (i % 32)) & 1
                        vals.append(str(bool(bv)))
                    else:
                        uv = struct.unpack_from("<I", s.p_bytes, item_off)[0]
                        vals.append(f"0x{uv:X}")
            preview = ", ".join(vals)
            if arr_size > len(vals):
                preview += ", ..."
            return f"{t_name} (size {arr_size}) [{preview}]"
        elif t_name == "Binary":
            off = raw_u32
            if off < HEADER_END_PROGRESS or off > len(s.p_bytes) - 4:
                return f"Binary at 0x{raw_u32:08X}"
            bin_size = struct.unpack_from("<I", s.p_bytes, off)[0]
            return f"Binary ({bin_size} bytes)"
        return f"0x{raw_u32:08X}"

    def _on_story_item_toggle(self, key_hash, var):
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
                var.set(not want)
                return
        else:
            self.refresh_walkthrough()

    # ---------- TAB 5: Guides ----------
    def _build_guides_tab(self, nb):
        from oot_guides import GuidesFrame
        self.guides_frame = GuidesFrame(nb, self, app_dir=USER_DATA_DIR)
        nb.add(self.guides_frame, text="Guides")

    # ---------- TAB 6: Cheats ----------
    def _build_cheats_tab(self, nb):
        cht = ttk.Frame(nb, padding=12)
        nb.add(cht, text="Cheats")

        self.cheat_warn = tk.StringVar(value="")
        ttk.Label(cht, textvariable=self.cheat_warn, style="Warn.TLabel", wraplength=850).pack(anchor="w", pady=(0, 6))

        cols = ("toggle", "name", "desc", "tested")
        self.cheat_tree = self._make_tree(cht, cols, height=12)
        self.cheat_tree.heading("toggle", text="", anchor="center")
        self.cheat_tree.heading("name", text="Cheat", anchor="w")
        self.cheat_tree.heading("desc", text="Description", anchor="w")
        self.cheat_tree.heading("tested", text="Compatibility", anchor="w")
        self.cheat_tree.column("toggle", width=36, stretch=False, anchor="center")
        self.cheat_tree.column("name", width=220)
        self.cheat_tree.column("desc", width=420)
        self.cheat_tree.column("tested", width=160)
        self.cheat_tree.bind("<Double-1>", lambda e: self.toggle_cheats())
        self.cheat_tree.bind("<space>", lambda e: self.toggle_cheats())

        row = ttk.Frame(cht)
        row.pack(fill="x", pady=(8, 0))
        self.primary_button(row, "Install to emulator", self.install_cheats).pack(side="left")
        ttk.Button(row, text="Uninstall from emulator", command=self.uninstall_cheats).pack(side="left", padx=4)
        ttk.Button(row, text="Export for real Switch 2...", command=self.export_cheats).pack(side="left")
        ttk.Button(row, text="Open cheat folder", command=self.open_cheat_folder).pack(side="left", padx=4)
        ttk.Button(row, text="Cheat guide & help", command=self.show_cheat_guide).pack(side="right")

    def _make_tree(self, parent, columns, row=None, height=10):
        frame = ttk.Frame(parent)
        if row is not None:
            frame.grid(row=row, column=0, columnspan=2, sticky="nsew", pady=4)
        else:
            frame.pack(fill="both", expand=True)
        tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse", height=height)
        tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        sb.pack(side="right", fill="y")
        tree.configure(yscrollcommand=sb.set)
        for col in columns:
            tree.heading(col, text=col.capitalize(), command=lambda c=col: self.sort_by(tree, c))
        return tree

    # ---------- Save File Loading & Refreshing ----------
    def set_folder(self, folder):
        self.root_dir.set(folder or "")
        if folder:
            self.settings["save_folder"] = folder
            store_settings(self.settings)
        self.emulator = emulator_for(folder)
        self.refresh_slots()
        self.update_backup_count()
        self.detect_cheat_target()

    def browse(self):
        f = filedialog.askdirectory(title="Choose Ocarina of Time save directory", parent=self,
                                    initialdir=self.root_dir.get() or None)
        if f:
            res = resolve_save_folder(f) or f
            self.set_folder(res)

    def redetect(self):
        found = autodetect()
        if found:
            self.set_folder(found)
            self.status.set(f"Detected: {found}")
        else:
            messagebox.showinfo("Not found", "Could not automatically locate Ocarina of Time save files.")

    def refresh_slots(self):
        f = self.root_dir.get()
        if not f or not os.path.isdir(f):
            return
        slot_infos = []
        for sname in sorted(os.listdir(f)):
            sdir = os.path.join(f, sname)
            prog = os.path.join(sdir, "progress.sav")
            cap = os.path.join(sdir, "caption.sav")
            if os.path.isdir(sdir) and os.path.exists(prog) and os.path.exists(cap):
                try:
                    mtime = max(os.path.getmtime(prog), os.path.getmtime(cap))
                    dt = datetime.fromtimestamp(mtime)
                    with open(cap, "rb") as cf:
                        cdata = cf.read()
                    c_entries = {}
                    for off in range(40, min(len(cdata), HEADER_END_CAPTION), 8):
                        k, v = struct.unpack_from("<II", cdata, off)
                        c_entries[k] = v
                    rup = c_entries.get(KEY_PREVIEW_RUPEES, 0)
                    max_h = c_entries.get(HASH_CAPT_MAX_HEARTS, 36) // 4
                    cur_h = c_entries.get(HASH_CAPT_HEARTS, max_h * 4) / 4.0
                    tok = 0
                    try:
                        with open(prog, "rb") as pf:
                            pdata = pf.read(min(os.path.getsize(prog), HEADER_END_PROGRESS))
                        for p_off in range(40, len(pdata), 8):
                            pk, pv = struct.unpack_from("<II", pdata, p_off)
                            if pk == 0x04735978:
                                tok = pv
                                break
                    except Exception:
                        pass
                    slot_infos.append({
                        "slot": sname,
                        "mtime": mtime,
                        "dt_str": dt.strftime("%b %d, %I:%M %p"),
                        "tokens": tok,
                        "rupees": rup,
                        "hearts": cur_h,
                        "max_hearts": max_h
                    })
                except Exception:
                    pass

        slot_infos.sort(key=lambda x: x["mtime"], reverse=True)
        self.slot_names = [info["slot"] for info in slot_infos]
        display_names = []
        for i, info in enumerate(slot_infos):
            slot_num = i + 1
            if i == 0:
                s_label = f"Slot {slot_num} [The latest]"
            elif i == len(slot_infos) - 1:
                s_label = f"Slot {slot_num} [The Oldest]"
            else:
                s_label = f"Slot {slot_num}"
            active_tag = " (Active)" if i == 0 else ""
            display_names.append(
                f"{s_label} - [{info['slot']}] {info['dt_str']} [{info['hearts']}/{info['max_hearts']} Hearts, {info['tokens']} Tokens, {info['rupees']}R]{active_tag}"
            )
        self.slot_box.configure(values=display_names)
        if slot_infos:
            self.slot_box.current(0)
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
        rupees = s.get(KEY_RUPEES, s.get_c(KEY_PREVIEW_RUPEES, 0))
        self.v_rupees.set(str(rupees))

        tokens = s.get(0x04735978, 0)
        self.v_tokens.set(str(tokens))

        # Hearts and Health
        max_h = s.get(HASH_PROG_MAX_HEARTS, s.get_c(HASH_CAPT_MAX_HEARTS, 36)) // 4
        max_h = max(3, min(20, max_h))
        self.v_hearts.set(str(max_h))

        held_pieces = s.get(0x51EC97B3, 0) # 0 to 3
        held_pieces = max(0, min(3, held_pieces))
        self.v_heart_pieces_held.set(str(held_pieces))

        # Calculate boss containers and total heart pieces from total hearts
        # User starts with 3 hearts. Max hearts = 3 + boss_containers + (total_pieces // 4)
        # In OoT, boss containers are up to 8. Pieces are up to 36.
        # Estimate:
        containers_earned = max_h - 3
        boss_containers = max(0, min(8, containers_earned // 2 if containers_earned > 2 else containers_earned))
        if max_h == 9:
            boss_containers = 3  # exactly 3 boss containers (Deku Tree, Dodongo, Jabu-Jabu)
        self.v_boss_containers.set(str(boss_containers))

        hearts_from_pieces = max_h - 3 - boss_containers
        total_pieces = hearts_from_pieces * 4 + held_pieces
        self.v_heart_pieces_total.set(str(total_pieces))
        self.v_hearts_from_pieces.set(str(hearts_from_pieces))

        cur_hp = s.get(HASH_PROG_HEARTS, s.get_c(HASH_CAPT_HEARTS, max_h * 4))
        cur_hp = max(1, min(max_h * 4, cur_hp))
        self.v_hp.set(str(cur_hp))
        self._update_hp_display()

        # Magic Meter & Double Defense
        max_mp_stored = s.get(HASH_PROG_MAX_MAGIC, s.get_c(HASH_CAPT_MAX_MAGIC, 0)) // 10
        cur_mp_stored = s.get(HASH_PROG_MAGIC, s.get_c(HASH_CAPT_MAGIC, 0)) / 10.0
        if max_mp_stored >= 48:
            self.v_magic.set("Double Magic Meter (48 MP)")
            self.v_magic_points.set(str(int(cur_mp_stored)))
        elif max_mp_stored >= 24:
            self.v_magic.set("Standard Magic Meter (24 MP)")
            self.v_magic_points.set(str(int(cur_mp_stored)))
        else:
            self.v_magic.set("None")
            self.v_magic_points.set("0")
        self._update_magic_display()

        self.v_double_defense.set(bool(s.get(BLESSING_DEFENSE_DOUBLE, 0)))

        # Populate Owned Equipment
        for s_name, kh, _ in SWORDS:
            if s_name in self.owned_swords:
                self.owned_swords[s_name].set(bool(s.get(kh, 0)) or (s_name == "Kokiri Sword"))

        for sh_name, kh, _ in SHIELDS:
            if sh_name in self.owned_shields:
                self.owned_shields[sh_name].set(bool(s.get(kh, 0)))

        for t_name, kh, _ in TUNICS:
            if t_name in self.owned_tunics:
                self.owned_tunics[t_name].set(bool(s.get(kh, 0)) or (t_name == "Kokiri Tunic"))

        for b_name, kh, _ in BOOTS:
            if b_name in self.owned_boots:
                self.owned_boots[b_name].set(bool(s.get(kh, 0)) or (b_name == "Kokiri Boots"))

        # Equipped Gear
        eq_sw = s.get_string(HASH_SWORD_SLOT, 64)
        if "Master" in eq_sw: sw = "Master Sword"
        elif "Biggoron" in eq_sw: sw = "Biggoron's Sword"
        else: sw = "Kokiri Sword"
        self.equip_vars["sword"].set(sw)

        eq_sh = s.get_string(HASH_SHIELD_SLOT, 64)
        if "Mirror" in eq_sh: sh = "Mirror Shield"
        elif "Hylian" in eq_sh: sh = "Hylian Shield"
        elif "Deku" in eq_sh: sh = "Deku Shield"
        else: sh = "Deku Shield"
        self.equip_vars["shield"].set(sh)

        self.equip_vars["tunic"].set("Kokiri Tunic")
        self.equip_vars["boots"].set("Kokiri Boots")
        self._sync_equipped_options()

        # Upgrades & Capacities
        wallet_str = s.get_string(KEY_WALLET, 64)
        matched_w = next((w["label"] for w in WALLETS if w["id"] == wallet_str), WALLETS[1]["label"])
        self.equip_vars["wallet"].set(matched_w)

        # Quiver
        q_cap = s.get(0x418DB791, 0)
        q_label = "Biggest Quiver (50)" if q_cap >= 50 else ("Bigger Quiver (40)" if q_cap >= 40 else ("Quiver (30)" if q_cap >= 30 else "None"))
        self.equip_vars["quiver"].set(q_label)

        # Bomb Bag
        bb_cap = s.get(0xE753508B, 0)
        bb_label = "Biggest Bomb Bag (40)" if bb_cap >= 40 else ("Bigger Bomb Bag (30)" if bb_cap >= 30 else ("Bomb Bag (20)" if bb_cap >= 20 else "None"))
        self.equip_vars["bomb_bag"].set(bb_label)

        # Stick Bag
        stk_cap = s.get(0x457616B0, 0)
        stk_label = "Biggest Deku-Stick Bag (30)" if stk_cap >= 30 else ("Bigger Deku-Stick Bag (20)" if stk_cap >= 20 else "Deku-Stick Bag (10)")
        self.equip_vars["stick_bag"].set(stk_label)

        # Nut Bag
        nut_cap = s.get(0x735B00F7, 0)
        nut_label = "Biggest Deku-Nut Bag (40)" if nut_cap >= 40 else ("Bigger Deku-Nut Bag (30)" if nut_cap >= 30 else "Deku-Nut Bag (20)")
        self.equip_vars["nut_bag"].set(nut_label)

        # Bullet Bag (Seeds)
        bul_cap = s.get(0xAE8CC742, 0)
        bul_label = "Biggest Deku-Seed Bag (50)" if bul_cap >= 50 else ("Bigger Deku-Seed Bag (40)" if bul_cap >= 40 else "Deku-Seed Bag (30)")
        self.equip_vars["bullet_bag"].set(bul_label)

        # Strength Gauntlets
        if s.get(0x40AE1183, 0) == 1: st = "Golden Gauntlets"
        elif s.get(0x0012B8C0, 0) == 1: st = "Silver Gauntlets"
        elif s.get(0xD1317941, 0) == 1: st = "Goron's Bracelet"
        else: st = "None"
        self.equip_vars["strength"].set(st)

        # Diving Scale
        if s.get(0x4AEB140A, 0) == 1: sc = "Golden Scale (8 meters)"
        elif s.get(0x1240044B, 0) == 1: sc = "Silver Scale (6 meters)"
        else: sc = "Default (1 meter)"
        self.equip_vars["scale"].set(sc)

        for k in ("quiver", "bomb_bag", "stick_bag", "nut_bag", "bullet_bag"):
            self._on_bag_or_capacity_changed(k)

        # Supplies / Ammo
        self.ammo_vars["arrows"][0].set(str(s.get(0x518EC74B, 0)))
        self.ammo_vars["bombs"][0].set(str(s.get(0xDB1BCD4F, 0)))
        self.ammo_vars["bombchus"][0].set(str(s.get(0xDF7C517A, 0)))
        self.ammo_vars["seeds"][0].set(str(s.get(0x5FADF7FC, 0)))
        self.ammo_vars["sticks"][0].set(str(s.get(0xB9494411, 0)))
        self.ammo_vars["nuts"][0].set(str(s.get(0xF30D9F54, 0)))
        self.ammo_vars["beans"][0].set(str(max(0, min(10, s.get(0xB003124D, 0)))))
        self.ammo_vars["scrub"][0].set(str(max(0, min(30, s.get(0x600E29EB, 0)))))

        # Bottles (5 Bottle Slots - Direct Dropdown Unlocking)
        for idx, (stk_h, val_h, cnt_h) in enumerate(BOTTLE_SLOTS, 1):
            stk = s.get(stk_h, 0)
            cnt = s.get_u32(cnt_h, EMPTY_BOTTLE)
            if stk == 0:
                name = "(Not Acquired / Locked)"
            else:
                name = BOTTLE_ID_TO_NAME.get(cnt, "Empty Bottle")
            if f"bottle_{idx}" in self.bottle_vars:
                self.bottle_vars[f"bottle_{idx}"].set(name)
                self.prev_bottle_selections[f"bottle_{idx}"] = name

        # Weapons, Tools & Spells
        all_inv_items = DUNGEON_TOOLS_BASE + MAGIC_SPELLS + MAGIC_ARROWS + MAGIC_POWERS
        for name, kh, _ in all_inv_items:
            if kh in self.special_item_vars:
                v, _ = self.special_item_vars[kh]
                v.set(bool(s.get(kh, 0)))

        # Hookshot Upgrade (mutually exclusive)
        if s.get(0x8499EA34, 0) == 1:
            self.hookshot_var.set("Longshot")
        elif s.get(0x8573D2CD, 0) == 1:
            self.hookshot_var.set("Hookshot")
        else:
            self.hookshot_var.set("None")

        # Active Mask (Happy Mask Shop)
        active_m = "None"
        for mname, (mhash, mactor) in MASK_MAP.items():
            if s.get(mhash, 0) == 1:
                active_m = mname
                break
        if active_m == "None":
            eq_mask_str = s.get_string(HASH_MASK_SLOT, 64)
            for mname, (mhash, mactor) in MASK_MAP.items():
                if mactor and mactor in eq_mask_str:
                    active_m = mname
                    break
        self.active_mask_var.set(active_m)

        # Child Quest Item (single active)
        if s.get(0x6BE5C3B0, 0) == 1:
            self.child_quest_var.set("Zelda's Letter")
        elif s.get(0x24596E8E, 0) == 1:
            self.child_quest_var.set("Weird Egg")
        else:
            self.child_quest_var.set("None")

        # Adult Trading Sequence (single active)
        found_trade = "None"
        for tname, thash in ADULT_TRADE_MAP.items():
            if s.get(thash, 0) == 1:
                found_trade = tname
                break
        self.adult_trade_var.set(found_trade)

        # Dungeon Small Keys
        for k in SMALL_KEYS:
            if k["id"] in self.key_vars:
                val = s.get(k["stock"], 0)
                self.key_vars[k["id"]][0].set(str(max(0, min(k["max"], val))))

        # Spiritual Stones & Medallions
        for _, kh, _ in STONES_MEDALLIONS:
            if kh in self.quest_vars:
                self.quest_vars[kh].set(bool(s.get(kh, 0)))

        # Songs (12-bit bitfield at 0x628BE485)
        song_mask = s.get(HASH_SONG_MASK, 0)
        for idx, (sname, bit_idx, isget_h, event_h, _) in enumerate(SONGS):
            learned = bool(song_mask & (1 << bit_idx))
            if bit_idx in self.song_vars:
                self.song_vars[bit_idx].set(learned)

        # Clear pending flag changes and populate Progress Flags & Field Inspector
        self.flag_changes.clear()
        self.populate_flags()
        self.populate_inspector()

        self.refresh_walkthrough()
        if hasattr(self, "guides_frame") and self.guides_frame:
            self.guides_frame.on_slot_changed()

        held = total_pieces % 4
        needed = 4 - held if held > 0 else 4
        self.gen_info.set(
            f"Location: {s.map_name}\n"
            f"Health: {cur_hp / 4.0:.2f} / {max_h} Hearts ({cur_hp} / {max_h * 4} Quarters)\n"
            f"Heart Pieces: {total_pieces} / {TOTAL_HEART_PIECES} ({held}/4 held, {needed} needed for next container)\n"
            f"Gold Skulltulas: {tokens} / {TOTAL_SKULLTULAS}\n"
            f"Status: Safe to edit (close emulator before saving)"
        )
        self.status.set(f"Loaded {s.map_name} ({sdir}). Close emulator before saving.")
        self.snapshot_current()

    def snapshot_current(self):
        self.orig_snapshot = {
            "rupees": self.v_rupees.get(),
            "boss_containers": self.v_boss_containers.get(),
            "heart_pieces_total": self.v_heart_pieces_total.get(),
            "hearts": self.v_hearts.get(),
            "hp": self.v_hp.get(),
            "tokens": self.v_tokens.get(),
            "magic": self.v_magic.get(),
            "magic_points": self.v_magic_points.get(),
            "double_defense": self.v_double_defense.get(),
            "hookshot": self.hookshot_var.get(),
            "active_mask": self.active_mask_var.get(),
            "child_quest": self.child_quest_var.get(),
            "adult_trade": self.adult_trade_var.get(),
        }
        for category, d in [("sword", self.owned_swords), ("shield", self.owned_shields),
                            ("tunic", self.owned_tunics), ("boot", self.owned_boots)]:
            for item_name, v in d.items():
                self.orig_snapshot[f"owned_{category}_{item_name}"] = v.get()

        for k in ("sword", "shield", "tunic", "boots", "strength", "scale", "wallet",
                  "quiver", "bomb_bag", "stick_bag", "nut_bag", "bullet_bag"):
            if k in self.equip_vars:
                self.orig_snapshot[k] = self.equip_vars[k].get()

        for k, (v, _, _) in self.ammo_vars.items():
            self.orig_snapshot[k] = v.get()

        for b in range(1, 6):
            k = f"bottle_{b}"
            if k in self.bottle_vars:
                self.orig_snapshot[k] = self.bottle_vars[k].get()

        for kh, (v, name) in self.special_item_vars.items():
            self.orig_snapshot[f"special_{kh}"] = v.get()

        for k in SMALL_KEYS:
            if k["id"] in self.key_vars:
                self.orig_snapshot[f"key_{k['id']}"] = self.key_vars[k["id"]][0].get()

        for name, kh, _ in STONES_MEDALLIONS:
            if kh in self.quest_vars:
                self.orig_snapshot[f"quest_{kh}"] = self.quest_vars[kh].get()

        for sname, bit_idx, _, _, _ in SONGS:
            if bit_idx in self.song_vars:
                self.orig_snapshot[f"song_{bit_idx}"] = self.song_vars[bit_idx].get()

    def max_general(self):
        w_choice = self.equip_vars.get("wallet", tk.StringVar(value=WALLETS[2]["label"])).get()
        target = 1000 if "1000" in w_choice else (500 if "500" in w_choice else 200)
        self.v_rupees.set(str(target))
        self.v_boss_containers.set("8")
        self.v_heart_pieces_total.set("36")
        self._recalc_hearts_from_components()
        self.heal_link()
        self.v_magic.set("Double Magic Meter (48 MP)")
        self.v_magic_points.set("48")
        self._update_magic_display()
        self.v_tokens.set("100")
        self.v_double_defense.set(True)
        self.status.set("Maxed all general stats (not saved yet).")

    def max_equipment(self):
        self.unlock_all_stored_equipment()
        self.equip_vars["sword"].set("Biggoron's Sword")
        self.equip_vars["shield"].set("Mirror Shield")
        self.equip_vars["tunic"].set("Goron Tunic")
        self.equip_vars["boots"].set("Hover Boots")
        self.equip_vars["wallet"].set(WALLETS[2]["label"])
        self.equip_vars["quiver"].set("Biggest Quiver (50)")
        self.equip_vars["bomb_bag"].set("Biggest Bomb Bag (40)")
        self.equip_vars["stick_bag"].set("Biggest Deku-Stick Bag (30)")
        self.equip_vars["nut_bag"].set("Biggest Deku-Nut Bag (40)")
        self.equip_vars["bullet_bag"].set("Biggest Deku-Seed Bag (50)")
        self.equip_vars["strength"].set("Golden Gauntlets")
        self.equip_vars["scale"].set("Golden Scale (8 meters)")
        self.hookshot_var.set("Longshot")
        self.active_mask_var.set("Mask of Truth")
        self.unlock_all_weapons_tools()
        self.unlock_all_spells()
        for k in ("quiver", "bomb_bag", "stick_bag", "nut_bag", "bullet_bag"):
            self._on_bag_or_capacity_changed(k)
        self.status.set("Maxed all equipment & upgrades (not saved yet).")

    def max_ammo(self):
        for k, (v, m, _) in self.ammo_vars.items():
            self._max_single_ammo(v, k)
        self.status.set("Maxed all ammo & consumables (not saved yet).")

    def fairies_in_all_bottles(self):
        count = 0
        for b in range(1, 6):
            k = f"bottle_{b}"
            if k in self.bottle_vars:
                cur = self.bottle_vars[k].get()
                if cur != "(Not Acquired / Locked)":
                    self.bottle_vars[k].set("Bottled Fairy (Revives Link)")
                    self.prev_bottle_selections[k] = "Bottled Fairy (Revives Link)"
                    count += 1
        self.status.set(f"Put Bottled Fairies in {count} acquired bottles (not saved yet).")

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
        for sname, bit_idx, _, _, _ in SONGS:
            if bit_idx in self.song_vars:
                self.song_vars[bit_idx].set(True)
        self.status.set("Learned all 12 Ocarina Songs.")

    def refresh_walkthrough(self):
        if not hasattr(self, "walk_tree") or not self.walk_tree:
            return
        self.walk_tree.delete(*self.walk_tree.get_children())
        if not getattr(self, "active_slot", None):
            return

        q_vars = getattr(self, "quest_vars", {})
        has_emerald = q_vars.get(0xCBD1E58C, tk.BooleanVar(value=False)).get()
        has_ruby = q_vars.get(0x7D69AD47, tk.BooleanVar(value=False)).get()
        has_sapphire = q_vars.get(0xB8E3BF45, tk.BooleanVar(value=False)).get()

        has_forest = q_vars.get(0x692D57CB, tk.BooleanVar(value=False)).get()
        has_fire = q_vars.get(0x5CE254A6, tk.BooleanVar(value=False)).get()
        has_water = q_vars.get(0x0151A68F, tk.BooleanVar(value=False)).get()
        has_shadow = q_vars.get(0x204D2063, tk.BooleanVar(value=False)).get()
        has_spirit = q_vars.get(0x0C7A5FD0, tk.BooleanVar(value=False)).get()
        has_light = q_vars.get(0x235C7D9A, tk.BooleanVar(value=False)).get()

        ch_status = [
            ("Chapter 1", "Inside the Deku Tree (Gohma)", "Completed" if has_emerald else "In Progress"),
            ("Chapter 2", "Dodongo's Cavern (King Dodongo)", "Completed" if has_ruby else ("Available" if has_emerald else "Locked")),
            ("Chapter 3", "Jabu-Jabu's Belly (Barinade)", "Completed" if has_sapphire else ("Available" if has_ruby else "Locked")),
            ("Chapter 4", "Temple of Time (Master Sword)", "Completed" if has_light else ("Available" if (has_emerald and has_ruby and has_sapphire) else "Locked")),
            ("Chapter 5", "Forest Temple (Phantom Ganon)", "Completed" if has_forest else ("Available" if has_light else "Locked")),
            ("Chapter 6", "Fire Temple (Volvagia)", "Completed" if has_fire else ("Available" if has_light else "Locked")),
            ("Chapter 7", "Water Temple (Morpha)", "Completed" if has_water else ("Available" if has_light else "Locked")),
            ("Chapter 8", "Shadow Temple (Bongo Bongo)", "Completed" if has_shadow else ("Available" if has_water else "Locked")),
            ("Chapter 9", "Spirit Temple (Twinrova)", "Completed" if has_spirit else ("Available" if has_water else "Locked")),
            ("Chapter 10", "Ganon's Castle & Final Battle", "Available" if (has_forest and has_fire and has_water and has_shadow and has_spirit and has_light) else "Locked"),
        ]

        for ch, obj, stat in ch_status:
            self.walk_tree.insert("", "end", values=(ch, obj, stat))

    def describe_changes(self):
        diffs = []
        if self.v_rupees.get() != self.orig_snapshot.get("rupees"):
            diffs.append(("General", f"Rupees: {self.orig_snapshot.get('rupees')} -> {self.v_rupees.get()}"))
        if self.v_boss_containers.get() != self.orig_snapshot.get("boss_containers"):
            diffs.append(("General", f"Boss Containers: {self.orig_snapshot.get('boss_containers')} -> {self.v_boss_containers.get()}"))
        if self.v_heart_pieces_total.get() != self.orig_snapshot.get("heart_pieces_total"):
            diffs.append(("General", f"Heart Pieces: {self.orig_snapshot.get('heart_pieces_total')} -> {self.v_heart_pieces_total.get()}"))
        if self.v_hearts.get() != self.orig_snapshot.get("hearts"):
            diffs.append(("General", f"Total Max Hearts: {self.orig_snapshot.get('hearts')} -> {self.v_hearts.get()}"))
        if self.v_hp.get() != self.orig_snapshot.get("hp"):
            diffs.append(("General", f"Current HP (Quarters): {self.orig_snapshot.get('hp')} -> {self.v_hp.get()}"))
        if self.v_tokens.get() != self.orig_snapshot.get("tokens"):
            diffs.append(("General", f"Tokens: {self.orig_snapshot.get('tokens')} -> {self.v_tokens.get()}"))
        if self.v_magic.get() != self.orig_snapshot.get("magic"):
            diffs.append(("General", f"Magic Meter: {self.orig_snapshot.get('magic')} -> {self.v_magic.get()}"))
        if self.v_magic_points.get() != self.orig_snapshot.get("magic_points"):
            diffs.append(("General", f"Current MP: {self.orig_snapshot.get('magic_points')} -> {self.v_magic_points.get()}"))
        if self.v_double_defense.get() != self.orig_snapshot.get("double_defense"):
            diffs.append(("General", f"Double Defense: {self.orig_snapshot.get('double_defense')} -> {self.v_double_defense.get()}"))

        for category, d in [("Sword", self.owned_swords), ("Shield", self.owned_shields),
                            ("Tunic", self.owned_tunics), ("Boot", self.owned_boots)]:
            for item_name, v in d.items():
                snap_key = f"owned_{category.lower()}_{item_name}"
                cur = v.get()
                orig = self.orig_snapshot.get(snap_key, False)
                if cur != orig:
                    diffs.append(("Equipment", f"Owned {item_name}: {'Stored/Added' if cur else 'Removed'}"))

        for k in ("sword", "shield", "tunic", "boots"):
            if k in self.equip_vars:
                choice = self.equip_vars[k].get()
                orig = self.orig_snapshot.get(k)
                if choice != orig:
                    diffs.append(("Equipment", f"Equipped {k.capitalize()}: {orig} -> {choice}"))

        for k in ("strength", "scale", "wallet", "quiver", "bomb_bag", "stick_bag", "nut_bag", "bullet_bag"):
            if k in self.equip_vars:
                choice = self.equip_vars[k].get()
                orig = self.orig_snapshot.get(k)
                if choice != orig:
                    diffs.append(("Upgrades", f"{k.replace('_', ' ').title()}: {orig} -> {choice}"))

        for k, (v, _, _) in self.ammo_vars.items():
            if v.get() != self.orig_snapshot.get(k):
                diffs.append(("Ammo & Consumables", f"{k.title()}: {self.orig_snapshot.get(k)} -> {v.get()}"))

        for b in range(1, 6):
            k = f"bottle_{b}"
            if k in self.bottle_vars:
                cur = self.bottle_vars[k].get()
                orig = self.orig_snapshot.get(k)
                if cur != orig:
                    diffs.append(("Bottles", f"Bottle {b}: {orig} -> {cur}"))

        for kh, (v, name) in self.special_item_vars.items():
            cur = v.get()
            orig = self.orig_snapshot.get(f"special_{kh}", False)
            if cur != orig:
                diffs.append(("Special Items & Spells", f"{name}: {'Unlocked' if cur else 'Locked'}"))

        if self.hookshot_var.get() != self.orig_snapshot.get("hookshot"):
            diffs.append(("Equipment & Inventory", f"Hookshot Upgrade: {self.orig_snapshot.get('hookshot')} -> {self.hookshot_var.get()}"))

        if self.active_mask_var.get() != self.orig_snapshot.get("active_mask"):
            diffs.append(("Equipment & Inventory", f"Active Mask: {self.orig_snapshot.get('active_mask')} -> {self.active_mask_var.get()}"))

        if self.child_quest_var.get() != self.orig_snapshot.get("child_quest"):
            diffs.append(("Quest Items", f"Child Quest Item: {self.orig_snapshot.get('child_quest')} -> {self.child_quest_var.get()}"))

        if self.adult_trade_var.get() != self.orig_snapshot.get("adult_trade"):
            diffs.append(("Quest Items", f"Adult Trade Item: {self.orig_snapshot.get('adult_trade')} -> {self.adult_trade_var.get()}"))

        for k in SMALL_KEYS:
            if k["id"] in self.key_vars:
                cur_k = self.key_vars[k["id"]][0].get()
                orig_k = self.orig_snapshot.get(f"key_{k['id']}")
                if cur_k != orig_k:
                    diffs.append(("Quest Items", f"{k['label']} Keys: {orig_k} -> {cur_k}"))

        for name, kh, _ in STONES_MEDALLIONS:
            if kh in self.quest_vars:
                cur = self.quest_vars[kh].get()
                orig = self.orig_snapshot.get(f"quest_{kh}", False)
                if cur != orig:
                    diffs.append(("Quest Items", f"{name}: {'Added' if cur else 'Removed'}"))

        for sname, bit_idx, _, _, _ in SONGS:
            if bit_idx in self.song_vars:
                cur = self.song_vars[bit_idx].get()
                orig = self.orig_snapshot.get(f"song_{bit_idx}", False)
                if cur != orig:
                    diffs.append(("Songs", f"{sname}: {'Learned' if cur else 'Unlearned'}"))

        if self.flag_changes:
            diffs.append(("Progress Flags", f"{len(self.flag_changes)} story/dialogue flags modified"))

        return diffs

    def save(self):
        if not self.active_slot:
            messagebox.showinfo("No save loaded", "Please select a valid save slot first.")
            return

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

        backup_path = self.make_backup("before edit")

        try:
            s = self.active_slot

            # 1. Wallet & Rupees
            wallet_label = self.equip_vars["wallet"].get()
            matched_wallet = next((w for w in WALLETS if w["label"] == wallet_label), WALLETS[1])
            rupees = int(self.v_rupees.get())
            rupees = max(0, min(matched_wallet["limit"], rupees))

            cur_wallet_id = s.get_string(KEY_WALLET, 64)
            if cur_wallet_id != matched_wallet["id"]:
                s.set_string(KEY_WALLET, matched_wallet["id"], 64)
                s.set(KEY_LIMIT, matched_wallet["limit"])
                for w in WALLETS:
                    s.set(w["stock"], 1 if w["id"] == matched_wallet["id"] else 0)

            s.set(KEY_RUPEES, rupees)
            s.set_c(KEY_PREVIEW_RUPEES, rupees)

            # 2. Vitals (Hearts & Magic)
            tot_hearts = int(self.v_hearts.get())
            tot_hearts = max(3, min(20, tot_hearts))
            cur_quarters = int(self.v_hp.get())
            cur_quarters = max(1, min(tot_hearts * 4, cur_quarters))

            s.set(HASH_PROG_HEARTS, cur_quarters)
            s.set_c(HASH_CAPT_HEARTS, cur_quarters)
            s.set(HASH_PROG_MAX_HEARTS, tot_hearts * 4)
            s.set_c(HASH_CAPT_MAX_HEARTS, tot_hearts * 4)

            # Heart Pieces held (0 to 3 towards next container)
            tot_pieces = int(self.v_heart_pieces_total.get() or 0)
            held_pieces = tot_pieces % 4
            s.set(0x51EC97B3, held_pieces)

            # Magic
            magic_choice = self.v_magic.get()
            if "Double" in magic_choice:
                max_mp = 48
            elif "Standard" in magic_choice:
                max_mp = 24
            else:
                max_mp = 0
            cur_mp = float(self.v_magic_points.get() or 0)
            cur_mp = max(0.0, min(float(max_mp), cur_mp))

            s.set(HASH_PROG_MAGIC, int(round(cur_mp * 10)))
            s.set_c(HASH_CAPT_MAGIC, int(round(cur_mp * 10)))
            s.set(HASH_PROG_MAX_MAGIC, int(max_mp * 10))
            s.set_c(HASH_CAPT_MAX_MAGIC, int(max_mp * 10))

            s.set(BLESSING_MP_STANDARD, 1 if max_mp >= 24 else 0)
            s.set(BLESSING_MP_DOUBLE, 1 if max_mp >= 48 else 0)
            s.set(BLESSING_DEFENSE_DOUBLE, 1 if self.v_double_defense.get() else 0)

            # Tokens
            s.set(0x04735978, max(0, min(100, int(self.v_tokens.get()))))

            # 3. Capacity Bags & Quivers
            # Seeds
            bul_choice = self.equip_vars["bullet_bag"].get()
            bul_limit = 50 if "50" in bul_choice else (40 if "40" in bul_choice else 30)
            bul_tier = 2 if bul_limit == 50 else (1 if bul_limit == 40 else 0)
            s.set(0xAE8CC742, bul_limit)
            s.set(0xDC52ACAF, 1 if bul_tier >= 0 else 0)
            s.set(0x9A30A9E5, 1 if bul_tier >= 1 else 0)
            s.set(0x7B9673F5, 1 if bul_tier >= 2 else 0)
            s.set_string(0xD732DD7F, f"Item_BulletBag_{['Small', 'Medium', 'Large'][bul_tier]}", 64)

            # Nuts
            nut_choice = self.equip_vars["nut_bag"].get()
            nut_limit = 40 if "40" in nut_choice else (30 if "30" in nut_choice else 20)
            nut_tier = 2 if nut_limit == 40 else (1 if nut_limit == 30 else 0)
            s.set(0x735B00F7, nut_limit)
            s.set(0x19B80DBC, 1 if nut_tier >= 0 else 0)
            s.set(0xEAA1785E, 1 if nut_tier >= 1 else 0)
            s.set(0xD60E4B23, 1 if nut_tier >= 2 else 0)
            s.set_string(0x0DA3A7A7, f"Item_NutBag_{['Small', 'Medium', 'Large'][nut_tier]}", 64)

            # Sticks
            stk_choice = self.equip_vars["stick_bag"].get()
            stk_limit = 30 if "30" in stk_choice else (20 if "20" in stk_choice else 10)
            stk_tier = 2 if stk_limit == 30 else (1 if stk_limit == 20 else 0)
            s.set(0x457616B0, stk_limit)
            s.set(0x2FE6AB1A, 1 if stk_tier >= 0 else 0)
            s.set(0x41DB7AB5, 1 if stk_tier >= 1 else 0)
            s.set(0x48E53698, 1 if stk_tier >= 2 else 0)
            s.set_string(0x2808EE1C, f"Item_StickBag_{['Small', 'Medium', 'Large'][stk_tier]}", 64)

            # Bombs
            bb_choice = self.equip_vars["bomb_bag"].get()
            bb_limit = 40 if "40" in bb_choice else (30 if "30" in bb_choice else (20 if "20" in bb_choice else 0))
            bb_tier = 2 if bb_limit == 40 else (1 if bb_limit == 30 else (0 if bb_limit == 20 else -1))
            s.set(0xE753508B, bb_limit)
            s.set(0xB0A1BF51, 1 if bb_tier >= 0 else 0)
            s.set(0xE5FF45AA, 1 if bb_tier >= 1 else 0)
            s.set(0xBD3CA2C6, 1 if bb_tier >= 2 else 0)
            if bb_tier >= 0:
                s.set_string(0xA835E3B0, f"Item_BombBag_{['Small', 'Medium', 'Large'][bb_tier]}", 64)

            # Quiver
            q_choice = self.equip_vars["quiver"].get()
            q_limit = 50 if "50" in q_choice else (40 if "40" in q_choice else (30 if "30" in q_choice else 0))
            q_tier = 2 if q_limit == 50 else (1 if q_limit == 40 else (0 if q_limit == 30 else -1))
            s.set(0x418DB791, q_limit)
            s.set(0xA8C3E1FB, 1 if q_tier >= 0 else 0)
            s.set(0x3BB370E1, 1 if q_tier >= 1 else 0)
            s.set(0xD331C7DA, 1 if q_tier >= 2 else 0)

            # Strength Gauntlets
            st_choice = self.equip_vars["strength"].get()
            s.set(0xD1317941, 1 if ("Bracelet" in st_choice or "Gauntlet" in st_choice) else 0)
            s.set(0x0012B8C0, 1 if ("Silver" in st_choice or "Golden" in st_choice) else 0)
            s.set(0x40AE1183, 1 if "Golden" in st_choice else 0)

            # Diving Scale
            sc_choice = self.equip_vars["scale"].get()
            s.set(0x1240044B, 1 if ("Silver" in sc_choice or "Golden" in sc_choice) else 0)
            s.set(0x4AEB140A, 1 if "Golden" in sc_choice else 0)

            # 4. Ammo & Consumables
            s.set(0x518EC74B, int(self.ammo_vars["arrows"][0].get()))
            s.set(0xDB1BCD4F, int(self.ammo_vars["bombs"][0].get()))
            s.set(0xDF7C517A, max(0, min(30, int(self.ammo_vars["bombchus"][0].get()))))
            s.set(0x5FADF7FC, int(self.ammo_vars["seeds"][0].get()))
            s.set(0xB9494411, int(self.ammo_vars["sticks"][0].get()))
            s.set(0xF30D9F54, int(self.ammo_vars["nuts"][0].get()))
            s.set(0xB003124D, max(0, min(10, int(self.ammo_vars["beans"][0].get()))))
            s.set(0x600E29EB, max(0, min(30, int(self.ammo_vars["scrub"][0].get()))))

            # 5. Bottles
            for idx, (stk_h, val_h, cnt_h) in enumerate(BOTTLE_SLOTS, 1):
                name = self.bottle_vars.get(f"bottle_{idx}", tk.StringVar(value="Empty Bottle")).get()
                cnt_id = BOTTLE_NAME_TO_ID.get(name, EMPTY_BOTTLE)
                # If bottle is acquired:
                if name != "(Not Acquired / Locked)":
                    s.set(stk_h, 1)
                    s.set(val_h, 1)
                    s.set_u32(cnt_h, cnt_id)
                else:
                    s.set(stk_h, 0)
                    s.set(val_h, 0)
                    s.set_u32(cnt_h, EMPTY_BOTTLE)

            # 6. Equipped Items (In-place Section 2 Strings)
            eq_sw = self.equip_vars["sword"].get()
            sw_actor = next((actor for name, _, actor in SWORDS if name == eq_sw), "Weapon_Sword_Kokiri")
            s.set_string(HASH_SWORD_SLOT, sw_actor, 64)

            eq_sh = self.equip_vars["shield"].get()
            sh_actor = next((actor for name, _, actor in SHIELDS if name == eq_sh), "Weapon_Shield_Deku")
            s.set_string(HASH_SHIELD_SLOT, sh_actor, 64)

            # 7. Owned Equipment Stocks
            for s_name, kh, _ in SWORDS:
                if s_name in self.owned_swords:
                    s.set(kh, 1 if self.owned_swords[s_name].get() else 0)

            for sh_name, kh, _ in SHIELDS:
                if sh_name in self.owned_shields:
                    s.set(kh, 1 if self.owned_shields[sh_name].get() else 0)

            for t_name, kh, _ in TUNICS:
                if t_name in self.owned_tunics:
                    s.set(kh, 1 if self.owned_tunics[t_name].get() else 0)

            for b_name, kh, _ in BOOTS:
                if b_name in self.owned_boots:
                    if kh != 0:
                        s.set(kh, 1 if self.owned_boots[b_name].get() else 0)

            # 8. Special Items, Tools & Spells
            for kh, (v, name) in self.special_item_vars.items():
                s.set(kh, 1 if v.get() else 0)

            # Hookshot Upgrade (mutually exclusive)
            hs_val = self.hookshot_var.get()
            s.set(0x8573D2CD, 1 if hs_val == "Hookshot" else 0)
            s.set(0x8499EA34, 1 if hs_val == "Longshot" else 0)

            # Active Mask (Happy Mask Shop)
            active_m = self.active_mask_var.get()
            for mname, (mhash, mactor) in MASK_MAP.items():
                s.set(mhash, 1 if mname == active_m else 0)
            if active_m in MASK_MAP:
                s.set_string(HASH_MASK_SLOT, MASK_MAP[active_m][1], 64)
            else:
                s.set_string(HASH_MASK_SLOT, "", 64)

            # Child Quest Item (single active)
            cq_val = self.child_quest_var.get()
            for name, kh in CHILD_QUEST_MAP.items():
                s.set(kh, 1 if name == cq_val else 0)

            # Adult Trading Sequence (single active)
            at_val = self.adult_trade_var.get()
            for name, kh in ADULT_TRADE_MAP.items():
                s.set(kh, 1 if name == at_val else 0)

            # Dungeon Small Keys
            for k in SMALL_KEYS:
                if k["id"] in self.key_vars:
                    val = int(self.key_vars[k["id"]][0].get() or 0)
                    s.set(k["stock"], max(0, min(k["max"], val)))

            # 9. Spiritual Stones & Medallions
            for _, kh, _ in STONES_MEDALLIONS:
                if kh in self.quest_vars:
                    s.set(kh, 1 if self.quest_vars[kh].get() else 0)

            # 10. Songs (12-bit bitfield at 0x628BE485 & event flags)
            song_mask = 0
            for sname, bit_idx, isget_h, event_h, _ in SONGS:
                learned = bool(self.song_vars[bit_idx].get()) if bit_idx in self.song_vars else False
                if learned:
                    song_mask |= (1 << bit_idx)
                    if isget_h: s.set(isget_h, 1)
                    if event_h: s.set(event_h, 1)
                else:
                    if isget_h: s.set(isget_h, 0)
                    if event_h: s.set(event_h, 0)
            s.set(HASH_SONG_MASK, song_mask)

            # 11. Apply Modified Progress Flags
            flags_saved = 0
            for h, flag_val in self.flag_changes.items():
                s.set(h, 1 if flag_val else 0)
                flags_saved += 1

            # 12. Synchronize All 105 Item Registration Flags
            reg_count = register_all_owned_inventory(s)

            # 13. Save Bytes In-Place to Disk
            s.save_to_files()

            # Clear flag modifications and refresh
            self.flag_changes.clear()
            self.snapshot_current()
            self.populate_flags()
            self.populate_inspector()
            self.refresh_walkthrough()
            self.update_backup_count()
            self.status.set(f"Successfully saved changes to {s.slot_dir} ({reg_count} item registrations verified).")
            messagebox.showinfo(
                "Save complete",
                f"Modifications saved safely to {os.path.basename(s.slot_dir)}!\n\n"
                f"- Exact binary format and Section 1 bounds strictly preserved.\n"
                f"- Vitals, wallet limits, and HUD preview synchronized.\n"
                f"- Automatic backup created: {os.path.basename(backup_path)}"
            )
        except Exception as e:
            messagebox.showerror("Save failed", f"Could not write save file:\n{str(e)}")

    def confirm_changes(self, changes):
        top = tk.Toplevel(self)
        top.title("Confirm modifications")
        top.transient(self)
        top.grab_set()

        body = ttk.Frame(top, padding=12)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Review your modifications before writing to save file:",
                  font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 6))

        tree_frame = ttk.Frame(body)
        tree_frame.pack(fill="both", expand=True)
        tree = ttk.Treeview(tree_frame, columns=("category", "change"), show="headings", height=12)
        tree.heading("category", text="Category", anchor="w")
        tree.heading("change", text="Modification", anchor="w")
        tree.column("category", width=160, stretch=False)
        tree.column("change", width=420)
        tree.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        sb.pack(side="right", fill="y")
        tree.configure(yscrollcommand=sb.set)

        for cat, change in changes:
            tree.insert("", "end", values=(cat, change))

        result = {"ok": False}
        def ok():
            result["ok"] = True
            top.destroy()

        btns = ttk.Frame(body)
        btns.pack(fill="x", pady=(10, 0))
        self.primary_button(btns, "Apply and save", ok).pack(side="right")
        ttk.Button(btns, text="Cancel", command=top.destroy).pack(side="right", padx=(0, 6))

        self.theme_window(top)
        self.center(top, 640, 420)
        top.wait_window()
        return result["ok"]

    def backup_now(self):
        f = self.make_backup("manual")
        if f:
            self.update_backup_count()
            self.status.set(f"Backup created: {os.path.basename(f)}")
            messagebox.showinfo("Backup complete", f"Backup created successfully:\n{f}")
        else:
            messagebox.showerror("Backup failed", "Could not create backup.")

    def make_backup(self, tag=""):
        f = self.root_dir.get()
        if not f or not os.path.isdir(f):
            return None
        os.makedirs(BACKUP_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        name = f"OOT_Backup_{ts}" + (f"_{tag}" if tag else "")
        dst = os.path.join(BACKUP_DIR, name)
        try:
            shutil.copytree(f, dst)
            return dst
        except OSError:
            return None

    def update_backup_count(self):
        count = len(list_backups(BACKUP_DIR))
        self.backup_count.set(f"{count} backup{'s' if count != 1 else ''} stored")

    def open_backups(self):
        os.makedirs(BACKUP_DIR, exist_ok=True)
        open_folder(BACKUP_DIR)

    def restore_dialog(self):
        bks = list_backups(BACKUP_DIR)
        if not bks:
            messagebox.showinfo("No backups", "No backups found to restore.")
            return

        top = tk.Toplevel(self)
        top.title("Restore a backup")
        top.transient(self)
        top.grab_set()

        body = ttk.Frame(top, padding=12)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Select a backup to restore:", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 2))
        ttk.Label(body, text=f"Backups are stored in: {BACKUP_DIR}", style="Faint.TLabel").pack(anchor="w", pady=(0, 6))

        lb = tk.Listbox(body, height=10)
        lb.pack(fill="both", expand=True)
        for b in bks:
            lb.insert("end", b)
        lb.selection_set(0)

        def restore():
            sel = lb.curselection()
            if not sel: return
            target_bk = bks[sel[0]]
            src = os.path.join(BACKUP_DIR, target_bk)
            dst = self.root_dir.get()
            if messagebox.askyesno("Confirm restore", f"Restore {target_bk} over current save folder?\n\n{dst}", parent=top):
                try:
                    self.make_backup("before_restore")
                    for sname in os.listdir(src):
                        s_src = os.path.join(src, sname)
                        s_dst = os.path.join(dst, sname)
                        if os.path.isdir(s_src):
                            shutil.rmtree(s_dst, ignore_errors=True)
                            shutil.copytree(s_src, s_dst)
                    top.destroy()
                    self.refresh_slots()
                    messagebox.showinfo("Restore complete", f"Restored backup {target_bk} successfully.")
                except Exception as e:
                    messagebox.showerror("Restore error", str(e), parent=top)

        btns = ttk.Frame(body)
        btns.pack(fill="x", pady=(10, 0))
        ttk.Button(btns, text="Open backups folder", command=self.open_backups).pack(side="left")
        self.primary_button(btns, "Restore selected backup", restore).pack(side="right")
        ttk.Button(btns, text="Cancel", command=top.destroy).pack(side="right", padx=6)

        self.theme_window(top)
        self.center(top, 560, 360)

    # ---------- Cheats Engine ----------
    def detect_cheat_target(self):
        bids = detect_build_ids(self.emulator)
        self.cheat_bids = bids
        self.load_cheats()

    def current_build(self):
        if hasattr(self, "cheat_bids") and self.cheat_bids:
            return self.cheat_bids[0]
        return "E0F3CCFAF50065AE"

    def load_cheats(self):
        bid = self.current_build()
        self.cheats = read_library(bid)
        self.refresh_cheats()

    def refresh_cheats(self):
        self.cheat_tree.delete(*self.cheat_tree.get_children())
        for c in self.cheats:
            on = bool(c.get("enabled", False))
            mark = "[x]" if on else "[ ]"
            t_str = ", ".join(f"{k}: {v}" for k, v in c.get("tested", {}).items())
            self.cheat_tree.insert("", "end", values=(mark, c["name"], c.get("description", ""), t_str))

    def toggle_cheats(self):
        sel = self.cheat_tree.selection()
        if not sel: return
        idx = self.cheat_tree.index(sel[0])
        if 0 <= idx < len(self.cheats):
            self.cheats[idx]["enabled"] = not self.cheats[idx].get("enabled", False)
            self.refresh_cheats()
            self.cheat_tree.selection_set(self.cheat_tree.get_children()[idx])

    def install_cheats(self):
        if not self.emulator:
            messagebox.showerror("Emulator not detected", "Could not detect active emulator directory.")
            return
        cdir = self.emulator.get("cheat_dir")
        if not cdir:
            messagebox.showerror("No cheat directory", "Emulator does not specify a cheat directory.")
            return
        os.makedirs(cdir, exist_ok=True)
        bid = self.current_build()
        path = os.path.join(cdir, bid + ".txt")
        active = [c for c in self.cheats if c.get("enabled")]
        if not active:
            if os.path.exists(path):
                os.remove(path)
            messagebox.showinfo("Cheats cleared", "No cheats enabled. Cheat file removed from emulator.")
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(format_cheats(active))
        messagebox.showinfo("Cheats installed", f"Installed {len(active)} active cheats to:\n{path}\n\nRestart game to apply.")

    def uninstall_cheats(self):
        if not self.emulator or not self.emulator.get("cheat_dir"):
            return
        path = os.path.join(self.emulator["cheat_dir"], self.current_build() + ".txt")
        if os.path.exists(path):
            os.remove(path)
            messagebox.showinfo("Cheats uninstalled", "Cheats removed from emulator.")
        else:
            messagebox.showinfo("No cheats", "No cheats were installed.")

    def export_cheats(self):
        bid = self.current_build()
        active = [c for c in self.cheats if c.get("enabled")]
        if not active:
            messagebox.showinfo("No cheats enabled", "Please enable at least one cheat to export.")
            return
        f = filedialog.asksaveasfilename(
            title="Export Cheats for Switch 2 Atmosphere",
            initialfile=bid + ".txt",
            filetypes=[("Text files", "*.txt")]
        )
        if f:
            with open(f, "w", encoding="utf-8") as out:
                out.write(format_cheats(active))
            messagebox.showinfo("Export complete", f"Saved {len(active)} cheats to:\n{f}")

    def open_cheat_folder(self):
        bid = self.current_build()
        folder = build_folder(bid)
        os.makedirs(folder, exist_ok=True)
        open_folder(folder)

    def show_cheat_guide(self):
        top = tk.Toplevel(self)
        top.title("Cheats guide")
        top.transient(self)
        top.grab_set()

        body = ttk.Frame(top, padding=12)
        body.pack(fill="both", expand=True)

        txt = tk.Text(body, wrap="word", height=18, width=70)
        txt.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(body, orient="vertical", command=txt.yview)
        sb.pack(side="right", fill="y")
        txt.configure(yscrollcommand=sb.set)

        for kind, text in CHEAT_GUIDE:
            if kind == "h":
                txt.insert("end", f"\n{text}\n", "header")
            elif kind == "warn":
                txt.insert("end", f"WARNING: {text}\n", "warn")
            else:
                txt.insert("end", f"{text}\n")

        txt.tag_configure("header", font=("Segoe UI", 10, "bold"))
        txt.tag_configure("warn", foreground="#b26a00", font=("Segoe UI", 9, "bold"))
        txt.configure(state="disabled")

        self.theme_window(top)
        self.center(top, 600, 400)

    # ---------- Theming & UI Helpers ----------
    def theme_mode(self):
        choice = self.theme_choice.get()
        if choice == "System":
            return "dark" if system_prefers_dark() else "light"
        return choice.lower()

    def store_settings(self):
        store_settings(self.settings)

    def on_theme_pick(self, _=None):
        self.settings["theme"] = self.theme_choice.get()
        store_settings(self.settings)
        self.apply_theme()

    def apply_theme(self):
        mode = self.theme_mode()
        p = self.palette = PALETTES[mode]
        s = self.style
        if mode == "dark":
            s.theme_use("clam")
            s.configure(".", background=p["bg"], foreground=p["fg"], fieldbackground=p["field"],
                        bordercolor=p["border"], lightcolor=p["surface"], darkcolor=p["surface"],
                        troughcolor=p["bg"], selectbackground=p["select"], selectforeground="#ffffff",
                        insertcolor=p["fg"], focuscolor=p["accent"])
            s.map(".", foreground=[("disabled", p["faint"])])
            s.configure("TFrame", background=p["bg"])
            s.configure("TLabelframe", background=p["bg"], bordercolor=p["border"])
            s.configure("TLabelframe.Label", background=p["bg"], foreground=p["fg"], font=("Segoe UI", 9, "bold"))
            s.configure("TLabel", background=p["bg"], foreground=p["fg"])
            s.configure("Muted.TLabel", background=p["bg"], foreground=p["muted"])
            s.configure("Faint.TLabel", background=p["bg"], foreground=p["faint"])
            s.configure("Warn.TLabel", background=p["bg"], foreground=p["warn"])
            s.configure("TButton", background=p["surface"], foreground=p["fg"], padding=(8, 3), bordercolor=p["border"])
            s.map("TButton", background=[("pressed", p["border"]), ("active", p["hover"])])
            s.configure("Primary.TButton", background=p["select"], foreground="#ffffff", bordercolor=p["border"], font=("Segoe UI", 9, "bold"))
            s.map("Primary.TButton", background=[("active", p["accent"])])
            for w in ("TEntry", "TCombobox", "TSpinbox"):
                s.configure(w, fieldbackground=p["field"], foreground=p["fg"], arrowcolor=p["fg"],
                            background=p["surface"], bordercolor=p["border"])
                s.map(w, fieldbackground=[("readonly", p["field"]), ("disabled", p["bg"])],
                      foreground=[("readonly", p["fg"])], background=[("active", p["hover"])],
                      selectbackground=[("readonly", p["field"])], selectforeground=[("readonly", p["fg"])])
            s.configure("TCheckbutton", background=p["bg"], foreground=p["fg"], indicatorbackground=p["field"])
            s.map("TCheckbutton", background=[("active", p["bg"])],
                  indicatorbackground=[("selected", p["accent"]), ("active", p["hover"])])
            s.configure("TNotebook", background=p["bg"], bordercolor=p["border"])
            s.configure("TNotebook.Tab", background=p["surface"], foreground=p["muted"], bordercolor=p["border"])
            s.map("TNotebook.Tab", background=[("selected", p["bg"]), ("active", p["hover"])])
            s.configure("Treeview", background=p["field"], fieldbackground=p["field"], foreground=p["fg"],
                        bordercolor=p["border"], rowheight=22)
            s.configure("Treeview.Heading", background=p["surface"], foreground=p["fg"], bordercolor=p["border"], relief="flat", font=("Segoe UI", 9, "bold"))
            s.map("Treeview.Heading", background=[("active", p["hover"])])
            s.map("Treeview", background=[("selected", p["select"])], foreground=[("selected", "#ffffff")])
            s.configure("Vertical.TScrollbar", background=p["hover"], troughcolor=p["bg"], gripcount=0,
                        lightcolor=p["hover"], darkcolor=p["hover"], arrowcolor=p["fg"], bordercolor=p["bg"])
            s.map("Vertical.TScrollbar", background=[("active", p["border"])])
            s.configure("Horizontal.TScrollbar", background=p["hover"], troughcolor=p["bg"], gripcount=0,
                        lightcolor=p["hover"], darkcolor=p["hover"], arrowcolor=p["fg"], bordercolor=p["bg"])
            s.map("Horizontal.TScrollbar", background=[("active", p["border"])])
        else:
            s.theme_use(self.base_theme)
            s.configure(".", background=p["bg"], foreground=p["fg"])
            s.configure("TFrame", background=p["bg"])
            s.configure("TLabelframe", background=p["bg"], foreground=p["fg"], bordercolor=p["border"])
            s.configure("TLabelframe.Label", background=p["bg"], foreground=p["fg"], font=("Segoe UI", 9, "bold"))
            s.configure("TLabel", background=p["bg"], foreground=p["fg"])
            s.configure("Muted.TLabel", background=p["bg"], foreground=p["muted"])
            s.configure("Faint.TLabel", background=p["bg"], foreground=p["faint"])
            s.configure("Warn.TLabel", background=p["bg"], foreground=p["warn"])
            s.configure("TButton", background=p["surface"], foreground=p["fg"], bordercolor=p["border"])
            s.map("TButton", background=[("active", p["hover"])])
            s.configure("Primary.TButton", font=("Segoe UI", 9, "bold"))
            s.configure("TCheckbutton", background=p["bg"], foreground=p["fg"])
            s.configure("TCombobox", fieldbackground=p["field"], background=p["surface"], foreground=p["fg"])
            s.configure("TSpinbox", fieldbackground=p["field"], background=p["surface"], foreground=p["fg"])
            s.configure("TEntry", fieldbackground=p["field"], foreground=p["fg"])
            s.configure("TNotebook", background=p["bg"], bordercolor=p["border"])
            s.configure("Treeview", background=p["field"], foreground=p["fg"], fieldbackground=p["field"])
            s.configure("Treeview.Heading", background=p["surface"], foreground=p["fg"], font=("Segoe UI", 9, "bold"))
            s.map("Treeview", background=[("selected", p["select"])], foreground=[("selected", "#ffffff")])

        self._style_common()

        for opt, value in (
            ("*TCombobox*Listbox.background", p["field"]),
            ("*TCombobox*Listbox.foreground", p["fg"]),
            ("*TCombobox*Listbox.selectBackground", p["select"]),
            ("*TCombobox*Listbox.selectForeground", "#ffffff"),
        ):
            self.option_add(opt, value)

        self.configure(bg=p["bg"])
        self._recolor(self)

        for tree in (getattr(self, "walk_tree", None), getattr(self, "cheat_tree", None),
                     getattr(self, "flag_tree", None), getattr(self, "inspector_tree", None)):
            if tree:
                tree.tag_configure("on", foreground=p["tag_on"])
                tree.tag_configure("off", foreground=p["faint"])
                tree.tag_configure("changed", foreground=p["tag_changed"], font=("Segoe UI", 9, "bold"))

        if hasattr(self, "guides_frame") and self.guides_frame:
            self.guides_frame.refresh_theme(p)

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
        style.configure("Primary.TButton", font=(font, 9, "bold"))
        style.map("Primary.TButton", background=[("active", "#005a9e")])

    def _recolor(self, widget):
        p = self.palette
        try:
            if isinstance(widget, (tk.Listbox, tk.Text)):
                widget.configure(bg=p["field"], fg=p["fg"], selectbackground=p["select"],
                                 selectforeground="#ffffff", highlightthickness=0)
            elif isinstance(widget, tk.Canvas):
                widget.configure(bg=p["bg"], highlightthickness=0)
        except (tk.TclError, AttributeError):
            pass
        for child in widget.winfo_children():
            self._recolor(child)

    def theme_window(self, win):
        p = self.palette
        win.configure(bg=p["bg"])
        self._recolor(win)

    def center(self, win, w=None, h=None):
        win.update_idletasks()
        if w is None: w = win.winfo_width()
        if h is None: h = win.winfo_height()
        parent = win.master or self
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        x = max(0, px + (pw - w) // 2)
        y = max(0, py + (ph - h) // 2)
        win.geometry(f"{w}x{h}+{x}+{y}")

    def primary_button(self, parent, text, command):
        return ttk.Button(parent, text=text, command=command, style="Primary.TButton")

    def sort_by(self, tree, col):
        desc = not self._sort.get((tree, col), False)
        self._sort[(tree, col)] = desc
        self.apply_sort(tree, col, desc)

    def apply_sort(self, tree, col, desc):
        items = list(tree.get_children(""))
        def key_func(item):
            val = tree.set(item, col)
            try: return (0, float(val))
            except ValueError: return (1, val.lower())
        items.sort(key=key_func, reverse=desc)
        for idx, item in enumerate(items):
            tree.move(item, "", idx)

    def on_tab_changed(self, event):
        try:
            selected = self.notebook.select()
            if hasattr(self, "guides_frame") and self.guides_frame:
                if selected == str(self.guides_frame):
                    self.guides_frame.ensure_cards_built()
        except Exception:
            pass


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else None
    app = OOTEditor(folder=folder)
    app.mainloop()


if __name__ == "__main__":
    main()
