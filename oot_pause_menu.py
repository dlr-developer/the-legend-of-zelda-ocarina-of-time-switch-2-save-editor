"""
The Legend of Zelda: Ocarina of Time (Nintendo Switch 2 Remake) - In-Game Pause Menu Interactive UI
Follows the authentic Switch 2 in-game pause menu structure (Collection, Equipment, Items, Key Items, Threads of Time, Song Book).
Driven by pause_menu_layout.json, scaled uniformly to the canvas (aspect-preserved, letterboxed).
Text loaded from menu_text.json.
Keeps existing Song Book / Key Items / Important Items code reachable for parallel tasks.
"""

import os
import sys
import math
import json
import re
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import tkinter.font as tkfont

try:
    from PIL import Image, ImageTk, ImageEnhance, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import app_paths
    RESOURCE_DIR = app_paths.RESOURCE_DIR
except Exception:
    RESOURCE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))

import oot_scarecrow

SWITCH2_ASSETS_DIR = os.path.join(RESOURCE_DIR, "assets", "switch2_ui")

# Load pause menu layout specification
LAYOUT_PATH = os.path.join(RESOURCE_DIR, "pause_menu_layout.json")
if not os.path.exists(LAYOUT_PATH):
    LAYOUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pause_menu_layout.json")

try:
    with open(LAYOUT_PATH, "r", encoding="utf-8") as _f:
        PAUSE_MENU_LAYOUT = json.load(_f)
except Exception:
    PAUSE_MENU_LAYOUT = {
        "reference_size": [1920, 1080],
        "plus_menu": {
            "tabs": ["Collection", "Equipment", "Items", "Key Items", "Threads of Time", "Song Book"],
            "top_bar": {
                "height": 95,
                "hearts": [40, 25],
                "magic_bar": [40, 82, 195, 90],
                "tabs_y": 42,
                "tab_x": {"L": 465, "Collection": 615, "Equipment": 845, "Items": 1075, "R": 1455},
                "rupees": [1880, 50],
            },
            "button_hints_y": 1050,
            "pages": {},
        },
    }

# Load menu text specification (items, chapters, songs)
MENU_TEXT_PATH = os.path.join(RESOURCE_DIR, "menu_text.json")
if not os.path.exists(MENU_TEXT_PATH):
    MENU_TEXT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "menu_text.json")

MENU_TEXT = {"items": {}, "chapters": {}, "songs": []}
try:
    with open(MENU_TEXT_PATH, "r", encoding="utf-8") as _mf:
        _loaded = json.load(_mf)
        if isinstance(_loaded, dict):
            MENU_TEXT["items"] = _loaded.get("items", {}) if isinstance(_loaded.get("items"), dict) else {}
            MENU_TEXT["chapters"] = _loaded.get("chapters", {}) if isinstance(_loaded.get("chapters"), dict) else {}
            MENU_TEXT["songs"] = _loaded.get("songs", []) if isinstance(_loaded.get("songs"), list) else []
except Exception:
    MENU_TEXT = {"items": {}, "chapters": {}, "songs": []}

# Load Threads of Time chapters specification
THREADS_PATH = os.path.join(RESOURCE_DIR, "threads_of_time.json")
if not os.path.exists(THREADS_PATH):
    THREADS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "threads_of_time.json")

try:
    with open(THREADS_PATH, "r", encoding="utf-8") as _tf:
        THREADS_OF_TIME_DATA = json.load(_tf)
except Exception:
    THREADS_OF_TIME_DATA = {"chapters": []}

# Nintendo Switch 2 In-Game Pause Menu Warm Carved Wood & Obsidian Colors
COLOR_BG = "#1d140d"                 # Dark warm brown pause background
COLOR_INNER_PANEL = "#0d0906"        # Near-black area behind preview
COLOR_PANEL_BG = "#3b2a1b"           # Lighter carved-wood brown panel behind slots
COLOR_PANEL_BORDER = "#24180e"       # 1px darker inner border
COLOR_TOP_BAR = "#785233"            # Carved wood header band
COLOR_TOP_BAR_ACCENT = "#8a6238"     # Lighter carved wood highlight
COLOR_TOP_BAR_BOTTOM = "#3b2616"     # Darker carved bottom contour
COLOR_TAB_ACTIVE_BG = "#382414"      # Active tab trapezoid backing
COLOR_SLOT_BG = "#1c130c"            # Unowned/recessed dark slot fill
COLOR_SLOT_BORDER = "#5a4128"        # Thin lighter beveled slot border
COLOR_SLOT_RIM = "#6b4f36"           # Carved outer rim around every slot
COLOR_SLOT_RECESS = "#1a120b"        # Dark recess inside the rim
COLOR_SLOT_SHADOW = "#0b0704"        # Soft drop shadow under a slot
COLOR_SLOT_INNER_EDGE = "#8a6a48"    # Lighter 2px inner edge along the top/left
COLOR_SLOT_EQUIPPED = "#c9a227"      # Equipped item slot gold fill
COLOR_SLOT_EQUIPPED_BORDER = "#facc15" # Equipped slot bright gold border
COLOR_CURSOR_WHITE = "#ffffff"       # Selected slot inner white glowing stroke
COLOR_CURSOR_GLOW = "#cbd5e1"        # Selected slot outer glowing stroke
COLOR_TEXT = "#ffffff"               # Clean crisp white
COLOR_TEXT_CREAM = "#f3e6c8"         # Warm parchment cream text
COLOR_TEXT_DIM = "#7c6a58"           # Muted/disabled brown text
COLOR_GREEN = "#5ad04a"              # Capacity max green / emerald magic
COLOR_HEART_RED = "#e8452c"          # In-game heart red
COLOR_HEART_OUTLINE = "#7a1a10"      # Darker outline for hearts
COLOR_MAGIC_GREEN = "#3fb24a"        # Magic bar green segments
COLOR_GOLD = "#e5c158"               # UI accent gold
COLOR_CYAN = "#38bdf8"               # Switch 2 trigger cyan

# Legacy Parchment Colors for Song Book compatibility
COLOR_PARCHMENT = "#F4ECD8"
COLOR_PARCHMENT_BORDER = "#854D0E"
COLOR_PARCHMENT_LINE = "#926322"
COLOR_PARCHMENT_TEXT = "#2E1A05"

# Upgrades choices in display order for tier cycling
UPGRADE_TIER_CHOICES = {
    "bomb_bag": ["No Bomb Bag (Locked)", "Bomb Bag (20)", "Big Bomb Bag (30)", "Biggest Bomb Bag (40)"],
    "quiver": ["No Quiver (Locked)", "Quiver (30)", "Big Quiver (40)", "Biggest Quiver (50)"],
    "bullet_bag": ["Deku-Seed Bag (30)", "Bigger Deku-Seed Bag (40)", "Biggest Deku-Seed Bag (50)"],
    "stick_bag": ["Deku-Stick Bag (10)", "Bigger Deku-Stick Bag (20)", "Biggest Deku-Stick Bag (30)"],
    "nut_bag": ["Deku-Nut Bag (20)", "Bigger Deku-Nut Bag (30)", "Biggest Deku-Nut Bag (40)"],
    "wallet": ["Default Child's Wallet (99)", "Adult's Wallet (200)", "Giant's Wallet (500)", "Tycoon's Wallet (1000)"],
    "strength": ["None", "Goron's Bracelet", "Silver Gauntlets", "Golden Gauntlets"],
    "scale": ["Default (1 meter)", "Silver Scale (6 meters)", "Golden Scale (8 meters)"],
}

# Song Book Short Names and Arc Order (for backwards compatibility)
SONG_SHORT_NAMES = {
    "Zelda's Lullaby": "Lullaby",
    "Song of Time": "Time",
    "Sun's Song": "Sun",
    "Song of Storms": "Storms",
    "Epona's Song": "Epona",
    "Saria's Song": "Saria",
    "Scarecrow's Song": "Scarecrow",
    "Minuet of Forest": "Minuet",
    "Bolero of Fire": "Bolero",
    "Serenade of Water": "Serenade",
    "Nocturne of Shadow": "Nocturne",
    "Requiem of Spirit": "Requiem",
    "Prelude of Light": "Prelude",
}

OUTER_ARC_SONGS = [
    "Zelda's Lullaby",
    "Song of Time",
    "Sun's Song",
    "Song of Storms",
    "Epona's Song",
    "Saria's Song",
    "Scarecrow's Song",
]

INNER_ARC_SONGS = [
    "Minuet of Forest",
    "Bolero of Fire",
    "Serenade of Water",
    "Nocturne of Shadow",
    "Requiem of Spirit",
    "Prelude of Light",
]


def compute_song_arc_positions(width, height, radius=28):
    """Compute (song_name, x, y, radius) positions for the 13 songs on outer and inner arcs."""
    positions = []
    cx = width / 2.0
    outer_span = width * 0.80
    outer_left = cx - outer_span / 2.0
    step_outer = outer_span / 6.0
    y_outer_base = height * 0.32
    arch_outer = height * 0.12

    for i, name in enumerate(OUTER_ARC_SONGS):
        x = outer_left + i * step_outer
        t = (i - 3.0) / 3.0
        y = y_outer_base - arch_outer * (1.0 - t * t)
        positions.append((name, x, y, radius))

    inner_span = width * 0.62
    inner_left = cx - inner_span / 2.0
    step_inner = inner_span / 5.0
    y_inner_base = height * 0.72
    arch_inner = height * 0.10

    for j, name in enumerate(INNER_ARC_SONGS):
        x = inner_left + j * step_inner
        t_in = (j - 2.5) / 2.5
        y = y_inner_base - arch_inner * (1.0 - t_in * t_in)
        positions.append((name, x, y, radius))

    return positions


# The five button notes sit on the five staff lines, bottom to top: L, R, A, Y, X.
STAFF_LINE_PITCHES = (4, 7, 11, 13, 16)


def compute_staff_note_y(pitch_val, staff_top_y, staff_bot_y):
    """Canvas y for a note value: button notes land exactly on their staff line,
    other pitches are placed proportionally between the neighbouring lines."""
    pts = STAFF_LINE_PITCHES
    step = (staff_bot_y - staff_top_y) / float(len(pts) - 1)
    p = float(pitch_val)
    if p <= pts[0]:
        pos = (p - pts[0]) / float(pts[1] - pts[0])
    elif p >= pts[-1]:
        pos = (len(pts) - 1) + (p - pts[-1]) / float(pts[-1] - pts[-2])
    else:
        pos = 0.0
        for i in range(len(pts) - 1):
            if pts[i] <= p <= pts[i + 1]:
                pos = i + (p - pts[i]) / float(pts[i + 1] - pts[i])
                break
    return staff_bot_y - pos * step


def murmur3_32(key, seed: int = 0) -> int:
    """Pure-Python MurmurHash3_32 (x86, 32-bit) implementation."""
    if isinstance(key, str):
        data = key.encode("utf-8")
    elif isinstance(key, (bytes, bytearray)):
        data = bytes(key)
    else:
        data = str(key).encode("utf-8")
    length = len(data)
    h = seed & 0xFFFFFFFF
    c1 = 0xCC9E2D51
    c2 = 0x1B873593
    nblocks = length // 4
    for i in range(nblocks):
        k = data[i * 4] | (data[i * 4 + 1] << 8) | (data[i * 4 + 2] << 16) | (data[i * 4 + 3] << 24)
        k = (k * c1) & 0xFFFFFFFF
        k = ((k << 15) | (k >> 17)) & 0xFFFFFFFF
        k = (k * c2) & 0xFFFFFFFF
        h ^= k
        h = ((h << 13) | (h >> 19)) & 0xFFFFFFFF
        h = (h * 5 + 0xE6546B64) & 0xFFFFFFFF
    tail = data[nblocks * 4:]
    k1 = 0
    if len(tail) == 3:
        k1 ^= tail[2] << 16
    if len(tail) >= 2:
        k1 ^= tail[1] << 8
    if len(tail) >= 1:
        k1 ^= tail[0]
        k1 = (k1 * c1) & 0xFFFFFFFF
        k1 = ((k1 << 15) | (k1 >> 17)) & 0xFFFFFFFF
        k1 = (k1 * c2) & 0xFFFFFFFF
        h ^= k1
    h ^= length
    h ^= (h >> 16)
    h = (h * 0x85EBCA6B) & 0xFFFFFFFF
    h ^= (h >> 13)
    h = (h * 0xC2B2AE35) & 0xFFFFFFFF
    h ^= (h >> 16)
    return h


def get_key_item_info_map():
    """Return map of actor name -> (English name, quest_vars hash)."""
    fallback = {
        "Item_Stone_Forest": ("Kokiri's Emerald", 0xCBD1E58C),
        "Item_Stone_Fire": ("Goron's Ruby", 0x7D69AD47),
        "Item_Stone_Water": ("Zora's Sapphire", 0xB8E3BF45),
        "Item_Medal_Light": ("Light Medallion", 0x235C7D9A),
        "Item_Medal_Forest": ("Forest Medallion", 0x692D57CB),
        "Item_Medal_Fire": ("Fire Medallion", 0x5CE254A6),
        "Item_Medal_Water": ("Water Medallion", 0x0151A68F),
        "Item_Medal_Shadow": ("Shadow Medallion", 0x204D2063),
        "Item_Medal_Spirit": ("Spirit Medallion", 0x0C7A5FD0),
    }
    try:
        from oot_save_editor import SPIRITUAL_STONES, MEDALLIONS
        name_to_hash = {name: h for name, h, _ in (SPIRITUAL_STONES + MEDALLIONS)}
        item_to_name = {
            "Item_Stone_Forest": "Kokiri's Emerald",
            "Item_Stone_Fire": "Goron's Ruby",
            "Item_Stone_Water": "Zora's Sapphire",
            "Item_Medal_Light": "Light Medallion",
            "Item_Medal_Forest": "Forest Medallion",
            "Item_Medal_Fire": "Fire Medallion",
            "Item_Medal_Water": "Water Medallion",
            "Item_Medal_Shadow": "Shadow Medallion",
            "Item_Medal_Spirit": "Spirit Medallion",
        }
        res = {}
        for item, en_name in item_to_name.items():
            h = name_to_hash.get(en_name, fallback[item][1])
            res[item] = (en_name, h)
        return res
    except Exception:
        return fallback


KEY_ITEM_ASSET_NAMES = {
    "Item_Medal_Light": "medallion_light.png",
    "Item_Medal_Forest": "medallion_forest.png",
    "Item_Medal_Fire": "medallion_fire.png",
    "Item_Medal_Water": "medallion_water.png",
    "Item_Medal_Shadow": "medallion_shadow.png",
    "Item_Medal_Spirit": "medallion_spirit.png",
    "Item_Stone_Forest": "stone_kokiri_emerald.png",
    "Item_Stone_Fire": "stone_goron_ruby.png",
    "Item_Stone_Water": "stone_zoras_sapphire.png",
}


def get_hexagon_flat_points(cx, cy, r):
    """Return flat top and bottom regular hexagon points."""
    pts = []
    for deg in (-60, 0, 60, 120, 180, 240):
        rad = math.radians(deg)
        pts.extend([cx + r * math.cos(rad), cy + r * math.sin(rad)])
    return pts


def safe_int(value, default=0):
    """Safely convert a value or Tk variable to int, returning default on invalid text or error."""
    if hasattr(value, "get"):
        try:
            value = value.get()
        except Exception:
            return default
    if value is None:
        return default
    try:
        if isinstance(value, (int, float)):
            return int(value)
        val_str = str(value).strip()
        if not val_str:
            return default
        return int(val_str)
    except (ValueError, TypeError):
        return default


def _font(px_at_ref, weight="normal", scale=1.0):
    """Return Tk font tuple with pixel size (negative int)."""
    return ("Segoe UI", -max(8, round(px_at_ref * scale)), weight)


def unwrap_caption(text):
    """Unwrap imported captions: replace single newlines with spaces and collapse
    repeated spaces, while preserving blank lines as paragraph breaks."""
    if not text:
        return ""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return ""
    paragraphs = re.split(r'\n\s*\n', normalized)
    unwrapped_paras = []
    for para in paragraphs:
        cleaned = " ".join(para.split())
        if cleaned:
            unwrapped_paras.append(cleaned)
    return "\n\n".join(unwrapped_paras)



# Actor names to generated PNG assets in assets/switch2_ui
ACTOR_TO_GENERATED_FILE = {
    # Items
    "Item_DekuStick": "item_deku_stick.png",
    "Weapon_Range_SlingShot": "item_slingshot.png",
    "Item_MagicBean": "item_magic_beans.png",
    "Item_Boomerang": "item_boomerang.png",
    "Weapon_Range_Bow": "item_bow.png",
    "Item_Arrow_Normal": "arrow_normal.png",
    "Item_Hookshot": "item_hookshot.png",
    "Item_Longshot": "item_longshot.png",
    "Item_Arrow_Fire": "arrow_fire.png",
    "Pouch_Range_BowAndArrow_Fire": "arrow_fire.png",
    "Item_Arrow_Ice": "arrow_ice.png",
    "Pouch_Range_BowAndArrow_Ice": "arrow_ice.png",
    "Item_Arrow_Light": "arrow_light.png",
    "Pouch_Range_BowAndArrow_Light": "arrow_light.png",
    "Item_Hammer": "item_hammer.png",
    "Item_Bomb": "item_bomb.png",
    "Item_Bombchu": "item_bombchu.png",
    "Item_DekuNut": "item_deku_nut.png",
    "Item_ScrubBusinessSeed": "item_scrub_seed.png",
    "Item_DinFire": "spell_dins_fire.png",
    "Item_FaroreWind": "spell_farores_wind.png",
    "Item_NayruLove": "spell_nayrus_love.png",
    "Item_ClaimCheck": "item_claim_check.png",
    "Item_EyeDrop": "item_eye_drops.png",
    "Item_EyeballFrog": "item_eyeball_frog.png",
    "Item_Prescription": "item_prescription.png",
    "Item_BrokenSword": "item_broken_sword.png",
    "Item_PoacherSaw": "item_poachers_saw.png",
    "Item_OddPowder": "item_odd_potion.png",
    "Item_OddMushroom": "item_odd_mushroom.png",
    "Item_CojiroCucco": "item_cojiro.png",
    "Item_PocketCucco": "item_cucco.png",
    "Item_PocketEgg": "item_pocket_egg.png",
    "Item_ZeldaLetter": "item_zeldas_letter.png",
    "Item_AlarmCucco": "item_cucco.png",
    "Item_WeirdEgg": "item_weird_egg.png",
    "Pouch_Amiibo": "item_amiibo.png",
    # Bottles
    "Item_Bottle": "bottle_empty.png",
    "Item_Bottle_RedPotion": "bottle_red_potion.png",
    "Item_Bottle_GreenPotion": "bottle_green_potion.png",
    "Item_Bottle_BluePotion": "bottle_blue_potion.png",
    "Item_Bottle_BlueFire": "bottle_blue_fire.png",
    "Item_Bottle_Fish": "bottle_fish.png",
    "Item_Bottle_Letter": "bottle_rutos_letter.png",
    "Item_Bottle_BigPoe": "bottle_big_poe.png",
    "Item_Bottle_Poe": "bottle_poe.png",
    "Item_Bottle_Bug": "bottle_bug.png",
    "Item_Bottle_Fairy": "bottle_fairy.png",
    "Item_Bottle_Milk": "bottle_milk.png",
    "Item_Bottle_HalfMilk": "bottle_half_milk.png",
    # Equipment
    "Weapon_Sword_Kokiri": "sword_kokiri.png",
    "Weapon_Sword_Master": "sword_master.png",
    "Weapon_Sword_Biggoron": "sword_biggoron.png",
    "Weapon_Sword_Giant": "sword_giants_knife.png",
    "Weapon_Sword_BrokenGiant": "item_broken_sword.png",
    "Weapon_Shield_Deku": "shield_deku.png",
    "Weapon_Shield_Hylian": "shield_hylian.png",
    "Weapon_Shield_Mirror": "shield_mirror.png",
    "Obj_Armor_Child_Normal": "tunic_kokiri.png",
    "Armor_Adult_Normal": "tunic_kokiri.png",
    "Armor_Adult_Goron": "tunic_goron.png",
    "Armor_Adult_Zora": "tunic_zora.png",
    "Armor_Child_Mask_Truth": "mask_truth.png",
    "Armor_Child_Mask_Goron": "mask_goron.png",
    "Armor_Child_Mask_Zora": "mask_zora.png",
    "Armor_Child_Mask_Gerudo": "mask_gerudo.png",
    "Armor_Child_Mask_Bunny": "mask_bunny.png",
    "Armor_Child_Mask_Spooky": "mask_spooky.png",
    "Armor_Child_Mask_Skull": "mask_skull.png",
    "Armor_Child_Mask_Keaton": "mask_keaton.png",
    "Armor_GlassTruth": "item_lens_of_truth.png",
    "Armor_Child_Mask_Amiibo0": "mask_bonus.png",
    "Armor_Child_Mask_Amiibo1": "mask_bonus.png",
    "Armor_Adult_HeavyBoot": "boots_iron.png",
    "Armor_Adult_HoverBoot": "boots_hover.png",
    "Item_AgonyStone": "stone_of_agony.png",
    # Collection
    "Item_Token_Gold": "token_skulltula.png",
    "Obj_Heart_Piece": "heart_full.png",
    "Item_Ocarina_Fairy": "item_ocarina_fairy.png",
    "Item_Ocarina_Time": "item_ocarina_of_time.png",
    "Item_FairyBless_MP": "gift_spin.png",
    "Item_FairyBless_MPDouble": "gift_magic.png",
    "Item_FairyBless_DefenseDouble": "heart_full_dd.png",
    "Armor_Child_Gauntlet_Goron": "gear_goron_bracelet.png",
    "Item_Scale_Silver": "scale_silver.png",
    "Item_Scale_Gold": "scale_golden.png",
    "Armor_Adult_Gauntlet_Silver": "gear_silver_gauntlets.png",
    "Armor_Adult_Gauntlet_Gold": "gear_golden_gauntlets.png",
    "Item_Token_Gerudo": "item_gerudo_card.png",
    "Item_Wallet_Small": "wallet_adults.png",
    "Item_Wallet_Medium": "wallet_giants.png",
    "Item_Wallet_Large": "wallet_tycoons.png",
    "Item_StickBag_Small": "item_stick_bag.png",
    "Item_StickBag_Medium": "item_stick_bag.png",
    "Item_StickBag_Large": "item_stick_bag.png",
    "Item_NutBag_Small": "item_nut_bag.png",
    "Item_NutBag_Medium": "item_nut_bag.png",
    "Item_NutBag_Large": "item_nut_bag.png",
    "Item_BulletBag_Small": "bag_bullet.png",
    "Item_BulletBag_Medium": "bag_bullet.png",
    "Item_BulletBag_Large": "bag_bullet.png",
    "Item_BombBag_Small": "bag_bomb.png",
    "Item_BombBag_Medium": "bag_bomb.png",
    "Item_BombBag_Large": "bag_bomb.png",
    "Item_Quiver_Small": "bag_quiver.png",
    "Item_Quiver_Medium": "bag_quiver.png",
    "Item_Quiver_Large": "bag_quiver.png",
}


def _prettify_actor(actor: str) -> str:
    """Prettify an actor identifier into a readable display name."""
    if not actor:
        return ""
    s = str(actor)
    for prefix in (
        "Item_Bottle_", "Item_Arrow_", "Item_", "Weapon_Range_", "Weapon_Sword_",
        "Weapon_Shield_", "Armor_Child_Mask_", "Armor_Adult_Gauntlet_",
        "Armor_Adult_", "Armor_Child_", "Armor_", "Obj_Heart_", "Obj_", "Pouch_Range_", "Pouch_",
    ):
        if s.startswith(prefix):
            s = s[len(prefix):]
            break
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)
    return s.replace("_", " ").strip()


BOTTLE_STRING_TO_ACTOR = {
    "(Not Acquired / Locked)": None,
    "Empty Bottle": "Item_Bottle",
    "Red Potion": "Item_Bottle_RedPotion",
    "Blue Potion": "Item_Bottle_BluePotion",
    "Green Potion": "Item_Bottle_GreenPotion",
    "Blue Fire": "Item_Bottle_BlueFire",
    "Fish": "Item_Bottle_Fish",
    "Ruto's Letter": "Item_Bottle_Letter",
    "Big Poe": "Item_Bottle_BigPoe",
    "Poe": "Item_Bottle_Poe",
    "Bug": "Item_Bottle_Bug",
    "Bugs": "Item_Bottle_Bug",
    "Fairy": "Item_Bottle_Fairy",
    "Lon Lon Milk": "Item_Bottle_Milk",
    "Milk": "Item_Bottle_Milk",
    "Half Milk": "Item_Bottle_HalfMilk",
}

ACTOR_TO_BOTTLE_STRING = {
    "Item_Bottle": "Empty Bottle",
    "Item_Bottle_RedPotion": "Red Potion",
    "Item_Bottle_BluePotion": "Blue Potion",
    "Item_Bottle_GreenPotion": "Green Potion",
    "Item_Bottle_BlueFire": "Blue Fire",
    "Item_Bottle_Fish": "Fish",
    "Item_Bottle_Letter": "Ruto's Letter",
    "Item_Bottle_BigPoe": "Big Poe",
    "Item_Bottle_Poe": "Poe",
    "Item_Bottle_Bug": "Bug",
    "Item_Bottle_Fairy": "Fairy",
    "Item_Bottle_Milk": "Lon Lon Milk",
    "Item_Bottle_HalfMilk": "Half Milk",
}

MASK_NAME_TO_ACTOR = {
    "Mask of Truth": "Armor_Child_Mask_Truth",
    "Goron Mask": "Armor_Child_Mask_Goron",
    "Zora Mask": "Armor_Child_Mask_Zora",
    "Gerudo Mask": "Armor_Child_Mask_Gerudo",
    "Bunny Hood": "Armor_Child_Mask_Bunny",
    "Spooky Mask": "Armor_Child_Mask_Spooky",
    "Skull Mask": "Armor_Child_Mask_Skull",
    "Keaton Mask": "Armor_Child_Mask_Keaton",
}

CHILD_QUEST_CHOICES = ["None", "Weird Egg", "Zelda's Letter"]
ADULT_TRADE_CHOICES = [
    "None", "Pocket Egg", "Pocket Cucco", "Cojiro", "Odd Mushroom", "Odd Poultice",
    "Poacher's Saw", "Broken Goron Sword", "Prescription", "Eyeball Frog",
    "Specialty Eye Drops", "Biggoron Receipt"
]

TRADE_NAME_TO_ACTOR = {
    "Weird Egg": "Item_WeirdEgg",
    "Zelda's Letter": "Item_ZeldaLetter",
    "Pocket Egg": "Item_PocketEgg",
    "Pocket Cucco": "Item_PocketCucco",
    "Cojiro": "Item_CojiroCucco",
    "Odd Mushroom": "Item_OddMushroom",
    "Odd Poultice": "Item_OddPowder",
    "Poacher's Saw": "Item_PoacherSaw",
    "Broken Goron Sword": "Item_BrokenSword",
    "Prescription": "Item_Prescription",
    "Eyeball Frog": "Item_EyeballFrog",
    "Specialty Eye Drops": "Item_EyeDrop",
    "Biggoron Receipt": "Item_ClaimCheck",
}


def _get_trade_choices():
    """Return (CHILD_QUEST_CHOICES, ADULT_TRADE_CHOICES) lazily from oot_save_editor if importable."""
    try:
        from oot_save_editor import CHILD_QUEST_CHOICES as cqc, ADULT_TRADE_CHOICES as atc
        return list(cqc), list(atc)
    except Exception:
        return list(CHILD_QUEST_CHOICES), list(ADULT_TRADE_CHOICES)


def compute_heart_polygon_points(cx, cy, w, h, num_points=40, expand=0.0):
    """Compute polygon points for parametric heart curve x=16 sin^3 t, y=13 cos t - 5 cos 2t - 2 cos 3t - cos 4t."""
    pts = []
    scaled_w = w + expand * 2.0
    scaled_h = h + expand * 2.0
    for i in range(num_points):
        t = i * (2.0 * math.pi / float(num_points))
        xt = 16.0 * (math.sin(t) ** 3)
        yt = -(13.0 * math.cos(t) - 5.0 * math.cos(2.0 * t) - 2.0 * math.cos(3.0 * t) - math.cos(4.0 * t))
        px = cx + (xt / 32.0) * scaled_w
        py = cy + ((yt - 2.55) / 29.0) * scaled_h
        pts.append((px, py))
    return pts


def clip_polygon_to_rect(poly, xmin, ymin, xmax, ymax):
    """Clip a 2D polygon against an axis-aligned bounding box using Sutherland-Hodgman."""
    def clip_edge(vertices, inside_fn, intersect_fn):
        out = []
        if not vertices:
            return out
        p = vertices[-1]
        for q in vertices:
            if inside_fn(q):
                if inside_fn(p):
                    out.append(q)
                else:
                    out.append(intersect_fn(p, q))
                    out.append(q)
            elif inside_fn(p):
                out.append(intersect_fn(p, q))
            p = q
        return out

    # Left (x >= xmin)
    poly = clip_edge(
        poly,
        lambda pt: pt[0] >= xmin,
        lambda p, q: (xmin, p[1] + (q[1] - p[1]) * (xmin - p[0]) / (q[0] - p[0]) if q[0] != p[0] else p[1])
    )
    # Right (x <= xmax)
    poly = clip_edge(
        poly,
        lambda pt: pt[0] <= xmax,
        lambda p, q: (xmax, p[1] + (q[1] - p[1]) * (xmax - p[0]) / (q[0] - p[0]) if q[0] != p[0] else p[1])
    )
    # Top (y >= ymin)
    poly = clip_edge(
        poly,
        lambda pt: pt[1] >= ymin,
        lambda p, q: (p[0] + (q[0] - p[0]) * (ymin - p[1]) / (q[1] - p[1]) if q[1] != p[1] else p[0], ymin)
    )
    # Bottom (y <= ymax)
    poly = clip_edge(
        poly,
        lambda pt: pt[1] <= ymax,
        lambda p, q: (p[0] + (q[0] - p[0]) * (ymax - p[1]) / (q[1] - p[1]) if q[1] != p[1] else p[0], ymax)
    )
    return poly


def upper_left_run(points, cx, cy):
    """Longest run of consecutive polygon vertices on the upper-left half (for a lit bevel edge).

    points is a flat [x0, y0, x1, y1, ...] list; returns a flat list (empty if no usable run)."""
    pts = list(zip(points[0::2], points[1::2]))
    n = len(pts)
    flags = [(px - cx) + (py - cy) <= 0 for px, py in pts]
    if n < 3 or all(flags) or not any(flags):
        return []
    best = []
    for i in range(n):
        if flags[i] and not flags[i - 1]:
            run = []
            j = i
            while flags[j % n] and len(run) < n:
                run.append(pts[j % n])
                j += 1
            if len(run) > len(best):
                best = run
    if len(best) < 2:
        return []
    return [c for p in best for c in p]


def get_rounded_rect_points(x1, y1, x2, y2, radius=10.0):
    """Compute polygon points for a rectangle with chamfered/rounded corners."""
    r = min(radius, (x2 - x1) / 2.0, (y2 - y1) / 2.0)
    return [
        x1 + r, y1,
        x2 - r, y1,
        x2, y1 + r,
        x2, y2 - r,
        x2 - r, y2,
        x1 + r, y2,
        x1, y2 - r,
        x1, y1 + r,
    ]


def get_shape_polygon(shape, cx, cy, w, h, expand=0.0):
    """Compute polygon points for Tkinter canvas drawing based on slot shape specification."""
    hw = (w / 2.0) + expand
    hh = (h / 2.0) + expand

    if shape in ("tall", "square", "wide", "big"):
        c = min(hw, hh) * 0.16
        return [
            cx - hw + c, cy - hh,
            cx + hw - c, cy - hh,
            cx + hw, cy - hh + c,
            cx + hw, cy + hh - c,
            cx + hw - c, cy + hh,
            cx - hw + c, cy + hh,
            cx - hw, cy + hh - c,
            cx - hw, cy - hh + c,
        ]

    elif shape == "bar":
        c = hh * 0.35
        return [
            cx - hw + c, cy - hh,
            cx + hw - c, cy - hh,
            cx + hw, cy - hh + c,
            cx + hw, cy + hh - c,
            cx + hw - c, cy + hh,
            cx - hw + c, cy + hh,
            cx - hw, cy + hh - c,
            cx - hw, cy - hh + c,
        ]

    elif shape == "hex":
        # Horizontal hexagon matching medallion, fairy blessing, and bag slots
        return [
            cx - hw, cy,
            cx - hw * 0.5, cy - hh,
            cx + hw * 0.5, cy - hh,
            cx + hw, cy,
            cx + hw * 0.5, cy + hh,
            cx - hw * 0.5, cy + hh,
        ]

    elif shape == "chevron":
        # Right-pointing chevron matching Boomerang slot
        return [
            cx - hw, cy - hh,
            cx + hw * 0.35, cy - hh,
            cx + hw, cy,
            cx + hw * 0.35, cy + hh,
            cx - hw, cy + hh,
            cx - hw * 0.35, cy,
        ]

    elif shape == "pentagon":
        if w > h:
            # Horizontal pentagon pointing right (Ocarina slots)
            return [
                cx - hw, cy - hh,
                cx + hw * 0.45, cy - hh,
                cx + hw, cy,
                cx + hw * 0.45, cy + hh,
                cx - hw, cy + hh,
            ]
        else:
            # Vertical pentagon pointing down (Hookshot, Hammer, Boots)
            return [
                cx - hw, cy - hh,
                cx + hw, cy - hh,
                cx + hw, cy + hh * 0.45,
                cx, cy + hh,
                cx - hw, cy + hh * 0.45,
            ]

    elif shape == "shield":
        # Flat top Zelda shield contour
        return [
            cx - hw, cy - hh,
            cx + hw, cy - hh,
            cx + hw, cy - hh * 0.05,
            cx + hw * 0.75, cy + hh * 0.55,
            cx, cy + hh,
            cx - hw * 0.75, cy + hh * 0.55,
            cx - hw, cy - hh * 0.05,
        ]

    elif shape == "circle":
        # Elliptical / circular polygon (24 segments)
        pts = []
        for i in range(24):
            angle = i * (2.0 * math.pi / 24.0)
            pts.append(cx + hw * math.cos(angle))
            pts.append(cy + hh * math.sin(angle))
        return pts

    elif shape == "heart":
        # Parametric heart polygon (~40 points)
        pts = compute_heart_polygon_points(cx, cy, w, h, num_points=40, expand=expand)
        return [coord for pt in pts for coord in pt]

    # Fallback to rectangle
    return [
        cx - hw, cy - hh,
        cx + hw, cy - hh,
        cx + hw, cy + hh,
        cx - hw, cy + hh,
    ]


class HDTextureManager:
    """Loads and caches Ultra HD Switch 2 Remake textures."""
    def __init__(self, base_dir=SWITCH2_ASSETS_DIR):
        self.base_dir = base_dir
        self.cache = {}

    def clear(self):
        """Clear cached PhotoImage objects."""
        self.cache.clear()

    def get_actor_icon(self, actor, size=(64, 64), dimmed=False):
        """Load icon for an actor from generated switch2_ui assets."""
        if not PIL_AVAILABLE:
            return None

        size_key = (int(size[0]), int(size[1]))
        cache_key = (actor, size_key, dimmed)
        if cache_key in self.cache:
            return self.cache[cache_key]

        img = None
        filename = ACTOR_TO_GENERATED_FILE.get(actor)
        if filename:
            full_path = os.path.join(self.base_dir, filename)
            if os.path.exists(full_path):
                try:
                    img = Image.open(full_path).convert("RGBA")
                except Exception:
                    img = None

        if img is None:
            img = Image.new("RGBA", size_key, (30, 41, 59, 0))

        try:
            target_w = max(1, size_key[0])
            target_h = max(1, size_key[1])
            img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        except Exception:
            pass

        if dimmed:
            try:
                alpha = img.split()[-1]
                gray = ImageOps.grayscale(img).convert("RGBA")
                enhancer = ImageEnhance.Brightness(gray)
                dim_img = enhancer.enhance(0.55)
                dim_img.putalpha(alpha)
                photo = ImageTk.PhotoImage(dim_img)
            except Exception:
                photo = ImageTk.PhotoImage(img)
        else:
            photo = ImageTk.PhotoImage(img)

        self.cache[cache_key] = photo
        return photo

    def _open_texture(self, filename):
        """Open an RGBA texture from the assets folder, or None (Pillow or the file missing)."""
        if not PIL_AVAILABLE:
            return None
        full_path = os.path.join(self.base_dir, filename)
        if not os.path.exists(full_path):
            return None
        try:
            return Image.open(full_path).convert("RGBA")
        except Exception:
            return None

    def get_tiled(self, filename, width, height, tile_px):
        """PhotoImage of width x height tiled from a seamless texture; None if unavailable."""
        width, height, tile_px = int(width), int(height), max(8, int(tile_px))
        if width < 1 or height < 1:
            return None
        key = ("tiled", filename, width, height, tile_px)
        if key in self.cache:
            return self.cache[key]
        photo = None
        img = self._open_texture(filename)
        if img is not None:
            try:
                tile = img.resize((tile_px, tile_px), Image.Resampling.LANCZOS)
                out = Image.new("RGBA", (width, height))
                for ty in range(0, height, tile_px):
                    for tx in range(0, width, tile_px):
                        out.paste(tile, (tx, ty))
                photo = ImageTk.PhotoImage(out)
            except Exception:
                photo = None
        self.cache[key] = photo
        return photo

    def get_stretched(self, filename, width, height):
        """PhotoImage of a texture stretched to width x height; None if unavailable."""
        width, height = int(width), int(height)
        if width < 1 or height < 1:
            return None
        key = ("stretched", filename, width, height)
        if key in self.cache:
            return self.cache[key]
        photo = None
        img = self._open_texture(filename)
        if img is not None:
            try:
                photo = ImageTk.PhotoImage(img.resize((width, height), Image.Resampling.LANCZOS))
            except Exception:
                photo = None
        self.cache[key] = photo
        return photo

    def get(self, filename, size=(44, 44), dimmed=False):
        """Legacy helper for direct filename loading."""
        if not PIL_AVAILABLE:
            return None
        size_key = (int(size[0]), int(size[1]))
        key = (filename, size_key, dimmed)
        if key in self.cache:
            return self.cache[key]

        full_path = os.path.join(self.base_dir, filename)
        if not os.path.exists(full_path):
            img = Image.new("RGBA", size_key, (30, 41, 59, 200))
        else:
            try:
                img = Image.open(full_path).convert("RGBA")
                img = img.resize(size_key, Image.Resampling.LANCZOS)
            except Exception:
                img = Image.new("RGBA", size_key, (30, 41, 59, 200))

        if dimmed:
            try:
                alpha = img.split()[-1]
                gray = ImageOps.grayscale(img).convert("RGBA")
                enhancer = ImageEnhance.Brightness(gray)
                dim_img = enhancer.enhance(0.55)
                dim_img.putalpha(alpha)
                photo = ImageTk.PhotoImage(dim_img)
            except Exception:
                photo = ImageTk.PhotoImage(img)
        else:
            photo = ImageTk.PhotoImage(img)

        self.cache[key] = photo
        return photo


class OOTTextureMenuFrame(tk.Frame):
    """Full In-Game Pause Menu Frame for the Switch 2 Remake driven by pause_menu_layout.json."""
    def __init__(self, parent, editor):
        super().__init__(parent, bg=COLOR_BG)
        self.editor = editor
        self.textures = HDTextureManager()
        self._last_rendered_size = None

        self.pages = ["Collection", "Equipment", "Items", "Key Items", "Threads of Time", "Song Book"]
        self.active_subscreen = 0  # 0: Collection, 1: Equipment, 2: Items, 3: Key Items, 4: Threads of Time, 5: Song Book
        self.selected_slot_id = None
        self.selected_key_item_id = "N_Info_03"
        self._key_item_sockets = {}
        self._threads_selected_index = 0
        self._threads_scroll_offset = 0
        self._threads_visible_chapters = []
        self._rendered_slots = {}  # slot_id -> dict of canvas item tags / bounds
        self.song_hit_boxes = []   # Backwards compatibility for Song Book tests
        self.selected_song_id = "Zelda's Lullaby"
        self._canvas_size = (1920, 1080)
        self._font_cache = {}
        self._tab_positions = {}
        self._lr_positions = {}
        self._topbar_hits = {}      # name -> (x1, y1, x2, y2) canvas rectangle of hearts / magic / rupees
        self._topbar_hover = None
        self._popup = None
        self._popup_widgets = {}

        # Main full-window scaling canvas
        self.canvas = tk.Canvas(self, bg=COLOR_BG, highlightthickness=0, bd=0, width=1920, height=1080)
        self.canvas.pack(fill="both", expand=True)

        # Bind events
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<Button-3>", self._on_canvas_right_click)
        self.canvas.bind("<Motion>", self._on_canvas_motion)
        self.canvas.bind("<Leave>", self._on_canvas_leave)
        self.canvas.bind("<MouseWheel>", self._on_canvas_wheel)
        self.canvas.bind("<Button-4>", self._on_canvas_wheel)
        self.canvas.bind("<Button-5>", self._on_canvas_wheel)

        # Keyboard shortcuts (scoped to pause view on frame and canvas)
        for target in (self, self.canvas):
            target.bind("<Key-Left>", self._on_key_arrow)
            target.bind("<Key-Right>", self._on_key_arrow)
            target.bind("<Key-Up>", self._on_key_arrow)
            target.bind("<Key-Down>", self._on_key_arrow)
            target.bind("<Return>", self._on_key_activate)
            target.bind("<space>", self._on_key_activate)
            target.bind("<a>", self._on_key_activate)
            target.bind("<A>", self._on_key_activate)
            target.bind("<Key-a>", self._on_key_activate)
            target.bind("<Key-A>", self._on_key_activate)
            target.bind("<q>", self._on_key_cycle_prev)
            target.bind("<Q>", self._on_key_cycle_prev)
            target.bind("<Key-q>", self._on_key_cycle_prev)
            target.bind("<Key-Q>", self._on_key_cycle_prev)
            target.bind("<e>", self._on_key_cycle_next)
            target.bind("<E>", self._on_key_cycle_next)
            target.bind("<Key-e>", self._on_key_cycle_next)
            target.bind("<Key-E>", self._on_key_cycle_next)
            target.bind("<Escape>", self._on_key_back)
            target.bind("<b>", self._on_key_back)
            target.bind("<B>", self._on_key_back)
            target.bind("<Key-b>", self._on_key_back)
            target.bind("<Key-B>", self._on_key_back)

        self.bind("<Map>", self._on_map)

        self.show_subscreen(0)

    # =========================================================================
    # SCALING & PROJECTION
    # =========================================================================
    def set_canvas_size(self, width, height):
        """Set explicit canvas reference size (for unit testing or sizing)."""
        self._canvas_size = (width, height)
        self.canvas.config(width=width, height=height)
        self.refresh_visuals()

    def get_transform(self):
        """Return (scale, ox, oy) projecting the 1920x1080 reference frame uniformly to the canvas."""
        ref_w, ref_h = 1920.0, 1080.0
        if getattr(self, "_canvas_size", None):
            cw, ch = self._canvas_size
        else:
            cw = self.canvas.winfo_width()
            ch = self.canvas.winfo_height()
            if cw <= 1 or ch <= 1:
                try:
                    cw = int(self.canvas.cget("width"))
                    ch = int(self.canvas.cget("height"))
                except Exception:
                    cw, ch = 1920, 1080
        if cw <= 10 or ch <= 10:
            cw, ch = 1920, 1080
        scale = min(cw / ref_w, ch / ref_h)
        ox = (cw - ref_w * scale) / 2.0
        oy = (ch - ref_h * scale) / 2.0
        return scale, ox, oy

    def to_canvas(self, x, y):
        """Transform reference (x, y) to current canvas (cx, cy)."""
        scale, ox, oy = self.get_transform()
        return ox + x * scale, oy + y * scale

    def to_ref(self, cx, cy):
        """Transform canvas (cx, cy) to reference (x, y)."""
        scale, ox, oy = self.get_transform()
        if scale <= 0:
            return 0.0, 0.0
        return (cx - ox) / scale, (cy - oy) / scale

    def _font(self, px_at_ref, weight="normal"):
        """Return Tk font tuple with pixel size (negative int) scaled to current canvas."""
        scale, _, _ = self.get_transform()
        return _font(px_at_ref, weight=weight, scale=scale)

    def _get_font(self, px_at_ref, weight="normal"):
        """Return cached tkinter.font.Font object with pixel size (negative int) for measurement."""
        scale, _, _ = self.get_transform()
        px = max(8, round(px_at_ref * scale))
        key = (px, weight)
        if not hasattr(self, "_font_cache") or self._font_cache is None:
            self._font_cache = {}
        if key not in self._font_cache:
            self._font_cache[key] = tkfont.Font(family="Segoe UI", size=-px, weight=weight)
        return self._font_cache[key]

    def _unwrap_caption(self, text):
        """Unwrap single newlines into spaces while preserving paragraph breaks."""
        return unwrap_caption(text)

    def _on_canvas_resize(self, event):
        if event.width > 10 and event.height > 10:
            self._canvas_size = (event.width, event.height)
        self.refresh_visuals()

    # =========================================================================
    # NAVIGATION
    # =========================================================================
    def current_page_name(self):
        idx = self.active_subscreen % len(self.pages)
        return self.pages[idx]

    def cycle_subscreen(self, delta):
        new_idx = (self.active_subscreen + delta) % len(self.pages)
        self.show_subscreen(new_idx)

    def show_subscreen(self, page):
        if isinstance(page, str):
            p_str = page.strip()
            matches = [i for i, name in enumerate(self.pages) if name.lower() == p_str.lower()]
            if matches:
                self.active_subscreen = matches[0]
            else:
                self.active_subscreen = 0
        else:
            self.active_subscreen = page % len(self.pages)

        # Select first slot or item on this page by default
        page_name = self.current_page_name()
        if page_name in ("Collection", "Equipment", "Items"):
            page_def = PAUSE_MENU_LAYOUT.get("plus_menu", {}).get("pages", {}).get(page_name, {})
            slots = page_def.get("slots", [])
            valid_slots = [s for s in slots if s.get("pos") is not None and not s.get("display_only")]
            if valid_slots:
                self.selected_slot_id = valid_slots[0]["id"]
            else:
                self.selected_slot_id = None
        elif page_name == "Key Items":
            if not getattr(self, "selected_key_item_id", None):
                self.selected_key_item_id = "N_Info_03"
        elif page_name == "Song Book":
            if not getattr(self, "selected_song_id", None):
                self.selected_song_id = "Zelda's Lullaby"
        elif page_name == "Threads of Time":
            self._threads_selected_index = 0

        self.refresh_visuals()
        if self.winfo_ismapped():
            try:
                self.canvas.focus_set()
            except Exception:
                pass

    def set_info(self, text):
        """Legacy helper for status info."""
        pass

    def _on_map(self, event=None):
        try:
            self.canvas.focus_set()
        except Exception:
            pass

    def _on_key_cycle_prev(self, event=None):
        if not self.winfo_ismapped():
            return
        self.cycle_subscreen(-1)

    def _on_key_cycle_next(self, event=None):
        if not self.winfo_ismapped():
            return
        self.cycle_subscreen(1)

    def _on_key_back(self, event=None):
        if not self.winfo_ismapped():
            return
        self._on_back_pressed()

    def _on_back_pressed(self):
        if hasattr(self.editor, "switch_to_standard_view"):
            self.editor.switch_to_standard_view()

    # =========================================================================
    # DRAWING ROUTINES
    # =========================================================================
    def refresh_visuals(self):
        """Redraw the entire pause menu canvas for the active subscreen."""
        canv = self.canvas
        canv.delete("all")
        self._rendered_slots.clear()

        # Canvas resize detection: clear PhotoImage cache when canvas size changes
        canv_w = canv.winfo_width()
        canv_h = canv.winfo_height()
        if getattr(self, "_canvas_size", None):
            cur_size = self._canvas_size
        elif canv_w > 10 and canv_h > 10:
            cur_size = (canv_w, canv_h)
        else:
            try:
                cur_size = (int(canv.cget("width")), int(canv.cget("height")))
            except Exception:
                cur_size = (1920, 1080)

        if getattr(self, "_last_rendered_size", None) != cur_size:
            self._last_rendered_size = cur_size
            if hasattr(self, "textures"):
                self.textures.clear()
            if hasattr(self, "_font_cache") and self._font_cache:
                self._font_cache.clear()

        scale, ox, oy = self.get_transform()
        ref_w, ref_h = 1920.0, 1080.0

        # 1. Main Background
        canv.create_rectangle(0, 0, canv.winfo_width(), canv.winfo_height(), fill=COLOR_BG, outline="")
        # Letterboxed inner frame
        ix1, iy1 = self.to_canvas(0, 0)
        ix2, iy2 = self.to_canvas(ref_w, ref_h)
        canv.create_rectangle(ix1, iy1, ix2, iy2, fill=COLOR_INNER_PANEL, outline="#2b1c11", width=max(1, int(2 * scale)))

        # 2. Lighter carved-wood panels (under the top bar so its ornamental edge overlaps them)
        page_name = self.current_page_name()
        self._draw_page_panel(page_name, scale)

        # 3. Shared Top Bar
        self._draw_top_bar(scale, ox, oy)

        # 4. Subscreen Slots & Content
        if page_name == "Key Items":
            self._draw_key_items_page(scale)
        elif page_name == "Threads of Time":
            self._draw_threads_of_time_page(scale)
        elif page_name == "Song Book":
            self._draw_song_book_page(scale)
        else:
            page_def = PAUSE_MENU_LAYOUT.get("plus_menu", {}).get("pages", {}).get(page_name, {})

            # Preview Panel / Oval
            self._draw_preview_panel(page_name, page_def, scale)

            # Draw Slots
            slots = page_def.get("slots", [])
            for slot in slots:
                self._draw_slot(slot, scale)

        # 5. Page edge navigation arrows (< and >)
        self._draw_edge_arrows(scale)
        self._draw_topbar_hover()

        if self.winfo_ismapped():
            try:
                self.canvas.focus_set()
            except Exception:
                pass

    def _draw_page_panel(self, page_name, scale):
        """Lighter carved-wood panel behind the slots of Collection, Equipment and Items."""
        top_h = PAUSE_MENU_LAYOUT.get("plus_menu", {}).get("top_bar", {}).get("height", 95)
        if page_name == "Items":
            # lighter panel over x 0..1085, full height under top bar; preview x 1085..1920 near-black
            rect = (0, top_h, 1085, 1080)
        elif page_name == "Collection":
            # lighter panel over x 830..1920; preview x 0..830 near-black
            rect = (830, top_h, 1920, 1080)
        elif page_name == "Equipment":
            # lighter panel over the whole page; central oval stays dark in preview
            rect = (0, top_h, 1920, 1080)
        else:
            return
        canv = self.canvas
        px1, py1 = self.to_canvas(rect[0], rect[1])
        px2, py2 = self.to_canvas(rect[2], rect[3])
        wood = self.textures.get_tiled("ui_panel_wood.png", px2 - px1, py2 - py1, 512 * scale)
        if wood is not None:
            canv.create_image(px1, py1, image=wood, anchor="nw", tags=("panel_wood",))
            canv.create_rectangle(px1, py1, px2, py2, fill="", outline="#24180e", width=max(1, int(1 * scale)))
        else:
            canv.create_rectangle(px1, py1, px2, py2, fill=COLOR_PANEL_BG, outline=COLOR_PANEL_BORDER, width=max(1, int(1 * scale)))

    def _draw_top_bar(self, scale, ox, oy):
        """Draw the authentic carved wood header band with Hearts, Magic meter, Tab bar, and Rupees."""
        canv = self.canvas
        top_def = PAUSE_MENU_LAYOUT.get("plus_menu", {}).get("top_bar", {})
        top_h = top_def.get("height", 95)

        x1, y1 = self.to_canvas(0, 0)
        x2, y2 = self.to_canvas(1920, top_h)

        strip = self.textures.get_stretched("ui_topbar.png", x2 - x1, 120 * scale)
        if strip is not None:
            # Carved wood strip with its ornamental lower edge
            canv.create_image(x1, y1, image=strip, anchor="nw", tags=("topbar_texture",))
        else:
            # Flat fallback: carved wood beam
            canv.create_rectangle(x1, y1, x2, y2, fill=COLOR_TOP_BAR, outline="")
            # Subtle horizontal wood grain lines
            for grain_y in (y1 + (y2 - y1) * 0.25, y1 + (y2 - y1) * 0.55):
                canv.create_line(x1, grain_y, x2, grain_y, fill=COLOR_TOP_BAR_ACCENT, width=1)

            # Wavy carved bottom edge
            wave_pts = [x1, y2]
            step = max(8, int(30 * scale))
            cur_x = x1
            w_up = True
            while cur_x < x2:
                cur_x += step
                w_y = y2 + (int(5 * scale) if w_up else 0)
                wave_pts.extend([cur_x, w_y])
                w_up = not w_up
            wave_pts.extend([x2, y2, x2, y1, x1, y1])
            canv.create_polygon(wave_pts, fill=COLOR_TOP_BAR, outline=COLOR_TOP_BAR_BOTTOM, width=max(1, int(2 * scale)))

        self._topbar_hits = {}

        # A. Hearts (Left)
        # each heart ~30px wide, two rows of up to 10, ~6px gap
        hx_ref, hy_ref = top_def.get("hearts", [40, 25])
        total_hearts = safe_int(getattr(self.editor, "v_hearts", 3), default=3)
        current_hp = safe_int(getattr(self.editor, "v_hp", 12), default=12)
        dd = False
        if hasattr(self.editor, "v_double_defense"):
            dd = bool(self.editor.v_double_defense.get())
        border_color = "#ffffff" if dd else "#7a1a10"

        hw_box = 30.0 * scale
        hh_box = 28.0 * scale

        for i in range(total_hearts):
            row = i // 10
            col = i % 10
            h_ref_x = hx_ref + col * 36
            h_ref_y = hy_ref + row * 34 - 7
            hcx, hcy = self.to_canvas(h_ref_x, h_ref_y)

            full_val = (i + 1) * 4
            if current_hp >= full_val:
                fill_q = 4
            elif current_hp <= i * 4:
                fill_q = 0
            else:
                fill_q = current_hp - (i * 4)

            heart_pts = compute_heart_polygon_points(hcx, hcy, hw_box, hh_box, num_points=40)
            flat_pts = [coord for pt in heart_pts for coord in pt]

            if fill_q == 4:
                canv.create_polygon(flat_pts, fill="#e8452c", outline=border_color, width=max(1, int(1.5 * scale)))
            elif fill_q == 0:
                canv.create_polygon(flat_pts, fill="#1c130c", outline=border_color, width=max(1, int(1.5 * scale)))
            else:
                canv.create_polygon(flat_pts, fill="#1c130c", outline=border_color, width=max(1, int(1.5 * scale)))
                m = max(hw_box, hh_box) * 2.0
                quads = [
                    (hcx - m, hcy - m, hcx, hcy),
                    (hcx, hcy - m, hcx + m, hcy),
                    (hcx, hcy, hcx + m, hcy + m),
                    (hcx - m, hcy, hcx, hcy + m),
                ]
                for q_idx in range(fill_q):
                    q_clipped = clip_polygon_to_rect(heart_pts, *quads[q_idx])
                    q_flat = [coord for pt in q_clipped for coord in pt]
                    canv.create_polygon(q_flat, fill="#e8452c", outline="")
                canv.create_polygon(flat_pts, fill="", outline=border_color, width=max(1, int(1.5 * scale)))

        n_cols = max(1, min(10, total_hearts))
        n_rows = max(1, (total_hearts + 9) // 10)
        hit_x1, hit_y1 = self.to_canvas(hx_ref - 18, hy_ref - 7 - 16)
        hit_x2, hit_y2 = self.to_canvas(hx_ref + (n_cols - 1) * 36 + 18, hy_ref + (n_rows - 1) * 34 - 7 + 16)
        self._topbar_hits["hearts"] = (hit_x1, hit_y1, hit_x2, hit_y2)

        # B. Magic Bar (Under Hearts)
        # ~10 small green (#3fb24a) segments ~16x14px each
        mb_def = top_def.get("magic_bar", [40, 82, 195, 90])
        mb_x1, mb_y1 = self.to_canvas(mb_def[0], mb_def[1] - 4)

        m_str = getattr(self.editor, "v_magic", tk.StringVar()).get() if hasattr(self.editor, "v_magic") else "None"
        has_magic = ("Standard" in m_str or "Double" in m_str)
        mp_val = safe_int(getattr(self.editor, "v_magic_points", 0), default=0)
        max_mp = 48 if "Double" in m_str else 24
        if has_magic:
            num_filled = 10 if mp_val == 0 else int(round((mp_val / max_mp) * 10))
            num_filled = max(1, min(10, num_filled))
        else:
            num_filled = 0

        seg_w = 16.0 * scale
        seg_h = 14.0 * scale
        seg_gap = 2.0 * scale
        self._topbar_hits["magic"] = (mb_x1, mb_y1, mb_x1 + 10 * (seg_w + seg_gap) - seg_gap, mb_y1 + seg_h)
        for s in range(10):
            sx1 = mb_x1 + s * (seg_w + seg_gap)
            sy1 = mb_y1
            sx2 = sx1 + seg_w
            sy2 = sy1 + seg_h
            if s < num_filled:
                canv.create_rectangle(sx1, sy1, sx2, sy2, fill="#3fb24a", outline="#246e2b", width=1)
            else:
                canv.create_rectangle(sx1, sy1, sx2, sy2, fill="#1c130c", outline="#24180e", width=1)

        # C. Centered Subscreen Tabs (6 tabs)
        tabs_list = self.pages
        current_page = self.current_page_name()
        tab_y_ref = top_def.get("tabs_y", 42)
        _, ty = self.to_canvas(0, tab_y_ref)
        center_x, _ = self.to_canvas(960, tab_y_ref)

        hud_right, _ = self.to_canvas(370, tab_y_ref)
        rupees_left, _ = self.to_canvas(1560, tab_y_ref)

        cap_margin = 30.0 * scale
        cap_hw = 16.0 * scale
        cap_hh = 12.0 * scale

        chosen_font_pt = 22
        chosen_gap_ref = 24
        chosen_widths = []

        found = False
        for font_pt in (30, 28, 26, 24, 22):
            font_obj = self._get_font(font_pt, "normal")
            widths = [font_obj.measure(tname) for tname in tabs_list]
            for gap_ref in range(48, 23, -2):
                tab_gap = gap_ref * scale
                total_w = sum(widths) + (len(tabs_list) - 1) * tab_gap
                g_start = center_x - (total_w / 2.0)
                g_end = g_start + total_w
                left_edge = g_start - cap_margin - 2.0 * cap_hw
                right_edge = g_end + cap_margin + 2.0 * cap_hw
                if left_edge >= hud_right and right_edge <= rupees_left:
                    chosen_font_pt = font_pt
                    chosen_gap_ref = gap_ref
                    chosen_widths = widths
                    found = True
                    break
            if found:
                break

        if not found:
            chosen_font_pt = 22
            chosen_gap_ref = 24
            font_obj = self._get_font(chosen_font_pt, "normal")
            chosen_widths = [font_obj.measure(tname) for tname in tabs_list]

        tab_gap = chosen_gap_ref * scale
        tab_widths = chosen_widths
        f_tab = self._font(chosen_font_pt, "normal")

        total_tabs_w = sum(tab_widths) + (len(tabs_list) - 1) * tab_gap
        group_start_x = center_x - (total_tabs_w / 2.0)
        group_end_x = group_start_x + total_tabs_w

        lx = group_start_x - cap_margin - cap_hw
        rx = group_end_x + cap_margin + cap_hw

        canv.create_rectangle(lx - cap_hw, ty - cap_hh, lx + cap_hw, ty + cap_hh, fill="#e2e8f0", outline="#64748b", width=1, tags=("tab_l",))
        canv.create_text(lx, ty, text="L", fill="#0f172a", font=self._font(11, "bold"), tags=("tab_l",))

        canv.create_rectangle(rx - cap_hw, ty - cap_hh, rx + cap_hw, ty + cap_hh, fill="#e2e8f0", outline="#64748b", width=1, tags=("tab_r",))
        canv.create_text(rx, ty, text="R", fill="#0f172a", font=self._font(11, "bold"), tags=("tab_r",))

        self._tab_positions = {}
        self._lr_positions = {"L": (lx, ty), "R": (rx, ty)}

        cur_left = group_start_x
        for i, tname in enumerate(tabs_list):
            w_t = tab_widths[i]
            tx = cur_left + (w_t / 2.0)
            self._tab_positions[tname] = (tx, ty, w_t)

            is_active = (tname == current_page)

            if is_active:
                # Active tab block: rounded rect 24px wider than measured text on each side, full top-bar height, #2a1c10
                pad = 24.0 * scale
                bx1 = cur_left - pad
                bx2 = cur_left + w_t + pad
                rect_pts = get_rounded_rect_points(bx1, y1, bx2, y2, radius=8.0 * scale)
                canv.create_polygon(rect_pts, fill="#2a1c10", outline="", tags=("tab_active_bg",))

            tag_name = f"tab_{tname}"
            canv.create_text(
                tx, ty, text=tname, fill="#f3e6c8",
                font=f_tab, tags=(tag_name, "tab")
            )

            cur_left += w_t + tab_gap

        # D. Rupees (Right)
        # "967 / 1,000" with current amount 44px bold and "/ 1,000" 28px - both via _font
        rup_ref = top_def.get("rupees", [1880, 50])
        rx, ry = self.to_canvas(rup_ref[0], rup_ref[1])

        cur_rupees = safe_int(getattr(self.editor, "v_rupees", 0), default=0)
        max_rupees = self._get_max_rupees()

        val_color = "#5ad04a" if cur_rupees >= max_rupees else "#ffffff"
        amt_str = f"{cur_rupees:,}"
        slash_str = f" / {max_rupees:,}"

        f_amt = self._font(44, "bold")
        f_slash = self._font(28, "normal")

        font_slash = self._get_font(28, "normal")
        font_amt = self._get_font(44, "bold")
        w_slash = font_slash.measure(slash_str)
        w_amt = font_amt.measure(amt_str)

        canv.create_text(rx, ry, text=slash_str, fill="#ffffff", font=f_slash, anchor="e")
        canv.create_text(rx - w_slash, ry, text=amt_str, fill=val_color, font=f_amt, anchor="e")

        # Green rupee gem polygon placed to left of rupee text
        gem_w = 12 * scale
        gem_h = 20 * scale
        gx = rx - w_slash - w_amt - (18 * scale)
        gem_pts = [
            gx, ry - gem_h,
            gx + gem_w, ry - gem_h * 0.4,
            gx + gem_w, ry + gem_h * 0.4,
            gx, ry + gem_h,
            gx - gem_w, ry + gem_h * 0.4,
            gx - gem_w, ry - gem_h * 0.4,
        ]
        canv.create_polygon(gem_pts, fill="#10b981", outline="#a7f3d0", width=1)
        self._topbar_hits["rupees"] = (gx - gem_w - 6 * scale, ry - 26 * scale, rx + 6 * scale, ry + 26 * scale)

    def _draw_edge_arrows(self, scale):
        """Draw authentic left (<) and right (>) navigation arrows on page borders."""
        canv = self.canvas
        # Left arrow
        lx, ly = self.to_canvas(25, 540)
        aw = 16 * scale
        ah = 28 * scale
        canv.create_polygon(
            lx + aw, ly - ah,
            lx, ly,
            lx + aw, ly + ah,
            fill="#5c4028", outline="#8a6238", width=max(1, int(1.5 * scale)),
            tags=("edge_arrow_left",)
        )

        # Right arrow
        rx, ry = self.to_canvas(1895, 540)
        canv.create_polygon(
            rx - aw, ry - ah,
            rx, ry,
            rx - aw, ry + ah,
            fill="#5c4028", outline="#8a6238", width=max(1, int(1.5 * scale)),
            tags=("edge_arrow_right",)
        )

    # =========================================================================
    # PREVIEW PANEL RENDERING
    # =========================================================================
    def _draw_preview_name_and_caption(
        self, nx, ny, preview_w_ref, item_name, count, max_count, item_caption, scale=None
    ):
        """Draw item name line, measured ornamental divider, and measured wrapped caption."""
        canv = self.canvas
        if scale is None:
            scale, _, _ = self.get_transform()

        if not item_name:
            return

        if item_caption:
            item_caption = unwrap_caption(item_caption)

        f_name = self._font(56, "bold")
        f_n = self._font(52, "bold")
        f_max = self._font(30, "normal")

        font_name = self._get_font(56, "bold")
        font_n = self._get_font(52, "bold")
        font_max = self._get_font(30, "normal")

        has_count = (count is not None and max_count is not None and max_count > 0)
        if has_count:
            is_full = (count >= max_count)
            n_str = str(count)
            max_str = f" / {max_count}"
            n_color = "#5ad04a" if is_full else "#ffffff"

            w_name = font_name.measure(item_name)
            w_sp = font_name.measure(" ")
            w_n = font_n.measure(n_str)
            w_max = font_max.measure(max_str)

            total_w = w_name + w_sp + w_n + w_max
            start_x = nx - (total_w / 2.0)

            canv.create_text(start_x, ny, text=item_name, fill="#ffffff", font=f_name, anchor="w", tags=("preview_name",))
            canv.create_text(start_x + w_name + w_sp, ny, text=n_str, fill=n_color, font=f_n, anchor="w", tags=("preview_name",))
            canv.create_text(start_x + w_name + w_sp + w_n, ny, text=max_str, fill="#ffffff", font=f_max, anchor="w", tags=("preview_name",))
        else:
            canv.create_text(nx, ny, text=item_name, fill="#ffffff", font=f_name, anchor="center", tags=("preview_name",))

        # Measure bottom of name line
        name_bbox = canv.bbox("preview_name")
        if name_bbox:
            name_bottom = name_bbox[3]
        else:
            name_bottom = ny + font_name.metrics("linespace") / 2.0

        # Caption (only if user imported game assets and caption exists)
        if item_caption and item_caption.strip():
            # Ornamental divider 14px (at ref) below name line bottom, width ~600px at ref, centred
            div_y = name_bottom + (14.0 * scale)
            div_w = 600.0 * scale
            self._draw_ornamental_divider(nx, div_y, div_w)

            div_bbox = canv.bbox("preview_divider")
            if div_bbox:
                div_bottom = div_bbox[3]
            else:
                div_bottom = div_y + (4.0 * scale)

            # Caption starting 18px (at ref) below divider, width = preview width minus 2x60px margins, centred
            cap_y = div_bottom + (18.0 * scale)
            cap_wrap_w = max(100, round((preview_w_ref - 120.0) * scale))

            # Bottom-hint band limit: nothing may draw below it
            hints_y_ref = PAUSE_MENU_LAYOUT.get("plus_menu", {}).get("button_hints_y", 1050)
            _, hy = self.to_canvas(0, hints_y_ref)
            band_top = hy - (29.0 * scale)
            max_bottom = band_top - (6.0 * scale)

            # Reduce font in 2px steps down to 22px at ref if needed
            for font_px in range(30, 20, -2):
                f_cap = self._font(font_px, "normal")
                cap_item = canv.create_text(
                    nx, cap_y, text=item_caption, fill="#f3e6c8",
                    font=f_cap, width=cap_wrap_w,
                    justify="center", anchor="n", tags=("preview_caption",)
                )
                cap_bbox = canv.bbox(cap_item)
                if cap_bbox and cap_bbox[3] > max_bottom and font_px > 22:
                    canv.delete(cap_item)
                else:
                    break

    def _draw_preview_panel(self, page_name, page_def, scale):
        """Draw the large item preview panel (or Equipment center oval) with name, divider, and caption."""
        canv = self.canvas
        preview_def = page_def.get("preview", {})
        if not preview_def:
            return

        selected_slot = self._get_selected_slot(page_def)
        actor, owned, equipped, dimmed, count, max_count = self.get_slot_state(selected_slot) if selected_slot else (None, False, False, False, None, None)

        text_actor = actor
        item_name, item_caption = self.get_actor_text(text_actor) if actor else ("", "")

        if "oval" in preview_def:
            # Equipment Page Center Oval
            ocx_ref, ocy_ref, ow_ref, oh_ref = preview_def["oval"]
            ocx, ocy = self.to_canvas(ocx_ref, ocy_ref)
            ow = ow_ref * scale
            oh = oh_ref * scale

            # Dark oval background (#0d0906 with soft lighter edge #5a4128)
            canv.create_oval(
                ocx - ow / 2, ocy - oh / 2,
                ocx + ow / 2, ocy + oh / 2,
                fill="#0d0906", outline="#5a4128", width=max(1, int(2 * scale))
            )

            # Equipped Tunic in center, equipped Sword and Shield smaller beside it
            tunic_actor = self._get_equipped_tunic_actor()
            sword_actor = self._get_equipped_sword_actor()
            shield_actor = self._get_equipped_shield_actor()

            tunic_size = (int(190 * scale), int(190 * scale))
            side_size = (int(100 * scale), int(100 * scale))

            # Equipped Sword (Left)
            if sword_actor:
                sw_img = self.textures.get_actor_icon(sword_actor, size=side_size)
                if sw_img:
                    canv.create_image(ocx - 170 * scale, ocy - 120 * scale, image=sw_img, anchor="center")

            # Equipped Shield (Right)
            if shield_actor:
                sh_img = self.textures.get_actor_icon(shield_actor, size=side_size)
                if sh_img:
                    canv.create_image(ocx + 170 * scale, ocy - 120 * scale, image=sh_img, anchor="center")

            # Large Equipped Tunic (Center)
            if tunic_actor:
                t_img = self.textures.get_actor_icon(tunic_actor, size=tunic_size)
                if t_img:
                    canv.create_image(ocx, ocy - 120 * scale, image=t_img, anchor="center")

            # Item Name, Divider, and Caption at bottom of oval
            nx_ref, ny_ref = preview_def.get("name", [910, 805])
            nx, ny = self.to_canvas(nx_ref, ny_ref)
            preview_w_ref = ow_ref

            self._draw_preview_name_and_caption(
                nx, ny, preview_w_ref,
                item_name, count, max_count, item_caption, scale
            )

        else:
            # Items / Collection Side Preview Panels
            icon_def = preview_def.get("icon", [1500, 470, 520])
            nx_ref, ny_ref = preview_def.get("name", [1500, 735])

            icx, icy = self.to_canvas(icon_def[0], icon_def[1])
            isize = int(icon_def[2] * scale)

            nx, ny = self.to_canvas(nx_ref, ny_ref)
            if "panel" in preview_def:
                p = preview_def["panel"]
                preview_w_ref = abs(p[2] - p[0])
            else:
                preview_w_ref = 830

            # Draw Big Icon
            if actor:
                big_img = self.textures.get_actor_icon(actor, size=(isize, isize))
                if big_img:
                    canv.create_image(icx, icy, image=big_img, anchor="center")

            self._draw_preview_name_and_caption(
                nx, ny, preview_w_ref,
                item_name, count, max_count, item_caption, scale
            )

    def _draw_ornamental_divider(self, cx, cy, width):
        """Draw thin ornamental line with centered flourish loop/diamond."""
        canv = self.canvas
        scale, _, _ = self.get_transform()
        hw = width / 2.0
        canv.create_line(cx - hw, cy, cx - 12 * scale, cy, fill="#8a6238", width=1, tags=("preview_divider",))
        canv.create_line(cx + 12 * scale, cy, cx + hw, cy, fill="#8a6238", width=1, tags=("preview_divider",))
        # Small diamond flourish
        canv.create_polygon(
            cx, cy - 4 * scale,
            cx + 6 * scale, cy,
            cx, cy + 4 * scale,
            cx - 6 * scale, cy,
            fill="#a17a4b", outline="#8a6238", width=1,
            tags=("preview_divider",)
        )

    # =========================================================================
    # SLOT RENDERING
    # =========================================================================
    def _draw_slot(self, slot, scale):
        """Draw an authentic beveled slot on the canvas with icon, count, and glowing cursor."""
        canv = self.canvas
        slot_id = slot["id"]
        pos = slot.get("pos")

        if not pos:
            # Place hidden item for slot ids without coordinates (e.g. Pa_HeadEquip_03)
            dummy = canv.create_rectangle(0, 0, 0, 0, state="hidden", tags=(slot_id, f"slot_{slot_id}", "slot"))
            self._rendered_slots[slot_id] = {"item": dummy, "slot": slot, "ref_pos": (0, 0)}
            return

        ref_x, ref_y = pos
        ref_w, ref_h = slot.get("size", [140, 140])
        shape = slot.get("shape", "square")

        cx, cy = self.to_canvas(ref_x, ref_y)
        sw = ref_w * scale
        sh = ref_h * scale

        actor, owned, equipped, dimmed, count, max_count = self.get_slot_state(slot)
        is_selected = (self.selected_slot_id == slot_id)

        # 1. Slot Body & Bevel (empty slot fill #1c130c with edge #5a4128)
        if slot_id != "heart_pieces":
            fill_col = COLOR_SLOT_EQUIPPED if equipped else COLOR_SLOT_RECESS
            border_col = COLOR_SLOT_EQUIPPED_BORDER if equipped else COLOR_SLOT_BORDER

            outer_pts = get_shape_polygon(shape, cx, cy, sw, sh)
            # Carved frame: soft drop shadow, outer rim, then the recess below
            shadow_pts = get_shape_polygon(shape, cx + 4 * scale, cy + 5 * scale, sw, sh, expand=2 * scale)
            canv.create_polygon(shadow_pts, fill=COLOR_SLOT_SHADOW, outline="", stipple="gray50")
            rim_pts = get_shape_polygon(shape, cx, cy, sw, sh, expand=3 * scale)
            canv.create_polygon(rim_pts, fill=COLOR_SLOT_RIM, outline="#3a2a1a", width=1)
            slot_item = canv.create_polygon(
                outer_pts, fill=fill_col, outline=border_col,
                width=max(1, int(1.8 * scale)),
                tags=(slot_id, f"slot_{slot_id}", "slot")
            )
            # Lighter 2px inner edge along the top/left
            lit = upper_left_run(get_shape_polygon(shape, cx, cy, sw, sh, expand=-2.5 * scale), cx, cy)
            if lit:
                canv.create_line(lit, fill=COLOR_SLOT_INNER_EDGE, width=max(1, int(2 * scale)),
                                 capstyle="round", joinstyle="round")
            self._rendered_slots[slot_id] = {
                "item": slot_item,
                "slot": slot,
                "ref_pos": (ref_x, ref_y),
                "cx": cx, "cy": cy,
                "sw": sw, "sh": sh,
            }

        # 2. Special Slot Rendering: Collection Heart Pieces
        if slot_id == "heart_pieces":
            held_pieces = safe_int(getattr(self.editor, "v_heart_pieces_held", 0), default=0) % 4
            held_pieces = max(0, min(3, held_pieces))
            edge_w = max(1, int(2.0 * scale))

            # 40-point parametric heart curve
            heart_pts = compute_heart_polygon_points(cx, cy, sw, sh, num_points=40)
            flat_pts = [coord for pt in heart_pts for coord in pt]

            # Base heart outline: dark fill (#1a120c), light edge (#d9c9a8, 2px at 1920 ref)
            slot_item = canv.create_polygon(
                flat_pts, fill="#1a120c", outline="#d9c9a8",
                width=edge_w, tags=(slot_id, f"slot_{slot_id}", "slot")
            )
            self._rendered_slots[slot_id] = {
                "item": slot_item,
                "slot": slot,
                "ref_pos": (ref_x, ref_y),
                "cx": cx, "cy": cy,
                "sw": sw, "sh": sh,
            }

            # 4 quarters (top-left, top-right, bottom-right, bottom-left)
            m = max(sw, sh) * 2.0
            quads = [
                (cx - m, cy - m, cx, cy),          # Top-Left
                (cx, cy - m, cx + m, cy),          # Top-Right
                (cx, cy, cx + m, cy + m),          # Bottom-Right
                (cx - m, cy, cx, cy + m),          # Bottom-Left
            ]
            for q_idx in range(held_pieces):
                q_clipped = clip_polygon_to_rect(heart_pts, *quads[q_idx])
                q_flat = [coord for pt in q_clipped for coord in pt]
                canv.create_polygon(q_flat, fill="#e8475f", outline="", tags=(slot_id, "heart_quarter_filled"))

            # Re-stroke outer light edge over quarter fills
            canv.create_polygon(flat_pts, fill="", outline="#d9c9a8", width=edge_w, tags=(slot_id,))

        # 3. Owned Icon
        elif owned and actor:
            icon_size = (int(sw * 0.76), int(sh * 0.76))
            photo = self.textures.get_actor_icon(actor, size=icon_size, dimmed=dimmed)
            if photo:
                canv.create_image(cx, cy, image=photo, anchor="center", tags=(slot_id,))
            elif dimmed:
                # Pillow stays optional - if missing, dimmed slots draw a dark stipple over the slot instead
                canv.create_polygon(outer_pts, fill="#000000", stipple="gray50", outline="", tags=(slot_id,))

        # 4. Count Display (slot counts 34px bold with 2px dark outline effect; no number label for heart pieces)
        if count is not None and not slot.get("display_only") and slot_id != "heart_pieces":
            count_str = str(count)
            is_full = (max_count is not None and count >= max_count)
            count_color = "#5ad04a" if is_full else COLOR_TEXT

            count_pos = slot.get("count_pos")
            if count_pos:
                # E.g. Skulltula token slot: count placed under token
                kpx, kpy = self.to_canvas(count_pos[0], count_pos[1])
                target_x, target_y, anchor = kpx, kpy, "center"
            elif count > 0 or slot_id in ("Pa_ItemIcon_00", "Pa_ItemIcon_01", "Pa_ItemIcon_08"):
                # Bottom-right corner of slot
                target_x = cx + sw * 0.38
                target_y = cy + sh * 0.38
                anchor = "se"
            else:
                target_x = None

            if target_x is not None:
                f_cnt = self._font(34, "bold")
                off = max(1, int(2.0 * scale))
                # 2px dark outline effect: draw the text 4 times offset in #000 first
                for dx, dy in ((-off, 0), (off, 0), (0, -off), (0, off)):
                    canv.create_text(
                        target_x + dx, target_y + dy, text=count_str,
                        fill="#000000", font=f_cnt, anchor=anchor, tags=(slot_id,)
                    )
                canv.create_text(
                    target_x, target_y, text=count_str,
                    fill=count_color, font=f_cnt, anchor=anchor, tags=(slot_id,)
                )

        # 5. Glowing Cursor Outline on Selected Slot
        if is_selected:
            # Outer light grey/glow outline
            outer_glow_pts = get_shape_polygon(shape, cx, cy, sw, sh, expand=3.5 * scale)
            canv.create_polygon(outer_glow_pts, fill="", outline=COLOR_CURSOR_GLOW, width=max(2, int(2.5 * scale)), tags=(slot_id,))
            # Inner bright white stroke
            inner_glow_pts = get_shape_polygon(shape, cx, cy, sw, sh, expand=1.0 * scale)
            canv.create_polygon(inner_glow_pts, fill="", outline=COLOR_CURSOR_WHITE, width=max(2, int(3.2 * scale)), tags=(slot_id,))

    # =========================================================================
    # SLOT STATE & ACTOR LOGIC
    # =========================================================================
    def get_slot_state(self, slot):
        """Return (actor, owned, equipped, dimmed, count, max_count) for a slot."""
        if not slot:
            return None, False, False, False, None, None

        slot_id = slot["id"]
        era = slot.get("era", "CA")
        dimmed = self._is_era_dimmed(era)
        owned = False
        equipped = False
        actor = None
        count = None
        max_count = None

        # Count tracking
        count_key = slot.get("count")
        if count_key:
            max_count = self.get_ammo_capacity(count_key)
            if count_key == "tokens":
                count = safe_int(getattr(self.editor, "v_tokens", 0), default=0)
                owned = (count > 0)
            elif count_key == "heart_pieces":
                count = safe_int(getattr(self.editor, "v_heart_pieces_held", 0), default=0)
                owned = (count > 0)
            elif hasattr(self.editor, "ammo_vars") and count_key in self.editor.ammo_vars:
                count = safe_int(self.editor.ammo_vars[count_key][0].get(), default=0)
                owned = (count > 0)

        # A. Tiered Items / Bags / Scales / Wallets / Swords
        items_list = slot.get("items", [])

        # Wallet
        if slot_id == "Pa_Bag_00":
            wal = self.editor.equip_vars.get("wallet", tk.StringVar()).get() if hasattr(self.editor, "equip_vars") else ""
            if "Tycoon" in wal or "Giant" in wal:
                actor = "Item_Wallet_Large"
                owned = True
            elif "Adult" in wal:
                actor = "Item_Wallet_Medium"
                owned = True
            elif "Child" in wal or "99" in wal:
                actor = "Item_Wallet_Small"
                owned = True
            else:
                actor = "Item_Wallet_Small"
                owned = False

        # Scale
        elif slot_id == "Pa_Scales_00":
            sc = self.editor.equip_vars.get("scale", tk.StringVar()).get() if hasattr(self.editor, "equip_vars") else ""
            if "Golden" in sc:
                actor = "Item_Scale_Gold"
                owned = True
            elif "Silver" in sc:
                actor = "Item_Scale_Silver"
                owned = True
            else:
                actor = "Item_Scale_Silver"
                owned = False

        # Hookshot / Longshot
        elif slot_id == "Pa_ItemIcon_07":
            hook = self.editor.hookshot_var.get() if hasattr(self.editor, "hookshot_var") else "None"
            if hook == "Longshot":
                actor = "Item_Longshot"
                owned = True
            elif hook == "Hookshot":
                actor = "Item_Hookshot"
                owned = True
            else:
                actor = "Item_Hookshot"
                owned = False

        # Strength / Gauntlets
        elif slot_id == "Pa_Gauntlet_00":  # Child Goron Bracelet
            str_val = self.editor.equip_vars.get("strength", tk.StringVar()).get() if hasattr(self.editor, "equip_vars") else "None"
            actor = "Armor_Child_Gauntlet_Goron"
            owned = (str_val in ("Goron's Bracelet", "Silver Gauntlets", "Golden Gauntlets"))
        elif slot_id == "Pa_Gauntlet_01":  # Adult Silver / Gold Gauntlets
            str_val = self.editor.equip_vars.get("strength", tk.StringVar()).get() if hasattr(self.editor, "equip_vars") else "None"
            if str_val == "Golden Gauntlets":
                actor = "Armor_Adult_Gauntlet_Gold"
                owned = True
            elif str_val == "Silver Gauntlets":
                actor = "Armor_Adult_Gauntlet_Silver"
                owned = True
            else:
                actor = "Armor_Adult_Gauntlet_Silver"
                owned = False

        # Capacity Bags
        elif slot_id == "Pa_Bag_01":  # Sticks
            sb = self.editor.equip_vars.get("stick_bag", tk.StringVar()).get() if hasattr(self.editor, "equip_vars") else ""
            actor = "Item_StickBag_Large" if "30" in sb else ("Item_StickBag_Medium" if "20" in sb else "Item_StickBag_Small")
            owned = bool(sb)
        elif slot_id == "Pa_Bag_02":  # Nuts
            nb = self.editor.equip_vars.get("nut_bag", tk.StringVar()).get() if hasattr(self.editor, "equip_vars") else ""
            actor = "Item_NutBag_Large" if "40" in nb else ("Item_NutBag_Medium" if "30" in nb else "Item_NutBag_Small")
            owned = bool(nb)
        elif slot_id == "Pa_Bag_03":  # Bullets
            bb = self.editor.equip_vars.get("bullet_bag", tk.StringVar()).get() if hasattr(self.editor, "equip_vars") else ""
            actor = "Item_BulletBag_Large" if "50" in bb else ("Item_BulletBag_Medium" if "40" in bb else "Item_BulletBag_Small")
            owned = bool(bb)
        elif slot_id == "Pa_Bag_04":  # Bombs
            bbag = self.editor.equip_vars.get("bomb_bag", tk.StringVar()).get() if hasattr(self.editor, "equip_vars") else ""
            actor = "Item_BombBag_Large" if "40" in bbag else ("Item_BombBag_Medium" if "30" in bbag else "Item_BombBag_Small")
            owned = ("Bomb Bag" in bbag)
        elif slot_id == "Pa_Bag_05":  # Quiver
            qb = self.editor.equip_vars.get("quiver", tk.StringVar()).get() if hasattr(self.editor, "equip_vars") else ""
            actor = "Item_Quiver_Large" if "50" in qb else ("Item_Quiver_Medium" if "40" in qb else "Item_Quiver_Small")
            owned = ("Quiver" in qb)

        # Bottles
        elif "bottle" in slot:
            bnum = slot["bottle"]
            bkey = f"bottle_{bnum}"
            val = self.editor.bottle_vars.get(bkey, tk.StringVar()).get() if hasattr(self.editor, "bottle_vars") else "(Not Acquired / Locked)"
            actor = BOTTLE_STRING_TO_ACTOR.get(val, "Item_Bottle")
            owned = (val != "(Not Acquired / Locked)" and bool(val))
            if not actor:
                actor = "Item_Bottle"

        # Trade Quest Item (Child Quest / Adult Trade)
        elif slot_id == "Pa_ItemIcon_23":
            age = self._get_current_age()
            adult_val = self.editor.adult_trade_var.get() if hasattr(self.editor, "adult_trade_var") else "None"
            child_val = self.editor.child_quest_var.get() if hasattr(self.editor, "child_quest_var") else "None"

            chosen_item = None
            if age == "adult" and adult_val and adult_val != "None":
                chosen_item = adult_val
            elif child_val and child_val != "None":
                chosen_item = child_val
            elif adult_val and adult_val != "None":
                chosen_item = adult_val
            else:
                chosen_item = None

            if chosen_item and chosen_item in TRADE_NAME_TO_ACTOR:
                actor = TRADE_NAME_TO_ACTOR[chosen_item]
                owned = True
            else:
                actor = None
                owned = False

        # Swords & Shields & Tunics & Boots
        elif slot_id == "Pa_Epuipment_02":  # Kokiri Sword
            actor = "Weapon_Sword_Kokiri"
            owned = self.editor.owned_swords.get("Kokiri Sword", tk.BooleanVar(value=True)).get() if hasattr(self.editor, "owned_swords") else True
            equipped = (self.editor.equip_vars.get("sword", tk.StringVar()).get() == "Kokiri Sword") if hasattr(self.editor, "equip_vars") else False
        elif slot_id == "Pa_Epuipment_01":  # Master Sword
            actor = "Weapon_Sword_Master"
            owned = self.editor.owned_swords.get("Master Sword", tk.BooleanVar(value=False)).get() if hasattr(self.editor, "owned_swords") else False
            equipped = (self.editor.equip_vars.get("sword", tk.StringVar()).get() == "Master Sword") if hasattr(self.editor, "equip_vars") else False
        elif slot_id == "Pa_Epuipment_00":  # Biggoron / Giant's Knife
            tier_name = self._big_sword_tier()
            actor = "Weapon_Sword_Biggoron" if tier_name == "Biggoron's Sword" else "Weapon_Sword_Giant"
            owned = tier_name is not None
            equipped = (tier_name is not None and self.editor.equip_vars.get("sword", tk.StringVar()).get() == tier_name) if hasattr(self.editor, "equip_vars") else False
        elif slot_id == "Pa_Epuipment_05":  # Deku Shield
            actor = "Weapon_Shield_Deku"
            owned = self.editor.owned_shields.get("Deku Shield", tk.BooleanVar(value=True)).get() if hasattr(self.editor, "owned_shields") else True
            equipped = (self.editor.equip_vars.get("shield", tk.StringVar()).get() == "Deku Shield") if hasattr(self.editor, "equip_vars") else False
        elif slot_id == "Pa_Epuipment_04":  # Hylian Shield
            actor = "Weapon_Shield_Hylian"
            owned = self.editor.owned_shields.get("Hylian Shield", tk.BooleanVar(value=False)).get() if hasattr(self.editor, "owned_shields") else False
            equipped = (self.editor.equip_vars.get("shield", tk.StringVar()).get() == "Hylian Shield") if hasattr(self.editor, "equip_vars") else False
        elif slot_id == "Pa_Epuipment_03":  # Mirror Shield
            actor = "Weapon_Shield_Mirror"
            owned = self.editor.owned_shields.get("Mirror Shield", tk.BooleanVar(value=False)).get() if hasattr(self.editor, "owned_shields") else False
            equipped = (self.editor.equip_vars.get("shield", tk.StringVar()).get() == "Mirror Shield") if hasattr(self.editor, "equip_vars") else False
        elif slot_id == "Pa_Epuipment_08":  # Kokiri Tunic
            actor = "Armor_Adult_Normal" if self._is_adult() else "Obj_Armor_Child_Normal"
            owned = self.editor.owned_tunics.get("Kokiri Tunic", tk.BooleanVar(value=True)).get() if hasattr(self.editor, "owned_tunics") else True
            equipped = (self.editor.equip_vars.get("tunic", tk.StringVar()).get() == "Kokiri Tunic") if hasattr(self.editor, "equip_vars") else False
        elif slot_id == "Pa_Epuipment_07":  # Goron Tunic
            actor = "Armor_Adult_Goron"
            owned = self.editor.owned_tunics.get("Goron Tunic", tk.BooleanVar(value=False)).get() if hasattr(self.editor, "owned_tunics") else False
            equipped = (self.editor.equip_vars.get("tunic", tk.StringVar()).get() == "Goron Tunic") if hasattr(self.editor, "equip_vars") else False
        elif slot_id == "Pa_Epuipment_06":  # Zora Tunic
            actor = "Armor_Adult_Zora"
            owned = self.editor.owned_tunics.get("Zora Tunic", tk.BooleanVar(value=False)).get() if hasattr(self.editor, "owned_tunics") else False
            equipped = (self.editor.equip_vars.get("tunic", tk.StringVar()).get() == "Zora Tunic") if hasattr(self.editor, "equip_vars") else False
        elif slot_id == "Pa_FootEquip_01":  # Iron Boots
            actor = "Armor_Adult_HeavyBoot"
            owned = self.editor.owned_boots.get("Iron Boots", tk.BooleanVar(value=False)).get() if hasattr(self.editor, "owned_boots") else False
            equipped = (self.editor.equip_vars.get("boots", tk.StringVar()).get() == "Iron Boots") if hasattr(self.editor, "equip_vars") else False
        elif slot_id == "Pa_FootEquip_00":  # Hover Boots
            actor = "Armor_Adult_HoverBoot"
            owned = self.editor.owned_boots.get("Hover Boots", tk.BooleanVar(value=False)).get() if hasattr(self.editor, "owned_boots") else False
            equipped = (self.editor.equip_vars.get("boots", tk.StringVar()).get() == "Hover Boots") if hasattr(self.editor, "equip_vars") else False
        elif slot_id == "Pa_HeadEquip_02":  # Active Mask
            cur_m = self.editor.active_mask_var.get() if hasattr(self.editor, "active_mask_var") else "None"
            if cur_m in MASK_NAME_TO_ACTOR:
                actor = MASK_NAME_TO_ACTOR[cur_m]
                owned = True
                equipped = True
            else:
                actor = "Armor_Child_Mask_Truth"
                owned = False
                equipped = False
        elif slot_id == "Pa_HeadEquip_00":  # Stone of Agony
            actor = "Item_AgonyStone"
            str_val = self.editor.equip_vars.get("strength", tk.StringVar()).get() if hasattr(self.editor, "equip_vars") else ""
            equipped = (str_val in ("Goron's Bracelet", "Silver Gauntlets", "Golden Gauntlets"))
            owned = True

        # Special Items / Tools / Songs / Fairy Blessings
        elif items_list:
            actor = items_list[0]
            # Check special_item_vars hash mapping
            hash_map = {
                "Weapon_Range_Bow": 0x938D56BF,
                "Weapon_Range_SlingShot": 0x80D34CE9,
                "Item_Boomerang": 0xA1D76D31,
                "Item_Hammer": 0x1AAFDB66,
                "Armor_GlassTruth": 0x49D1C374,
                "Item_DinFire": 0xB796C16D,
                "Item_FaroreWind": 0x47F2CA87,
                "Item_NayruLove": 0xF0828CD0,
                "Item_Arrow_Fire": 0x5E529AB9,
                "Item_Arrow_Ice": 0x40735A8D,
                "Item_Arrow_Light": 0xBFB285C8,
                "Item_Ocarina_Fairy": 0xB7DF60F1,
                "Item_Ocarina_Time": 0x54E2A3D1,
                "Item_Token_Gerudo": 0xFEB4D56B,
            }
            if actor in hash_map and hasattr(self.editor, "special_item_vars"):
                h_val = hash_map[actor]
                if h_val in self.editor.special_item_vars:
                    owned = bool(self.editor.special_item_vars[h_val][0].get())

            # Fairy blessings
            if slot_id == "Pa_Fairy_00":  # Magic MP
                owned = bool(self.editor.v_gift_spin.get()) if hasattr(self.editor, "v_gift_spin") else False
            elif slot_id == "Pa_Fairy_01":  # Gift of Doubled Magic
                owned = bool(self.editor.v_gift_magic.get()) if hasattr(self.editor, "v_gift_magic") else False
            elif slot_id == "Pa_Fairy_02":  # Double Defense
                owned = bool(self.editor.v_double_defense.get()) if hasattr(self.editor, "v_double_defense") else False

        if actor is None and items_list:
            actor = items_list[0]

        return actor, owned, equipped, dimmed, count, max_count

    def _big_sword_tier(self):
        """Name of the sword the big-sword slot shows: Biggoron's Sword, else Giant's Knife, else None."""
        owned = getattr(self.editor, "owned_swords", {})
        if "Biggoron's Sword" in owned and owned["Biggoron's Sword"].get():
            return "Biggoron's Sword"
        if "Giant's Knife" in owned and owned["Giant's Knife"].get():
            return "Giant's Knife"
        return None

    def get_actor_text(self, actor):
        """Retrieve (name, caption) for an actor from menu_text.json items, falling back to prettified name."""
        if not actor:
            return "", ""
        items_dict = MENU_TEXT.get("items", {})
        if actor in items_dict and isinstance(items_dict[actor], dict):
            entry = items_dict[actor]
            return entry.get("name", ""), entry.get("caption", "")
        fallback_name = _prettify_actor(actor)
        return fallback_name, ""

    def _get_current_age(self):
        """Derive Link's age ('adult' or 'child') or None if unknown.
        Honors editor.current_age first, then derives from equipped sword."""
        # 1. Check editor.current_age first
        if hasattr(self.editor, "current_age"):
            val = self.editor.current_age
            if hasattr(val, "get"):
                val = val.get()
            if val is not None:
                val_s = str(val).lower()
                if "adult" in val_s or val_s == "a":
                    return "adult"
                if "child" in val_s or val_s == "c":
                    return "child"

        # 2. Derive from equipped sword in equip_vars (Master/Biggoron -> adult, Kokiri -> child)
        equip_vars = getattr(self.editor, "equip_vars", None)
        if isinstance(equip_vars, dict) and "sword" in equip_vars:
            sword_var = equip_vars.get("sword")
            if sword_var is not None:
                sword_val = sword_var.get() if hasattr(sword_var, "get") else str(sword_var)
                if sword_val:
                    if "Master" in sword_val or "Biggoron" in sword_val:
                        return "adult"
                    elif "Kokiri" in sword_val:
                        return "child"

        # 3. Anything else / missing -> unknown (no dimming)
        return None

    def _is_adult(self):
        return self._get_current_age() == "adult"

    def _is_era_dimmed(self, era):
        if era == "CA" or not era:
            return False
        age = self._get_current_age()
        if age == "adult" and era == "C":
            return True
        if age == "child" and era == "A":
            return True
        return False

    def _get_max_rupees(self):
        wal = self.editor.equip_vars.get("wallet", tk.StringVar()).get() if hasattr(self.editor, "equip_vars") else ""
        if "Tycoon" in wal or "1000" in wal: return 1000
        elif "Giant" in wal or "500" in wal: return 500
        elif "Adult" in wal or "200" in wal: return 200
        return 99

    def _get_equipped_tunic_actor(self):
        tunic = self.editor.equip_vars.get("tunic", tk.StringVar()).get() if hasattr(self.editor, "equip_vars") else "Kokiri Tunic"
        if tunic == "Goron Tunic": return "Armor_Adult_Goron"
        elif tunic == "Zora Tunic": return "Armor_Adult_Zora"
        return "Armor_Adult_Normal" if self._is_adult() else "Obj_Armor_Child_Normal"

    def _get_equipped_sword_actor(self):
        sword = self.editor.equip_vars.get("sword", tk.StringVar()).get() if hasattr(self.editor, "equip_vars") else "Kokiri Sword"
        if sword == "Master Sword": return "Weapon_Sword_Master"
        elif sword == "Biggoron's Sword": return "Weapon_Sword_Biggoron"
        elif sword == "Giant's Knife": return "Weapon_Sword_Giant"
        return "Weapon_Sword_Kokiri"

    def _get_equipped_shield_actor(self):
        shield = self.editor.equip_vars.get("shield", tk.StringVar()).get() if hasattr(self.editor, "equip_vars") else "Deku Shield"
        if shield == "Hylian Shield": return "Weapon_Shield_Hylian"
        elif shield == "Mirror Shield": return "Weapon_Shield_Mirror"
        return "Weapon_Shield_Deku"

    def _get_selected_slot(self, page_def):
        slots = page_def.get("slots", [])
        if not self.selected_slot_id and slots:
            return slots[0]
        for s in slots:
            if s["id"] == self.selected_slot_id:
                return s
        return slots[0] if slots else None

    # =========================================================================
    # INTERACTION & SELECTION
    # =========================================================================
    def _find_slot_at(self, cx, cy):
        """Find slot under canvas coordinates (cx, cy)."""
        ref_x, ref_y = self.to_ref(cx, cy)
        page_name = self.current_page_name()
        slots = PAUSE_MENU_LAYOUT.get("plus_menu", {}).get("pages", {}).get(page_name, {}).get("slots", [])

        for s in slots:
            pos = s.get("pos")
            if not pos:
                continue
            sx, sy = pos
            sw, sh = s.get("size", [140, 140])
            hw, hh = sw / 2.0, sh / 2.0
            if (sx - hw <= ref_x <= sx + hw) and (sy - hh <= ref_y <= sy + hh):
                return s
        return None

    def _find_key_item_socket_at(self, cx, cy):
        """Find key item socket under canvas coordinates (cx, cy)."""
        for sock_id, sdata in self._key_item_sockets.items():
            scx, scy = sdata["canvas_pos"]
            sr = sdata["r"]
            if math.hypot(cx - scx, cy - scy) <= sr + 4:
                return sdata
        return None

    def _on_canvas_click(self, event):
        """Handle Left-Click: tab switching, edge arrows, or select/activate slots/sockets/songs."""
        self.canvas.focus_set()
        scale, ox, oy = self.get_transform()
        top_def = PAUSE_MENU_LAYOUT.get("plus_menu", {}).get("top_bar", {})
        tab_y_ref = top_def.get("tabs_y", 42)
        tab_x_def = top_def.get("tab_x", {})

        # Check tab clicks
        if hasattr(self, "_tab_positions") and self._tab_positions:
            for tname, (tx, ty, tw) in self._tab_positions.items():
                if tname in self.pages:
                    if abs(event.x - tx) < (tw / 2.0 + 12.0 * scale) and abs(event.y - ty) < 24.0 * scale:
                        self.show_subscreen(tname)
                        return
        else:
            for tname in self.pages:
                if tname in tab_x_def:
                    tx, ty = self.to_canvas(tab_x_def[tname], tab_y_ref)
                    if abs(event.x - tx) < 80 * scale and abs(event.y - ty) < 24 * scale:
                        self.show_subscreen(tname)
                        return

        # Check L / R clicks
        if hasattr(self, "_lr_positions") and self._lr_positions:
            lx, ly = self._lr_positions.get("L", (0, 0))
            if abs(event.x - lx) < 22 * scale and abs(event.y - ly) < 20 * scale:
                self.cycle_subscreen(-1)
                return
            rx, ry = self._lr_positions.get("R", (0, 0))
            if abs(event.x - rx) < 22 * scale and abs(event.y - ry) < 20 * scale:
                self.cycle_subscreen(1)
                return
        else:
            lx, ly = self.to_canvas(tab_x_def.get("L", 465), tab_y_ref)
            if abs(event.x - lx) < 22 * scale and abs(event.y - ly) < 20 * scale:
                self.cycle_subscreen(-1)
                return
            rx, ry = self.to_canvas(tab_x_def.get("R", 1455), tab_y_ref)
            if abs(event.x - rx) < 22 * scale and abs(event.y - ry) < 20 * scale:
                self.cycle_subscreen(1)
                return

        # Check Page Edge Navigation Arrows
        el_x, el_y = self.to_canvas(25, 540)
        if abs(event.x - el_x) < 30 * scale and abs(event.y - el_y) < 40 * scale:
            self.cycle_subscreen(-1)
            return
        er_x, er_y = self.to_canvas(1895, 540)
        if abs(event.x - er_x) < 30 * scale and abs(event.y - er_y) < 40 * scale:
            self.cycle_subscreen(1)
            return

        # Top bar: hearts, magic and rupees open an edit popup
        hit = self._topbar_hit_at(event.x, event.y)
        if hit:
            self._open_topbar_popup(hit, event)
            return

        # Subscreen interactions
        pname = self.current_page_name()
        if pname == "Key Items":
            sock = self._find_key_item_socket_at(event.x, event.y)
            if sock:
                sid = sock["id"]
                if self.selected_key_item_id != sid:
                    self.selected_key_item_id = sid
                    self.refresh_visuals()
                else:
                    h = sock.get("hash")
                    if h is not None and hasattr(self.editor, "quest_vars") and h in self.editor.quest_vars:
                        var = self.editor.quest_vars[h]
                        var.set(not var.get())
                        self.refresh_visuals()
            return
        elif pname == "Threads of Time":
            ref_x, ref_y = self.to_ref(event.x, event.y)
            if 50 <= ref_x <= 590:
                row_slot = int((ref_y - 290) // 95)
                n_vis = len(self._threads_visible_chapters) if self._threads_visible_chapters else 0
                if 0 <= row_slot < 7 and (row_slot + self._threads_scroll_offset) < n_vis:
                    if (ref_y - 290) % 95 < 88:
                        self._threads_selected_index = row_slot + self._threads_scroll_offset
                        self.refresh_visuals()
            return
        elif pname == "Song Book":
            hit_entry = None
            for entry in self.song_hit_boxes:
                s, sx, sy, srad = entry
                if math.hypot(event.x - sx, event.y - sy) <= srad:
                    hit_entry = entry
                    break
            if hit_entry:
                s = hit_entry[0]
                if self.selected_song_id != s["name"]:
                    self.selected_song_id = s["name"]
                    self.refresh_visuals()
                else:
                    self._on_song_arc_click(event)
            return

        # Plus menu slot click
        slot = self._find_slot_at(event.x, event.y)
        if slot:
            slot_id = slot["id"]
            if self.selected_slot_id != slot_id:
                # First click: Select slot and update preview
                self.selected_slot_id = slot_id
                self.refresh_visuals()
            else:
                # Second click: Activate slot action
                self.activate_slot(slot)

    def _on_canvas_right_click(self, event):
        """Handle Right-Click: Equipment -> equip; ammo slots -> menu; bottles -> contents menu."""
        self.canvas.focus_set()
        slot = self._find_slot_at(event.x, event.y)
        if not slot:
            return

        slot_id = slot["id"]
        page_name = self.current_page_name()

        # Equipment Page: Right-click directly equips item
        if page_name == "Equipment":
            equip_map = {
                "Pa_Epuipment_02": "Kokiri Sword",
                "Pa_Epuipment_01": "Master Sword",
                "Pa_Epuipment_00": "Biggoron's Sword",
                "Pa_Epuipment_05": "Deku Shield",
                "Pa_Epuipment_04": "Hylian Shield",
                "Pa_Epuipment_03": "Mirror Shield",
                "Pa_Epuipment_08": "Kokiri Tunic",
                "Pa_Epuipment_07": "Goron Tunic",
                "Pa_Epuipment_06": "Zora Tunic",
                "Pa_FootEquip_01": "Iron Boots",
                "Pa_FootEquip_00": "Hover Boots",
            }
            if slot_id == "Pa_Epuipment_00":
                self._on_gear_equip(self._big_sword_tier() or "Biggoron's Sword")
                return
            if slot_id in equip_map:
                self._on_gear_equip(equip_map[slot_id])
                return

        # Ammo slot: Right-click menu (Max, Empty, Set amount...)
        count_key = slot.get("count")
        if count_key:
            self._show_quantity_menu(event, count_key)
            return

        # Bottles: Right-click contents menu
        if "bottle" in slot:
            bkey = f"bottle_{slot['bottle']}"
            self._on_bottle_right_click(event, bkey)
            return

        # Child trade: Right-click menu
        if slot_id == "Pa_ItemIcon_23":
            self._on_child_trade_right_click(event)

    # =========================================================================
    # EDITABLE TOP BAR (hearts, magic, rupees)
    # =========================================================================
    def _topbar_hit_at(self, x, y):
        """Name of the top bar block ('hearts', 'magic', 'rupees') under canvas point (x, y), or None."""
        for name, (x1, y1, x2, y2) in self._topbar_hits.items():
            if x1 <= x <= x2 and y1 <= y <= y2:
                return name
        return None

    def _on_canvas_motion(self, event):
        hit = self._topbar_hit_at(event.x, event.y)
        if hit != self._topbar_hover:
            self._topbar_hover = hit
            try:
                self.canvas.configure(cursor="hand2" if hit else "")
            except Exception:
                pass
            self._draw_topbar_hover()

    def _on_canvas_leave(self, event=None):
        if self._topbar_hover is not None:
            self._topbar_hover = None
            try:
                self.canvas.configure(cursor="")
            except Exception:
                pass
            self._draw_topbar_hover()

    def _draw_topbar_hover(self):
        """Subtle cream outline around the hovered top bar block."""
        canv = self.canvas
        canv.delete("topbar_hover")
        rect = self._topbar_hits.get(self._topbar_hover) if self._topbar_hover else None
        if rect:
            scale, _, _ = self.get_transform()
            x1, y1, x2, y2 = rect
            canv.create_rectangle(x1 - 3, y1 - 3, x2 + 3, y2 + 3, fill="", outline=COLOR_TEXT_CREAM,
                                  width=max(1, int(2 * scale)), tags=("topbar_hover",))

    @staticmethod
    def _wheel_direction(event):
        num = getattr(event, "num", None)
        if num == 4:
            return 1
        if num == 5:
            return -1
        delta = getattr(event, "delta", 0) or 0
        return 1 if delta > 0 else (-1 if delta < 0 else 0)

    def _topbar_wheel(self, name, event):
        """Wheel over hearts (+-1 heart; Shift: max hearts), magic (+-1 MP) or rupees (+-1, Shift 10, Ctrl 100)."""
        d = self._wheel_direction(event)
        if d == 0:
            return
        state = getattr(event, "state", 0) or 0
        shift = bool(state & 0x0001)
        ctrl = bool(state & 0x0004)
        ed = self.editor

        if name == "hearts" and hasattr(ed, "v_hp") and hasattr(ed, "v_hearts"):
            tot = max(3, min(20, safe_int(ed.v_hearts, default=3)))
            if shift:
                ed.v_hearts.set(str(max(3, min(20, tot + d))))
                if hasattr(ed, "_on_total_hearts_change"):
                    ed._on_total_hearts_change()
            else:
                cur = safe_int(ed.v_hp, default=tot * 4)
                ed.v_hp.set(str(max(1, min(tot * 4, cur + 4 * d))))
                if hasattr(ed, "_on_hp_change"):
                    ed._on_hp_change()
        elif name == "magic" and hasattr(ed, "v_magic_points"):
            m_str = ed.v_magic.get() if hasattr(ed, "v_magic") else "None"
            max_mp = 48 if "Double" in m_str else (24 if "Standard" in m_str else 0)
            cur = safe_int(ed.v_magic_points, default=0)
            ed.v_magic_points.set(str(max(0, min(max_mp, cur + d))))
            if hasattr(ed, "_on_mp_change"):
                ed._on_mp_change()
        elif name == "rupees" and hasattr(ed, "v_rupees"):
            step = 100 if ctrl else (10 if shift else 1)
            cur = safe_int(ed.v_rupees, default=0)
            ed.v_rupees.set(str(max(0, min(self._get_max_rupees(), cur + d * step))))
        else:
            return
        self.refresh_visuals()

    def _close_topbar_popup(self, event=None):
        popup = self._popup
        self._popup = None
        self._popup_widgets = {}
        if popup is not None:
            try:
                popup.destroy()
            except Exception:
                pass

    def _popup_focus_out(self, event=None):
        """Close the popup when focus leaves it (but not when moving between its own widgets)."""
        def check():
            popup = self._popup
            if popup is None:
                return
            try:
                focus = popup.focus_get()
            except Exception:
                focus = None
            if focus is None or str(focus) != str(popup) and not str(focus).startswith(str(popup) + "."):
                self._close_topbar_popup()
        try:
            self.after(80, check)
        except Exception:
            pass

    def _open_topbar_popup(self, name, event=None):
        """Small dark popup bound to the editor's own variables for hearts, magic or rupees."""
        self._close_topbar_popup()
        ed = self.editor
        top = tk.Toplevel(self)
        top.withdraw()
        top.configure(bg=COLOR_BG, padx=10, pady=8)
        try:
            top.transient(self.winfo_toplevel())
        except Exception:
            pass
        top.title({"hearts": "Hearts", "magic": "Magic", "rupees": "Rupees"}.get(name, "Edit"))
        top.resizable(False, False)
        try:
            # The editor may be running as __main__, so look it up instead of importing a second copy
            _se = sys.modules.get("oot_save_editor") or sys.modules.get("__main__")
            _se.apply_title_bar_theme(top, {"bg": COLOR_BG, "fg": "#ffffff", "border": COLOR_BG}, True)
        except Exception:
            pass
        self._popup = top
        widgets = {}

        def after_change(helper=None):
            def run(event=None):
                if helper and hasattr(ed, helper):
                    getattr(ed, helper)()
                self.refresh_visuals()
            return run

        def add_row(row, label, key, var, lo, hi, helper=None):
            tk.Label(top, text=label, bg=COLOR_BG, fg=COLOR_TEXT_CREAM, anchor="w").grid(
                row=row, column=0, sticky="w", pady=2, padx=(0, 8))
            cb = after_change(helper)
            sb = tk.Spinbox(top, from_=lo, to=hi, textvariable=var, width=9, command=cb,
                            bg=COLOR_INNER_PANEL, fg=COLOR_TEXT, insertbackground=COLOR_TEXT,
                            buttonbackground=COLOR_PANEL_BG, relief="flat")
            sb.grid(row=row, column=1, sticky="w", pady=2)
            sb.bind("<KeyRelease>", cb)
            widgets[key] = sb
            return sb

        def add_combo(row, label, key, var, values, helper=None):
            tk.Label(top, text=label, bg=COLOR_BG, fg=COLOR_TEXT_CREAM, anchor="w").grid(
                row=row, column=0, sticky="w", pady=2, padx=(0, 8))
            box = ttk.Combobox(top, textvariable=var, values=list(values), state="readonly", width=30)
            box.grid(row=row, column=1, sticky="w", pady=2)
            box.bind("<<ComboboxSelected>>", after_change(helper))
            widgets[key] = box
            return box

        if name == "hearts":
            add_row(0, "Boss Heart Containers", "boss", ed.v_boss_containers, 0, 8, "_recalc_hearts_from_components")
            add_row(1, "Heart Pieces Found", "pieces", ed.v_heart_pieces_total, 0, 36, "_recalc_hearts_from_components")
            add_row(2, "Total Maximum Hearts", "hearts", ed.v_hearts, 3, 20, "_on_total_hearts_change")
            add_row(3, "Current Health (Quarters)", "hp", ed.v_hp, 1, 80, "_on_hp_change")
        elif name == "magic":
            add_combo(0, "Magic Meter Level", "magic", ed.v_magic,
                      ["None", "Standard Magic Meter (24 MP)", "Double Magic Meter (48 MP)"], "_on_magic_level_change")
            add_row(1, "Current Magic (MP)", "mp", ed.v_magic_points, 0, 48, "_on_mp_change")
        elif name == "rupees":
            add_row(0, "Rupees", "rupees", ed.v_rupees, 0, 1000)
            wallet_var = getattr(ed, "equip_vars", {}).get("wallet")
            if wallet_var is not None:
                combo = getattr(ed, "equipped_combos", {}).get("wallet")
                try:
                    values = list(combo.cget("values")) if combo is not None else []
                except Exception:
                    values = []
                add_combo(1, "Wallet", "wallet", wallet_var, values or UPGRADE_TIER_CHOICES["wallet"],
                          None)
                widgets["wallet"].bind("<<ComboboxSelected>>", lambda e: (
                    ed._on_bag_or_capacity_changed("wallet") if hasattr(ed, "_on_bag_or_capacity_changed") else None,
                    self.refresh_visuals()), add="+")
        self._popup_widgets = widgets

        try:
            px = getattr(event, "x_root", None)
            py = getattr(event, "y_root", None)
            if px is None or py is None:
                px, py = self.winfo_pointerx(), self.winfo_pointery()
            top.geometry(f"+{int(px) + 14}+{int(py) + 14}")
        except Exception:
            pass
        top.bind("<Escape>", self._close_topbar_popup)
        top.bind("<FocusOut>", self._popup_focus_out)
        top.deiconify()
        try:
            first = next(iter(widgets.values()))
            first.focus_set()
        except Exception:
            pass
        return top

    def _on_canvas_wheel(self, event):
        """Handle mouse wheel adjustments over the top bar, ammo or countable slots, or scroll Threads of Time."""
        hit = self._topbar_hit_at(event.x, event.y)
        if hit:
            self._topbar_wheel(hit, event)
            return

        if self.current_page_name() == "Threads of Time":
            delta = 0
            if hasattr(event, "delta") and event.delta:
                delta = -1 if event.delta > 0 else 1
            elif hasattr(event, "num"):
                if event.num == 4:
                    delta = -1
                elif event.num == 5:
                    delta = 1
            if delta != 0 and self._threads_visible_chapters:
                max_scroll = max(0, len(self._threads_visible_chapters) - 7)
                self._threads_scroll_offset = max(0, min(max_scroll, self._threads_scroll_offset + delta))
                max_sel = min(self._threads_scroll_offset + 6, len(self._threads_visible_chapters) - 1)
                self._threads_selected_index = max(self._threads_scroll_offset, min(max_sel, self._threads_selected_index))
                self.refresh_visuals()
            return

        slot = self._find_slot_at(event.x, event.y)
        if not slot:
            return
        count_key = slot.get("count")
        if count_key:
            self._handle_wheel(event, count_key)

    def _on_key_arrow(self, event):
        """Keyboard navigation: move cursor to the nearest slot / socket / song in the pressed direction."""
        if not self.winfo_ismapped():
            return
        key = event.keysym
        dx, dy = 0, 0
        if key == "Left": dx = -1
        elif key == "Right": dx = 1
        elif key == "Up": dy = -1
        elif key == "Down": dy = 1
        else: return

        page_name = self.current_page_name()
        if page_name in ("Key Items", "Threads of Time", "Song Book"):
            if page_name == "Key Items":
                if not self._key_item_sockets:
                    return
                cur = self._key_item_sockets.get(self.selected_key_item_id)
                if not cur:
                    self.selected_key_item_id = next(iter(self._key_item_sockets))
                    self.refresh_visuals()
                    return
                cx, cy = cur["ref_pos"]
                best_id = None
                best_dist = float("inf")
                for sid, sdata in self._key_item_sockets.items():
                    if sid == cur["id"]:
                        continue
                    sx, sy = sdata["ref_pos"]
                    diff_x = sx - cx
                    diff_y = sy - cy
                    in_dir = False
                    if dx > 0 and diff_x > 20: in_dir = True
                    elif dx < 0 and diff_x < -20: in_dir = True
                    elif dy > 0 and diff_y > 20: in_dir = True
                    elif dy < 0 and diff_y < -20: in_dir = True
                    if in_dir:
                        dist = (abs(diff_x) + abs(diff_y) * 2.0) if dx != 0 else (abs(diff_y) + abs(diff_x) * 2.0)
                        if dist < best_dist:
                            best_dist = dist
                            best_id = sid
                if best_id:
                    self.selected_key_item_id = best_id
                    self.refresh_visuals()
                return

            elif page_name == "Threads of Time":
                if not self._threads_visible_chapters:
                    return
                if dy < 0:
                    self._threads_selected_index = max(0, self._threads_selected_index - 1)
                elif dy > 0:
                    self._threads_selected_index = min(len(self._threads_visible_chapters) - 1, self._threads_selected_index + 1)
                self.refresh_visuals()
                return

            elif page_name == "Song Book":
                if not self.song_hit_boxes:
                    return
                cur_entry = next((item for item in self.song_hit_boxes if item[0]["name"] == self.selected_song_id), self.song_hit_boxes[0])
                cx, cy = cur_entry[1], cur_entry[2]
                best_name = None
                best_dist = float("inf")
                for s, sx, sy, _ in self.song_hit_boxes:
                    if s["name"] == cur_entry[0]["name"]:
                        continue
                    diff_x = sx - cx
                    diff_y = sy - cy
                    in_dir = False
                    if dx > 0 and diff_x > 10: in_dir = True
                    elif dx < 0 and diff_x < -10: in_dir = True
                    elif dy > 0 and diff_y > 10: in_dir = True
                    elif dy < 0 and diff_y < -10: in_dir = True
                    if in_dir:
                        dist = (abs(diff_x) + abs(diff_y) * 2.0) if dx != 0 else (abs(diff_y) + abs(diff_x) * 2.0)
                        if dist < best_dist:
                            best_dist = dist
                            best_name = s["name"]
                if best_name:
                    self.selected_song_id = best_name
                    self.refresh_visuals()
                return

        # Plus menu
        slots = [s for s in PAUSE_MENU_LAYOUT.get("plus_menu", {}).get("pages", {}).get(page_name, {}).get("slots", []) if s.get("pos")]
        if not slots:
            return

        cur_slot = next((s for s in slots if s["id"] == self.selected_slot_id), slots[0])
        cx, cy = cur_slot["pos"]

        best_slot = None
        best_dist = float("inf")

        for s in slots:
            if s["id"] == cur_slot["id"]:
                continue
            sx, sy = s["pos"]
            diff_x = sx - cx
            diff_y = sy - cy

            # Directional alignment check
            in_dir = False
            if dx > 0 and diff_x > 20: in_dir = True
            elif dx < 0 and diff_x < -20: in_dir = True
            elif dy > 0 and diff_y > 20: in_dir = True
            elif dy < 0 and diff_y < -20: in_dir = True

            if in_dir:
                # Weighted distance favoring the primary axis
                if dx != 0:
                    dist = abs(diff_x) + abs(diff_y) * 2.0
                else:
                    dist = abs(diff_y) + abs(diff_x) * 2.0
                if dist < best_dist:
                    best_dist = dist
                    best_slot = s

        if best_slot:
            self.selected_slot_id = best_slot["id"]
            self.refresh_visuals()

    def _on_key_activate(self, event=None):
        """Activate the currently selected slot via Enter/Space/A key."""
        if not self.winfo_ismapped():
            return
        page_name = self.current_page_name()
        if page_name in ("Key Items", "Threads of Time", "Song Book"):
            if page_name == "Key Items":
                sock = self._key_item_sockets.get(self.selected_key_item_id)
                if sock:
                    h = sock.get("hash")
                    if h is not None and hasattr(self.editor, "quest_vars") and h in self.editor.quest_vars:
                        var = self.editor.quest_vars[h]
                        var.set(not var.get())
                        self.refresh_visuals()
                return
            elif page_name == "Threads of Time":
                return
            elif page_name == "Song Book":
                cur = next((item for item in self.song_hit_boxes if item[0]["name"] == self.selected_song_id), None)
                if cur:
                    s, sx, sy, _ = cur
                    class _Ev:
                        pass
                    ev = _Ev()
                    ev.x = sx
                    ev.y = sy
                    self._on_song_arc_click(ev)
                return

        slots = PAUSE_MENU_LAYOUT.get("plus_menu", {}).get("pages", {}).get(page_name, {}).get("slots", [])
        slot = next((s for s in slots if s["id"] == self.selected_slot_id), None)
        if slot:
            self.activate_slot(slot)

    # =========================================================================
    # SLOT ACTIVATION HELPERS (TOGGLE / CYCLE)
    # =========================================================================
    def activate_slot(self, slot):
        """Perform slot activation action: toggle owned, cycle tiers, or cycle bottle contents."""
        slot_id = slot["id"]

        # 1. Items Page Slots
        if slot_id == "Pa_ItemIcon_00":  # Deku Sticks
            self._on_inv_slot_click("sticks")
        elif slot_id == "Pa_ItemIcon_01":  # Slingshot
            self._on_inv_slot_click("slingshot")
        elif slot_id == "Pa_ItemIcon_12":  # Magic Bean
            self._on_inv_slot_click("beans")
        elif slot_id == "Pa_ItemIcon_02":  # Boomerang
            self._toggle_special_item(0xA1D76D31)
        elif slot_id == "Pa_ItemIcon_08":  # Bow
            self._on_inv_slot_click("bow")
        elif slot_id == "Pa_ItemIcon_07":  # Hookshot / Longshot
            self._on_inv_slot_click("hookshot")
        elif slot_id == "Pa_ItemIcon_09":  # Fire Arrow
            self._toggle_special_item(0x5E529AB9)
        elif slot_id == "Pa_ItemIcon_10":  # Ice Arrow
            self._toggle_special_item(0x40735A8D)
        elif slot_id == "Pa_ItemIcon_11":  # Light Arrow
            self._toggle_special_item(0xBFB285C8)
        elif slot_id == "Pa_ItemIcon_06":  # Hammer
            self._toggle_special_item(0x1AAFDB66)
        elif slot_id == "Pa_ItemIcon_04":  # Bomb
            self._on_inv_slot_click("bombs")
        elif slot_id == "Pa_ItemIcon_05":  # Bombchu
            self._on_inv_slot_click("bombchus")
        elif slot_id == "Pa_ItemIcon_03":  # Deku Nut
            self._on_inv_slot_click("nuts")
        elif slot_id == "Pa_ItemIcon_22":  # Scrub Seed
            self._on_inv_slot_click("scrub")
        elif slot_id == "Pa_ItemIcon_14":  # Din's Fire
            self._toggle_special_item(0xB796C16D)
        elif slot_id == "Pa_ItemIcon_15":  # Farore's Wind
            self._toggle_special_item(0x47F2CA87)
        elif slot_id == "Pa_ItemIcon_16":  # Nayru's Love
            self._toggle_special_item(0xF0828CD0)
        elif slot_id == "Pa_ItemIcon_23":  # Child Trade
            self._on_inv_slot_click("child_trade")
        elif "bottle" in slot:
            self._on_inv_slot_click(f"bottle_{slot['bottle']}")

        # 2. Equipment Page Slots
        elif slot_id == "Pa_Epuipment_02":
            self._on_gear_click("Kokiri Sword")
        elif slot_id == "Pa_Epuipment_01":
            self._on_gear_click("Master Sword")
        elif slot_id == "Pa_Epuipment_00":
            self._cycle_big_sword()
        elif slot_id == "Pa_Epuipment_05":
            self._on_gear_click("Deku Shield")
        elif slot_id == "Pa_Epuipment_04":
            self._on_gear_click("Hylian Shield")
        elif slot_id == "Pa_Epuipment_03":
            self._on_gear_click("Mirror Shield")
        elif slot_id == "Pa_Epuipment_08":
            self._on_gear_click("Kokiri Tunic")
        elif slot_id == "Pa_Epuipment_07":
            self._on_gear_click("Goron Tunic")
        elif slot_id == "Pa_Epuipment_06":
            self._on_gear_click("Zora Tunic")
        elif slot_id == "Pa_FootEquip_01":
            self._on_gear_click("Iron Boots")
        elif slot_id == "Pa_FootEquip_00":
            self._on_gear_click("Hover Boots")
        elif slot_id == "Pa_HeadEquip_02":
            self._cycle_active_mask()
        elif slot_id == "Pa_HeadEquip_01":
            self._toggle_special_item(0x49D1C374)

        # 3. Collection Page Slots
        elif slot_id == "Pa_SkullSign_00":
            self.change_quantity("tokens", 1)
        elif slot_id == "heart_pieces":
            self.change_quantity("heart_pieces", 1)
        elif slot_id == "Pa_Ocarina_00":
            self._toggle_special_item(0xB7DF60F1)
        elif slot_id == "Pa_Ocarina_01":
            self._toggle_special_item(0x54E2A3D1)
        elif slot_id == "Pa_Fairy_00":
            self._on_blessing_click("gift_spin")
        elif slot_id == "Pa_Fairy_01":
            self._on_blessing_click("gift_magic")
        elif slot_id == "Pa_Fairy_02":
            self._on_blessing_click("double_defense")
        elif slot_id == "Pa_Gauntlet_00":
            self._toggle_goron_bracelet()
        elif slot_id == "Pa_Scales_00":
            self._on_upgrade_click("scale")
        elif slot_id == "Pa_Gauntlet_01":
            self._on_upgrade_click("strength")
        elif slot_id == "Pa_Membership_00":
            self._toggle_special_item(0xFEB4D56B)
        elif slot_id == "Pa_Bag_00":
            self._cycle_bag_tier("wallet")
        elif slot_id == "Pa_Bag_01":
            self._cycle_bag_tier("stick_bag")
        elif slot_id == "Pa_Bag_02":
            self._cycle_bag_tier("nut_bag")
        elif slot_id == "Pa_Bag_03":
            self._cycle_bag_tier("bullet_bag")
        elif slot_id == "Pa_Bag_04":
            self._cycle_bag_tier("bomb_bag")
        elif slot_id == "Pa_Bag_05":
            self._cycle_bag_tier("quiver")

    # =========================================================================
    # REUSED HELPERS (QUANTITY, AMMO, GEAR, BAGS)
    # =========================================================================
    def get_ammo_capacity(self, key):
        """Return maximum capacity for ammo or counter keys."""
        if hasattr(self.editor, "ammo_capacity"):
            return self.editor.ammo_capacity(key)
        if key == "arrows":
            q = self.editor.equip_vars.get("quiver", tk.StringVar()).get() if hasattr(self.editor, "equip_vars") else ""
            return 50 if "50" in q else (40 if "40" in q else (30 if "30" in q else 0))
        elif key == "bombs":
            bb = self.editor.equip_vars.get("bomb_bag", tk.StringVar()).get() if hasattr(self.editor, "equip_vars") else ""
            return 40 if "40" in bb else (30 if "30" in bb else (20 if "20" in bb else 0))
        elif key == "sticks":
            sb = self.editor.equip_vars.get("stick_bag", tk.StringVar()).get() if hasattr(self.editor, "equip_vars") else ""
            return 30 if "30" in sb else (20 if "20" in sb else 10)
        elif key == "nuts":
            nb = self.editor.equip_vars.get("nut_bag", tk.StringVar()).get() if hasattr(self.editor, "equip_vars") else ""
            return 40 if "40" in nb else (30 if "30" in nb else 20)
        elif key == "seeds":
            bul = self.editor.equip_vars.get("bullet_bag", tk.StringVar()).get() if hasattr(self.editor, "equip_vars") else ""
            return 50 if "50" in bul else (40 if "40" in bul else 30)
        elif key == "bombchus":
            return 30
        elif key == "beans":
            return 10
        elif key == "tokens":
            return 100
        elif key == "heart_pieces":
            return 3
        return 99

    def change_quantity(self, key, delta):
        """Adjust quantity clamping between 0 and current capacity."""
        cap = self.get_ammo_capacity(key)
        if key == "tokens":
            cur = safe_int(getattr(self.editor, "v_tokens", 0), default=0)
            new_val = max(0, min(cap, cur + delta))
            if hasattr(self.editor, "v_tokens"):
                self.editor.v_tokens.set(str(new_val))
        elif key == "heart_pieces":
            tot = safe_int(getattr(self.editor, "v_heart_pieces_total", 0), default=0)
            cur_held = tot % 4
            new_held = max(0, min(3, cur_held + delta))
            base_h = (tot // 4) * 4
            new_tot = base_h + new_held
            if hasattr(self.editor, "v_heart_pieces_total"):
                self.editor.v_heart_pieces_total.set(str(new_tot))
            if hasattr(self.editor, "_recalc_hearts_from_components"):
                self.editor._recalc_hearts_from_components()
            elif hasattr(self.editor, "v_heart_pieces_held"):
                self.editor.v_heart_pieces_held.set(str(new_held))
        elif hasattr(self.editor, "ammo_vars") and key in self.editor.ammo_vars:
            var = self.editor.ammo_vars[key][0]
            cur = safe_int(var.get(), default=0)
            new_val = max(0, min(cap, cur + delta))
            var.set(str(new_val))
            if key == "arrows" and new_val > 0 and 0x938D56BF in self.editor.special_item_vars:
                self.editor.special_item_vars[0x938D56BF][0].set(True)
            elif key == "seeds" and new_val > 0 and 0x80D34CE9 in self.editor.special_item_vars:
                self.editor.special_item_vars[0x80D34CE9][0].set(True)
        self.refresh_visuals()

    def set_quantity_max(self, key):
        cap = self.get_ammo_capacity(key)
        if key == "tokens":
            if hasattr(self.editor, "v_tokens"): self.editor.v_tokens.set(str(cap))
        elif key == "heart_pieces":
            tot = safe_int(getattr(self.editor, "v_heart_pieces_total", 0), default=0)
            base_h = (tot // 4) * 4
            if hasattr(self.editor, "v_heart_pieces_total"):
                self.editor.v_heart_pieces_total.set(str(base_h + 3))
            if hasattr(self.editor, "_recalc_hearts_from_components"):
                self.editor._recalc_hearts_from_components()
            elif hasattr(self.editor, "v_heart_pieces_held"):
                self.editor.v_heart_pieces_held.set("3")
        elif hasattr(self.editor, "ammo_vars") and key in self.editor.ammo_vars:
            self.editor.ammo_vars[key][0].set(str(cap))
            if key == "arrows" and cap > 0 and 0x938D56BF in self.editor.special_item_vars:
                self.editor.special_item_vars[0x938D56BF][0].set(True)
            elif key == "seeds" and cap > 0 and 0x80D34CE9 in self.editor.special_item_vars:
                self.editor.special_item_vars[0x80D34CE9][0].set(True)
        self.refresh_visuals()

    def set_quantity_empty(self, key):
        if key == "tokens":
            if hasattr(self.editor, "v_tokens"): self.editor.v_tokens.set("0")
        elif key == "heart_pieces":
            tot = safe_int(getattr(self.editor, "v_heart_pieces_total", 0), default=0)
            base_h = (tot // 4) * 4
            if hasattr(self.editor, "v_heart_pieces_total"):
                self.editor.v_heart_pieces_total.set(str(base_h))
            if hasattr(self.editor, "_recalc_hearts_from_components"):
                self.editor._recalc_hearts_from_components()
            elif hasattr(self.editor, "v_heart_pieces_held"):
                self.editor.v_heart_pieces_held.set("0")
        elif hasattr(self.editor, "ammo_vars") and key in self.editor.ammo_vars:
            self.editor.ammo_vars[key][0].set("0")
        self.refresh_visuals()

    def prompt_set_quantity(self, key):
        cap = self.get_ammo_capacity(key)
        cur = 0
        if key == "tokens": cur = safe_int(getattr(self.editor, "v_tokens", 0), default=0)
        elif key == "heart_pieces": cur = safe_int(getattr(self.editor, "v_heart_pieces_held", 0), default=0)
        elif hasattr(self.editor, "ammo_vars") and key in self.editor.ammo_vars:
            cur = safe_int(self.editor.ammo_vars[key][0].get(), default=0)
        val = simpledialog.askinteger("Set Amount", f"Enter amount (0-{cap}):", parent=self, minvalue=0, maxvalue=cap, initialvalue=cur)
        if val is not None:
            if key == "tokens":
                if hasattr(self.editor, "v_tokens"): self.editor.v_tokens.set(str(val))
            elif key == "heart_pieces":
                tot = safe_int(getattr(self.editor, "v_heart_pieces_total", 0), default=0)
                base_h = (tot // 4) * 4
                if hasattr(self.editor, "v_heart_pieces_total"):
                    self.editor.v_heart_pieces_total.set(str(base_h + val))
                if hasattr(self.editor, "_recalc_hearts_from_components"):
                    self.editor._recalc_hearts_from_components()
                elif hasattr(self.editor, "v_heart_pieces_held"):
                    self.editor.v_heart_pieces_held.set(str(val))
            elif hasattr(self.editor, "ammo_vars") and key in self.editor.ammo_vars:
                self.editor.ammo_vars[key][0].set(str(val))
                if key == "arrows" and val > 0 and 0x938D56BF in self.editor.special_item_vars:
                    self.editor.special_item_vars[0x938D56BF][0].set(True)
                elif key == "seeds" and val > 0 and 0x80D34CE9 in self.editor.special_item_vars:
                    self.editor.special_item_vars[0x80D34CE9][0].set(True)
            self.refresh_visuals()

    def _show_quantity_menu(self, event, key):
        cap = self.get_ammo_capacity(key)
        m = tk.Menu(self, tearoff=0, bg=COLOR_INNER_PANEL, fg=COLOR_TEXT, activebackground=COLOR_GOLD, activeforeground="#000")
        m.add_command(label=f"Max ({cap})", command=lambda: self.set_quantity_max(key))
        m.add_command(label="Empty (0)", command=lambda: self.set_quantity_empty(key))
        m.add_separator()
        m.add_command(label="Set amount...", command=lambda: self.prompt_set_quantity(key))
        m.tk_popup(event.x_root, event.y_root)

    def _handle_wheel(self, event, key):
        shift = bool(event.state & 0x0001)
        step = 10 if shift else 1
        delta = 0
        if getattr(event, "num", None) == 4:
            delta = step
        elif getattr(event, "num", None) == 5:
            delta = -step
        elif hasattr(event, "delta") and event.delta != 0:
            delta = step if event.delta > 0 else -step
        if delta != 0:
            self.change_quantity(key, delta)

    def _on_inv_slot_click(self, item_id):
        """Toggle or cycle inventory slots."""
        if item_id == "hookshot":
            cur = self.editor.hookshot_var.get() if hasattr(self.editor, "hookshot_var") else "None"
            if cur == "None": self.editor.hookshot_var.set("Hookshot")
            elif cur == "Hookshot": self.editor.hookshot_var.set("Longshot")
            else: self.editor.hookshot_var.set("None")
            self.refresh_visuals()

        elif item_id == "ocarina":
            oot_var = self.editor.special_item_vars[0x54E2A3D1][0]
            fairy_var = self.editor.special_item_vars[0xB7DF60F1][0]
            if not fairy_var.get() and not oot_var.get():
                fairy_var.set(True)
            elif fairy_var.get() and not oot_var.get():
                oot_var.set(True)
                fairy_var.set(False)
            else:
                oot_var.set(False)
                fairy_var.set(False)
            self.refresh_visuals()

        elif item_id.startswith("bottle_"):
            cur = self.editor.bottle_vars[item_id].get() if hasattr(self.editor, "bottle_vars") else ""
            b_choices = [
                "(Not Acquired / Locked)", "Empty Bottle", "Red Potion", "Green Potion",
                "Blue Potion", "Fairy", "Fish", "Blue Fire", "Bug", "Poe", "Big Poe", "Lon Lon Milk", "Ruto's Letter"
            ]
            try:
                idx = b_choices.index(cur)
                next_idx = (idx + 1) % len(b_choices)
                next_val = b_choices[next_idx]
            except ValueError:
                next_val = "Empty Bottle"
            if hasattr(self.editor, "bottle_vars") and item_id in self.editor.bottle_vars:
                self.editor.bottle_vars[item_id].set(next_val)
            try:
                b_num = int(item_id.split("_")[1])
                if hasattr(self.editor, "_on_bottle_selected"):
                    self.editor._on_bottle_selected(b_num)
            except Exception:
                pass
            self.refresh_visuals()

        elif item_id == "child_trade":
            child_choices, adult_choices = _get_trade_choices()
            age = self._get_current_age()
            adult_val = self.editor.adult_trade_var.get() if hasattr(self.editor, "adult_trade_var") else "None"
            child_val = self.editor.child_quest_var.get() if hasattr(self.editor, "child_quest_var") else "None"

            # Determine which group is currently shown
            if age == "adult":
                group = "child" if ((not adult_val or adult_val == "None") and child_val and child_val != "None") else "adult"
            else:
                group = "adult" if ((not child_val or child_val == "None") and adult_val and adult_val != "None") else "child"

            if group == "adult":
                cur = adult_val if adult_val in adult_choices else "None"
                nxt = adult_choices[(adult_choices.index(cur) + 1) % len(adult_choices)]
                if hasattr(self.editor, "adult_trade_var"):
                    self.editor.adult_trade_var.set(nxt)
            else:
                cur = child_val if child_val in child_choices else "None"
                nxt = child_choices[(child_choices.index(cur) + 1) % len(child_choices)]
                if hasattr(self.editor, "child_quest_var"):
                    self.editor.child_quest_var.set(nxt)
            self.refresh_visuals()

        elif item_id == "bow":
            var = self.editor.special_item_vars[0x938D56BF][0]
            var.set(not var.get())
            if var.get():
                cur_ammo = safe_int(self.editor.ammo_vars["arrows"][0].get(), default=0)
                if cur_ammo == 0:
                    self.editor.ammo_vars["arrows"][0].set(str(self.get_ammo_capacity("arrows")))
            self.refresh_visuals()

        elif item_id == "slingshot":
            var = self.editor.special_item_vars[0x80D34CE9][0]
            var.set(not var.get())
            if var.get():
                cur_ammo = safe_int(self.editor.ammo_vars["seeds"][0].get(), default=0)
                if cur_ammo == 0:
                    self.editor.ammo_vars["seeds"][0].set(str(self.get_ammo_capacity("seeds")))
            self.refresh_visuals()

        elif item_id in getattr(self.editor, "ammo_vars", {}):
            var = self.editor.ammo_vars[item_id][0]
            cur = safe_int(var.get(), default=0)
            cap = self.get_ammo_capacity(item_id)
            if cap == 0:
                var.set("0")
            else:
                var.set("0" if cur > 0 else str(cap))
            self.refresh_visuals()

    def _on_gear_click(self, item_name):
        if item_name == "Kokiri Boots":
            self._on_gear_equip(item_name)
            return

        cat = None
        var = None
        if item_name in getattr(self.editor, "owned_swords", {}):
            cat = "sword"
            var = self.editor.owned_swords[item_name]
        elif item_name in getattr(self.editor, "owned_shields", {}):
            cat = "shield"
            var = self.editor.owned_shields[item_name]
        elif item_name in getattr(self.editor, "owned_tunics", {}):
            cat = "tunic"
            var = self.editor.owned_tunics[item_name]
        elif item_name in getattr(self.editor, "owned_boots", {}):
            cat = "boots"
            var = self.editor.owned_boots[item_name]

        if var:
            var.set(not var.get())
            if hasattr(self.editor, "_sync_equipped_options"):
                self.editor._sync_equipped_options()
            self.refresh_visuals()

    def _cycle_big_sword(self):
        """Big-sword slot: none -> Giant's Knife -> Biggoron's Sword -> none."""
        owned = getattr(self.editor, "owned_swords", {})
        giant = owned.get("Giant's Knife")
        big = owned.get("Biggoron's Sword")
        tier = self._big_sword_tier()
        sword_var = getattr(self.editor, "equip_vars", {}).get("sword")
        was_equipped = sword_var is not None and tier is not None and sword_var.get() == tier
        if tier is None:
            new_tier = "Giant's Knife"
            if giant is not None:
                giant.set(True)
        elif tier == "Giant's Knife":
            new_tier = "Biggoron's Sword"
            if giant is not None:
                giant.set(False)
            if big is not None:
                big.set(True)
        else:
            new_tier = None
            if giant is not None:
                giant.set(False)
            if big is not None:
                big.set(False)
        # Keep the big sword equipped across the upgrade (Giant's Knife -> Biggoron's Sword).
        if was_equipped and new_tier is not None:
            sword_var.set(new_tier)
        if hasattr(self.editor, "_sync_equipped_options"):
            self.editor._sync_equipped_options()
        self.refresh_visuals()

    def _on_gear_equip(self, item_name):
        cat = None
        var = None
        if item_name in getattr(self.editor, "owned_swords", {}):
            cat = "sword"
            var = self.editor.owned_swords[item_name]
        elif item_name in getattr(self.editor, "owned_shields", {}):
            cat = "shield"
            var = self.editor.owned_shields[item_name]
        elif item_name in getattr(self.editor, "owned_tunics", {}):
            cat = "tunic"
            var = self.editor.owned_tunics[item_name]
        elif item_name in getattr(self.editor, "owned_boots", {}):
            cat = "boots"
            var = self.editor.owned_boots[item_name]

        if var:
            var.set(True)
        if cat and hasattr(self.editor, "equip_vars") and cat in self.editor.equip_vars:
            self.editor.equip_vars[cat].set(item_name)
        if hasattr(self.editor, "_sync_equipped_options"):
            self.editor._sync_equipped_options()
        self.refresh_visuals()

    def _on_mask_click(self, mask_name):
        cur = self.editor.active_mask_var.get() if hasattr(self.editor, "active_mask_var") else "None"
        if cur == mask_name:
            self.editor.active_mask_var.set("None")
        else:
            self.editor.active_mask_var.set(mask_name)
            if hasattr(self.editor, "child_quest_var"):
                self.editor.child_quest_var.set("None")
        self.refresh_visuals()

    def _cycle_active_mask(self):
        masks = ["None", "Keaton Mask", "Skull Mask", "Spooky Mask", "Bunny Hood", "Goron Mask", "Zora Mask", "Gerudo Mask", "Mask of Truth"]
        cur = self.editor.active_mask_var.get() if hasattr(self.editor, "active_mask_var") else "None"
        try:
            n_idx = (masks.index(cur) + 1) % len(masks)
        except ValueError:
            n_idx = 1
        self.editor.active_mask_var.set(masks[n_idx])
        if hasattr(self.editor, "child_quest_var"):
            self.editor.child_quest_var.set("None")
        self.refresh_visuals()

    def _toggle_special_item(self, kh):
        if hasattr(self.editor, "special_item_vars") and kh in self.editor.special_item_vars:
            var, _ = self.editor.special_item_vars[kh]
            var.set(not var.get())
            self.refresh_visuals()

    def _toggle_quest_item(self, kh):
        if hasattr(self.editor, "quest_vars") and kh in self.editor.quest_vars:
            var = self.editor.quest_vars[kh]
            var.set(not var.get())
            if hasattr(self.editor, "_on_story_item_toggle"):
                self.editor._on_story_item_toggle(kh, var)
            self.refresh_visuals()

    def _on_blessing_click(self, bid):
        if bid == "gift_spin":
            if hasattr(self.editor, "v_gift_spin"):
                self.editor.v_gift_spin.set(not self.editor.v_gift_spin.get())
        elif bid == "gift_magic":
            if hasattr(self.editor, "v_gift_magic"):
                self.editor.v_gift_magic.set(not self.editor.v_gift_magic.get())
        elif bid == "magic":
            cur = self.editor.v_magic.get() if hasattr(self.editor, "v_magic") else "None"
            nxt = "Standard Magic" if cur == "None" else "None"
            if hasattr(self.editor, "v_magic"):
                self.editor.v_magic.set(nxt)
        elif bid == "double_magic":
            cur = self.editor.v_magic.get() if hasattr(self.editor, "v_magic") else "None"
            nxt = "Double Magic" if "Double" not in cur else "Standard Magic"
            if hasattr(self.editor, "v_magic"):
                self.editor.v_magic.set(nxt)
        elif bid == "double_defense":
            val = not (self.editor.v_double_defense.get() if hasattr(self.editor, "v_double_defense") else False)
            if hasattr(self.editor, "v_double_defense"):
                self.editor.v_double_defense.set(val)
        self.refresh_visuals()

    def _toggle_goron_bracelet(self):
        str_val = self.editor.equip_vars.get("strength", tk.StringVar()).get() if hasattr(self.editor, "equip_vars") else "None"
        nxt = "None" if str_val in ("Goron's Bracelet", "Silver Gauntlets", "Golden Gauntlets") else "Goron's Bracelet"
        if hasattr(self.editor, "equip_vars") and "strength" in self.editor.equip_vars:
            self.editor.equip_vars["strength"].set(nxt)
        self.refresh_visuals()

    def _on_upgrade_click(self, uid):
        if uid == "strength":
            choices = UPGRADE_TIER_CHOICES["strength"]
            cur = self.editor.equip_vars.get("strength", tk.StringVar()).get()
            n_idx = (choices.index(cur) + 1) % len(choices) if cur in choices else 1
            self.editor.equip_vars["strength"].set(choices[n_idx])
        elif uid == "scale":
            choices = UPGRADE_TIER_CHOICES["scale"]
            cur = self.editor.equip_vars.get("scale", tk.StringVar()).get()
            n_idx = (choices.index(cur) + 1) % len(choices) if cur in choices else 1
            self.editor.equip_vars["scale"].set(choices[n_idx])
        elif uid == "gerudo_card":
            self._toggle_special_item(0xFEB4D56B)
        self.refresh_visuals()

    def _cycle_bag_tier(self, bid):
        choices = UPGRADE_TIER_CHOICES.get(bid, [])
        if choices and hasattr(self.editor, "equip_vars") and bid in self.editor.equip_vars:
            cur = self.editor.equip_vars[bid].get()
            n_idx = (choices.index(cur) + 1) % len(choices) if cur in choices else 0
            self.editor.equip_vars[bid].set(choices[n_idx])
            if hasattr(self.editor, "_on_bag_or_capacity_changed"):
                self.editor._on_bag_or_capacity_changed(bid)
            self.refresh_visuals()

    def _on_bottle_right_click(self, event, item_id):
        m = tk.Menu(self, tearoff=0, bg=COLOR_INNER_PANEL, fg=COLOR_TEXT, activebackground=COLOR_GOLD, activeforeground="#000")
        choices = ["(Not Acquired / Locked)", "Empty Bottle", "Red Potion", "Green Potion", "Blue Potion", "Fairy", "Fish", "Blue Fire", "Bug", "Poe", "Big Poe", "Lon Lon Milk", "Ruto's Letter"]
        for c in choices:
            m.add_command(label=c, command=lambda ch=c: self._set_bottle_choice(item_id, ch))
        if event is not None and hasattr(event, "x_root") and hasattr(event, "y_root"):
            try:
                m.tk_popup(event.x_root, event.y_root)
            except Exception:
                pass
        return m

    def _set_bottle_choice(self, item_id, choice):
        if hasattr(self.editor, "bottle_vars") and item_id in self.editor.bottle_vars:
            self.editor.bottle_vars[item_id].set(choice)
        try:
            b_num = int(item_id.split("_")[1])
            if hasattr(self.editor, "_on_bottle_selected"):
                self.editor._on_bottle_selected(b_num)
        except Exception:
            pass
        self.refresh_visuals()

    def _on_child_trade_right_click(self, event=None):
        child_choices, adult_choices = _get_trade_choices()
        m = tk.Menu(self, tearoff=0, bg=COLOR_INNER_PANEL, fg=COLOR_TEXT, activebackground=COLOR_GOLD, activeforeground="#000")
        for c in child_choices:
            m.add_command(label=c, command=lambda ch=c: self._set_child_quest(ch))
        m.add_separator()
        for a in adult_choices:
            m.add_command(label=a, command=lambda ad=a: self._set_adult_trade(ad))
        if event is not None and hasattr(event, "x_root") and hasattr(event, "y_root"):
            try:
                m.tk_popup(event.x_root, event.y_root)
            except Exception:
                pass
        return m

    def _set_child_quest(self, val):
        if hasattr(self.editor, "child_quest_var"):
            self.editor.child_quest_var.set(val)
        self.refresh_visuals()

    def _set_adult_trade(self, val):
        if hasattr(self.editor, "adult_trade_var"):
            self.editor.adult_trade_var.set(val)
        self.refresh_visuals()

    # =========================================================================
    # MINUS MENU PAGES (KEY ITEMS, THREADS OF TIME, SONG BOOK)
    # =========================================================================
    def _draw_key_items_page(self, scale):
        canv = self.canvas
        top_h = PAUSE_MENU_LAYOUT.get("plus_menu", {}).get("top_bar", {}).get("height", 95)
        scale, ox, oy = self.get_transform()

        # 1. Dark stone-brick background: rectangles ~200x110 px at ref
        row_h = 110.0 * scale
        brick_w = 200.0 * scale
        mortar_w = max(1, int(2 * scale))
        brick_colors = ["#3a2c22", "#45352a", "#3d2e24", "#423228", "#382a20"]

        start_cy = oy + top_h * scale
        end_cy = oy + 1080.0 * scale
        start_cx = ox
        end_cx = ox + 1920.0 * scale

        row = 0
        cur_y = start_cy
        while cur_y < end_cy:
            next_y = min(end_cy, cur_y + row_h)
            x_offset = (brick_w / 2.0) if (row % 2 == 1) else 0.0
            cur_x = start_cx - x_offset
            col = 0
            while cur_x < end_cx:
                next_x = cur_x + brick_w
                color = brick_colors[(row * 7 + col * 3) % len(brick_colors)]
                canv.create_rectangle(
                    max(start_cx, cur_x), cur_y, min(end_cx, next_x), next_y,
                    fill=color, outline="#1a120c", width=mortar_w
                )
                cur_x = next_x
                col += 1
            cur_y = next_y
            row += 1

        # 2. Large Hexagon Board: centre [960, 545], radius 520, flat top/bottom
        bcx, bcy = self.to_canvas(960, 545)
        # Outer bevel (#5b4636)
        r_bevel = 520.0 * scale
        canv.create_polygon(get_hexagon_flat_points(bcx, bcy, r_bevel), fill="#5b4636", outline="#3d2c20", width=max(1, int(3 * scale)))
        # Face (#8a6d52)
        r_face = 500.0 * scale
        canv.create_polygon(get_hexagon_flat_points(bcx, bcy, r_face), fill="#8a6d52", outline="#4d3826", width=max(1, int(2 * scale)))
        # Lighter inner hexagon (#9c7d60)
        r_inner = 440.0 * scale
        canv.create_polygon(get_hexagon_flat_points(bcx, bcy, r_inner), fill="#9c7d60", outline="#7a5f47", width=max(1, int(1.5 * scale)))

        # 3. Horizontal inner tray behind the three stones: x 625 to 1295, y 455 to 640 at ref, #7a5f47
        tx1, ty1 = self.to_canvas(625, 455)
        tx2, ty2 = self.to_canvas(1295, 640)
        tray_pts = get_rounded_rect_points(tx1, ty1, tx2, ty2, radius=14.0 * scale)
        canv.create_polygon(tray_pts, fill="#7a5f47", outline="#5b4430", width=max(1, int(2 * scale)))

        # 4. Sockets & Medallions/Stones
        minus_layout = PAUSE_MENU_LAYOUT.get("minus_menu", {}).get("Key Items", {})
        medallions = minus_layout.get("medallions", [])
        stones = minus_layout.get("stones", [])
        all_sockets = medallions + stones
        key_item_map = get_key_item_info_map()

        self._key_item_sockets = {}
        for sock in all_sockets:
            sock_id = sock["id"]
            item_name = sock["item"]
            ref_pos = sock["pos"]
            r_ref = sock.get("r", 95)
            scx, scy = self.to_canvas(ref_pos[0], ref_pos[1])
            sr = r_ref * scale

            en_name, item_hash = key_item_map.get(item_name, (item_name, None))
            is_owned = False
            if hasattr(self.editor, "quest_vars") and item_hash in self.editor.quest_vars:
                is_owned = bool(self.editor.quest_vars[item_hash].get())

            self._key_item_sockets[sock_id] = {
                "id": sock_id,
                "item": item_name,
                "en_name": en_name,
                "hash": item_hash,
                "canvas_pos": (scx, scy),
                "ref_pos": ref_pos,
                "r": sr,
            }

            # Round socket: ring #6b5340 with dark inner circle #4a3829
            canv.create_oval(scx - sr, scy - sr, scx + sr, scy + sr,
                             fill="#6b5340", outline="#3d2a1c", width=max(1, int(2 * scale)),
                             tags=(sock_id, "key_item_socket"))
            inner_r = sr * 0.82
            canv.create_oval(scx - inner_r, scy - inner_r, scx + inner_r, scy + inner_r,
                             fill="#4a3829", outline="#2b1c11", width=1,
                             tags=(sock_id, "key_item_socket"))

            # Owned items draw their icon in the socket; unowned show empty socket
            if is_owned:
                icon_path = None
                gen_name = KEY_ITEM_ASSET_NAMES.get(item_name)
                if gen_name:
                    cand = os.path.join(SWITCH2_ASSETS_DIR, gen_name)
                    if os.path.exists(cand):
                        icon_path = cand

                icon_drawn = False
                if icon_path:
                    icon_sz = max(24, int(sr * 1.55))
                    img = self.textures.get(icon_path, (icon_sz, icon_sz))
                    if img:
                        canv.create_image(scx, scy, image=img, tags=(sock_id, "key_item_socket", "key_item_icon"))
                        icon_drawn = True

                if not icon_drawn:
                    canv.create_oval(scx - inner_r * 0.7, scy - inner_r * 0.7,
                                     scx + inner_r * 0.7, scy + inner_r * 0.7,
                                     fill="#eab308", outline="#fef08a", width=1,
                                     tags=(sock_id, "key_item_socket", "key_item_icon"))

            # Selected cursor: white glowing ring around socket
            if self.selected_key_item_id == sock_id:
                canv.create_oval(scx - (sr + 6 * scale), scy - (sr + 6 * scale),
                                 scx + (sr + 6 * scale), scy + (sr + 6 * scale),
                                 fill="", outline="#93c5fd", width=max(1, int(1.5 * scale)), tags=("cursor",))
                canv.create_oval(scx - (sr + 4 * scale), scy - (sr + 4 * scale),
                                 scx + (sr + 4 * scale), scy + (sr + 4 * scale),
                                 fill="", outline="#ffffff", width=max(2, int(3 * scale)), tags=("cursor",))

        # 5. Small caption band at bottom-left: shows selected item's name and caption
        sel_data = self._key_item_sockets.get(self.selected_key_item_id)
        if sel_data:
            item_name = sel_data["item"]
            item_entry = MENU_TEXT.get("items", {}).get(item_name, {})
            disp_name = item_entry.get("name") if isinstance(item_entry, dict) else None
            disp_caption = item_entry.get("caption") if isinstance(item_entry, dict) else None
            if not disp_name:
                disp_name = sel_data.get("en_name", item_name)

            cx1, cy1 = self.to_canvas(80, 930)
            cx2, cy2 = self.to_canvas(560, 1010)
            cap_pts = get_rounded_rect_points(cx1, cy1, cx2, cy2, radius=10.0 * scale)
            canv.create_polygon(cap_pts, fill="#1a140f", outline="#3a2c20", width=max(1, int(1.5 * scale)))
            mid_cx = (cx1 + cx2) / 2.0
            if disp_caption:
                name_y = cy1 + (cy2 - cy1) * 0.35
                cap_y = cy1 + (cy2 - cy1) * 0.72
                canv.create_text(mid_cx, name_y, text=disp_name, fill="#f3e6c8", font=self._font(28, "normal"), anchor="center")
                canv.create_text(mid_cx, cap_y, text=disp_caption, fill="#c7b299", font=self._font(18, "normal"), anchor="center")
            else:
                mid_cy = (cy1 + cy2) / 2.0
                canv.create_text(mid_cx, mid_cy, text=disp_name, fill="#f3e6c8", font=self._font(30, "normal"), anchor="center")

    def _draw_threads_of_time_page(self, scale):
        canv = self.canvas
        top_h = PAUSE_MENU_LAYOUT.get("plus_menu", {}).get("top_bar", {}).get("height", 95)
        bx1, by1 = self.to_canvas(0, top_h)
        bx2, by2 = self.to_canvas(1920, 1080)
        canv.create_rectangle(bx1, by1, bx2, by2, fill="#1d140d", outline="")

        # 1. Filter visible chapters
        complete_val = murmur3_32("Complete")
        not_ready_val = murmur3_32("NotReady")

        visible_chapters = []
        shown_ids = set()

        for ch in THREADS_OF_TIME_DATA.get("chapters", []):
            cid = ch["id"]
            parent = ch.get("parent")
            field_hex = ch.get("field", "0x0")
            field_val = 0
            if hasattr(self.editor, "active_slot") and self.editor.active_slot:
                try:
                    f_int = int(field_hex, 16)
                    field_val = self.editor.active_slot.get(f_int, 0)
                except Exception:
                    field_val = 0

            if field_val == complete_val:
                status = "Complete"
            elif field_val == 0 or field_val == not_ready_val:
                status = "Not started"
            else:
                status = "In progress"

            if status == "Not started":
                continue
            if parent is not None and parent not in shown_ids:
                continue

            shown_ids.add(cid)
            visible_chapters.append((ch, status))

        self._threads_visible_chapters = visible_chapters

        if visible_chapters:
            self._threads_selected_index = max(0, min(self._threads_selected_index, len(visible_chapters) - 1))
        else:
            self._threads_selected_index = 0

        # Adjust scroll offset to keep selected row in view (7 rows visible)
        if self._threads_selected_index < self._threads_scroll_offset:
            self._threads_scroll_offset = self._threads_selected_index
        elif self._threads_selected_index >= self._threads_scroll_offset + 7:
            self._threads_scroll_offset = self._threads_selected_index - 6
        max_scroll = max(0, len(visible_chapters) - 7)
        self._threads_scroll_offset = max(0, min(max_scroll, self._threads_scroll_offset))

        # 2. Draw Left Chapter List (x 50..590 at ref, first row y 290, row height 95, child rows indented 48)
        start_idx = self._threads_scroll_offset
        end_idx = min(len(visible_chapters), start_idx + 7)

        for idx in range(start_idx, end_idx):
            ch, status = visible_chapters[idx]
            row_slot = idx - start_idx
            ref_row_y = 290.0 + row_slot * 95.0
            is_child = bool(ch.get("parent"))
            ref_x1 = 50.0 + (48.0 if is_child else 0.0)
            ref_x2 = 590.0

            rx1, ry1 = self.to_canvas(ref_x1, ref_row_y)
            rx2, ry2 = self.to_canvas(ref_x2, ref_row_y + 88.0)

            ch_data = MENU_TEXT.get("chapters", {}).get(ch["id"], {})
            title = ch_data.get("title") if isinstance(ch_data, dict) else None
            if not title:
                title = ch["id"].replace("_", " ")

            is_selected = (idx == self._threads_selected_index)
            row_tag = f"chapter_row_{idx}"

            if is_selected:
                # Deep blue gradient band (#1d2c52 -> #24365f) with white bar at left edge
                canv.create_rectangle(rx1, ry1, rx2, ry2, fill="#1d2c52", outline="#24365f", width=1, tags=(row_tag, "chapter_row"))
                canv.create_rectangle(rx1, ry1, rx1 + 6 * scale, ry2, fill="#ffffff", outline="", tags=(row_tag, "chapter_row"))
                canv.create_text(rx1 + 24 * scale, (ry1 + ry2) / 2.0, text=title, fill="#ffffff",
                                 font=self._font(34, "normal"), anchor="w", tags=(row_tag, "chapter_row"))
            else:
                # Dark band (#1a140f, 1px edge #3a2c20) with title in 34px Segoe UI cream
                canv.create_rectangle(rx1, ry1, rx2, ry2, fill="#1a140f", outline="#3a2c20", width=1, tags=(row_tag, "chapter_row"))
                canv.create_text(rx1 + 20 * scale, (ry1 + ry2) / 2.0, text=title, fill="#f3e6c8",
                                 font=self._font(34, "normal"), anchor="w", tags=(row_tag, "chapter_row"))

        # Thin scrollbar at x ~ 20 (if more than 7 chapters)
        if len(visible_chapters) > 7:
            sb_x, sb_y1 = self.to_canvas(20, 290)
            _, sb_y2 = self.to_canvas(20, 290 + 7 * 95)
            sb_total_h = sb_y2 - sb_y1
            canv.create_line(sb_x, sb_y1, sb_x, sb_y2, fill="#2a1e14", width=max(1, int(3 * scale)))
            thumb_ratio = 7.0 / len(visible_chapters)
            thumb_h = max(20.0 * scale, sb_total_h * thumb_ratio)
            scroll_pct = self._threads_scroll_offset / float(len(visible_chapters) - 7)
            thumb_y1 = sb_y1 + (sb_total_h - thumb_h) * scroll_pct
            canv.create_line(sb_x, thumb_y1, sb_x, thumb_y1 + thumb_h, fill="#8a6540", width=max(2, int(5 * scale)))

        # 3. Right Detail Panel (x 660..1500)
        p_x1, p_y1 = self.to_canvas(630, 110)
        p_x2, p_y2 = self.to_canvas(1880, 1020)
        canv.create_rectangle(p_x1, p_y1, p_x2, p_y2, fill="#0d0906", outline="#24180e", width=1)

        if visible_chapters and 0 <= self._threads_selected_index < len(visible_chapters):
            sel_ch, sel_status = visible_chapters[self._threads_selected_index]
            cid = sel_ch["id"]

            ch_data = MENU_TEXT.get("chapters", {}).get(cid, {})
            title = ch_data.get("title") if isinstance(ch_data, dict) else None
            if not title:
                title = cid.replace("_", " ")
            body_raw = ch_data.get("summary", "") if isinstance(ch_data, dict) else ""

            # Small-caps state label ("COMPLETE" in #b07a3c, or "IN PROGRESS") at y 200
            st_x, st_y = self.to_canvas(660, 200)
            st_text = "COMPLETE" if sel_status == "Complete" else "IN PROGRESS"
            st_color = "#b07a3c" if sel_status == "Complete" else "#5a8cc8"
            canv.create_text(st_x, st_y, text=st_text, fill=st_color, font=self._font(28, "bold"), anchor="w")

            # Title in large bold small-caps style (64px, white) at y 265
            t_x, t_y = self.to_canvas(660, 265)
            canv.create_text(t_x, t_y, text=title, fill="#ffffff", font=self._font(64, "bold"), anchor="w")

            # Ornamental divider
            div_x1, div_y = self.to_canvas(660, 335)
            div_x2, _ = self.to_canvas(1550, 335)
            canv.create_line(div_x1, div_y, div_x2, div_y, fill="#5a3d24", width=max(1, int(2 * scale)))

            # Body text (34px, line spacing 1.4, width 830) unwrapped
            if body_raw:
                paragraphs = [p.replace("\n", " ").strip() for p in body_raw.split("\n\n")]
                body_fmt = "\n\n".join(p for p in paragraphs if p)
                b_x, b_y = self.to_canvas(660, 385)
                canv.create_text(b_x, b_y, text=body_fmt, fill="#f3e6c8",
                                 font=self._font(34, "normal"), width=int(830 * scale), anchor="nw")

    def _draw_song_book_page(self, scale):
        canv = self.canvas
        top_h = PAUSE_MENU_LAYOUT.get("plus_menu", {}).get("top_bar", {}).get("height", 95)
        bx1, by1 = self.to_canvas(0, top_h)
        bx2, by2 = self.to_canvas(1920, 1080)
        canv.create_rectangle(bx1, by1, bx2, by2, fill="#1d140d", outline="")

        # 1. Arc of 13 Songs
        arc_w = 1920.0
        arc_h = 460.0
        r_ref = 55.0
        pos_list = compute_song_arc_positions(arc_w, arc_h, radius=r_ref)
        song_defs = {s["name"]: s for s in self._get_song_list()}

        self.song_hit_boxes = []
        for name, rx, ry, _ in pos_list:
            s_ref_y = ry + 95.0
            cx, cy = self.to_canvas(rx, s_ref_y)
            rad = r_ref * scale
            s_def = song_defs.get(name, {"name": name, "bit_idx": None, "is_scarecrow": False})
            self.song_hit_boxes.append((s_def, cx, cy, rad))

        for s_def, cx, cy, rad in self.song_hit_boxes:
            name = s_def["name"]
            is_sc = s_def.get("is_scarecrow", False)
            bit_idx = s_def.get("bit_idx")
            fam_color = s_def.get("color", "#e9dcc0")
            g_idx = s_def.get("game_idx", 0)

            is_learned = False
            if is_sc:
                if hasattr(self.editor, "scarecrow_state_var"):
                    is_learned = (self.editor.scarecrow_state_var.get() == "Learned")
            elif bit_idx is not None and hasattr(self.editor, "song_vars"):
                var = self.editor.song_vars.get(bit_idx)
                if var:
                    is_learned = bool(var.get())

            is_selected = (name == self.selected_song_id)
            disc_tag = f"song_{g_idx}"

            if is_learned:
                canv.create_oval(cx - rad, cy - rad, cx + rad, cy + rad,
                                 fill="#2a1d12", outline=fam_color, width=max(2, int(4 * scale)),
                                 tags=(disc_tag, "song_disc"))
                in_rad = rad * 0.78
                canv.create_oval(cx - in_rad, cy - in_rad, cx + in_rad, cy + in_rad,
                                 fill="#1a110a", outline=fam_color, width=1,
                                 tags=(disc_tag, "song_disc"))
                note_file = s_def.get("icon", "note_gold.png")
                note_path = os.path.join(SWITCH2_ASSETS_DIR, note_file)
                icon_sz = max(16, int(rad * 1.1))
                img = self.textures.get(note_path, (icon_sz, icon_sz)) if os.path.exists(note_path) else None
                if img:
                    canv.create_image(cx, cy, image=img, tags=(disc_tag, "song_disc"))
                else:
                    canv.create_text(cx, cy, text="♪", fill=fam_color, font=self._font(36, "bold"), tags=(disc_tag, "song_disc"))
            else:
                canv.create_oval(cx - rad, cy - rad, cx + rad, cy + rad,
                                 fill="#140f0a", outline="#3d2c1e", width=max(1, int(2 * scale)),
                                 tags=(disc_tag, "song_disc"))
                in_rad = rad * 0.78
                canv.create_oval(cx - in_rad, cy - in_rad, cx + in_rad, cy + in_rad,
                                 fill="#0c0906", outline="#241a12", width=1,
                                 tags=(disc_tag, "song_disc"))
                canv.create_text(cx, cy, text="♪", fill="#3d2c1e", font=self._font(32, "bold"), tags=(disc_tag, "song_disc"))

            if is_selected:
                canv.create_oval(cx - (rad + 6 * scale), cy - (rad + 6 * scale),
                                 cx + (rad + 6 * scale), cy + (rad + 6 * scale),
                                 fill="", outline="#93c5fd", width=max(1, int(1.5 * scale)), tags=("cursor",))
                canv.create_oval(cx - (rad + 4 * scale), cy - (rad + 4 * scale),
                                 cx + (rad + 4 * scale), cy + (rad + 4 * scale),
                                 fill="", outline="#ffffff", width=max(2, int(3 * scale)), tags=("cursor",))

        # 2. Parchment Panel with 5 Staff Lines
        px1, py1 = self.to_canvas(340, 560)
        px2, py2 = self.to_canvas(1580, 990)
        parch_pts = get_rounded_rect_points(px1, py1, px2, py2, radius=18.0 * scale)
        canv.create_polygon(parch_pts, fill="#e8d9b5", outline="#b89d6a", width=max(2, int(3 * scale)))

        sel_entry = next((item for item in self.song_hit_boxes if item[0]["name"] == self.selected_song_id), self.song_hit_boxes[0])
        sel_def = sel_entry[0]
        sel_name = sel_def["name"]
        sel_g_idx = sel_def.get("game_idx", 0)

        song_list = MENU_TEXT.get("songs", [])
        song_data = song_list[sel_g_idx] if (isinstance(song_list, list) and 0 <= sel_g_idx < len(song_list)) else None
        title_txt = song_data.get("name") if isinstance(song_data, dict) else None
        caption_txt = song_data.get("caption") if isinstance(song_data, dict) else None
        if not title_txt:
            title_txt = sel_name

        tcx, tcy = self.to_canvas(960, 620)
        canv.create_text(tcx, tcy, text=title_txt, fill="#4a3018", font=self._font(40, "bold"), anchor="center")

        staff_top_ref = 690.0
        staff_bot_ref = 830.0
        for i in range(5):
            line_ref_y = staff_top_ref + i * (staff_bot_ref - staff_top_ref) / 4.0
            lx1, ly = self.to_canvas(440, line_ref_y)
            lx2, _ = self.to_canvas(1480, line_ref_y)
            canv.create_line(lx1, ly, lx2, ly, fill="#9c805a", width=max(1, int(2 * scale)))

        if sel_def.get("is_scarecrow"):
            sc_notes = []
            if hasattr(self.editor, "scarecrow_note_vars"):
                label_to_val = {lbl: val for val, lbl in oot_scarecrow.NOTE_LABELS.items()}
                for nv in self.editor.scarecrow_note_vars:
                    val = nv.get() if hasattr(nv, "get") else nv
                    if val is None or val == "-" or val == 0:
                        continue
                    pitch = None
                    if isinstance(val, int) and not isinstance(val, bool):
                        pitch = val
                    elif isinstance(val, str):
                        s = val.strip()
                        if not s or s == "-" or s == "0":
                            continue
                        if s.isdigit():
                            pitch = int(s)
                        elif s in label_to_val:
                            pitch = label_to_val[s]
                        elif s.startswith("? (") and s.endswith(")") and s[3:-1].isdigit():
                            pitch = int(s[3:-1])
                    if pitch is None or pitch <= 0:
                        continue
                    lbl = oot_scarecrow.BUTTON_LABELS.get(pitch, "?")
                    sc_notes.append((lbl, pitch))
            song_notes = sc_notes
        else:
            song_notes = []
            pitches = oot_scarecrow.GAME_SONGS.get(sel_name, [])
            for p in pitches:
                lbl = oot_scarecrow.BUTTON_LABELS.get(p, "?")
                song_notes.append((lbl, p))

        if song_notes:
            start_x_ref = 540.0
            end_x_ref = 1380.0
            n_count = len(song_notes)
            n_cap_rad = 22.0 * scale
            for idx, (lbl, pitch) in enumerate(song_notes):
                nx_ref = start_x_ref + (idx + 0.5) * (end_x_ref - start_x_ref) / max(1, n_count)
                ny_ref = compute_staff_note_y(pitch, staff_top_ref, staff_bot_ref)
                ncx, ncy = self.to_canvas(nx_ref, ny_ref)

                canv.create_oval(ncx - n_cap_rad, ncy - n_cap_rad, ncx + n_cap_rad, ncy + n_cap_rad,
                                 fill="#fdfaf2", outline="#8c6b45", width=max(1, int(2 * scale)),
                                 tags=("staff_note", "staff_note_cap"))
                canv.create_text(ncx, ncy, text=lbl, fill="#4a3018", font=self._font(22, "bold"),
                                 tags=("staff_note", "staff_note_text"))

        if caption_txt:
            ccx, ccy = self.to_canvas(960, 910)
            canv.create_text(ccx, ccy, text=caption_txt, fill="#5c4028", font=self._font(28, "normal"),
                             width=int(1000 * scale), anchor="center")

    # =========================================================================
    # BACKWARDS COMPATIBILITY (SONG BOOK & LEGACY TEST METHODS)
    # =========================================================================
    def _get_song_list(self):
        fallback = {
            "Zelda's Lullaby": 0,
            "Epona's Song": 1,
            "Saria's Song": 2,
            "Song of Time": 3,
            "Sun's Song": 4,
            "Song of Storms": 5,
            "Minuet of Forest": 6,
            "Bolero of Fire": 7,
            "Serenade of Water": 8,
            "Requiem of Spirit": 9,
            "Nocturne of Shadow": 10,
            "Prelude of Light": 11,
        }
        try:
            from oot_save_editor import SONGS
            bit_map = {name: bit for name, bit, *_ in SONGS}
        except Exception:
            bit_map = fallback

        songs_order = [
            (0, "Zelda's Lullaby", False, "#e9dcc0", "note_gold.png"),
            (1, "Epona's Song", False, "#e9dcc0", "note_gold.png"),
            (2, "Saria's Song", False, "#e9dcc0", "note_gold.png"),
            (3, "Sun's Song", False, "#e9dcc0", "note_gold.png"),
            (4, "Song of Time", False, "#e9dcc0", "note_gold.png"),
            (5, "Song of Storms", False, "#e9dcc0", "note_gold.png"),
            (6, "Minuet of Forest", False, "#3fae4a", "note_green.png"),
            (7, "Bolero of Fire", False, "#d8452f", "note_red.png"),
            (8, "Serenade of Water", False, "#3a7bd5", "note_cyan.png"),
            (9, "Requiem of Spirit", False, "#e08a2e", "note_gold.png"),
            (10, "Nocturne of Shadow", False, "#8a4fc4", "note_purple.png"),
            (11, "Prelude of Light", False, "#e6c84a", "note_gold.png"),
            (12, "Scarecrow's Song", True, "#a87a4a", "note_gold.png"),
        ]
        res = []
        for g_idx, name, is_sc, color, icon in songs_order:
            bit_idx = None if is_sc else bit_map.get(name, fallback.get(name))
            res.append({
                "game_idx": g_idx,
                "name": name,
                "bit_idx": bit_idx,
                "is_scarecrow": is_sc,
                "color": color,
                "icon": icon,
            })
        return res

    def _render_song_arc(self, canvas_w=None, canvas_h=None):
        w = canvas_w or 900
        h = canvas_h or 260
        pos_list = compute_song_arc_positions(w, h, radius=28)
        song_defs = {s["name"]: s for s in self._get_song_list()}
        self.song_hit_boxes = []
        for name, x, y, rad in pos_list:
            s_def = song_defs.get(name, {"name": name, "bit_idx": None, "is_scarecrow": False})
            self.song_hit_boxes.append((s_def, x, y, rad))

    def _on_song_arc_click(self, event):
        if not self.song_hit_boxes:
            self._render_song_arc()
        for s, x, y, rad in self.song_hit_boxes:
            dist = math.hypot(event.x - x, event.y - y)
            if dist <= rad:
                self.selected_song_id = s["name"]
                if s["is_scarecrow"]:
                    if hasattr(self.editor, "switch_to_quest_tab_scarecrow"):
                        self.editor.switch_to_quest_tab_scarecrow()
                elif s["bit_idx"] is not None and hasattr(self.editor, "song_vars"):
                    var = self.editor.song_vars[s["bit_idx"]]
                    var.set(not var.get())
                self.refresh_visuals()
                return
