"""
The Legend of Zelda: Ocarina of Time (Nintendo Switch 2 Remake) - In-Game Pause Menu Interactive UI
Follows the authentic Switch 2 in-game pause menu structure (+ Menu: Collection, Equipment, Items, System).
Driven by pause_menu_layout.json, scaled uniformly to the canvas (aspect-preserved, letterboxed).
Supports imported game icons via oot_game_assets when available and generated Switch 2 icons otherwise.
Keeps existing Song Book / Key Items / Important Items code reachable for parallel tasks.
"""

import os
import sys
import math
import json
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

try:
    from PIL import Image, ImageTk, ImageEnhance, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import oot_game_assets
except ImportError:
    oot_game_assets = None

import oot_scarecrow

RESOURCE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
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
            "tabs": ["Collection", "Equipment", "Items", "System"],
            "top_bar": {
                "height": 95,
                "hearts": [40, 25],
                "magic_bar": [40, 82, 195, 90],
                "tabs_y": 42,
                "tab_x": {"L": 465, "Collection": 615, "Equipment": 845, "Items": 1075, "System": 1305, "R": 1455},
                "rupees": [1880, 50],
            },
            "button_hints_y": 1050,
            "pages": {},
        },
    }

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


def compute_staff_note_y(pitch_val, staff_top_y, staff_bot_y):
    """Compute canvas y coordinate for a pitch value on the musical staff."""
    staff_height = staff_bot_y - staff_top_y
    return staff_bot_y - ((pitch_val - 4.0) / 12.0) * staff_height


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


# Actor names to generated PNG assets in assets/switch2_ui
ACTOR_TO_GENERATED_FILE = {
    # Items
    "Item_DekuStick": "item_deku_stick.png",
    "Weapon_Range_SlingShot": "item_slingshot.png",
    "Item_MagicBean": "item_magic_beans.png",
    "Item_Boomerang": "item_boomerang.png",
    "Weapon_Range_Bow": "item_bow.png",
    "Item_Arrow_Normal": "item_bow.png",
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
    "Item_ScrubBusinessSeed": "item_magic_beans.png",
    "Item_DinFire": "spell_dins_fire.png",
    "Item_FaroreWind": "spell_farores_wind.png",
    "Item_NayruLove": "spell_nayrus_love.png",
    "Item_ClaimCheck": "item_small_key.png",
    "Item_EyeDrop": "bottle_empty.png",
    "Item_EyeballFrog": "bottle_empty.png",
    "Item_Prescription": "item_small_key.png",
    "Item_BrokenSword": "sword_kokiri.png",
    "Item_PoacherSaw": "item_hammer.png",
    "Item_OddPowder": "spell_dins_fire.png",
    "Item_OddMushroom": "item_magic_beans.png",
    "Item_CojiroCucco": "item_cucco.png",
    "Item_PocketCucco": "item_cucco.png",
    "Item_PocketEgg": "item_pocket_egg.png",
    "Item_ZeldaLetter": "bottle_rutos_letter.png",
    "Item_AlarmCucco": "item_cucco.png",
    "Item_WeirdEgg": "item_weird_egg.png",
    "Pouch_Amiibo": "item_small_key.png",
    # Bottles
    "Item_Bottle": "bottle_empty.png",
    "Item_Bottle_RedPotion": "bottle_red_potion.png",
    "Item_Bottle_GreenPotion": "bottle_green_potion.png",
    "Item_Bottle_BluePotion": "bottle_blue_potion.png",
    "Item_Bottle_BlueFire": "bottle_blue_fire.png",
    "Item_Bottle_Fish": "bottle_empty.png",
    "Item_Bottle_Letter": "bottle_rutos_letter.png",
    "Item_Bottle_BigPoe": "bottle_poe.png",
    "Item_Bottle_Poe": "bottle_poe.png",
    "Item_Bottle_Bug": "bottle_empty.png",
    "Item_Bottle_Fairy": "bottle_fairy.png",
    "Item_Bottle_Milk": "bottle_milk.png",
    "Item_Bottle_HalfMilk": "bottle_milk.png",
    # Equipment
    "Weapon_Sword_Kokiri": "sword_kokiri.png",
    "Weapon_Sword_Master": "sword_master.png",
    "Weapon_Sword_Biggoron": "sword_biggoron.png",
    "Weapon_Sword_Giant": "sword_biggoron.png",
    "Weapon_Sword_BrokenGiant": "sword_biggoron.png",
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
    "Armor_Adult_HeavyBoot": "boots_iron.png",
    "Armor_Adult_HoverBoot": "boots_hover.png",
    "Item_AgonyStone": "stone_kokiri_emerald.png",
    # Collection
    "Item_Token_Gold": "token_skulltula.png",
    "Obj_Heart_Piece": "heart_full.png",
    "Item_Ocarina_Fairy": "item_ocarina_fairy.png",
    "Item_Ocarina_Time": "item_ocarina_of_time.png",
    "Item_FairyBless_MP": "spell_farores_wind.png",
    "Item_FairyBless_MPDouble": "spell_dins_fire.png",
    "Item_FairyBless_DefenseDouble": "heart_full_dd.png",
    "Armor_Child_Gauntlet_Goron": "gear_goron_bracelet.png",
    "Item_Scale_Silver": "scale_silver.png",
    "Item_Scale_Gold": "scale_golden.png",
    "Armor_Adult_Gauntlet_Silver": "gear_silver_gauntlets.png",
    "Armor_Adult_Gauntlet_Gold": "gear_golden_gauntlets.png",
    "Item_Token_Gerudo": "item_gerudo_card.png",
    "Item_Wallet_Small": "wallet_adults.png",
    "Item_Wallet_Medium": "wallet_adults.png",
    "Item_Wallet_Large": "wallet_giants.png",
    "Item_StickBag_Small": "item_deku_stick.png",
    "Item_StickBag_Medium": "item_deku_stick.png",
    "Item_StickBag_Large": "item_deku_stick.png",
    "Item_NutBag_Small": "item_deku_nut.png",
    "Item_NutBag_Medium": "item_deku_nut.png",
    "Item_NutBag_Large": "item_deku_nut.png",
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

# English item name fallback dictionary (names only; captions come strictly from user-imported assets)
ACTOR_TEXT_FALLBACK = {
    # Items
    "Item_DekuStick": "Deku Stick",
    "Weapon_Range_SlingShot": "Fairy Slingshot",
    "Item_MagicBean": "Magic Beans",
    "Item_Boomerang": "Boomerang",
    "Weapon_Range_Bow": "Fairy Bow",
    "Item_Arrow_Normal": "Arrows",
    "Item_Hookshot": "Hookshot",
    "Item_Longshot": "Longshot",
    "Item_Arrow_Fire": "Fire Arrow",
    "Pouch_Range_BowAndArrow_Fire": "Fire Arrow",
    "Item_Arrow_Ice": "Ice Arrow",
    "Pouch_Range_BowAndArrow_Ice": "Ice Arrow",
    "Item_Arrow_Light": "Light Arrow",
    "Pouch_Range_BowAndArrow_Light": "Light Arrow",
    "Item_Hammer": "Megaton Hammer",
    "Item_Bomb": "Bomb",
    "Item_Bombchu": "Bombchu",
    "Item_DekuNut": "Deku Nut",
    "Item_ScrubBusinessSeed": "Scrub Seed",
    "Item_DinFire": "Din's Fire",
    "Item_FaroreWind": "Farore's Wind",
    "Item_NayruLove": "Nayru's Love",
    "Item_ClaimCheck": "Claim Check",
    "Item_EyeDrop": "World's Finest Eye Drops",
    "Item_EyeballFrog": "Eyeball Frog",
    "Item_Prescription": "Prescription",
    "Item_BrokenSword": "Broken Giant's Knife",
    "Item_PoacherSaw": "Poacher's Saw",
    "Item_OddPowder": "Odd Powder",
    "Item_OddMushroom": "Odd Mushroom",
    "Item_CojiroCucco": "Cojiro",
    "Item_PocketCucco": "Pocket Cucco",
    "Item_PocketEgg": "Pocket Egg",
    "Item_ZeldaLetter": "Zelda's Letter",
    "Item_AlarmCucco": "Alarm Cucco",
    "Item_WeirdEgg": "Weird Egg",
    "Pouch_Amiibo": "amiibo",
    # Bottles
    "Item_Bottle": "Empty Bottle",
    "Item_Bottle_RedPotion": "Red Potion",
    "Item_Bottle_GreenPotion": "Green Potion",
    "Item_Bottle_BluePotion": "Blue Potion",
    "Item_Bottle_BlueFire": "Blue Fire",
    "Item_Bottle_Fish": "Fish",
    "Item_Bottle_Letter": "Ruto's Letter",
    "Item_Bottle_BigPoe": "Big Poe",
    "Item_Bottle_Poe": "Poe",
    "Item_Bottle_Bug": "Bugs",
    "Item_Bottle_Fairy": "Fairy",
    "Item_Bottle_Milk": "Lon Lon Milk",
    "Item_Bottle_HalfMilk": "Lon Lon Milk (Half)",
    # Equipment
    "Weapon_Sword_Kokiri": "Kokiri Sword",
    "Weapon_Sword_Master": "Master Sword",
    "Weapon_Sword_Biggoron": "Biggoron's Sword",
    "Weapon_Sword_Giant": "Giant's Knife",
    "Weapon_Sword_BrokenGiant": "Broken Giant's Knife",
    "Weapon_Shield_Deku": "Deku Shield",
    "Weapon_Shield_Hylian": "Hylian Shield",
    "Weapon_Shield_Mirror": "Mirror Shield",
    "Obj_Armor_Child_Normal": "Kokiri Tunic",
    "Armor_Adult_Normal": "Hero's Clothes",
    "Armor_Adult_Goron": "Goron Tunic",
    "Armor_Adult_Zora": "Zora Tunic",
    "Armor_Child_Mask_Truth": "Mask of Truth",
    "Armor_Child_Mask_Goron": "Goron Mask",
    "Armor_Child_Mask_Zora": "Zora Mask",
    "Armor_Child_Mask_Gerudo": "Gerudo Mask",
    "Armor_Child_Mask_Bunny": "Bunny Hood",
    "Armor_Child_Mask_Spooky": "Spooky Mask",
    "Armor_Child_Mask_Skull": "Skull Mask",
    "Armor_Child_Mask_Keaton": "Keaton Mask",
    "Armor_GlassTruth": "Lens of Truth",
    "Armor_Adult_HeavyBoot": "Iron Boots",
    "Armor_Adult_HoverBoot": "Hover Boots",
    "Item_AgonyStone": "Stone of Agony",
    # Collection
    "Item_Token_Gold": "Gold Skulltula Token",
    "Obj_Heart_Piece": "Piece of Heart",
    "Item_Ocarina_Fairy": "Fairy Ocarina",
    "Item_Ocarina_Time": "Ocarina of Time",
    "Item_FairyBless_MP": "Magic Meter",
    "Item_FairyBless_MPDouble": "Double Magic",
    "Item_FairyBless_DefenseDouble": "Double Defense",
    "Armor_Child_Gauntlet_Goron": "Goron's Bracelet",
    "Item_Scale_Silver": "Silver Scale",
    "Item_Scale_Gold": "Golden Scale",
    "Armor_Adult_Gauntlet_Silver": "Silver Gauntlets",
    "Armor_Adult_Gauntlet_Gold": "Golden Gauntlets",
    "Item_Token_Gerudo": "Gerudo Membership Card",
    "Item_Wallet_Small": "Child's Wallet",
    "Item_Wallet_Medium": "Adult's Wallet",
    "Item_Wallet_Large": "Giant's Wallet",
    "Item_StickBag_Small": "Deku Stick Bag",
    "Item_StickBag_Medium": "Deku Stick Bag (20)",
    "Item_StickBag_Large": "Deku Stick Bag (30)",
    "Item_NutBag_Small": "Deku Nut Bag",
    "Item_NutBag_Medium": "Deku Nut Bag (30)",
    "Item_NutBag_Large": "Deku Nut Bag (40)",
    "Item_BulletBag_Small": "Bullet Bag (30)",
    "Item_BulletBag_Medium": "Bullet Bag (40)",
    "Item_BulletBag_Large": "Bullet Bag (50)",
    "Item_BombBag_Small": "Bomb Bag (20)",
    "Item_BombBag_Medium": "Bomb Bag (30)",
    "Item_BombBag_Large": "Bomb Bag (40)",
    "Item_Quiver_Small": "Quiver (30)",
    "Item_Quiver_Medium": "Quiver (40)",
    "Item_Quiver_Large": "Quiver (50)",
}

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
    """Loads and caches Ultra HD Switch 2 Remake textures and imported game icons."""
    def __init__(self, base_dir=SWITCH2_ASSETS_DIR):
        self.base_dir = base_dir
        self.cache = {}

    def get_actor_icon(self, actor, size=(64, 64), dimmed=False):
        """Load icon for an actor: checks oot_game_assets first, then generated switch2_ui assets."""
        if not PIL_AVAILABLE:
            return None

        size_key = (int(size[0]), int(size[1]))
        cache_key = (actor, size_key, dimmed)
        if cache_key in self.cache:
            return self.cache[cache_key]

        img = None
        # 1. Try importing from user's extracted game assets
        if oot_game_assets is not None and hasattr(oot_game_assets, "icon_path"):
            try:
                g_path = oot_game_assets.icon_path(actor)
                if g_path and os.path.exists(g_path):
                    img = Image.open(g_path).convert("RGBA")
            except Exception:
                img = None

        # 2. Fall back to generated switch2_ui textures
        if img is None:
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

        self.pages = ["Collection", "Equipment", "Items"]
        self.active_subscreen = 0  # 0: Collection, 1: Equipment, 2: Items
        self.selected_slot_id = None
        self._rendered_slots = {}  # slot_id -> dict of canvas item tags / bounds
        self.song_hit_boxes = []   # Backwards compatibility for Song Book tests
        self.selected_song_id = "Zelda's Lullaby"
        self._canvas_size = (1920, 1080)

        # Main full-window scaling canvas
        self.canvas = tk.Canvas(self, bg=COLOR_BG, highlightthickness=0, bd=0, width=1920, height=1080)
        self.canvas.pack(fill="both", expand=True)

        # Bind events
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<Button-3>", self._on_canvas_right_click)
        self.canvas.bind("<MouseWheel>", self._on_canvas_wheel)
        self.canvas.bind("<Button-4>", self._on_canvas_wheel)
        self.canvas.bind("<Button-5>", self._on_canvas_wheel)

        # Keyboard shortcuts
        self.bind_all("<Key-Left>", self._on_key_arrow)
        self.bind_all("<Key-Right>", self._on_key_arrow)
        self.bind_all("<Key-Up>", self._on_key_arrow)
        self.bind_all("<Key-Down>", self._on_key_arrow)
        self.bind_all("<Return>", self._on_key_activate)
        self.bind_all("<space>", self._on_key_activate)
        self.bind_all("<a>", self._on_key_activate)
        self.bind_all("<A>", self._on_key_activate)
        self.bind_all("<q>", lambda e: self.cycle_subscreen(-1))
        self.bind_all("<Q>", lambda e: self.cycle_subscreen(-1))
        self.bind_all("<e>", lambda e: self.cycle_subscreen(1))
        self.bind_all("<E>", lambda e: self.cycle_subscreen(1))
        self.bind_all("<Escape>", lambda e: self._on_back_pressed())
        self.bind_all("<b>", lambda e: self._on_back_pressed())
        self.bind_all("<B>", lambda e: self._on_back_pressed())

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
            if page in self.pages:
                self.active_subscreen = self.pages.index(page)
            elif page.lower() == "collection":
                self.active_subscreen = 0
            elif page.lower() == "equipment":
                self.active_subscreen = 1
            elif page.lower() == "items":
                self.active_subscreen = 2
        else:
            self.active_subscreen = page % len(self.pages)

        # Select first slot on this page by default
        page_name = self.current_page_name()
        page_def = PAUSE_MENU_LAYOUT.get("plus_menu", {}).get("pages", {}).get(page_name, {})
        slots = page_def.get("slots", [])
        valid_slots = [s for s in slots if s.get("pos") is not None and not s.get("display_only")]
        if valid_slots:
            self.selected_slot_id = valid_slots[0]["id"]
        else:
            self.selected_slot_id = None

        self.refresh_visuals()

    def set_info(self, text):
        """Legacy helper for status info."""
        pass

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

        scale, ox, oy = self.get_transform()
        ref_w, ref_h = 1920.0, 1080.0

        # 1. Main Background
        canv.create_rectangle(0, 0, canv.winfo_width(), canv.winfo_height(), fill=COLOR_BG, outline="")
        # Letterboxed inner frame
        ix1, iy1 = self.to_canvas(0, 0)
        ix2, iy2 = self.to_canvas(ref_w, ref_h)
        canv.create_rectangle(ix1, iy1, ix2, iy2, fill=COLOR_INNER_PANEL, outline="#2b1c11", width=max(1, int(2 * scale)))

        # 2. Shared Top Bar
        self._draw_top_bar(scale, ox, oy)

        # 3. Subscreen Slots & Content
        page_name = self.current_page_name()
        page_def = PAUSE_MENU_LAYOUT.get("plus_menu", {}).get("pages", {}).get(page_name, {})

        # Draw lighter carved-wood brown panels before slots
        top_h = PAUSE_MENU_LAYOUT.get("plus_menu", {}).get("top_bar", {}).get("height", 95)
        if page_name == "Items":
            # Items: lighter panel over x 0..1085, full height under top bar; preview x 1085..1920 near-black
            px1, py1 = self.to_canvas(0, top_h)
            px2, py2 = self.to_canvas(1085, 1080)
            canv.create_rectangle(px1, py1, px2, py2, fill="#3b2a1b", outline="#24180e", width=max(1, int(1 * scale)))
        elif page_name == "Collection":
            # Collection: lighter panel over x 830..1920; preview x 0..830 near-black
            px1, py1 = self.to_canvas(830, top_h)
            px2, py2 = self.to_canvas(1920, 1080)
            canv.create_rectangle(px1, py1, px2, py2, fill="#3b2a1b", outline="#24180e", width=max(1, int(1 * scale)))
        elif page_name == "Equipment":
            # Equipment: lighter panel over the whole page; central oval stays dark in preview
            px1, py1 = self.to_canvas(0, top_h)
            px2, py2 = self.to_canvas(1920, 1080)
            canv.create_rectangle(px1, py1, px2, py2, fill="#3b2a1b", outline="#24180e", width=max(1, int(1 * scale)))

        # Preview Panel / Oval
        self._draw_preview_panel(page_name, page_def, scale)

        # Draw Slots
        slots = page_def.get("slots", [])
        for slot in slots:
            self._draw_slot(slot, scale)

        # 4. Page edge navigation arrows (< and >)
        self._draw_edge_arrows(scale)

        # 5. Bottom button hints
        self._draw_button_hints(page_name, scale)

    def _draw_top_bar(self, scale, ox, oy):
        """Draw the authentic carved wood header band with Hearts, Magic meter, Tab bar, and Rupees."""
        canv = self.canvas
        top_def = PAUSE_MENU_LAYOUT.get("plus_menu", {}).get("top_bar", {})
        top_h = top_def.get("height", 95)

        x1, y1 = self.to_canvas(0, 0)
        x2, y2 = self.to_canvas(1920, top_h)

        # Carved wood beam
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

        # A. Hearts (Left)
        # each heart ~30px wide, two rows of up to 10, red #e8452c with a darker outline #7a1a10, empty hearts dark
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
            h_ref_x = hx_ref + col * 32
            h_ref_y = hy_ref + row * 28 - 7
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
        for s in range(10):
            sx1 = mb_x1 + s * (seg_w + seg_gap)
            sy1 = mb_y1
            sx2 = sx1 + seg_w
            sy2 = sy1 + seg_h
            if s < num_filled:
                canv.create_rectangle(sx1, sy1, sx2, sy2, fill="#3fb24a", outline="#246e2b", width=1)
            else:
                canv.create_rectangle(sx1, sy1, sx2, sy2, fill="#1c130c", outline="#24180e", width=1)

        # C. Centered Subscreen Tabs
        tab_y_ref = top_def.get("tabs_y", 42)
        tab_x_def = top_def.get("tab_x", {})

        # "L" trigger cap
        lx, ly = self.to_canvas(tab_x_def.get("L", 465), tab_y_ref)
        canv.create_rectangle(lx - 16 * scale, ly - 12 * scale, lx + 16 * scale, ly + 12 * scale, fill="#e2e8f0", outline="#64748b", width=1, tags=("tab_l",))
        canv.create_text(lx, ly, text="L", fill="#0f172a", font=("Segoe UI", max(8, int(11 * scale)), "bold"), tags=("tab_l",))

        # "R" trigger cap
        rx, ry = self.to_canvas(tab_x_def.get("R", 1455), tab_y_ref)
        canv.create_rectangle(rx - 16 * scale, ry - 12 * scale, rx + 16 * scale, ry + 12 * scale, fill="#e2e8f0", outline="#64748b", width=1, tags=("tab_r",))
        canv.create_text(rx, ry, text="R", fill="#0f172a", font=("Segoe UI", max(8, int(11 * scale)), "bold"), tags=("tab_r",))

        # Tabs: Collection, Equipment, Items, System (34px semibold cream #f3e6c8; System greyed)
        tabs_list = PAUSE_MENU_LAYOUT.get("plus_menu", {}).get("tabs", ["Collection", "Equipment", "Items", "System"])
        current_page = self.current_page_name()

        for tname in tabs_list:
            if tname not in tab_x_def:
                continue
            tx, ty = self.to_canvas(tab_x_def[tname], tab_y_ref)
            is_active = (tname == current_page)
            is_disabled = (tname == "System")

            if is_active:
                bw = 100 * scale
                bh = 24 * scale
                trap_pts = [
                    tx - bw, ty - bh,
                    tx + bw, ty - bh,
                    tx + bw * 0.92, ty + bh,
                    tx - bw * 0.92, ty + bh,
                ]
                canv.create_polygon(trap_pts, fill=COLOR_TAB_ACTIVE_BG, outline=COLOR_TOP_BAR_BOTTOM, width=max(1, int(1.5 * scale)))

            txt_color = "#7c6a58" if is_disabled else "#f3e6c8"
            f_tab = ("Segoe UI Semibold", max(10, int(34 * scale)))

            tag_name = f"tab_{tname}"
            canv.create_text(
                tx, ty, text=tname, fill=txt_color,
                font=f_tab, tags=(tag_name, "tab")
            )

        # D. Rupees (Right)
        # "967 / 1,000" with current amount 44px bold (green #5ad04a when full, white otherwise) and "/ 1,000" 28px
        rup_ref = top_def.get("rupees", [1880, 50])
        rx, ry = self.to_canvas(rup_ref[0], rup_ref[1])

        cur_rupees = safe_int(getattr(self.editor, "v_rupees", 0), default=0)
        max_rupees = self._get_max_rupees()

        val_color = "#5ad04a" if cur_rupees >= max_rupees else "#ffffff"
        amt_str = f"{cur_rupees:,}"
        slash_str = f" / {max_rupees:,}"

        f_amt = ("Segoe UI", max(11, int(44 * scale)), "bold")
        f_slash = ("Segoe UI", max(10, int(28 * scale)))

        try:
            import tkinter.font as tkfont
            font_slash = tkfont.Font(family="Segoe UI", size=max(10, int(28 * scale)))
            font_amt = tkfont.Font(family="Segoe UI", size=max(11, int(44 * scale)), weight="bold")
            w_slash = font_slash.measure(slash_str)
            w_amt = font_amt.measure(amt_str)
        except Exception:
            w_slash = int(len(slash_str) * 16 * scale)
            w_amt = int(len(amt_str) * 26 * scale)

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

    def _draw_button_hints(self, page_name, scale):
        """Draw bottom-right button legend hints on darker rounded band."""
        canv = self.canvas
        hints_y_ref = PAUSE_MENU_LAYOUT.get("plus_menu", {}).get("button_hints_y", 1050)
        rx, hy = self.to_canvas(1880, hints_y_ref)

        if page_name == "Equipment":
            hints = [("Rotate", "R"), ("Equip", "A"), ("Back", "B")]
        else:
            hints = [("Rotate", "R"), ("Select", "A"), ("Back", "B")]

        f_lbl = ("Segoe UI", max(10, int(30 * scale)))
        f_key = ("Segoe UI", max(9, int(20 * scale)), "bold")
        cap_rad = 17.0 * scale
        sp_lbl_key = 8.0 * scale
        item_gap = 24.0 * scale

        try:
            import tkinter.font as tkfont
            font_lbl = tkfont.Font(family="Segoe UI", size=max(10, int(30 * scale)))
        except Exception:
            font_lbl = None

        measured = []
        total_w = 0.0
        for i, (label, key) in enumerate(hints):
            if font_lbl:
                w_lbl = font_lbl.measure(label)
            else:
                w_lbl = len(label) * 16 * scale
            w_total_item = w_lbl + sp_lbl_key + (cap_rad * 2.0)
            measured.append((label, key, w_lbl))
            total_w += w_total_item
            if i < len(hints) - 1:
                total_w += item_gap

        # Rounded band background (#0d0906 with darker border)
        pad_x = 20.0 * scale
        pad_y = 12.0 * scale
        bx2 = rx
        bx1 = bx2 - total_w - (pad_x * 2.0)
        by1 = hy - cap_rad - pad_y
        by2 = hy + cap_rad + pad_y

        band_pts = get_rounded_rect_points(bx1, by1, bx2, by2, radius=14.0 * scale)
        canv.create_polygon(band_pts, fill="#0d0906", outline="#24180e", width=max(1, int(1 * scale)))

        # Draw each hint: label text 30px then white circle ~34px with dark letter
        cur_x = bx1 + pad_x
        for i, (label, key, w_lbl) in enumerate(measured):
            canv.create_text(cur_x, hy, text=label, fill="#f3e6c8", font=f_lbl, anchor="w")
            cur_x += w_lbl + sp_lbl_key + cap_rad
            canv.create_oval(
                cur_x - cap_rad, hy - cap_rad,
                cur_x + cap_rad, hy + cap_rad,
                fill="#ffffff", outline="#cbd5e1", width=1
            )
            canv.create_text(cur_x, hy, text=key, fill="#0d0906", font=f_key, anchor="center")
            cur_x += cap_rad + item_gap

    # =========================================================================
    # PREVIEW PANEL RENDERING
    # =========================================================================
    def _draw_preview_name_and_caption(self, nx, ny, div_y, div_w, cx, cy, wrap_w, item_name, count, max_count, item_caption, scale):
        """Draw item name 56px bold white, N 52px bold (green when full), / Max 30px, and 30px regular caption."""
        canv = self.canvas
        if not item_name:
            return

        f_name = ("Segoe UI", max(12, int(56 * scale)), "bold")
        f_n = ("Segoe UI", max(11, int(52 * scale)), "bold")
        f_max = ("Segoe UI", max(10, int(30 * scale)))

        has_count = (count is not None and max_count is not None and max_count > 0)
        if has_count:
            is_full = (count >= max_count)
            n_str = str(count)
            max_str = f" / {max_count}"
            n_color = "#5ad04a" if is_full else "#ffffff"

            try:
                import tkinter.font as tkfont
                font_name = tkfont.Font(family="Segoe UI", size=max(12, int(56 * scale)), weight="bold")
                font_n = tkfont.Font(family="Segoe UI", size=max(11, int(52 * scale)), weight="bold")
                font_max = tkfont.Font(family="Segoe UI", size=max(10, int(30 * scale)))
                w_name = font_name.measure(item_name)
                w_sp = font_name.measure(" ")
                w_n = font_n.measure(n_str)
                w_max = font_max.measure(max_str)
            except Exception:
                w_name = int(len(item_name) * 32 * scale)
                w_sp = int(14 * scale)
                w_n = int(len(n_str) * 30 * scale)
                w_max = int(len(max_str) * 16 * scale)

            total_w = w_name + w_sp + w_n + w_max
            start_x = nx - (total_w / 2.0)

            canv.create_text(start_x, ny, text=item_name, fill="#ffffff", font=f_name, anchor="w")
            canv.create_text(start_x + w_name + w_sp, ny, text=n_str, fill=n_color, font=f_n, anchor="w")
            canv.create_text(start_x + w_name + w_sp + w_n, ny, text=max_str, fill="#ffffff", font=f_max, anchor="w")
        else:
            canv.create_text(nx, ny, text=item_name, fill="#ffffff", font=f_name, anchor="center")

        # Caption (only if user imported game assets and caption exists)
        if item_caption and item_caption.strip():
            self._draw_ornamental_divider(nx, div_y, div_w)
            canv.create_text(
                cx, cy, text=item_caption, fill="#f3e6c8",
                font=("Segoe UI", max(10, int(30 * scale))), width=wrap_w,
                justify="center", anchor="center", tags=("preview_caption",)
            )

    def _draw_preview_panel(self, page_name, page_def, scale):
        """Draw the large item preview panel (or Equipment center oval) with name, divider, and caption."""
        canv = self.canvas
        preview_def = page_def.get("preview", {})
        if not preview_def:
            return

        selected_slot = self._get_selected_slot(page_def)
        actor, owned, equipped, dimmed, count, max_count = self.get_slot_state(selected_slot) if selected_slot else (None, False, False, False, None, None)

        item_name, item_caption = self.get_actor_text(actor) if actor else ("", "")

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
            div_y_ref = preview_def.get("divider_y", 852)
            cap_ref = preview_def.get("caption", [910, 930, 600])

            nx, ny = self.to_canvas(nx_ref, ny_ref)
            _, div_y = self.to_canvas(nx_ref, div_y_ref)
            cx, cy = self.to_canvas(cap_ref[0], cap_ref[1])
            wrap_w = int(cap_ref[2] * scale)

            self._draw_preview_name_and_caption(
                nx, ny, div_y, int(340 * scale), cx, cy, wrap_w,
                item_name, count, max_count, item_caption, scale
            )

        else:
            # Items / Collection Side Preview Panels
            icon_def = preview_def.get("icon", [1500, 470, 520])
            nx_ref, ny_ref = preview_def.get("name", [1500, 735])
            div_y_ref = preview_def.get("divider_y", 782)
            cap_ref = preview_def.get("caption", [1500, 840, 620])

            icx, icy = self.to_canvas(icon_def[0], icon_def[1])
            isize = int(icon_def[2] * scale)

            nx, ny = self.to_canvas(nx_ref, ny_ref)
            _, div_y = self.to_canvas(nx_ref, div_y_ref)
            cx, cy = self.to_canvas(cap_ref[0], cap_ref[1])
            wrap_w = int(cap_ref[2] * scale)

            # Draw Big Icon
            if actor:
                big_img = self.textures.get_actor_icon(actor, size=(isize, isize))
                if big_img:
                    canv.create_image(icx, icy, image=big_img, anchor="center")

            self._draw_preview_name_and_caption(
                nx, ny, div_y, int(420 * scale), cx, cy, wrap_w,
                item_name, count, max_count, item_caption, scale
            )

    def _draw_ornamental_divider(self, cx, cy, width):
        """Draw thin ornamental line with centered flourish loop/diamond."""
        canv = self.canvas
        hw = width / 2.0
        canv.create_line(cx - hw, cy, cx - 12, cy, fill="#8a6238", width=1)
        canv.create_line(cx + 12, cy, cx + hw, cy, fill="#8a6238", width=1)
        # Small diamond flourish
        canv.create_polygon(
            cx, cy - 4,
            cx + 6, cy,
            cx, cy + 4,
            cx - 6, cy,
            fill="#a17a4b", outline="#8a6238", width=1
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
            fill_col = COLOR_SLOT_EQUIPPED if equipped else COLOR_SLOT_BG
            border_col = COLOR_SLOT_EQUIPPED_BORDER if equipped else COLOR_SLOT_BORDER

            outer_pts = get_shape_polygon(shape, cx, cy, sw, sh)
            slot_item = canv.create_polygon(
                outer_pts, fill=fill_col, outline=border_col,
                width=max(1, int(1.8 * scale)),
                tags=(slot_id, f"slot_{slot_id}", "slot")
            )
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
                f_cnt = ("Segoe UI", max(10, int(34 * scale)), "bold")
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

        # Child Trade Quest Item / Mask
        elif slot_id == "Pa_ItemIcon_23":
            cq = self.editor.child_quest_var.get() if hasattr(self.editor, "child_quest_var") else "None"
            am = self.editor.active_mask_var.get() if hasattr(self.editor, "active_mask_var") else "None"
            trade_map = {
                "Weird Egg": "Item_WeirdEgg",
                "Zelda's Letter": "Item_ZeldaLetter",
                "Pocket Egg": "Item_PocketEgg",
                "Pocket Cucco": "Item_PocketCucco",
                "Cojiro": "Item_CojiroCucco",
                "Odd Mushroom": "Item_OddMushroom",
                "Odd Powder": "Item_OddPowder",
                "Poacher's Saw": "Item_PoacherSaw",
                "Broken Sword": "Item_BrokenSword",
                "Prescription": "Item_Prescription",
                "Eyeball Frog": "Item_EyeballFrog",
                "Eye Drops": "Item_EyeDrop",
                "Claim Check": "Item_ClaimCheck",
            }
            if cq in trade_map:
                actor = trade_map[cq]
                owned = True
            elif am in MASK_NAME_TO_ACTOR:
                actor = MASK_NAME_TO_ACTOR[am]
                owned = True
            else:
                actor = "Item_PocketCucco"
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
            actor = "Weapon_Sword_Biggoron"
            owned = self.editor.owned_swords.get("Biggoron's Sword", tk.BooleanVar(value=False)).get() if hasattr(self.editor, "owned_swords") else False
            equipped = (self.editor.equip_vars.get("sword", tk.StringVar()).get() in ("Biggoron's Sword", "Giant's Knife")) if hasattr(self.editor, "equip_vars") else False
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
                m_str = getattr(self.editor, "v_magic", tk.StringVar()).get() if hasattr(self.editor, "v_magic") else ""
                owned = ("Standard" in m_str or "Double" in m_str)
            elif slot_id == "Pa_Fairy_01":  # MP Double
                m_str = getattr(self.editor, "v_magic", tk.StringVar()).get() if hasattr(self.editor, "v_magic") else ""
                owned = ("Double" in m_str)
            elif slot_id == "Pa_Fairy_02":  # Double Defense
                owned = bool(self.editor.v_double_defense.get()) if hasattr(self.editor, "v_double_defense") else False

        if actor is None and items_list:
            actor = items_list[0]

        return actor, owned, equipped, dimmed, count, max_count

    def get_actor_text(self, actor):
        """Retrieve (name, caption) for an actor, consulting oot_game_assets first."""
        if not actor:
            return "", ""
        if oot_game_assets is not None and hasattr(oot_game_assets, "item_text"):
            try:
                txt = oot_game_assets.item_text(actor)
                if isinstance(txt, tuple) and len(txt) == 2:
                    return txt[0], txt[1]
                elif isinstance(txt, dict):
                    return txt.get("name", ""), txt.get("caption", "")
                elif isinstance(txt, str):
                    return txt, ""
            except Exception:
                pass
        fallback_name = ACTOR_TEXT_FALLBACK.get(actor, actor.replace("_", " "))
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
        elif sword in ("Biggoron's Sword", "Giant's Knife"): return "Weapon_Sword_Biggoron"
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

    def _on_canvas_click(self, event):
        """Handle Left-Click: tab switching, edge arrows, or select/activate slots."""
        scale, ox, oy = self.get_transform()
        top_def = PAUSE_MENU_LAYOUT.get("plus_menu", {}).get("top_bar", {})
        tab_y_ref = top_def.get("tabs_y", 42)
        tab_x_def = top_def.get("tab_x", {})

        # Check tab clicks
        for tname in ("Collection", "Equipment", "Items"):
            if tname in tab_x_def:
                tx, ty = self.to_canvas(tab_x_def[tname], tab_y_ref)
                if abs(event.x - tx) < 80 * scale and abs(event.y - ty) < 24 * scale:
                    self.show_subscreen(tname)
                    return

        # Check L / R clicks
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

        # Check Slot Click
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

    def _on_canvas_wheel(self, event):
        """Handle mouse wheel adjustments over ammo or countable slots."""
        slot = self._find_slot_at(event.x, event.y)
        if not slot:
            return
        count_key = slot.get("count")
        if count_key:
            self._handle_wheel(event, count_key)

    def _on_key_arrow(self, event):
        """Keyboard navigation: move cursor to the nearest slot in the pressed direction."""
        key = event.keysym
        dx, dy = 0, 0
        if key == "Left": dx = -1
        elif key == "Right": dx = 1
        elif key == "Up": dy = -1
        elif key == "Down": dy = 1
        else: return

        page_name = self.current_page_name()
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
        page_name = self.current_page_name()
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
            self._on_gear_click("Biggoron's Sword")
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
            self._on_blessing_click("magic")
        elif slot_id == "Pa_Fairy_01":
            self._on_blessing_click("double_magic")
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
                self.editor.bottle_vars[item_id].set(b_choices[next_idx])
            except ValueError:
                self.editor.bottle_vars[item_id].set("Empty Bottle")
            self.refresh_visuals()

        elif item_id == "child_trade":
            choices = ["None", "Weird Egg", "Zelda's Letter", "Keaton Mask", "Skull Mask", "Spooky Mask", "Bunny Hood", "Goron Mask", "Zora Mask", "Gerudo Mask", "Mask of Truth"]
            cur_cq = self.editor.child_quest_var.get() if hasattr(self.editor, "child_quest_var") else "None"
            cur_m = self.editor.active_mask_var.get() if hasattr(self.editor, "active_mask_var") else "None"
            cur = cur_cq if cur_cq in ("Weird Egg", "Zelda's Letter") else cur_m
            try:
                n_idx = (choices.index(cur) + 1) % len(choices)
            except ValueError:
                n_idx = 1
            nxt = choices[n_idx]
            if nxt in ("Weird Egg", "Zelda's Letter"):
                if hasattr(self.editor, "child_quest_var"): self.editor.child_quest_var.set(nxt)
                if hasattr(self.editor, "active_mask_var"): self.editor.active_mask_var.set("None")
            elif nxt == "None":
                if hasattr(self.editor, "child_quest_var"): self.editor.child_quest_var.set("None")
                if hasattr(self.editor, "active_mask_var"): self.editor.active_mask_var.set("None")
            else:
                if hasattr(self.editor, "child_quest_var"): self.editor.child_quest_var.set("None")
                if hasattr(self.editor, "active_mask_var"): self.editor.active_mask_var.set(nxt)
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
        if bid == "magic":
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
            m.add_command(label=c, command=lambda ch=c: (self.editor.bottle_vars[item_id].set(ch), self.refresh_visuals()))
        m.tk_popup(event.x_root, event.y_root)

    def _on_child_trade_right_click(self, event):
        m = tk.Menu(self, tearoff=0, bg=COLOR_INNER_PANEL, fg=COLOR_TEXT, activebackground=COLOR_GOLD, activeforeground="#000")
        m.add_command(label="None", command=lambda: (self.editor.child_quest_var.set("None"), self.editor.active_mask_var.set("None"), self.refresh_visuals()))
        m.add_separator()
        for t in ["Weird Egg", "Zelda's Letter", "Pocket Egg", "Pocket Cucco", "Cojiro", "Odd Mushroom", "Odd Powder", "Poacher's Saw", "Broken Sword", "Prescription", "Eyeball Frog", "Eye Drops", "Claim Check"]:
            m.add_command(label=t, command=lambda tn=t: (self.editor.child_quest_var.set(tn), self.editor.active_mask_var.set("None"), self.refresh_visuals()))
        m.add_separator()
        for mask_name in ["Keaton Mask", "Skull Mask", "Spooky Mask", "Bunny Hood", "Goron Mask", "Zora Mask", "Gerudo Mask", "Mask of Truth"]:
            m.add_command(label=mask_name, command=lambda mn=mask_name: (self.editor.child_quest_var.set("None"), self.editor.active_mask_var.set(mn), self.refresh_visuals()))
        m.tk_popup(event.x_root, event.y_root)

    # =========================================================================
    # BACKWARDS COMPATIBILITY (SONG BOOK & LEGACY TEST METHODS)
    # =========================================================================
    def _get_song_list(self):
        return [
            {"name": "Zelda's Lullaby", "bit_idx": 0, "is_scarecrow": False},
            {"name": "Epona's Song", "bit_idx": 1, "is_scarecrow": False},
            {"name": "Saria's Song", "bit_idx": 2, "is_scarecrow": False},
            {"name": "Sun's Song", "bit_idx": 3, "is_scarecrow": False},
            {"name": "Song of Time", "bit_idx": 4, "is_scarecrow": False},
            {"name": "Song of Storms", "bit_idx": 5, "is_scarecrow": False},
            {"name": "Minuet of Forest", "bit_idx": 6, "is_scarecrow": False},
            {"name": "Bolero of Fire", "bit_idx": 7, "is_scarecrow": False},
            {"name": "Serenade of Water", "bit_idx": 8, "is_scarecrow": False},
            {"name": "Requiem of Spirit", "bit_idx": 9, "is_scarecrow": False},
            {"name": "Nocturne of Shadow", "bit_idx": 10, "is_scarecrow": False},
            {"name": "Prelude of Light", "bit_idx": 11, "is_scarecrow": False},
            {"name": "Scarecrow's Song", "bit_idx": None, "is_scarecrow": True},
        ]

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
                if s["is_scarecrow"]:
                    if hasattr(self.editor, "switch_to_quest_tab_scarecrow"):
                        self.editor.switch_to_quest_tab_scarecrow()
                elif s["bit_idx"] is not None and hasattr(self.editor, "song_vars"):
                    var = self.editor.song_vars[s["bit_idx"]]
                    var.set(not var.get())
                return
