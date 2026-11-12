import os
import math
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "switch2_ui")
os.makedirs(OUT_DIR, exist_ok=True)

SIZE = 128
SS = 4  # 4x supersampling for ultra-crisp anti-aliasing
CANVAS_SIZE = SIZE * SS

def create_base():
    return Image.new("RGBA", (CANVAS_SIZE, CANVAS_SIZE), (0, 0, 0, 0))

# Every icon is rendered in Blender by tools/render_icons.py; this flat generator is kept only for reference and
# never overwrites a rendered file.
BLENDER_RENDERED = None  # all files


def finalize(img, filename):
    if BLENDER_RENDERED is None or filename in BLENDER_RENDERED:
        return
    out = img.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
    out.save(os.path.join(OUT_DIR, filename), "PNG")

def draw_circle(draw, center, radius, fill, outline=None, width=1):
    x, y = center
    draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=fill, outline=outline, width=width)

# =============================================================================
# 1. SWORDS
# =============================================================================
def gen_kokiri_sword():
    img = create_base()
    d = ImageDraw.Draw(img)
    # Brown hilt
    d.rectangle([236, 360, 276, 440], fill="#8B4513", outline="#5C2E0B", width=6)
    # Wooden crossguard
    d.rounded_rectangle([190, 340, 322, 370], radius=12, fill="#A0522D", outline="#5C2E0B", width=6)
    # Steel blade
    d.polygon([(220, 340), (292, 340), (266, 90), (256, 60), (246, 90)], fill="#E2E8F0", outline="#94A3B8", width=6)
    # Center ridge
    d.line([(256, 340), (256, 75)], fill="#CBD5E1", width=6)
    finalize(img, "sword_kokiri.png")

def gen_master_sword():
    img = create_base()
    d = ImageDraw.Draw(img)
    # Blue grip
    d.rectangle([240, 370, 272, 450], fill="#1E3A8A", outline="#172554", width=6)
    # Golden pommel
    draw_circle(d, (256, 460), 22, fill="#F59E0B", outline="#B45309", width=6)
    # Winged purple/blue guard
    d.polygon([(256, 350), (160, 390), (140, 340), (230, 350), (256, 370), (282, 350), (372, 340), (352, 390)], fill="#3B82F6", outline="#1D4ED8", width=8)
    # Triforce in gold
    d.polygon([(256, 345), (242, 368), (270, 368)], fill="#FCD34D", outline="#D97706", width=4)
    # Gleaming master blade
    d.polygon([(234, 340), (278, 340), (270, 80), (256, 40), (242, 80)], fill="#F8FAFC", outline="#94A3B8", width=8)
    # Fuller
    d.rectangle([252, 120, 260, 330], fill="#93C5FD")
    finalize(img, "sword_master.png")

def gen_biggoron_sword():
    img = create_base()
    d = ImageDraw.Draw(img)
    # Long hilt with red grip
    d.rectangle([238, 360, 274, 460], fill="#DC2626", outline="#991B1B", width=6)
    # Massive gold pommel
    draw_circle(d, (256, 470), 26, fill="#F59E0B", outline="#B45309", width=6)
    # Sturdy steel/gold crossguard
    d.rectangle([160, 340, 352, 370], fill="#475569", outline="#1E293B", width=8)
    # Massive broad blade
    d.polygon([(220, 340), (292, 340), (280, 70), (256, 30), (232, 70)], fill="#E2E8F0", outline="#64748B", width=8)
    # Dual blood grooves
    d.line([(246, 330), (246, 90)], fill="#94A3B8", width=6)
    d.line([(266, 330), (266, 90)], fill="#94A3B8", width=6)
    finalize(img, "sword_biggoron.png")

# =============================================================================
# 2. SHIELDS
# =============================================================================
def gen_deku_shield():
    img = create_base()
    d = ImageDraw.Draw(img)
    # Wood bark texture shield
    d.rounded_rectangle([140, 100, 372, 420], radius=80, fill="#854D0E", outline="#451A03", width=12)
    # Wood grain lines
    d.arc([160, 120, 352, 400], 40, 140, fill="#713F12", width=8)
    d.arc([180, 140, 332, 380], 40, 140, fill="#713F12", width=8)
    # Kokiri red swirl emblem
    d.ellipse([216, 216, 296, 296], fill="#DC2626", outline="#991B1B", width=6)
    draw_circle(d, (256, 256), 24, fill="#854D0E")
    finalize(img, "shield_deku.png")

def gen_hylian_shield():
    img = create_base()
    d = ImageDraw.Draw(img)
    # Shield shape points
    pts = [(140, 100), (372, 100), (372, 280), (256, 440), (140, 280)]
    # Silver rim
    d.polygon(pts, fill="#3B82F6", outline="#E2E8F0", width=16)
    # Gold Triforce
    d.polygon([(256, 130), (210, 200), (302, 200)], fill="#F59E0B", outline="#D97706", width=4)
    d.polygon([(256, 200), (233, 165), (279, 165)], fill="#3B82F6")
    # Red Crimson Loftwing Crest
    d.polygon([(256, 240), (200, 310), (230, 310), (256, 280), (282, 310), (312, 310)], fill="#EF4444")
    d.polygon([(256, 300), (220, 370), (256, 400), (292, 370)], fill="#EF4444")
    finalize(img, "shield_hylian.png")

def gen_mirror_shield():
    img = create_base()
    d = ImageDraw.Draw(img)
    # Polished mirror silver
    draw_circle(d, (256, 256), 160, fill="#F1F5F9", outline="#94A3B8", width=16)
    draw_circle(d, (256, 256), 140, fill="#E2E8F0", outline="#CBD5E1", width=8)
    # Mirror shine glare
    d.polygon([(200, 140), (312, 140), (256, 220)], fill="#FFFFFF")
    # Gerudo Gold/Red Crest
    d.polygon([(256, 220), (210, 290), (302, 290)], fill="#F59E0B", outline="#B45309", width=6)
    draw_circle(d, (256, 256), 18, fill="#DC2626")
    finalize(img, "shield_mirror.png")

# =============================================================================
# 3. TUNICS & BOOTS
# =============================================================================
def gen_tunic(color, border, name):
    img = create_base()
    d = ImageDraw.Draw(img)
    # Collar & Sleeves
    d.polygon([(190, 110), (322, 110), (410, 180), (360, 250), (310, 210), (310, 410), (202, 410), (202, 210), (152, 250), (102, 180)],
              fill=color, outline=border, width=12)
    # V-Neck Collar
    d.polygon([(230, 110), (256, 190), (282, 110)], fill="#1E293B", outline=border, width=6)
    # Belt
    d.rectangle([202, 320, 310, 350], fill="#78350F", outline="#451A03", width=6)
    d.rectangle([242, 316, 270, 354], fill="#F59E0B", outline="#B45309", width=4)
    finalize(img, name)

def gen_boots(color, accent, wing, name):
    img = create_base()
    d = ImageDraw.Draw(img)
    # Boot Left
    d.polygon([(160, 140), (220, 140), (220, 340), (250, 370), (140, 370), (140, 320), (160, 320)], fill=color, outline=accent, width=10)
    # Boot Right
    d.polygon([(280, 140), (340, 140), (340, 320), (360, 320), (360, 370), (250, 370), (280, 340)], fill=color, outline=accent, width=10)
    if wing:
        # Hover boots wings
        d.polygon([(140, 200), (70, 160), (90, 240), (140, 240)], fill="#FDE047", outline="#CA8A04", width=6)
        d.polygon([(360, 200), (430, 160), (410, 240), (360, 240)], fill="#FDE047", outline="#CA8A04", width=6)
    finalize(img, name)

# =============================================================================
# 4. ESSENTIAL ITEMS (Hookshot, Bow, Bombs, Ocarina, etc.)
# =============================================================================
def gen_ocarina_of_time():
    img = create_base()
    d = ImageDraw.Draw(img)
    # Royal blue ocarina body
    d.rounded_rectangle([120, 180, 380, 320], radius=60, fill="#2563EB", outline="#1D4ED8", width=12)
    # Mouthpiece
    d.polygon([(140, 200), (80, 240), (120, 270)], fill="#CBD5E1", outline="#94A3B8", width=8)
    # Gold band with Triforce
    d.rectangle([140, 190, 180, 310], fill="#F59E0B", outline="#B45309", width=6)
    d.polygon([(160, 230), (150, 260), (170, 260)], fill="#FEF08A")
    # Finger holes
    holes = [(230, 220), (280, 210), (330, 220), (250, 270), (300, 270)]
    for h in holes:
        draw_circle(d, h, 14, fill="#1E293B", outline="#93C5FD", width=4)
    finalize(img, "item_ocarina_of_time.png")

def gen_fairy_bow():
    img = create_base()
    d = ImageDraw.Draw(img)
    # Wooden curved bow
    d.arc([100, 60, 380, 440], 280, 80, fill="#A16207", width=18)
    # String
    d.line([(350, 95), (350, 405)], fill="#E2E8F0", width=6)
    # Arrow notched
    d.line([(220, 250), (360, 250)], fill="#475569", width=8)
    # Arrow head
    d.polygon([(200, 250), (230, 235), (230, 265)], fill="#94A3B8")
    finalize(img, "item_bow.png")

def gen_bomb():
    img = create_base()
    d = ImageDraw.Draw(img)
    # Round dark blue bomb
    draw_circle(d, (256, 290), 130, fill="#1E293B", outline="#0F172A", width=12)
    # Fuse cap
    d.rectangle([236, 130, 276, 160], fill="#94A3B8", outline="#475569", width=6)
    # Burning spark
    d.arc([256, 80, 320, 140], 180, 360, fill="#F59E0B", width=8)
    draw_circle(d, (320, 90), 18, fill="#EF4444")
    draw_circle(d, (320, 90), 10, fill="#FDE047")
    finalize(img, "item_bomb.png")

def gen_bombchu():
    img = create_base()
    d = ImageDraw.Draw(img)
    # Mechanical mouse body
    d.ellipse([140, 200, 360, 330], fill="#3B82F6", outline="#1D4ED8", width=10)
    # Bomb pack on back
    draw_circle(d, (220, 180), 50, fill="#1E293B", outline="#0F172A", width=8)
    # Wheels
    d.ellipse([130, 310, 190, 360], fill="#64748B", outline="#334155", width=6)
    d.ellipse([300, 310, 360, 360], fill="#64748B", outline="#334155", width=6)
    # Tail / Fuse
    d.arc([220, 90, 280, 150], 90, 270, fill="#DC2626", width=8)
    finalize(img, "item_bombchu.png")

def gen_hookshot(longshot=False):
    img = create_base()
    d = ImageDraw.Draw(img)
    # Cylinder shaft
    col = "#DC2626" if longshot else "#2563EB"
    d.rectangle([140, 220, 320, 290], fill=col, outline="#0F172A", width=10)
    # Grip
    d.rectangle([120, 270, 170, 370], fill="#475569", outline="#1E293B", width=8)
    # Spike claw tip
    d.polygon([(320, 255), (380, 210), (430, 255), (380, 300)], fill="#E2E8F0", outline="#64748B", width=8)
    finalize(img, "item_longshot.png" if longshot else "item_hookshot.png")

def gen_boomerang():
    img = create_base()
    d = ImageDraw.Draw(img)
    # Curved boomerang
    d.polygon([(140, 120), (220, 260), (380, 340), (360, 380), (180, 300), (100, 140)], fill="#F59E0B", outline="#B45309", width=10)
    # Red tips
    d.polygon([(140, 120), (160, 160), (115, 170), (100, 140)], fill="#DC2626")
    d.polygon([(380, 340), (340, 325), (330, 365), (360, 380)], fill="#DC2626")
    finalize(img, "item_boomerang.png")

def gen_lens_of_truth():
    img = create_base()
    d = ImageDraw.Draw(img)
    # Golden Sheikah magnifying lens
    draw_circle(d, (256, 210), 120, fill="#FEF08A", outline="#CA8A04", width=16)
    # Sheikah Eye in red
    d.ellipse([190, 175, 322, 245], fill="#DC2626")
    draw_circle(d, (256, 210), 24, fill="#1E293B")
    # Teardrop
    d.polygon([(256, 245), (244, 280), (268, 280)], fill="#DC2626")
    # Handle
    d.rectangle([240, 330, 272, 450], fill="#CA8A04", outline="#854D0E", width=8)
    finalize(img, "item_lens_of_truth.png")

def gen_hammer():
    img = create_base()
    d = ImageDraw.Draw(img)
    # Handle
    d.rectangle([240, 180, 272, 450], fill="#854D0E", outline="#451A03", width=8)
    # Huge steel hammer head
    d.rounded_rectangle([130, 100, 382, 210], radius=24, fill="#475569", outline="#0F172A", width=12)
    # Face plates
    d.rectangle([130, 115, 160, 195], fill="#94A3B8")
    d.rectangle([352, 115, 382, 195], fill="#94A3B8")
    finalize(img, "item_hammer.png")

def gen_slingshot():
    img = create_base()
    d = ImageDraw.Draw(img)
    # Y-fork wood
    d.polygon([(230, 430), (282, 430), (282, 300), (370, 150), (320, 120), (256, 230), (192, 120), (142, 150), (230, 300)],
              fill="#A16207", outline="#713F12", width=10)
    # Elastic band
    d.line([(167, 135), (256, 280), (345, 135)], fill="#DC2626", width=8)
    finalize(img, "item_slingshot.png")

def gen_beans():
    img = create_base()
    d = ImageDraw.Draw(img)
    # Magic beans pouch
    d.ellipse([140, 180, 372, 420], fill="#16A34A", outline="#15803D", width=12)
    # Tie rope
    d.rectangle([210, 160, 302, 190], fill="#F59E0B", outline="#B45309", width=6)
    finalize(img, "item_magic_beans.png")

def gen_sticks():
    img = create_base()
    d = ImageDraw.Draw(img)
    d.line([(140, 372), (372, 140)], fill="#854D0E", width=24)
    finalize(img, "item_deku_stick.png")

def gen_nuts():
    img = create_base()
    d = ImageDraw.Draw(img)
    draw_circle(d, (256, 256), 110, fill="#A16207", outline="#713F12", width=12)
    # Flash sparkles
    d.polygon([(256, 80), (270, 130), (320, 140), (270, 160), (256, 210), (242, 160), (192, 140), (242, 130)], fill="#FEF08A")
    finalize(img, "item_deku_nut.png")

# =============================================================================
# 5. GREAT FAIRY SPELLS (Din, Farore, Nayru) & ELEMENTAL ARROWS
# =============================================================================
def gen_spell(color, glow, name):
    img = create_base()
    d = ImageDraw.Draw(img)
    # Outer mystic crystal
    d.polygon([(256, 60), (390, 256), (256, 452), (122, 256)], fill=color, outline=glow, width=14)
    # Inner energy core
    draw_circle(d, (256, 256), 60, fill="#FFFFFF")
    draw_circle(d, (256, 256), 40, fill=color)
    finalize(img, name)

def gen_arrow(color, tip_glow, name):
    img = create_base()
    d = ImageDraw.Draw(img)
    # Shaft
    d.line([(120, 392), (360, 152)], fill="#A16207", width=10)
    # Fletching
    d.polygon([(110, 402), (80, 432), (130, 412)], fill="#E2E8F0")
    # Glowing magical head
    d.polygon([(360, 152), (350, 200), (390, 210), (430, 120), (340, 160)], fill=color, outline=tip_glow, width=8)
    finalize(img, name)

# =============================================================================
# 6. BOTTLES (5 Modern Bottles + Contents)
# =============================================================================
def gen_bottle(content_color=None, label=None, name="bottle_empty.png"):
    img = create_base()
    d = ImageDraw.Draw(img)
    # Glass flask body
    d.rounded_rectangle([150, 180, 362, 420], radius=70, fill="#F8FAFC", outline="#94A3B8", width=12)
    # Flask neck & lip
    d.rectangle([210, 100, 302, 180], fill="#F8FAFC", outline="#94A3B8", width=12)
    # Cork
    d.rectangle([220, 60, 292, 100], fill="#854D0E", outline="#451A03", width=6)
    # Liquid content if filled
    if content_color:
        d.rounded_rectangle([166, 230, 346, 404], radius=50, fill=content_color)
        # Highlight bubble
        draw_circle(d, (200, 270), 16, fill="#FFFFFF")
    if label == "fairy":
        # Glowing pink fairy inside
        draw_circle(d, (256, 300), 30, fill="#F472B6")
        d.ellipse([210, 280, 256, 305], fill="#FFFFFF")
        d.ellipse([256, 280, 302, 305], fill="#FFFFFF")
    elif label == "poe":
        # Spooky yellow ghost flame
        draw_circle(d, (256, 300), 36, fill="#FDE047")
        draw_circle(d, (244, 290), 8, fill="#1E293B")
        draw_circle(d, (268, 290), 8, fill="#1E293B")
    elif label == "letter":
        # White scroll with red seal
        d.rectangle([200, 270, 312, 350], fill="#FFFFFF", outline="#CBD5E1", width=4)
        draw_circle(d, (256, 310), 14, fill="#DC2626")
    finalize(img, name)

# =============================================================================
# 7. SAGE MEDALLIONS & SPIRITUAL STONES
# =============================================================================
def gen_medallion(color, glow, rune, name):
    img = create_base()
    d = ImageDraw.Draw(img)
    # Gold coin rim
    draw_circle(d, (256, 256), 160, fill="#F59E0B", outline="#D97706", width=14)
    # Glowing elemental face
    draw_circle(d, (256, 256), 130, fill=color, outline=glow, width=10)
    # Core symbol
    draw_circle(d, (256, 256), 50, fill="#FFFFFF")
    draw_circle(d, (256, 256), 36, fill=color)
    finalize(img, name)

def gen_spiritual_stone(color, border, name):
    img = create_base()
    d = ImageDraw.Draw(img)
    # Golden setting mount
    draw_circle(d, (256, 256), 150, fill="#F59E0B", outline="#B45309", width=14)
    # Jewel
    d.polygon([(256, 120), (370, 256), (256, 392), (142, 256)], fill=color, outline=border, width=12)
    # Jewel facets
    d.line([(256, 120), (256, 392)], fill="#FFFFFF", width=6)
    d.line([(142, 256), (370, 256)], fill="#FFFFFF", width=6)
    finalize(img, name)

# =============================================================================
# 8. HUD & UI GLYPHS (Hearts, Skulltula, Keys, Buttons)
# =============================================================================
def gen_heart(double_defense=False, quarter=4, name="heart_full.png"):
    img = create_base()
    d = ImageDraw.Draw(img)
    # Heart path
    # If double defense, thick white outline
    border_col = "#FFFFFF" if double_defense else "#7F1D1D"
    border_w = 20 if double_defense else 10

    # Draw heart using two overlapping circles + bottom triangle
    c1 = (196, 180)
    c2 = (316, 180)
    r = 85
    tri = [(116, 200), (396, 200), (256, 420)]
    
    # Outer border
    draw_circle(d, c1, r + border_w, fill=border_col)
    draw_circle(d, c2, r + border_w, fill=border_col)
    d.polygon([(116 - border_w, 200), (396 + border_w, 200), (256, 420 + border_w*2)], fill=border_col)

    # Inner red heart
    fill_col = "#DC2626"
    draw_circle(d, c1, r, fill=fill_col)
    draw_circle(d, c2, r, fill=fill_col)
    d.polygon(tri, fill=fill_col)

    # Gloss shine
    draw_circle(d, (180, 160), 24, fill="#FCA5A5")
    finalize(img, name)

def gen_skulltula():
    img = create_base()
    d = ImageDraw.Draw(img)
    # Golden skull medallion
    draw_circle(d, (256, 240), 130, fill="#F59E0B", outline="#78350F", width=12)
    # Skull eye sockets
    d.ellipse([180, 200, 230, 260], fill="#1E293B")
    d.ellipse([282, 200, 332, 260], fill="#1E293B")
    # Teeth / mandible
    d.rectangle([210, 300, 302, 340], fill="#1E293B")
    finalize(img, "token_skulltula.png")

print("Generating Switch 2 Remake HD Assets...")
# 1. Swords
gen_kokiri_sword()
gen_master_sword()
gen_biggoron_sword()

# 2. Shields
gen_deku_shield()
gen_hylian_shield()
gen_mirror_shield()

# 3. Tunics & Boots
gen_tunic("#16A34A", "#14532D", "tunic_kokiri.png")
gen_tunic("#DC2626", "#7F1D1D", "tunic_goron.png")
gen_tunic("#2563EB", "#1E3A8A", "tunic_zora.png")
gen_boots("#854D0E", "#451A03", False, "boots_kokiri.png")
gen_boots("#475569", "#1E293B", False, "boots_iron.png")
gen_boots("#F59E0B", "#B45309", True, "boots_hover.png")

# 4. Items
gen_ocarina_of_time()
gen_fairy_bow()
gen_bomb()
gen_bombchu()
gen_hookshot(False)
gen_hookshot(True)
gen_boomerang()
gen_lens_of_truth()
gen_hammer()
gen_slingshot()
gen_beans()
gen_sticks()
gen_nuts()

# 5. Spells & Arrows
gen_spell("#DC2626", "#F87171", "spell_dins_fire.png")
gen_spell("#16A34A", "#4ADE80", "spell_farores_wind.png")
gen_spell("#2563EB", "#60A5FA", "spell_nayrus_love.png")
gen_arrow("#DC2626", "#F87171", "arrow_fire.png")
gen_arrow("#06B6D4", "#67E8F9", "arrow_ice.png")
gen_arrow("#F59E0B", "#FDE047", "arrow_light.png")

# 6. Bottles
gen_bottle(None, None, "bottle_empty.png")
gen_bottle("#DC2626", None, "bottle_red_potion.png")
gen_bottle("#16A34A", None, "bottle_green_potion.png")
gen_bottle("#2563EB", None, "bottle_blue_potion.png")
gen_bottle("#F472B6", "fairy", "bottle_fairy.png")
gen_bottle("#06B6D4", None, "bottle_blue_fire.png")
gen_bottle("#FDE047", "poe", "bottle_poe.png")
gen_bottle("#FFFFFF", "letter", "bottle_rutos_letter.png")
gen_bottle("#F8FAFC", None, "bottle_milk.png")

# 7. Medallions & Stones
gen_medallion("#FEF08A", "#F59E0B", "sun", "medallion_light.png")
gen_medallion("#22C55E", "#15803D", "leaf", "medallion_forest.png")
gen_medallion("#EF4444", "#B91C1C", "flame", "medallion_fire.png")
gen_medallion("#3B82F6", "#1D4ED8", "wave", "medallion_water.png")
gen_medallion("#8B5CF6", "#6D28D9", "eye", "medallion_shadow.png")
gen_medallion("#F97316", "#C2410C", "spirit", "medallion_spirit.png")

gen_spiritual_stone("#22C55E", "#15803D", "stone_kokiri_emerald.png")
gen_spiritual_stone("#EF4444", "#B91C1C", "stone_goron_ruby.png")
gen_spiritual_stone("#3B82F6", "#1D4ED8", "stone_zoras_sapphire.png")

# 8. HUD & UI
gen_heart(False, 4, "heart_full.png")
gen_heart(True, 4, "heart_full_dd.png")
gen_skulltula()

print("All Switch 2 Remake HD Assets generated successfully!")
