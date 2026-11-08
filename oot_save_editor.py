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
HASH_HEALTH = 0x76b18200            # progress.sav current health (16 = 1 heart, 144 = 9 hearts, 320 = 20 hearts)
HASH_CAPTION_HEALTH = 0x19f26b6a    # caption.sav health
HASH_CAPTION_MAX_HEALTH = 0x943f8ec3
HASH_HEARTS = 0x9b6b4b33            # progress.sav total hearts (3-20, exactly 9 in user save)
HASH_HEART_PIECES = 0x67be435e      # progress.sav heart pieces collected (exactly 13 in user save)
HASH_CAPTION_HEART_PIECES = 0x74bd05d0
HASH_TOKENS = 0x04735978            # progress.sav Gold Skulltula Tokens (0-100)
HASH_CAPTION_TOKENS = 0xdc941483    # caption.sav tokens preview
HASH_DEFENSE = 0xfb2b5f6b           # progress.sav & caption.sav Double Defense
HASH_CAPTION_DEFENSE = 0xfb2b5f6b

# Ammo Hashes (Verified with user save slot_01)
HASH_ARROWS = 0x361b83ad            # Bow arrows (0-50, 0 if no bow)
HASH_BOMBS = 0xdb1bcd4f             # Bombs (0-40, 22 in user save)
HASH_BOMBCHUS = 0xdf7c517a          # Bombchus (0-50, 29 in user save)
HASH_DEKU_SEEDS = 0x5fadf7fc        # Slingshot seeds (0-50, 49 in user save)
HASH_DEKU_STICKS = 0xb9494411       # Deku sticks (0-30, 19 in user save)
HASH_DEKU_NUTS = 0xf30d9f54         # Deku nuts (0-40, 29 in user save)
HASH_MAGIC_BEANS = 0x1e9e1b91       # Magic beans (0-10, 0 in user save)

# Songs Bitmask Hash in progress.sav (12-bit bitfield: 15 = 0b1111 for 4 learned songs)
HASH_SONG_MASK = 0x628be485

# 5 Bottle Hashes (OoT Enhanced Switch release supports 5 bottles)
BOTTLE_HASHES = [
    0x37c3f735,  # Bottle 1 (3 = Poe)
    0x73736cde,  # Bottle 2 (4 = Bug)
    0xa6c38c34,  # Bottle 3 (23 = Bottled Fairy)
    0x3874fcc4,  # Bottle 4 (28 = Bug)
    0x9b529f63,  # Bottle 5 (4294967295 = Not Acquired)
]

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

# Ocarina Songs (Exact 12 song bitmask verified in progress.sav at 0x628be485)
# In OoT 3D / Remake bit order: Bit 0=Lullaby, 1=Epona, 2=Saria, 3=Song of Time, 4=Sun's Song, 5=Storms
SONGS = [
    ("Zelda's Lullaby", 0xf9d63fd4, "Royal Family mystery theme"),
    ("Epona's Song", 0x574aef59, "Summons Epona & heals milk cows"),
    ("Saria's Song", 0xab6b5962, "Talk to Saria & cheer up Darunia"),
    ("Song of Time", 0x1eda08d5, "Opens the Door of Time"),
    ("Sun's Song", 0x99b50b91, "Changes day to night and freezes ReDeads"),
    ("Song of Storms", 0x2f793671, "Summons rain and drains the Well"),
    ("Minuet of Forest", 0xe1ca50c6, "Warp to Sacred Forest Meadow"),
    ("Bolero of Fire", 0x17464eb8, "Warp to Death Mountain Crater"),
    ("Serenade of Water", 0x85f5194d, "Warp to Lake Hylia"),
    ("Requiem of Spirit", 0x83254520, "Warp to Desert Colossus"),
    ("Nocturne of Shadow", 0x10dc0608, "Warp to Graveyard"),
    ("Prelude of Light", 0x059ce596, "Warp to Temple of Time"),
]

# Magic Spells & Magical Arrows (From IGN All Items guide)
IGN_ALL_ITEMS_URL = "https://www.ign.com/wikis/ocarina-of-time-remake/All_Items"

MAGIC_SPELLS = [
    ("Din's Fire", 0x3cd8eff5, "Sphere of magical flame that scorches enemies and lights torches (Hyrule Castle)"),
    ("Farore's Wind", 0x4fd7baed, "Sets warp points inside dungeons for fast traversal (Zora's Fountain)"),
    ("Nayru's Love", 0x8cee97a2, "Crystalline defensive barrier that blocks all damage (Desert Colossus)"),
]

MAGIC_ARROWS = [
    ("Fire Arrows", 0x310edbf8, "Ignites torches and melts red ice from long range (costs 2 MP)"),
    ("Ice Arrows", 0x4150392f, "Freezes enemies in solid blocks of ice (costs 2 MP)"),
    ("Light Arrows", 0x431db556, "Pierces dark barriers, penetrates magic and stuns Ganondorf (costs 4 MP)"),
]

MAGIC_POWERS = [
    ("Enhanced Spin Attack", 0x1fb5294d, "Super Spin Attack with fiery red aura & massive blast (Ganon's Castle Great Fairy)"),
]

DUNGEON_TOOLS = [
    ("Fairy Slingshot", 0xa0df2650, "Shoots Deku Seeds at targets and eye switches (Deku Tree)"),
    ("Fairy Bow", 0x6de63df3, "Fires arrows at long range (Forest Temple)"),
    ("Boomerang", 0xf061f15c, "Retrieves faraway items and stuns enemies (Jabu-Jabu's Belly)"),
    ("Hookshot", 0x6e2eac84, "Grapples onto wooden targets to cross chasms (Graveyard Dampé)"),
    ("Longshot", 0x763edcc0, "Extended chain hookshot with double the reach (Water Temple)"),
    ("Megaton Hammer", 0xa1ebf96f, "Smashes rusted floor switches and solid boulders (Fire Temple)"),
    ("Lens of Truth", 0xad234438, "Reveals illusory walls, fake floors and invisible foes (Bottom of the Well)"),
    ("Fairy Ocarina", 0xb72cd3fd, "Saria's parting gift to Link at the Kokiri Forest exit"),
    ("Ocarina of Time", 0xb72cd3fc, "Legendary mystical instrument passed down by the Royal Family"),
]

# Happy Mask Shop Masks
MASKS = [
    ("Keaton Mask", 0xfbe01da1, "Fox mask sold to the guard at the Death Mountain Gate"),
    ("Skull Mask", 0x361b83ae, "Skull mask sold to the Skull Kid in the Lost Woods"),
    ("Spooky Mask", 0x361b83af, "ReDead-face mask sold to the boy in Kakariko Graveyard"),
    ("Bunny Hood", 0x361b83b0, "Rabbit ears mask sold to the Running Man in Hyrule Field"),
    ("Mask of Truth", 0x59d9c7b3, "Allows Link to hear the secret thoughts of Gossip Stones"),
    ("Goron Mask", 0x59d9c7b4, "Friendly smiling Goron mask borrowed from Happy Mask Shop"),
    ("Zora Mask", 0x59d9c7b5, "Fin-eared Zora mask borrowed from Happy Mask Shop"),
    ("Gerudo Mask", 0x59d9c7b6, "Gerudo disguise borrowed from Happy Mask Shop"),
]

# Child Quest Items
CHILD_QUEST_ITEMS = [
    ("Weird Egg", 0x04735978, "Given by Malon at Hyrule Castle gate to wake Talon"),
    ("Pocket Chicken", 0x80c4765, "Hatched from the Weird Egg, crows to wake sleeping Talon"),
    ("Zelda's Letter", 0x80c4764, "Royal scroll signed by Princess Zelda to access Death Mountain"),
]

# Adult Trading Sequence (Biggoron's Sword Quest)
ADULT_TRADE_ITEMS = [
    ("Pocket Egg", 0x4269b3f2, "Given by the Cucco Lady in Kakariko Village"),
    ("Pocket Cucco", 0x4269b3f3, "Hatched Cucco used to wake the sleeping man in the Kakariko House"),
    ("Cojiro", 0xb5fa6c5b, "Blue Cucco that only crows for nice people, owned by Master Craftsman's Son"),
    ("Odd Mushroom", 0xb5fa6c5c, "Fresh mushroom that spoils quickly, trade to Granny's Potion Shop"),
    ("Odd Potion", 0xb5fa6c5d, "Magic potion made from the Odd Mushroom for the woodsman"),
    ("Poacher's Saw", 0xae8cc742, "Saw left behind by the woodsman, trade to Master Craftsman in Gerudo Valley"),
    ("Broken Goron's Sword", 0xae8cc743, "Two-handed blade snapped in half, take to Biggoron atop Death Mountain"),
    ("Prescription", 0xae8cc744, "Medical note from Biggoron for King Zora to cure eye irritation"),
    ("Eyeball Frog", 0xae8cc745, "Rare ingredient from King Zora, deliver to Lake Hylia Scientist"),
    ("World's Finest Eye Drops", 0xae8cc746, "Soothing drops brewed by the Scientist, rush back to Biggoron"),
    ("Claim Check", 0xae8cc747, "Receipt given by Biggoron; returns Biggoron's Sword after forging"),
]

# Quest Perks & Abilities (Managed in Equipment Tab)
QUEST_PERKS = [
    ("Gerudo's Membership Card", 0xba6a1b74, "Grants access to Gerudo Fortress"),
    ("Stone of Agony", 0x75bd1ecf, "Vibrates near hidden grottos and secrets"),
    ("Magic Meter (Single)", 0x89ae7032, "Grants magic power for Spin Attack & magic items"),
    ("Double Magic Meter", 0xc72044fc, "Doubles maximum magic capacity"),
    ("Double Defense", 0xfb2b5f6b, "White heart borders, halves all damage taken"),
]

# Equipment list & Upgrades (Giant's Knife removed per remake specification)
SWORDS = ["(None)", "Kokiri Sword", "Master Sword", "Biggoron's Sword"]
SHIELDS = ["(None)", "Deku Shield", "Hylian Shield", "Mirror Shield"]
TUNICS = ["Kokiri Tunic", "Goron Tunic", "Zora Tunic"]
BOOTS = ["Kokiri Boots", "Iron Boots", "Hover Boots"]
WALLETS = ["Child's Wallet (99 Rupees)", "Adult's Wallet (200 Rupees)", "Giant's Wallet (500 Rupees)", "Tycoon's Wallet (999 Rupees)"]
QUIVERS = ["None", "Fairy Bow Quiver (30)", "Bigger Quiver (40)", "Biggest Quiver (50)"]
BOMB_BAGS = ["None", "Bomb Bag (20)", "Bigger Bomb Bag (30)", "Biggest Bomb Bag (40)"]
STICK_BAGS = ["Deku-Stick Bag (10)", "Bigger Deku-Stick Bag (20)", "Biggest Deku-Stick Bag (30)"]
NUT_BAGS = ["Deku-Nut Bag (20)", "Bigger Deku-Nut Bag (30)", "Biggest Deku-Nut Bag (40)"]
BULLET_BAGS = ["Deku-Seed Bag (30)", "Bigger Deku-Seed Bag (40)", "Biggest Deku-Seed Bag (50)"]
STRENGTH_UPGRADES = ["None", "Goron's Bracelet", "Silver Gauntlets", "Golden Gauntlets"]
SCALES = ["Default (1 meter)", "Silver Scale (6 meters)", "Golden Scale (8 meters)"]

EQUIPMENT_STRING_MAP = {
    # Swords
    "Kokiri Sword": "Weapon_Sword_Kokiri",
    "Master Sword": "Weapon_Sword_Master",
    "Biggoron's Sword": "Weapon_Sword_Biggoron",
    # Shields
    "Deku Shield": "Weapon_Shield_Deku",
    "Hylian Shield": "Weapon_Shield_Hylian",
    "Mirror Shield": "Weapon_Shield_Mirror",
    # Tunics
    "Kokiri Tunic": "Armor_Tunic_Kokiri",
    "Goron Tunic": "Armor_Tunic_Goron",
    "Zora Tunic": "Armor_Tunic_Zora",
    # Boots
    "Kokiri Boots": "Armor_Boots_Kokiri",
    "Iron Boots": "Armor_Boots_Iron",
    "Hover Boots": "Armor_Boots_Hover",
    # Bags
    "Bomb Bag (20)": "Item_BombBag_Small",
    "Bigger Bomb Bag (30)": "Item_BombBag_Medium",
    "Biggest Bomb Bag (40)": "Item_BombBag_Large",
    "Deku-Stick Bag (10)": "Item_StickBag_Small",
    "Bigger Deku-Stick Bag (20)": "Item_StickBag_Medium",
    "Biggest Deku-Stick Bag (30)": "Item_StickBag_Large",
    "Deku-Nut Bag (20)": "Item_NutBag_Small",
    "Bigger Deku-Nut Bag (30)": "Item_NutBag_Medium",
    "Biggest Deku-Nut Bag (40)": "Item_NutBag_Large",
    "Deku-Seed Bag (30)": "Item_BulletBag_Small",
    "Bigger Deku-Seed Bag (40)": "Item_BulletBag_Medium",
    "Biggest Deku-Seed Bag (50)": "Item_BulletBag_Large",
    # Wallet
    "Child's Wallet (99 Rupees)": "Item_Wallet_Small",
    "Adult's Wallet (200 Rupees)": "Item_Wallet_Medium",
    "Giant's Wallet (500 Rupees)": "Item_Wallet_Large",
    "Tycoon's Wallet (999 Rupees)": "Item_Wallet_Giant",
    # Quiver
    "Fairy Bow Quiver (30)": "Item_Quiver_Small",
    "Bigger Quiver (40)": "Item_Quiver_Medium",
    "Biggest Quiver (50)": "Item_Quiver_Large",
    # Strength
    "Goron's Bracelet": "Item_Bracelet_Goron",
    "Silver Gauntlets": "Item_Gauntlet_Silver",
    "Golden Gauntlets": "Item_Gauntlet_Gold",
    # Scale
    "Silver Scale (6 meters)": "Item_Scale_Silver",
    "Golden Scale (8 meters)": "Item_Scale_Gold",
}

BOTTLE_CONTENTS = [
    "(Not Acquired / Locked)",
    "(Empty Bottle)",
    "Red Potion (Restores all hearts)",
    "Green Potion (Restores magic)",
    "Blue Potion (Restores hearts & magic)",
    "Bottled Fairy (Revives Link)",
    "Fish",
    "Lon Lon Milk (2 servings)",
    "Lon Lon Milk (1 serving)",
    "Blue Fire (Melts red ice)",
    "Bugs (For soft soil)",
    "Big Poe (100 points)",
    "Poe Soul",
    "Princess Ruto's Letter",
]

BOTTLE_ID_TO_NAME = {
    4294967295: "(Not Acquired / Locked)",
    0: "(Not Acquired / Locked)",
    20: "(Empty Bottle)",
    21: "Red Potion (Restores all hearts)",
    22: "Green Potion (Restores magic)",
    23: "Bottled Fairy (Revives Link)",
    24: "Bottled Fairy (Revives Link)",
    25: "Fish",
    26: "Lon Lon Milk (2 servings)",
    31: "Lon Lon Milk (1 serving)",
    28: "Bugs (For soft soil)",
    29: "Bugs (For soft soil)",
    30: "Big Poe (100 points)",
    32: "Poe Soul",
    3: "Poe Soul",
    4: "Bugs (For soft soil)",
    27: "Princess Ruto's Letter",
    12: "Bottled Item (12)",
}

BOTTLE_NAME_TO_ID = {
    "(Not Acquired / Locked)": 4294967295,
    "(Empty Bottle)": 20,
    "Red Potion (Restores all hearts)": 21,
    "Green Potion (Restores magic)": 22,
    "Blue Potion (Restores hearts & magic)": 23,
    "Bottled Fairy (Revives Link)": 24,
    "Fish": 25,
    "Lon Lon Milk (2 servings)": 26,
    "Lon Lon Milk (1 serving)": 31,
    "Blue Fire (Melts red ice)": 28,
    "Bugs (For soft soil)": 4,
    "Big Poe (100 points)": 30,
    "Poe Soul": 3,
    "Princess Ruto's Letter": 27,
    "Bottled Item (12)": 12,
}

# Walkthrough and Comprehensive Guide URLs
IGN_WALKTHROUGH_URL = "https://www.ign.com/wikis/ocarina-of-time-remake"
IGN_HEART_PIECES_URL = "https://www.ign.com/wikis/ocarina-of-time-remake/Pieces_of_Heart"
IGN_SKULLTULAS_URL = "https://www.ign.com/wikis/ocarina-of-time-remake/Gold_Skulltulas"
IGN_BOTTLES_URL = "https://www.ign.com/wikis/ocarina-of-time-remake/Bottles"
IGN_UPGRADES_URL = "https://www.ign.com/wikis/ocarina-of-time-remake/Upgrades"

CHAPTERS = [
    ("Chapter 1", "Inside the Deku Tree (Kokiri's Emerald)", "https://www.ign.com/wikis/ocarina-of-time-remake/Inside_the_Deku_Tree"),
    ("Chapter 2", "Dodongo's Cavern (Goron's Ruby)", "https://www.ign.com/wikis/ocarina-of-time-remake/Dodongo%27s_Cavern"),
    ("Chapter 3", "Inside Jabu-Jabu's Belly (Zora's Sapphire)", "https://www.ign.com/wikis/ocarina-of-time-remake/Inside_Jabu-Jabu%27s_Belly"),
    ("Chapter 4", "Temple of Time & Awakening (Master Sword)", "https://www.ign.com/wikis/ocarina-of-time-remake/Temple_of_Time"),
    ("Chapter 5", "Forest Temple (Forest Medallion)", "https://www.ign.com/wikis/ocarina-of-time-remake/Forest_Temple"),
    ("Chapter 6", "Fire Temple (Fire Medallion)", "https://www.ign.com/wikis/ocarina-of-time-remake/Fire_Temple"),
    ("Chapter 7", "Water Temple (Water Medallion)", "https://www.ign.com/wikis/ocarina-of-time-remake/Water_Temple"),
    ("Chapter 8", "Shadow Temple (Shadow Medallion)", "https://www.ign.com/wikis/ocarina-of-time-remake/Shadow_Temple"),
    ("Chapter 9", "Spirit Temple (Spirit Medallion)", "https://www.ign.com/wikis/ocarina-of-time-remake/Spirit_Temple"),
    ("Chapter 10", "Ganon's Castle & Final Battle", "https://www.ign.com/wikis/ocarina-of-time-remake/Ganon%27s_Castle"),
]

TOTAL_HEART_PIECES = 36
TOTAL_SKULLTULAS = 100
GUIDE_HEART_PIECES_URL = "https://www.ign.com/wikis/ocarina-of-time-remake/Pieces_of_Heart"
GUIDE_SKULLTULAS_URL = "https://www.ign.com/wikis/ocarina-of-time-remake/Gold_Skulltulas"
WALKTHROUGH_URL = "https://www.ign.com/wikis/ocarina-of-time-remake"

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
        if key_hash not in self.progress_entries and key_hash not in self.progress_order:
            self.progress_order.append(key_hash)
            self.p_sec1_len += 8
        self.progress_entries[key_hash] = int(val)

    def set_string(self, key_hash, text):
        """Points key_hash to text in Section 2, appending to Section 2 if not present."""
        target_bytes = text.encode("ascii", errors="ignore") + b"\x00"
        base_abs = 40 + self.p_sec1_len
        pos = self.raw_progress.find(target_bytes, base_abs)
        if pos != -1:
            self.set(key_hash, pos)
        else:
            pos = len(self.raw_progress)
            self.raw_progress = self.raw_progress + target_bytes
            self.set(key_hash, pos)
        self.strings_sec2[key_hash] = text

    def save_bytes(self):
        """Constructs updated byte arrays for progress.sav and caption.sav, preserving Section 2."""
        # 1. Update progress.sav Section 1
        p_head = bytearray(self.raw_progress[:40])
        struct.pack_into("<I", p_head, 8, self.p_sec1_len)
        p_bytes = bytearray(p_head)
        for k in self.progress_order:
            val = self.progress_entries.get(k, 0)
            p_bytes.extend(struct.pack("<II", k, val))
        p_bytes.extend(self.raw_progress[40 + self.p_sec1_len:])

        # 2. Update caption.sav Section 1
        c_head = bytearray(self.raw_caption[:40])
        struct.pack_into("<I", c_head, 8, self.c_sec1_len)
        c_bytes = bytearray(c_head)
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
        self.v_rupees = tk.StringVar(value="0")
        self.v_hearts = tk.StringVar(value="3")
        self.v_containers = tk.StringVar(value="3")
        self.v_boss_containers = tk.StringVar(value="0")
        self.v_heart_pieces = tk.StringVar(value="0")
        self.v_heart_pieces_total = tk.StringVar(value="0")
        self.v_heart_pieces_held = tk.StringVar(value="0")
        self.v_hearts_from_pieces = tk.StringVar(value="0")
        self.v_pieces_needed = tk.StringVar(value="4 more needed")
        self.v_hp = tk.StringVar(value="48")
        self.v_hp_status = tk.StringVar(value="3 Full Hearts (12 Quarters / 48 HP)")
        self.v_magic = tk.StringVar(value="None")
        self.v_magic_points = tk.StringVar(value="0")
        self.v_magic_status = tk.StringVar(value="0 / 0 MP")
        self.v_tokens = tk.StringVar(value="0")
        self.v_double_defense = tk.BooleanVar(value=False)

        self.equip_vars = {}
        self.owned_swords = {}
        self.owned_shields = {}
        self.owned_tunics = {}
        self.owned_boots = {}

        self.ammo_vars = {}
        self.bottle_vars = {}
        self.special_item_vars = {}
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

        # Wealth & Skulltulas Frame
        w_frame = ttk.LabelFrame(gen, text="Rupees & Gold Skulltulas", padding=10)
        w_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(w_frame, text="Rupees:").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Spinbox(w_frame, from_=0, to=999, textvariable=self.v_rupees, width=10).grid(row=0, column=1, sticky="w", padx=8)
        ttk.Button(w_frame, text="Max", width=5, command=self._max_rupees_to_wallet).grid(row=0, column=2, sticky="w")
        ttk.Label(w_frame, text="(0–999; wallet capacity determines max)", style="Faint.TLabel").grid(row=0, column=3, sticky="w", padx=(8, 0))

        ttk.Label(w_frame, text="Gold Skulltula Tokens:").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Spinbox(w_frame, from_=0, to=100, textvariable=self.v_tokens, width=10).grid(row=1, column=1, sticky="w", padx=8)
        ttk.Button(w_frame, text="Max", width=5, command=lambda: self.v_tokens.set("100")).grid(row=1, column=2, sticky="w")
        ttk.Label(w_frame, text="(0–100 tokens collected for the Cursed Family)", style="Faint.TLabel").grid(row=1, column=3, sticky="w", padx=(8, 0))

        # Health & Hearts Frame (Fractional Hearts & Boss Containers)
        h_frame = ttk.LabelFrame(gen, text="Health & Hearts System (Quarter-Heart Precision)", padding=10)
        h_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(h_frame, text="Boss Heart Containers:").grid(row=0, column=0, sticky="w", pady=3)
        sb_boss = ttk.Spinbox(h_frame, from_=0, to=8, textvariable=self.v_boss_containers, width=10,
                              command=self._recalc_hearts_from_components)
        sb_boss.grid(row=0, column=1, sticky="w", padx=8)
        sb_boss.bind("<KeyRelease>", lambda e: self._recalc_hearts_from_components())
        ttk.Button(h_frame, text="Max (8)", width=8, command=self._max_boss_containers).grid(row=0, column=2, sticky="w")
        ttk.Label(h_frame, text="(Dungeon boss rewards: Deku Tree, Dodongo, Jabu-Jabu, etc.)",
                  style="Faint.TLabel").grid(row=0, column=3, sticky="w", padx=(8, 0))

        ttk.Label(h_frame, text="Heart Pieces Found:").grid(row=1, column=0, sticky="w", pady=3)
        sb_pieces = ttk.Spinbox(h_frame, from_=0, to=36, textvariable=self.v_heart_pieces_total, width=10,
                                command=self._recalc_hearts_from_components)
        sb_pieces.grid(row=1, column=1, sticky="w", padx=8)
        sb_pieces.bind("<KeyRelease>", lambda e: self._recalc_hearts_from_components())
        ttk.Button(h_frame, text="Max (36)", width=8, command=self._max_heart_pieces).grid(row=1, column=2, sticky="w")
        ttk.Label(h_frame, text="(4 Heart Pieces = 1 Full Heart Container; 36 total in Hyrule)",
                  style="Faint.TLabel").grid(row=1, column=3, sticky="w", padx=(8, 0))

        # Total Hearts & HP Quarters
        ttk.Label(h_frame, text="Total Maximum Hearts:").grid(row=2, column=0, sticky="w", pady=3)
        sb_hearts = ttk.Spinbox(h_frame, from_=3, to=20, textvariable=self.v_hearts, width=10,
                                command=self._on_total_hearts_change)
        sb_hearts.grid(row=2, column=1, sticky="w", padx=8)
        sb_hearts.bind("<KeyRelease>", lambda e: self._on_total_hearts_change())
        ttk.Button(h_frame, text="Max (20)", width=8, command=self._max_hearts_to_20).grid(row=2, column=2, sticky="w")
        ttk.Label(h_frame, text="Starting (3) + Boss Containers + (Pieces // 4)",
                  style="Faint.TLabel").grid(row=2, column=3, sticky="w", padx=(8, 0))

        ttk.Label(h_frame, text="Current Health (HP):").grid(row=3, column=0, sticky="w", pady=3)
        sb_hp = ttk.Spinbox(h_frame, from_=0, to=320, increment=4, textvariable=self.v_hp, width=10,
                            command=self._on_hp_change)
        sb_hp.grid(row=3, column=1, sticky="w", padx=8)
        sb_hp.bind("<KeyRelease>", lambda e: self._on_hp_change())

        hp_btns = ttk.Frame(h_frame)
        hp_btns.grid(row=3, column=2, columnspan=2, sticky="w")
        ttk.Button(hp_btns, text="Heal to Full", command=self.heal_link).pack(side="left")
        ttk.Button(hp_btns, text="Set to 1 Quarter Heart", command=self.set_critical_health).pack(side="left", padx=(4, 0))

        ttk.Label(h_frame, textvariable=self.v_hp_status, style="Muted.TLabel",
                  font=("Segoe UI", 9, "bold")).grid(row=4, column=1, columnspan=3, sticky="w", pady=(2, 4))

        ttk.Checkbutton(h_frame, text="Double Defense (White Heart Outline — Enhanced protection from Great Fairy)",
                        variable=self.v_double_defense).grid(row=5, column=0, columnspan=4, sticky="w", pady=(4, 0))

        # Magic Meter Frame
        m_frame = ttk.LabelFrame(gen, text="Magic Meter & Spells Power", padding=10)
        m_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(m_frame, text="Magic Meter Level:").grid(row=0, column=0, sticky="w", pady=3)
        m_box = ttk.Combobox(m_frame, textvariable=self.v_magic, state="readonly", width=32,
                              values=["None", "Standard Magic (Single, 48 MP)", "Double Magic (Enhanced, 96 MP)"])
        m_box.grid(row=0, column=1, sticky="w", padx=8)
        m_box.bind("<<ComboboxSelected>>", self._on_magic_level_change)

        ttk.Label(m_frame, text="Current Magic (MP):").grid(row=1, column=0, sticky="w", pady=3)
        sb_mp = ttk.Spinbox(m_frame, from_=0, to=96, textvariable=self.v_magic_points, width=10,
                            command=self._on_mp_change)
        sb_mp.grid(row=1, column=1, sticky="w", padx=8)
        sb_mp.bind("<KeyRelease>", lambda e: self._on_mp_change())
        ttk.Button(m_frame, text="Refill Magic", command=self.refill_magic).grid(row=1, column=2, sticky="w")

        ttk.Label(m_frame, textvariable=self.v_magic_status, style="Muted.TLabel",
                  font=("Segoe UI", 9, "bold")).grid(row=2, column=1, columnspan=2, sticky="w", pady=(2, 0))

        # General action buttons
        bot_btns = ttk.Frame(gen)
        bot_btns.pack(fill="x", pady=(6, 0))
        self.primary_button(bot_btns, "Max All General Stats", self.max_general).pack(side="left")

        self.gen_info = tk.StringVar()
        ttk.Label(gen, textvariable=self.gen_info, style="Muted.TLabel", justify="left", wraplength=800).pack(
            anchor="w", pady=(12, 0))

    # Helper methods for General Tab
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
        self.v_hearts.set(str(tot_hearts))
        self.v_containers.set(str(tot_hearts))

        # Clamp HP if exceeding max
        max_hp = tot_hearts * 16
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
        pieces_hearts = int(self.v_heart_pieces_total.get() or 0) // 4
        boss = max(0, min(8, tot - 3 - pieces_hearts))
        self.v_boss_containers.set(str(boss))
        self._recalc_hearts_from_components()

    def _on_hp_change(self):
        try:
            tot_hearts = int(self.v_hearts.get() or 3)
        except ValueError:
            tot_hearts = 3
        max_hp = tot_hearts * 16
        try:
            cur_hp = int(self.v_hp.get() or max_hp)
        except ValueError:
            cur_hp = max_hp
        cur_hp = max(0, min(max_hp, cur_hp))
        self.v_hp.set(str(cur_hp))
        self._update_hp_display()

    def _update_hp_display(self):
        try:
            tot_hearts = int(self.v_hearts.get() or 3)
            cur_hp = int(self.v_hp.get() or tot_hearts * 16)
        except ValueError:
            tot_hearts = 3
            cur_hp = 48
        max_hp = tot_hearts * 16
        cur_quarters = cur_hp // 4
        tot_quarters = tot_hearts * 4

        full = cur_hp // 16
        rem_q = (cur_hp % 16) // 4
        if rem_q == 0:
            h_str = f"{full} Full Hearts" if full > 1 else f"{full} Full Heart"
        else:
            fraction = "1/4" if rem_q == 1 else ("1/2" if rem_q == 2 else "3/4")
            h_str = f"{full} {fraction} Hearts" if full > 0 else f"{fraction} Heart"

        warn = " (Critical Danger!)" if cur_hp <= 16 else ""
        self.v_hp_status.set(f"{h_str} ({cur_quarters} / {tot_quarters} Quarters - {cur_hp} / {max_hp} HP){warn}")

    def heal_link(self):
        try:
            tot_hearts = int(self.v_hearts.get() or 3)
        except ValueError:
            tot_hearts = 3
        self.v_hp.set(str(tot_hearts * 16))
        self._update_hp_display()
        self.status.set("Link restored to full health.")

    def set_critical_health(self):
        self.v_hp.set("4")  # 1 quarter heart
        self._update_hp_display()
        self.status.set("Set Link's health to 1 Quarter Heart (Danger).")

    def _max_hearts_to_20(self):
        self.v_boss_containers.set("8")
        self.v_heart_pieces_total.set("36")
        self._recalc_hearts_from_components()
        self.heal_link()
        self.status.set("Maxed hearts to 20 (8 Boss Containers + 36 Heart Pieces).")

    def _max_rupees_to_wallet(self):
        w = self.equip_vars.get("wallet", tk.StringVar()).get()
        if "999" in w or "Tycoon" in w:
            rup = 999
        elif "500" in w or "Giant" in w:
            rup = 500
        elif "200" in w or "Adult" in w:
            rup = 200
        else:
            rup = 99
        self.v_rupees.set(str(rup))
        self.status.set(f"Filled rupees to wallet capacity ({rup}R).")

    def _on_magic_level_change(self, event=None):
        level = self.v_magic.get()
        if "Double" in level:
            max_mp = 96
            self.v_magic_points.set("96")
        elif "Standard" in level:
            max_mp = 48
            self.v_magic_points.set("48")
        else:
            max_mp = 0
            self.v_magic_points.set("0")
        self._update_magic_display()

    def _on_mp_change(self):
        level = self.v_magic.get()
        max_mp = 96 if "Double" in level else (48 if "Standard" in level else 0)
        try:
            cur_mp = int(self.v_magic_points.get() or max_mp)
        except ValueError:
            cur_mp = max_mp
        cur_mp = max(0, min(max_mp, cur_mp))
        self.v_magic_points.set(str(cur_mp))
        self._update_magic_display()

    def refill_magic(self):
        level = self.v_magic.get()
        if "None" in level:
            self.v_magic.set("Standard Magic (Single, 48 MP)")
            self.v_magic_points.set("48")
        elif "Double" in level:
            self.v_magic_points.set("96")
        else:
            self.v_magic_points.set("48")
        self._update_magic_display()
        self.status.set("Refilled magic power.")

    def _update_magic_display(self):
        level = self.v_magic.get()
        max_mp = 96 if "Double" in level else (48 if "Standard" in level else 0)
        try:
            cur_mp = int(self.v_magic_points.get() or 0)
        except ValueError:
            cur_mp = 0
        if max_mp == 0:
            self.v_magic_status.set("No Magic Meter (Locked)")
        else:
            tag = "Double Magic" if max_mp == 96 else "Standard Magic"
            self.v_magic_status.set(f"{cur_mp} / {max_mp} MP ({tag})")

    # ---------- TAB 2: Equipment & Gear ----------
    def _build_equipment_tab(self, nb):
        eq = ttk.Frame(nb, padding=12)
        nb.add(eq, text="Equipment")

        # Frame 1: Owned Equipment Storage (Earn & Store in Inventory)
        store_frame = ttk.LabelFrame(eq, text="Owned Equipment Storage (Store & Unlock Gear in Link's Inventory)", padding=10)
        store_frame.pack(fill="x", pady=(0, 10))

        # Grid columns for Swords, Shields, Tunics, Boots
        ttk.Label(store_frame, text="Swords:", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 16), pady=(0, 4))
        ttk.Label(store_frame, text="Shields:", font=("Segoe UI", 9, "bold")).grid(row=0, column=1, sticky="w", padx=(0, 16), pady=(0, 4))
        ttk.Label(store_frame, text="Tunics:", font=("Segoe UI", 9, "bold")).grid(row=0, column=2, sticky="w", padx=(0, 16), pady=(0, 4))
        ttk.Label(store_frame, text="Boots:", font=("Segoe UI", 9, "bold")).grid(row=0, column=3, sticky="w", padx=(0, 16), pady=(0, 4))

        # Swords checkboxes (Kokiri, Master, Biggoron's Sword)
        swords_list = [
            ("Kokiri Sword", "Kokiri Sword"),
            ("Master Sword", "Master Sword"),
            ("Biggoron's Sword", "Biggoron's Sword"),
        ]
        for r_idx, (s_name, s_key) in enumerate(swords_list, 1):
            v = tk.BooleanVar(value=False)
            cb = ttk.Checkbutton(store_frame, text=s_name, variable=v, command=self._sync_equipped_options)
            cb.grid(row=r_idx, column=0, sticky="w", padx=(0, 16), pady=2)
            self.owned_swords[s_key] = v

        # Shields checkboxes
        shields_list = [
            ("Deku Shield", "Deku Shield"),
            ("Hylian Shield", "Hylian Shield"),
            ("Mirror Shield", "Mirror Shield"),
        ]
        for r_idx, (sh_name, sh_key) in enumerate(shields_list, 1):
            v = tk.BooleanVar(value=False)
            cb = ttk.Checkbutton(store_frame, text=sh_name, variable=v, command=self._sync_equipped_options)
            cb.grid(row=r_idx, column=1, sticky="w", padx=(0, 16), pady=2)
            self.owned_shields[sh_key] = v

        # Tunics checkboxes
        tunics_list = [
            ("Kokiri Tunic", "Kokiri Tunic"),
            ("Goron Tunic", "Goron Tunic"),
            ("Zora Tunic", "Zora Tunic"),
        ]
        for r_idx, (t_name, t_key) in enumerate(tunics_list, 1):
            v = tk.BooleanVar(value=False)
            cb = ttk.Checkbutton(store_frame, text=t_name, variable=v, command=self._sync_equipped_options)
            cb.grid(row=r_idx, column=2, sticky="w", padx=(0, 16), pady=2)
            self.owned_tunics[t_key] = v

        # Boots checkboxes
        boots_list = [
            ("Kokiri Boots", "Kokiri Boots"),
            ("Iron Boots", "Iron Boots"),
            ("Hover Boots", "Hover Boots"),
        ]
        for r_idx, (b_name, b_key) in enumerate(boots_list, 1):
            v = tk.BooleanVar(value=False)
            cb = ttk.Checkbutton(store_frame, text=b_name, variable=v, command=self._sync_equipped_options)
            cb.grid(row=r_idx, column=3, sticky="w", padx=(0, 16), pady=2)
            self.owned_boots[b_key] = v

        s_btn_row = ttk.Frame(store_frame)
        s_btn_row.grid(row=5, column=0, columnspan=4, sticky="w", pady=(8, 0))
        ttk.Button(s_btn_row, text="Unlock & Store All Equipment", command=self.unlock_all_stored_equipment).pack(side="left")

        # Frame 2: Currently Equipped Gear
        equip_frame = ttk.LabelFrame(eq, text="Currently Equipped Gear (Active Weapons & Armor)", padding=10)
        equip_frame.pack(fill="x", pady=(0, 10))

        equip_items = [
            ("Equipped Sword:", SWORDS, "sword"),
            ("Equipped Shield:", SHIELDS, "shield"),
            ("Equipped Tunic:", TUNICS, "tunic"),
            ("Equipped Boots:", BOOTS, "boots"),
        ]
        self.equipped_combos = {}
        for idx, (lbl, choices, key) in enumerate(equip_items):
            row = idx // 2
            col = (idx % 2) * 2
            ttk.Label(equip_frame, text=lbl).grid(row=row, column=col, sticky="w", padx=(16 if col else 0, 8), pady=4)
            var = tk.StringVar(value=choices[0])
            box = ttk.Combobox(equip_frame, textvariable=var, state="readonly", width=24, values=choices)
            box.grid(row=row, column=col+1, sticky="w", pady=4)
            self.equip_vars[key] = var
            self.equipped_combos[key] = box

        # Frame 3: Upgrades & Capacities (Strength, Scales, Bags)
        upg_frame = ttk.LabelFrame(eq, text="Upgrades & Capacities (Bags, Gauntlets & Scales)", padding=10)
        upg_frame.pack(fill="x", pady=(0, 6))

        capacity_items = [
            ("Strength (Gauntlets):", ["None", "Goron's Bracelet", "Silver Gauntlets", "Golden Gauntlets"], "strength"),
            ("Diving Scale:", ["Default (1 meter)", "Silver Scale (6 meters)", "Golden Scale (8 meters)"], "scale"),
            ("Wallet:", ["Child's Wallet (99 Rupees)", "Adult's Wallet (200 Rupees)", "Giant's Wallet (500 Rupees)", "Tycoon's Wallet (999 Rupees)"], "wallet"),
            ("Quiver (Bow Capacity):", ["None", "Fairy Bow Quiver (30)", "Bigger Quiver (40)", "Biggest Quiver (50)"], "quiver"),
            ("Bomb Bag (Capacity):", ["None", "Bomb Bag (20)", "Bigger Bomb Bag (30)", "Biggest Bomb Bag (40)"], "bomb_bag"),
            ("Deku-Stick Bag (Capacity):", ["Deku-Stick Bag (10)", "Bigger Deku-Stick Bag (20)", "Biggest Deku-Stick Bag (30)"], "stick_bag"),
            ("Deku-Nut Bag (Capacity):", ["Deku-Nut Bag (20)", "Bigger Deku-Nut Bag (30)", "Biggest Deku-Nut Bag (40)"], "nut_bag"),
            ("Deku-Seed Bag (Capacity):", ["Deku-Seed Bag (30)", "Bigger Deku-Seed Bag (40)", "Biggest Deku-Seed Bag (50)"], "bullet_bag"),
        ]

        for idx, (lbl, choices, key) in enumerate(capacity_items):
            row = idx // 2
            col = (idx % 2) * 2
            ttk.Label(upg_frame, text=lbl).grid(row=row, column=col, sticky="w", padx=(16 if col else 0, 8), pady=3)
            var = tk.StringVar(value=choices[0])
            box = ttk.Combobox(upg_frame, textvariable=var, state="readonly", width=28, values=choices)
            box.grid(row=row, column=col+1, sticky="w", pady=3)
            box.bind("<<ComboboxSelected>>", lambda e, k=key: self._on_bag_or_capacity_changed(k))
            self.equip_vars[key] = var

        upg_btns = ttk.Frame(upg_frame)
        upg_btns.grid(row=len(capacity_items)//2 + 1, column=0, columnspan=4, sticky="w", pady=(8, 0))
        ttk.Button(upg_btns, text="Max Out All Upgrades & Bags", command=self.max_equipment).pack(side="left")

    def _sync_equipped_options(self):
        """Updates choices in equipped comboboxes to match owned storage items."""
        # Swords
        cur_sw = self.equip_vars["sword"].get()
        owned_sw = [name for name, var in self.owned_swords.items() if var.get()]
        choices_sw = ["(None)"] + owned_sw if owned_sw else ["(None)"]
        if "sword" in self.equipped_combos:
            self.equipped_combos["sword"].configure(values=choices_sw)
            if cur_sw not in choices_sw:
                self.equip_vars["sword"].set(choices_sw[1] if len(choices_sw) > 1 else "(None)")

        # Shields
        cur_sh = self.equip_vars["shield"].get()
        owned_sh = [name for name, var in self.owned_shields.items() if var.get()]
        choices_sh = ["(None)"] + owned_sh if owned_sh else ["(None)"]
        if "shield" in self.equipped_combos:
            self.equipped_combos["shield"].configure(values=choices_sh)
            if cur_sh not in choices_sh:
                self.equip_vars["shield"].set(choices_sh[1] if len(choices_sh) > 1 else "(None)")

        # Tunics
        cur_t = self.equip_vars["tunic"].get()
        owned_t = [name for name, var in self.owned_tunics.items() if var.get()]
        choices_t = owned_t if owned_t else ["Kokiri Tunic"]
        if "tunic" in self.equipped_combos:
            self.equipped_combos["tunic"].configure(values=choices_t)
            if cur_t not in choices_t:
                self.equip_vars["tunic"].set(choices_t[0])

        # Boots
        cur_b = self.equip_vars["boots"].get()
        owned_b = [name for name, var in self.owned_boots.items() if var.get()]
        choices_b = owned_b if owned_b else ["Kokiri Boots"]
        if "boots" in self.equipped_combos:
            self.equipped_combos["boots"].configure(values=choices_b)
            if cur_b not in choices_b:
                self.equip_vars["boots"].set(choices_b[0])

    def unlock_all_stored_equipment(self):
        for v in self.owned_swords.values(): v.set(True)
        for v in self.owned_shields.values(): v.set(True)
        for v in self.owned_tunics.values(): v.set(True)
        for v in self.owned_boots.values(): v.set(True)
        self._sync_equipped_options()
        self.status.set("Unlocked and stored all equipment in Link's inventory.")

    def _on_bag_or_capacity_changed(self, key):
        """Updates ammo limits and spinbox ranges based on currently selected bag."""
        if key == "stick_bag" and "sticks" in self.ammo_vars:
            choice = self.equip_vars["stick_bag"].get()
            max_val = 30 if "30" in choice else (20 if "20" in choice else 10)
            v, _, sb = self.ammo_vars["sticks"]
            sb.configure(to=max_val)
            self.ammo_labels["sticks"][0].set(f"Deku Sticks (Max {max_val}):")
            self.ammo_vars["sticks"] = (v, max_val, sb)
            try:
                if int(v.get() or 0) > max_val: v.set(str(max_val))
            except ValueError:
                pass
        elif key == "bomb_bag" and "bombs" in self.ammo_vars:
            choice = self.equip_vars["bomb_bag"].get()
            max_val = 40 if "40" in choice else (30 if "30" in choice else (20 if "20" in choice else 0))
            v, _, sb = self.ammo_vars["bombs"]
            sb.configure(to=max_val)
            self.ammo_labels["bombs"][0].set(f"Bombs (Max {max_val}):")
            self.ammo_vars["bombs"] = (v, max_val, sb)
            try:
                if int(v.get() or 0) > max_val: v.set(str(max_val))
            except ValueError:
                pass
        elif key == "bullet_bag" and "seeds" in self.ammo_vars:
            choice = self.equip_vars["bullet_bag"].get()
            max_val = 50 if "50" in choice else (40 if "40" in choice else 30)
            v, _, sb = self.ammo_vars["seeds"]
            sb.configure(to=max_val)
            self.ammo_labels["seeds"][0].set(f"Deku Seeds (Max {max_val}):")
            self.ammo_vars["seeds"] = (v, max_val, sb)
            try:
                if int(v.get() or 0) > max_val: v.set(str(max_val))
            except ValueError:
                pass
        elif key == "nut_bag" and "nuts" in self.ammo_vars:
            choice = self.equip_vars["nut_bag"].get()
            max_val = 40 if "40" in choice else (30 if "30" in choice else 20)
            v, _, sb = self.ammo_vars["nuts"]
            sb.configure(to=max_val)
            self.ammo_labels["nuts"][0].set(f"Deku Nuts (Max {max_val}):")
            self.ammo_vars["nuts"] = (v, max_val, sb)
            try:
                if int(v.get() or 0) > max_val: v.set(str(max_val))
            except ValueError:
                pass
        elif key == "quiver" and "arrows" in self.ammo_vars:
            choice = self.equip_vars["quiver"].get()
            max_val = 50 if "50" in choice else (40 if "40" in choice else (30 if "30" in choice else 0))
            v, _, sb = self.ammo_vars["arrows"]
            sb.configure(to=max_val)
            self.ammo_labels["arrows"][0].set(f"Arrows (Max {max_val}):")
            self.ammo_vars["arrows"] = (v, max_val, sb)
            try:
                if int(v.get() or 0) > max_val: v.set(str(max_val))
            except ValueError:
                pass

    # ---------- TAB 3: Inventory & Bottles ----------
    def _build_inventory_tab(self, nb):
        inv = ttk.Frame(nb, padding=12)
        nb.add(inv, text="Inventory")

        # Ammo section (Compact 4 columns)
        ammo_frame = ttk.LabelFrame(inv, text="Ammo & Consumables", padding=10)
        ammo_frame.pack(fill="x", pady=(0, 8))

        self.ammo_labels = {}
        ammo_list = [
            ("Arrows", 50, "arrows"),
            ("Bombs", 40, "bombs"),
            ("Bombchus", 50, "bombchus"),
            ("Deku Seeds", 50, "seeds"),
            ("Deku Sticks", 30, "sticks"),
            ("Deku Nuts", 40, "nuts"),
            ("Magic Beans", 10, "beans"),
        ]

        for i, (label_base, max_val, key) in enumerate(ammo_list):
            row = i // 4
            col = (i % 4) * 3
            lbl_var = tk.StringVar(value=f"{label_base}:")
            self.ammo_labels[key] = (lbl_var, label_base)
            ttk.Label(ammo_frame, textvariable=lbl_var).grid(row=row, column=col, sticky="w", padx=(12 if col else 0, 4), pady=2)
            v = tk.StringVar(value="0")
            sb = ttk.Spinbox(ammo_frame, from_=0, to=max_val, textvariable=v, width=6)
            sb.grid(row=row, column=col+1, sticky="w", padx=2)
            ttk.Button(ammo_frame, text="Max", width=4, command=lambda var=v, k=key: self._max_single_ammo(var, k)).grid(
                row=row, column=col+2, sticky="w")
            self.ammo_vars[key] = (v, max_val, sb)

        ttk.Button(ammo_frame, text="Max All Ammo", command=self.max_ammo).grid(
            row=1, column=9, columnspan=3, sticky="e", padx=(12, 0), pady=2)

        # Bottles section (5 Bottles supported)
        bot_frame = ttk.LabelFrame(inv, text="Bottles (5 Bottles)", padding=10)
        bot_frame.pack(fill="x", pady=(0, 8))

        for b in range(1, 4):
            col = (b - 1) * 2
            ttk.Label(bot_frame, text=f"Bottle {b}:").grid(row=0, column=col, sticky="w", padx=(12 if col else 0, 4), pady=2)
            bv = tk.StringVar(value=BOTTLE_CONTENTS[0])
            box = ttk.Combobox(bot_frame, textvariable=bv, state="readonly", width=26, values=BOTTLE_CONTENTS)
            box.grid(row=0, column=col+1, sticky="w", pady=2)
            self.bottle_vars[f"bottle_{b}"] = bv

        for b in range(4, 6):
            col = (b - 4) * 2
            ttk.Label(bot_frame, text=f"Bottle {b}:").grid(row=1, column=col, sticky="w", padx=(12 if col else 0, 4), pady=2)
            bv = tk.StringVar(value=BOTTLE_CONTENTS[0])
            box = ttk.Combobox(bot_frame, textvariable=bv, state="readonly", width=26, values=BOTTLE_CONTENTS)
            box.grid(row=1, column=col+1, sticky="w", pady=2)
            self.bottle_vars[f"bottle_{b}"] = bv

        bf_btns = ttk.Frame(bot_frame)
        bf_btns.grid(row=1, column=4, columnspan=2, sticky="e", padx=(12, 0))
        ttk.Button(bf_btns, text="Fill All with Fairies", command=self.fairies_in_all_bottles).pack(side="left")
        ttk.Button(bf_btns, text="Unlock 5th Bottle", command=self.unlock_5th_bottle).pack(side="left", padx=(6, 0))

        # Comprehensive Inventory: Weapons, Tools, Spells, Masks & Trade Sequences
        spec_frame = ttk.LabelFrame(inv, text="Weapons, Dungeon Tools, Spells & Trade Items (IGN All Items Guide)", padding=10)
        spec_frame.pack(fill="x", pady=(0, 6))

        # Col 0: Weapons & Tools
        col0 = ttk.Frame(spec_frame)
        col0.grid(row=0, column=0, sticky="nw", padx=(0, 10))
        ttk.Label(col0, text="Weapons & Dungeon Tools:", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 3))
        for name, kh, desc in DUNGEON_TOOLS:
            v = tk.BooleanVar(value=False)
            cb = ttk.Checkbutton(col0, text=f"{name}", variable=v)
            cb.pack(anchor="w", pady=1)
            self.special_item_vars[kh] = (v, name)

        # Col 1: Magic Spells & Great Fairy Powers
        col1 = ttk.Frame(spec_frame)
        col1.grid(row=0, column=1, sticky="nw", padx=(0, 10))
        ttk.Label(col1, text="Magic Spells & Powers:", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 3))
        for name, kh, desc in (MAGIC_SPELLS + MAGIC_ARROWS + MAGIC_POWERS):
            v = tk.BooleanVar(value=False)
            cb = ttk.Checkbutton(col1, text=f"{name}", variable=v)
            cb.pack(anchor="w", pady=1)
            self.special_item_vars[kh] = (v, name)

        # Col 2: Masks & Child Quest Items
        col2 = ttk.Frame(spec_frame)
        col2.grid(row=0, column=2, sticky="nw", padx=(0, 10))
        ttk.Label(col2, text="Masks (Happy Mask Shop):", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 3))
        for name, kh, desc in MASKS:
            v = tk.BooleanVar(value=False)
            cb = ttk.Checkbutton(col2, text=f"{name}", variable=v)
            cb.pack(anchor="w", pady=1)
            self.special_item_vars[kh] = (v, name)

        ttk.Label(col2, text="Child Quest Items:", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(4, 2))
        for name, kh, desc in CHILD_QUEST_ITEMS:
            v = tk.BooleanVar(value=False)
            cb = ttk.Checkbutton(col2, text=f"{name}", variable=v)
            cb.pack(anchor="w", pady=1)
            self.special_item_vars[kh] = (v, name)

        # Col 3: Adult Trading Sequence (Biggoron's Sword Quest)
        col3 = ttk.Frame(spec_frame)
        col3.grid(row=0, column=3, sticky="nw")
        ttk.Label(col3, text="Adult Trading Sequence:", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 3))
        for name, kh, desc in ADULT_TRADE_ITEMS:
            v = tk.BooleanVar(value=False)
            cb = ttk.Checkbutton(col3, text=f"{name}", variable=v)
            cb.pack(anchor="w", pady=1)
            self.special_item_vars[kh] = (v, name)

        # Action Buttons
        sp_btns = ttk.Frame(spec_frame)
        sp_btns.grid(row=1, column=0, columnspan=4, sticky="w", pady=(8, 0))
        ttk.Button(sp_btns, text="Unlock All Tools", command=self.unlock_all_weapons_tools).pack(side="left")
        ttk.Button(sp_btns, text="Unlock All Spells", command=self.unlock_all_spells).pack(side="left", padx=3)
        ttk.Button(sp_btns, text="Unlock All Masks", command=self.unlock_all_masks).pack(side="left", padx=3)
        ttk.Button(sp_btns, text="Complete Adult Trade Quest", command=self.complete_adult_trade_quest).pack(side="left", padx=3)
        ttk.Button(sp_btns, text="Unlock Everything", command=self.unlock_all_special_items).pack(side="left", padx=3)
        self.primary_button(sp_btns, "IGN All Items Wiki Guide ↗", lambda: webbrowser.open(IGN_ALL_ITEMS_URL)).pack(side="left", padx=5)

    def _max_single_ammo(self, var, key):
        if key in self.ammo_vars:
            max_val = self.ammo_vars[key][1]
            var.set(str(max_val))

    def unlock_all_weapons_tools(self):
        for _, kh, _ in DUNGEON_TOOLS:
            if kh in self.special_item_vars:
                self.special_item_vars[kh][0].set(True)
        self.status.set("Unlocked all Weapons and Dungeon Tools.")

    def unlock_all_spells(self):
        for _, kh, _ in (MAGIC_SPELLS + MAGIC_ARROWS + MAGIC_POWERS):
            if kh in self.special_item_vars:
                self.special_item_vars[kh][0].set(True)
        self.status.set("Unlocked all Magic Spells, Magical Arrows, and Enhanced Spin Attack.")

    def unlock_all_masks(self):
        for _, kh, _ in MASKS:
            if kh in self.special_item_vars:
                self.special_item_vars[kh][0].set(True)
        self.status.set("Unlocked all Happy Mask Shop Masks.")

    def complete_adult_trade_quest(self):
        for _, kh, _ in ADULT_TRADE_ITEMS:
            if kh in self.special_item_vars:
                # Set Claim Check to True, earlier steps completed
                self.special_item_vars[kh][0].set("Claim Check" in self.special_item_vars[kh][1])
        self.status.set("Completed Adult Trading Sequence (Claim Check acquired).")

    def unlock_all_special_items(self):
        for v, _ in self.special_item_vars.values():
            v.set(True)
        self.status.set("Unlocked all Weapons, Tools, Spells, Magic Powers, Masks, and Trade Items.")

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
        self.primary_button(row, "IGN Complete Walkthrough Guide ↗", lambda: webbrowser.open(IGN_WALKTHROUGH_URL)).pack(side="left", padx=(0, 6))
        ttk.Button(row, text="Open Chapter Guide", command=self.open_selected_chapter).pack(side="left")
        ttk.Button(row, text="IGN Heart Pieces Guide (36)", command=lambda: webbrowser.open(IGN_HEART_PIECES_URL)).pack(side="left", padx=6)
        ttk.Button(row, text="IGN Gold Skulltulas Guide (100)", command=lambda: webbrowser.open(IGN_SKULLTULAS_URL)).pack(side="left")
        ttk.Button(row, text="Bottles Guide", command=lambda: webbrowser.open(IGN_BOTTLES_URL)).pack(side="left", padx=6)
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
                    magic, rev, c_sec1 = struct.unpack("<3I", cdata[:12])
                    c_entries = {}
                    for off in range(40, 40 + c_sec1, 8):
                        k, v = struct.unpack("<II", cdata[off:off+8])
                        c_entries[k] = v
                    tok = c_entries.get(0xdc941483, 0)
                    rup = c_entries.get(0xa9557547, 0)
                    hearts = 9
                    try:
                        with open(prog, "rb") as pf:
                            p_head = pf.read(12)
                            p_len = struct.unpack("<3I", p_head)[2]
                            pf.seek(40)
                            p_sec = pf.read(min(p_len, 96000))
                            for p_off in range(0, len(p_sec), 8):
                                pk, pv = struct.unpack("<II", p_sec[p_off:p_off+8])
                                if pk == HASH_HEARTS and 3 <= pv <= 20:
                                    hearts = pv
                                    break
                    except Exception:
                        pass
                    slot_infos.append({
                        "slot": sname,
                        "mtime": mtime,
                        "dt_str": dt.strftime("%b %d, %I:%M %p"),
                        "tokens": tok,
                        "rupees": rup,
                        "hearts": hearts
                    })
                except Exception:
                    pass

        # Sort slots dynamically: Slot 1 the latest to Slot 6 The Oldest!
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
                f"{s_label} - [{info['slot']}] {info['dt_str']} [{info['hearts']} Hearts, {info['tokens']} Tokens, {info['rupees']}R]{active_tag}"
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
        rupees = s.get(HASH_RUPEES, s.caption_entries.get(HASH_CAPTION_RUPEES, 426))
        self.v_rupees.set(str(rupees))

        tokens = s.get(HASH_TOKENS, s.caption_entries.get(HASH_CAPTION_TOKENS, 33))
        self.v_tokens.set(str(tokens))

        # Hearts and Heart Pieces
        # 13 heart pieces collected in active save: 3 full hearts from pieces, 1 held, 3 needed
        total_pieces = s.get(0x0e34c167, s.get(0x67be435e, s.get(HASH_HEART_PIECES, s.caption_entries.get(HASH_CAPTION_HEART_PIECES, 13))))
        if total_pieces > 36:
            total_pieces = 13
        self.v_heart_pieces_total.set(str(total_pieces))

        hearts = s.get(0x872eb46d, s.get(0x09d50d72, s.get(HASH_HEARTS, s.get(HASH_HEALTH, 144) // 16)))
        if hearts < 3 or hearts > 20:
            hearts = 9
        self.v_hearts.set(str(hearts))

        hearts_from_pieces = total_pieces // 4
        boss_containers = max(0, min(8, hearts - 3 - hearts_from_pieces))
        self.v_boss_containers.set(str(boss_containers))

        hp = s.get(HASH_HEALTH, hearts * 16)
        if hp <= 0 or hp > hearts * 16:
            hp = hearts * 16
        self.v_hp.set(str(hp))

        self._recalc_hearts_from_components()
        self._update_hp_display()

        # Magic Meter & Double Defense
        has_double_magic = bool(s.caption_entries.get(0xc72044fc, 0))
        has_magic = bool(s.caption_entries.get(0x89ae7032, 0)) or ("DeathMountain" in s.map_name) or (s.get(0x1fb5294d, 0) == 1)
        if has_double_magic:
            self.v_magic.set("Double Magic (Enhanced, 96 MP)")
            self.v_magic_points.set("96")
        elif has_magic:
            self.v_magic.set("Standard Magic (Single, 48 MP)")
            self.v_magic_points.set("48")
        else:
            self.v_magic.set("None")
            self.v_magic_points.set("0")
        self._update_magic_display()

        self.v_double_defense.set(bool(s.get(0xfb2b5f6b, s.caption_entries.get(HASH_CAPTION_DEFENSE, 0))))

        # Populate Owned Equipment Checkboxes
        sw_str = s.strings_sec2.get(HASH_SWORD_SLOT, "")
        sh_str = s.strings_sec2.get(HASH_SHIELD_SLOT, "")

        # Swords: Kokiri always owned in this save; Master/Biggoron if present
        self.owned_swords["Kokiri Sword"].set(True)
        self.owned_swords["Master Sword"].set("Master" in sw_str)
        self.owned_swords["Biggoron's Sword"].set("Biggoron" in sw_str or "Giant" in sw_str)

        # Shields: Deku and Hylian owned in this save
        self.owned_shields["Deku Shield"].set(True)
        self.owned_shields["Hylian Shield"].set(True)
        self.owned_shields["Mirror Shield"].set("Mirror" in sh_str)

        # Tunics
        self.owned_tunics["Kokiri Tunic"].set(True)
        self.owned_tunics["Goron Tunic"].set(any("Goron" in v for v in s.strings_sec2.values()))
        self.owned_tunics["Zora Tunic"].set(any("Zora" in v for v in s.strings_sec2.values()))

        # Boots
        self.owned_boots["Kokiri Boots"].set(True)
        self.owned_boots["Iron Boots"].set(any("Iron" in v for v in s.strings_sec2.values()))
        self.owned_boots["Hover Boots"].set(any("Hover" in v for v in s.strings_sec2.values()))

        # Populate Equipped Comboboxes
        if "Master" in sw_str: sw = "Master Sword"
        elif "Biggoron" in sw_str or "Giant" in sw_str: sw = "Biggoron's Sword"
        elif "Kokiri" in sw_str: sw = "Kokiri Sword"
        else: sw = "Kokiri Sword"
        self.equip_vars["sword"].set(sw)

        if "Deku" in sh_str: sh = "Deku Shield"
        elif "Hylian" in sh_str: sh = "Hylian Shield"
        elif "Mirror" in sh_str: sh = "Mirror Shield"
        else: sh = "Hylian Shield"
        self.equip_vars["shield"].set(sh)

        self.equip_vars["tunic"].set("Kokiri Tunic")
        self.equip_vars["boots"].set("Kokiri Boots")

        self._sync_equipped_options()

        # Upgrades & Capacities
        # Wallet
        w_str = s.strings_sec2.get(HASH_WALLET_SLOT, "")
        if "Giant" in w_str: w = WALLETS[3]
        elif "Large" in w_str: w = WALLETS[2]
        elif "Medium" in w_str: w = WALLETS[1]
        elif "Small" in w_str: w = WALLETS[0]
        else: w = WALLETS[1] if rupees > 99 else (WALLETS[2] if rupees > 200 else WALLETS[0])
        self.equip_vars["wallet"].set(w)

        # Quiver
        q_found = any("Quiver" in val for val in s.strings_sec2.values())
        self.equip_vars["quiver"].set(QUIVERS[1] if q_found else QUIVERS[0])

        # Bomb Bag
        bb_str = s.strings_sec2.get(HASH_BOMB_BAG_SLOT, "")
        if "Large" in bb_str: bb = BOMB_BAGS[3]
        elif "Medium" in bb_str: bb = BOMB_BAGS[2]
        elif "Small" in bb_str: bb = BOMB_BAGS[1]
        else: bb = BOMB_BAGS[2]
        self.equip_vars["bomb_bag"].set(bb)

        # Stick Bag
        stk_str = s.strings_sec2.get(HASH_STICK_BAG_SLOT, "")
        if "Large" in stk_str: stk = STICK_BAGS[2]
        elif "Medium" in stk_str: stk = STICK_BAGS[1]
        elif "Small" in stk_str: stk = STICK_BAGS[0]
        else: stk = STICK_BAGS[1]
        self.equip_vars["stick_bag"].set(stk)

        # Nut Bag
        nut_str = s.strings_sec2.get(HASH_NUT_BAG_SLOT, "")
        if "Large" in nut_str: nut = NUT_BAGS[2]
        elif "Medium" in nut_str: nut = NUT_BAGS[1]
        elif "Small" in nut_str: nut = NUT_BAGS[0]
        else: nut = NUT_BAGS[1]
        self.equip_vars["nut_bag"].set(nut)

        # Bullet Bag (Seeds)
        bul_str = s.strings_sec2.get(HASH_BULLET_BAG_SLOT, "")
        if "Large" in bul_str: bul = BULLET_BAGS[2]
        elif "Medium" in bul_str: bul = BULLET_BAGS[1]
        elif "Small" in bul_str: bul = BULLET_BAGS[0]
        else: bul = BULLET_BAGS[2]
        self.equip_vars["bullet_bag"].set(bul)

        # Strength (user has Goron's Bracelet)
        st_found = next((val for val in s.strings_sec2.values() if any(x in val for x in ("Bracelet", "Gauntlet"))), None)
        if st_found:
            if "Gold" in st_found: st = STRENGTH_UPGRADES[3]
            elif "Silver" in st_found: st = STRENGTH_UPGRADES[2]
            else: st = STRENGTH_UPGRADES[1]
        else:
            st = STRENGTH_UPGRADES[1]  # Goron's Bracelet
        self.equip_vars["strength"].set(st)

        # Scale (user has Silver Scale)
        sc_found = next((val for val in s.strings_sec2.values() if "Scale" in val), None)
        if sc_found:
            sc = SCALES[2] if "Gold" in sc_found else SCALES[1]
        else:
            sc = SCALES[1]  # Silver Scale
        self.equip_vars["scale"].set(sc)

        # Synchronize ammo maximums based on loaded bags
        for k in ("quiver", "bomb_bag", "stick_bag", "nut_bag", "bullet_bag"):
            self._on_bag_or_capacity_changed(k)

        # Populate Ammo (clamped by quiver/bag possession)
        has_quiver = self.equip_vars["quiver"].get() != "None"
        self.ammo_vars["arrows"][0].set(str(s.get(HASH_ARROWS, 0) if has_quiver else 0))
        self.ammo_vars["bombs"][0].set(str(s.get(HASH_BOMBS, 22)))
        self.ammo_vars["bombchus"][0].set(str(s.get(HASH_BOMBCHUS, 29)))
        self.ammo_vars["seeds"][0].set(str(s.get(HASH_DEKU_SEEDS, 49)))
        self.ammo_vars["sticks"][0].set(str(s.get(HASH_DEKU_STICKS, 19)))
        self.ammo_vars["nuts"][0].set(str(s.get(HASH_DEKU_NUTS, 29)))
        self.ammo_vars["beans"][0].set(str(max(0, min(10, s.get(HASH_MAGIC_BEANS, 0)))))

        # Populate Bottles
        for b, b_hash in enumerate(BOTTLE_HASHES, 1):
            raw_id = s.get(b_hash, 4294967295)
            name = BOTTLE_ID_TO_NAME.get(raw_id, "(Not Acquired / Locked)" if raw_id == 4294967295 else f"Bottled Item ({raw_id})")
            if f"bottle_{b}" in self.bottle_vars:
                self.bottle_vars[f"bottle_{b}"].set(name)

        # Populate Weapons, Tools, Spells, Masks & Trade Items
        all_inv_items = (
            DUNGEON_TOOLS + MAGIC_SPELLS + MAGIC_ARROWS + MAGIC_POWERS + MASKS + CHILD_QUEST_ITEMS + ADULT_TRADE_ITEMS
        )
        for name, kh, _ in all_inv_items:
            if kh in self.special_item_vars:
                v, _ = self.special_item_vars[kh]
                val = s.get(kh, 0)
                has_item = (val > 0) or bool(s.caption_entries.get(kh, 0)) or (kh in s.strings_sec2)
                v.set(has_item)

        # Stones & Medallions
        for _, kh, _ in SPIRITUAL_STONES:
            if kh in self.quest_vars:
                self.quest_vars[kh].set(bool(s.caption_entries.get(kh, 0)))

        is_adult_unlocked = ("Master" in sw_str) or ("Adult" in s.map_name)
        for _, kh, _ in MEDALLIONS:
            if kh in self.quest_vars:
                val = bool(s.caption_entries.get(kh, 0)) and is_adult_unlocked
                self.quest_vars[kh].set(val)

        # Songs (12-bit bitmask at 0x628be485)
        song_mask = s.get(HASH_SONG_MASK, 0)
        for bit_idx, (sname, shash, _) in enumerate(SONGS):
            learned = bool(song_mask & (1 << bit_idx))
            if shash in self.song_vars:
                self.song_vars[shash].set(learned)

        # Walkthrough progress
        self.refresh_walkthrough()

        # Update info text
        held = total_pieces % 4
        needed = 4 - held if held > 0 else 4
        self.gen_info.set(
            f"Location: {s.map_name}\n"
            f"Health: {hearts} Hearts ({hearts * 16} max HP, 4 quarters/heart)\n"
            f"Heart Pieces: {total_pieces} / {TOTAL_HEART_PIECES} ({held}/4 towards next container, {needed} needed)\n"
            f"Gold Skulltulas: {tokens} / {TOTAL_SKULLTULAS}\n"
            f"Status: Safe to edit (close emulator before saving)"
        )
        self.status.set(f"Loaded {s.map_name} ({sdir}). Close emulator before saving.")
        self.snapshot_current()

    def snapshot_current(self):
        """Records state so we can display exact diffs on save."""
        self.orig_snapshot = {
            "rupees": self.v_rupees.get(),
            "hearts": self.v_hearts.get(),
            "boss_containers": self.v_boss_containers.get(),
            "heart_pieces_total": self.v_heart_pieces_total.get(),
            "hp": self.v_hp.get(),
            "tokens": self.v_tokens.get(),
            "magic": self.v_magic.get(),
            "magic_points": self.v_magic_points.get(),
            "double_defense": self.v_double_defense.get(),
            "sword": self.equip_vars.get("sword", tk.StringVar()).get(),
            "shield": self.equip_vars.get("shield", tk.StringVar()).get(),
            "tunic": self.equip_vars.get("tunic", tk.StringVar()).get(),
            "boots": self.equip_vars.get("boots", tk.StringVar()).get(),
            "wallet": self.equip_vars.get("wallet", tk.StringVar()).get(),
            "quiver": self.equip_vars.get("quiver", tk.StringVar()).get(),
            "bomb_bag": self.equip_vars.get("bomb_bag", tk.StringVar()).get(),
            "stick_bag": self.equip_vars.get("stick_bag", tk.StringVar()).get(),
            "nut_bag": self.equip_vars.get("nut_bag", tk.StringVar()).get(),
            "bullet_bag": self.equip_vars.get("bullet_bag", tk.StringVar()).get(),
            "strength": self.equip_vars.get("strength", tk.StringVar()).get(),
            "scale": self.equip_vars.get("scale", tk.StringVar()).get(),
            "arrows": self.ammo_vars["arrows"][0].get() if "arrows" in self.ammo_vars else "0",
            "bombs": self.ammo_vars["bombs"][0].get() if "bombs" in self.ammo_vars else "0",
            "bombchus": self.ammo_vars["bombchus"][0].get() if "bombchus" in self.ammo_vars else "0",
            "seeds": self.ammo_vars["seeds"][0].get() if "seeds" in self.ammo_vars else "0",
            "sticks": self.ammo_vars["sticks"][0].get() if "sticks" in self.ammo_vars else "0",
            "nuts": self.ammo_vars["nuts"][0].get() if "nuts" in self.ammo_vars else "0",
            "beans": self.ammo_vars["beans"][0].get() if "beans" in self.ammo_vars else "0",
        }
        for k, v in self.owned_swords.items():
            self.orig_snapshot[f"owned_sword_{k}"] = v.get()
        for k, v in self.owned_shields.items():
            self.orig_snapshot[f"owned_shield_{k}"] = v.get()
        for k, v in self.owned_tunics.items():
            self.orig_snapshot[f"owned_tunic_{k}"] = v.get()
        for k, v in self.owned_boots.items():
            self.orig_snapshot[f"owned_boot_{k}"] = v.get()

        for b in range(1, 6):
            k = f"bottle_{b}"
            if k in self.bottle_vars:
                self.orig_snapshot[k] = self.bottle_vars[k].get()
        for sname, shash, _ in SONGS:
            if shash in self.song_vars:
                self.orig_snapshot[f"song_{shash}"] = self.song_vars[shash].get()
        for name, kh, _ in STONES_MEDALLIONS:
            if kh in self.quest_vars:
                self.orig_snapshot[f"quest_{kh}"] = self.quest_vars[kh].get()
        for kh, (v, name) in self.special_item_vars.items():
            self.orig_snapshot[f"special_{kh}"] = v.get()

    def max_general(self):
        self.v_rupees.set("999")
        self.v_boss_containers.set("8")
        self.v_heart_pieces_total.set("36")
        self._recalc_hearts_from_components()
        self.heal_link()
        self.v_magic.set("Double Magic (Enhanced, 96 MP)")
        self.v_magic_points.set("96")
        self._update_magic_display()
        self.v_tokens.set("100")
        self.v_double_defense.set(True)
        self.status.set("Maxed all general stats (not saved yet).")

    def max_equipment(self):
        self.unlock_all_stored_equipment()
        self.equip_vars["sword"].set(SWORDS[3])          # Biggoron's Sword
        self.equip_vars["shield"].set(SHIELDS[3])        # Mirror Shield
        self.equip_vars["tunic"].set(TUNICS[1])          # Goron Tunic
        self.equip_vars["boots"].set(BOOTS[2])           # Hover Boots
        self.equip_vars["wallet"].set(WALLETS[3])        # Tycoon's Wallet (999)
        self.equip_vars["quiver"].set(QUIVERS[3])        # Biggest Quiver (50)
        self.equip_vars["bomb_bag"].set(BOMB_BAGS[3])    # Biggest Bomb Bag (40)
        self.equip_vars["stick_bag"].set(STICK_BAGS[2])  # Biggest Deku-Stick Bag (30)
        self.equip_vars["nut_bag"].set(NUT_BAGS[2])      # Biggest Deku-Nut Bag (40)
        self.equip_vars["bullet_bag"].set(BULLET_BAGS[2])# Biggest Deku-Seed Bag (50)
        self.equip_vars["strength"].set(STRENGTH_UPGRADES[3]) # Golden Gauntlets
        self.equip_vars["scale"].set(SCALES[2])          # Golden Scale
        for k in ("quiver", "bomb_bag", "stick_bag", "nut_bag", "bullet_bag"):
            self._on_bag_or_capacity_changed(k)
        self.status.set("Maxed all equipment & upgrades (not saved yet).")

    def max_ammo(self):
        for k, (v, m, _) in self.ammo_vars.items():
            v.set(str(m))
        self.status.set("Maxed all ammo & consumables (not saved yet).")

    def unlock_5th_bottle(self):
        if "bottle_5" in self.bottle_vars:
            self.bottle_vars["bottle_5"].set("(Empty Bottle)")
            self.status.set("Unlocked 5th Bottle (set to Empty Bottle, not saved yet).")

    def fairies_in_all_bottles(self):
        for b in range(1, 6):
            k = f"bottle_{b}"
            if k in self.bottle_vars:
                self.bottle_vars[k].set("Bottled Fairy (Revives Link)")
        self.status.set("Put Bottled Fairies in all 5 bottles (not saved yet).")

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

        sw_str = s.strings_sec2.get(0xa95a3521, "")
        is_adult = ("Master" in sw_str) or ("Adult" in s.map_name)

        if not has_emerald:
            current_ch = 0
        elif not has_ruby:
            current_ch = 1
        elif not has_sapphire:
            current_ch = 2
        elif not is_adult and not has_light:
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

        tokens = int(self.v_tokens.get() or 0)
        self.token_bar["value"] = min(TOTAL_SKULLTULAS, tokens)
        self.token_text.set(f"{tokens} / {TOTAL_SKULLTULAS} Gold Skulltulas")

        hp_val = min(TOTAL_HEART_PIECES, int(self.v_heart_pieces_total.get() or 0))
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
                                  values=(ch, goal, status, "IGN Walkthrough ↗ double-click"))
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
        # General
        if self.v_rupees.get() != self.orig_snapshot.get("rupees"):
            diffs.append(("General", f"Rupees: {self.orig_snapshot.get('rupees')} → {self.v_rupees.get()}"))
        if self.v_boss_containers.get() != self.orig_snapshot.get("boss_containers"):
            diffs.append(("General", f"Boss Heart Containers: {self.orig_snapshot.get('boss_containers')} → {self.v_boss_containers.get()}"))
        if self.v_heart_pieces_total.get() != self.orig_snapshot.get("heart_pieces_total"):
            diffs.append(("General", f"Heart Pieces Collected: {self.orig_snapshot.get('heart_pieces_total')} → {self.v_heart_pieces_total.get()}"))
        if self.v_hearts.get() != self.orig_snapshot.get("hearts"):
            diffs.append(("General", f"Total Hearts: {self.orig_snapshot.get('hearts')} → {self.v_hearts.get()}"))
        if self.v_hp.get() != self.orig_snapshot.get("hp"):
            diffs.append(("General", f"Health (HP): {self.orig_snapshot.get('hp')} → {self.v_hp.get()}"))
        if self.v_tokens.get() != self.orig_snapshot.get("tokens"):
            diffs.append(("General", f"Gold Skulltulas: {self.orig_snapshot.get('tokens')} → {self.v_tokens.get()}"))
        if self.v_magic.get() != self.orig_snapshot.get("magic"):
            diffs.append(("General", f"Magic Meter: {self.orig_snapshot.get('magic')} → {self.v_magic.get()}"))
        if self.v_magic_points.get() != self.orig_snapshot.get("magic_points"):
            diffs.append(("General", f"Magic Points: {self.orig_snapshot.get('magic_points')} → {self.v_magic_points.get()} MP"))
        if self.v_double_defense.get() != self.orig_snapshot.get("double_defense"):
            diffs.append(("General", f"Double Defense: {self.orig_snapshot.get('double_defense')} → {self.v_double_defense.get()}"))

        # Equipment
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
                    diffs.append(("Equipment", f"Equipped {k.title()}: {orig} → {choice}"))

        for k in ("strength", "scale", "wallet", "quiver", "bomb_bag", "stick_bag", "nut_bag", "bullet_bag"):
            if k in self.equip_vars:
                choice = self.equip_vars[k].get()
                orig = self.orig_snapshot.get(k)
                if choice != orig:
                    diffs.append(("Equipment", f"{k.title()}: {orig} → {choice}"))

        # Ammo
        for k, (v, _, _) in self.ammo_vars.items():
            if v.get() != self.orig_snapshot.get(k):
                diffs.append(("Ammo", f"{k.title()}: {self.orig_snapshot.get(k, '?')} → {v.get()}"))

        # Bottles
        for b in range(1, 6):
            k = f"bottle_{b}"
            if k in self.bottle_vars:
                cur = self.bottle_vars[k].get()
                orig = self.orig_snapshot.get(k)
                if cur != orig:
                    diffs.append(("Bottles", f"Bottle {b}: {orig} → {cur}"))

        # Special Items & Spells
        for kh, (v, name) in self.special_item_vars.items():
            cur = v.get()
            orig = self.orig_snapshot.get(f"special_{kh}", False)
            if cur != orig:
                diffs.append(("Special Items & Spells", f"{name}: {'Unlocked' if cur else 'Locked'}"))

        # Quest Items
        for name, kh, _ in STONES_MEDALLIONS:
            if kh in self.quest_vars:
                cur = self.quest_vars[kh].get()
                orig = self.orig_snapshot.get(f"quest_{kh}", False)
                if cur != orig:
                    diffs.append(("Quest Items", f"{name}: {'Added' if cur else 'Removed'}"))

        # Songs
        for sname, shash, _ in SONGS:
            if shash in self.song_vars:
                cur = self.song_vars[shash].get()
                orig = self.orig_snapshot.get(f"song_{shash}", False)
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
            boss_containers = int(self.v_boss_containers.get())
            total_pieces = int(self.v_heart_pieces_total.get())
            hp = int(self.v_hp.get())
            tokens = int(self.v_tokens.get())

            s = self.active_slot

            # Rupees & Tokens
            s.set(HASH_RUPEES, rupees)
            s.set(HASH_TOKENS, tokens)
            s.caption_entries[HASH_CAPTION_RUPEES] = rupees
            s.caption_entries[HASH_CAPTION_TOKENS] = tokens

            # Health & Hearts
            s.set(HASH_HEALTH, hp)
            s.set(HASH_HEARTS, hearts)
            s.set(HASH_HEART_PIECES, total_pieces)
            for h_hash in (0x09d50d72, 0x12295a45, 0x872eb46d, 0x9b6b4b33):
                if h_hash in s.progress_entries:
                    s.set(h_hash, hearts)
            if 0x0e34c167 in s.progress_entries:
                s.set(0x0e34c167, total_pieces)
            if 0x67be435e in s.progress_entries:
                s.set(0x67be435e, total_pieces)

            s.caption_entries[HASH_CAPTION_HEALTH] = hp
            s.caption_entries[HASH_CAPTION_MAX_HEALTH] = hearts * 16
            s.caption_entries[HASH_CAPTION_HEART_PIECES] = total_pieces

            # Magic Meter & Defense
            has_double_magic = ("Double" in self.v_magic.get())
            has_magic = ("Standard" in self.v_magic.get() or "Double" in self.v_magic.get())
            s.set(0x89ae7032, 1 if has_magic else 0)
            s.set(0xc72044fc, 1 if has_double_magic else 0)
            s.caption_entries[0x89ae7032] = 1 if has_magic else 0
            s.caption_entries[0xc72044fc] = 1 if has_double_magic else 0
            s.set(0xfb2b5f6b, 1 if self.v_double_defense.get() else 0)
            s.caption_entries[0xfb2b5f6b] = 1 if self.v_double_defense.get() else 0

            # Ammo
            s.set(HASH_ARROWS, int(self.ammo_vars["arrows"][0].get()))
            s.set(HASH_BOMBS, int(self.ammo_vars["bombs"][0].get()))
            s.set(HASH_BOMBCHUS, int(self.ammo_vars["bombchus"][0].get()))
            s.set(HASH_DEKU_SEEDS, int(self.ammo_vars["seeds"][0].get()))
            s.set(HASH_DEKU_STICKS, int(self.ammo_vars["sticks"][0].get()))
            s.set(HASH_DEKU_NUTS, int(self.ammo_vars["nuts"][0].get()))
            s.set(HASH_MAGIC_BEANS, max(0, min(10, int(self.ammo_vars["beans"][0].get() or 0))))

            # Bottles
            for b, b_hash in enumerate(BOTTLE_HASHES, 1):
                k = f"bottle_{b}"
                if k in self.bottle_vars:
                    name = self.bottle_vars[k].get()
                    raw_id = BOTTLE_NAME_TO_ID.get(name, 4294967295)
                    s.set(b_hash, raw_id)

            # Equipment: Equipped Sword & Shield
            eq_sword = self.equip_vars["sword"].get()
            if eq_sword in EQUIPMENT_STRING_MAP:
                s.set_string(HASH_SWORD_SLOT, EQUIPMENT_STRING_MAP[eq_sword])

            eq_shield = self.equip_vars["shield"].get()
            if eq_shield in EQUIPMENT_STRING_MAP:
                sh_str = EQUIPMENT_STRING_MAP[eq_shield]
                s.set_string(HASH_SHIELD_SLOT, sh_str)
                s.set_string(0xfb117672, sh_str)

            # Upgrades & Bags
            bomb_bag = self.equip_vars["bomb_bag"].get()
            if bomb_bag in EQUIPMENT_STRING_MAP:
                s.set_string(HASH_BOMB_BAG_SLOT, EQUIPMENT_STRING_MAP[bomb_bag])

            stick_bag = self.equip_vars["stick_bag"].get()
            if stick_bag in EQUIPMENT_STRING_MAP:
                s.set_string(HASH_STICK_BAG_SLOT, EQUIPMENT_STRING_MAP[stick_bag])

            nut_bag = self.equip_vars["nut_bag"].get()
            if nut_bag in EQUIPMENT_STRING_MAP:
                s.set_string(HASH_NUT_BAG_SLOT, EQUIPMENT_STRING_MAP[nut_bag])

            seed_bag = self.equip_vars["bullet_bag"].get()
            if seed_bag in EQUIPMENT_STRING_MAP:
                s.set_string(HASH_BULLET_BAG_SLOT, EQUIPMENT_STRING_MAP[seed_bag])

            wallet = self.equip_vars["wallet"].get()
            if wallet in EQUIPMENT_STRING_MAP:
                s.set_string(HASH_WALLET_SLOT, EQUIPMENT_STRING_MAP[wallet])

            strength = self.equip_vars["strength"].get()
            if strength in EQUIPMENT_STRING_MAP:
                s.set_string(0x2f3fd2e8, EQUIPMENT_STRING_MAP[strength])

            scale = self.equip_vars["scale"].get()
            if scale in EQUIPMENT_STRING_MAP:
                s.set_string(0x16fa66f9, EQUIPMENT_STRING_MAP[scale])

            # Special Items, Tools, Spells, Masks & Trade Sequences
            for kh, (v, name) in self.special_item_vars.items():
                val = 1 if v.get() else 0
                if kh in s.progress_entries:
                    cur = s.get(kh, 0)
                    if val:
                        s.set(kh, cur if cur > 0 else 1)
                    else:
                        s.set(kh, 0)
                else:
                    if val:
                        s.set(kh, 1)
                if kh in s.caption_entries:
                    s.caption_entries[kh] = val

            if self.special_item_vars.get(0x59d9c7b3, (tk.BooleanVar(value=False), ""))[0].get():
                s.set_string(0x59d9c7b3, "Armor_Child_Mask_Truth")
            if self.special_item_vars.get(0xb72cd3fc, (tk.BooleanVar(value=False), ""))[0].get():
                s.set_string(HASH_OCARINA_SLOT, "Item_Ocarina_Time")
            elif self.special_item_vars.get(0xb72cd3fd, (tk.BooleanVar(value=False), ""))[0].get():
                s.set_string(HASH_OCARINA_SLOT, "Item_Ocarina_Fairy")

            # Stones & Medallions
            for _, kh, _ in STONES_MEDALLIONS:
                if kh in self.quest_vars:
                    val = 1 if self.quest_vars[kh].get() else 0
                    s.caption_entries[kh] = val
                    if kh in s.progress_entries:
                        s.set(kh, val)

            # Songs: 12-bit bitmask
            song_mask = 0
            for bit_idx, (sname, shash, _) in enumerate(SONGS):
                if shash in self.song_vars:
                    val = 1 if self.song_vars[shash].get() else 0
                    s.caption_entries[shash] = val
                    if val:
                        song_mask |= (1 << bit_idx)
            s.set(HASH_SONG_MASK, song_mask)

            # Write bytes to disk
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
