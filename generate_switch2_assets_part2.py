import os
import math
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "switch2_ui")
os.makedirs(OUT_DIR, exist_ok=True)

SIZE = 128
SS = 4
CANVAS_SIZE = SIZE * SS

def create_base():
    return Image.new("RGBA", (CANVAS_SIZE, CANVAS_SIZE), (0, 0, 0, 0))

# Rendered in Blender by tools/render_key_items.py; never overwrite them with the flat versions.
BLENDER_RENDERED = {f"medallion_{n}.png" for n in ("light", "forest", "fire", "water", "shadow", "spirit")} | {
    "stone_kokiri_emerald.png", "stone_goron_ruby.png", "stone_zoras_sapphire.png"} | {
    f"note_{c}.png" for c in ("cyan", "gold", "green", "purple", "red")}


def finalize(img, filename):
    if filename in BLENDER_RENDERED:
        return
    out = img.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
    out.save(os.path.join(OUT_DIR, filename), "PNG")

def draw_circle(draw, center, radius, fill, outline=None, width=1):
    x, y = center
    draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=fill, outline=outline, width=width)

# =============================================================================
# 9. GAUNTLETS & SCALES & WALLETS
# =============================================================================
def gen_gauntlets(color, trim, ruby, name):
    img = create_base()
    d = ImageDraw.Draw(img)
    # Heavy armored gauntlet cuff
    d.polygon([(170, 160), (342, 160), (370, 370), (142, 370)], fill=color, outline=trim, width=12)
    # Knuckle guard
    d.rounded_rectangle([150, 340, 362, 420], radius=24, fill=trim, outline="#0F172A", width=8)
    if ruby:
        # Goron Bracelet ruby
        draw_circle(d, (256, 260), 40, fill="#EF4444", outline="#B91C1C", width=8)
    else:
        # Engraved Triforce
        d.polygon([(256, 220), (216, 290), (296, 290)], fill="#FEF08A", outline="#CA8A04", width=6)
    finalize(img, name)

def gen_scale(color, trim, name):
    img = create_base()
    d = ImageDraw.Draw(img)
    # Zora swimming scale
    d.polygon([(256, 100), (370, 256), (256, 412), (142, 256)], fill=color, outline=trim, width=14)
    # Ripple rings
    d.arc([180, 180, 332, 332], 0, 360, fill="#FFFFFF", width=8)
    finalize(img, name)

def gen_wallet(color, trim, name):
    img = create_base()
    d = ImageDraw.Draw(img)
    # Leather rupee purse
    d.rounded_rectangle([140, 180, 372, 420], radius=80, fill=color, outline=trim, width=14)
    # Clasp
    d.rectangle([210, 130, 302, 190], fill="#F59E0B", outline="#B45309", width=8)
    draw_circle(d, (256, 160), 18, fill="#FEF08A")
    finalize(img, name)

def gen_bag(symbol_color, label, name):
    img = create_base()
    d = ImageDraw.Draw(img)
    # Leather satchel
    d.rounded_rectangle([140, 160, 372, 420], radius=60, fill="#92400E", outline="#78350F", width=14)
    # Straps
    d.line([(200, 160), (200, 420)], fill="#451A03", width=10)
    d.line([(312, 160), (312, 420)], fill="#451A03", width=10)
    # Badge
    draw_circle(d, (256, 290), 50, fill=symbol_color, outline="#FEF08A", width=8)
    finalize(img, name)

# =============================================================================
# 10. MASKS & QUEST ITEMS
# =============================================================================
def gen_mask(color, name):
    img = create_base()
    d = ImageDraw.Draw(img)
    # Mask oval
    d.ellipse([140, 130, 372, 410], fill=color, outline="#E2E8F0", width=12)
    # Eye holes
    d.ellipse([180, 220, 230, 290], fill="#0F172A")
    d.ellipse([282, 220, 332, 290], fill="#0F172A")
    finalize(img, name)

def gen_egg(spotted=False, name="item_egg.png"):
    img = create_base()
    d = ImageDraw.Draw(img)
    d.ellipse([160, 130, 352, 410], fill="#FEF08A" if spotted else "#FFFFFF", outline="#CBD5E1", width=12)
    if spotted:
        draw_circle(d, (220, 220), 20, fill="#3B82F6")
        draw_circle(d, (290, 280), 26, fill="#3B82F6")
        draw_circle(d, (240, 330), 16, fill="#3B82F6")
    finalize(img, name)

def gen_chicken(name):
    img = create_base()
    d = ImageDraw.Draw(img)
    # Cucco body
    d.ellipse([160, 200, 360, 380], fill="#F8FAFC", outline="#CBD5E1", width=12)
    # Head & beak
    draw_circle(d, (330, 220), 50, fill="#F8FAFC", outline="#CBD5E1", width=10)
    d.polygon([(360, 210), (410, 230), (360, 240)], fill="#F59E0B")
    # Red comb
    d.polygon([(320, 170), (340, 130), (360, 170)], fill="#EF4444")
    finalize(img, name)

def gen_note(color, name):
    img = create_base()
    d = ImageDraw.Draw(img)
    # Modern glowing music note
    draw_circle(d, (200, 330), 50, fill=color)
    d.rectangle([230, 130, 256, 330], fill=color)
    d.polygon([(256, 130), (340, 150), (340, 210), (256, 190)], fill=color)
    finalize(img, name)

def gen_fairy_ocarina(name="item_ocarina_fairy.png"):
    img = create_base()
    d = ImageDraw.Draw(img)
    # Natural green fairy ocarina body
    d.rounded_rectangle([120, 180, 380, 320], radius=60, fill="#15803D", outline="#166534", width=12)
    # Mouthpiece
    d.polygon([(140, 200), (80, 240), (120, 270)], fill="#CBD5E1", outline="#94A3B8", width=8)
    # Wooden earthy band
    d.rectangle([140, 190, 180, 310], fill="#854D0E", outline="#713F12", width=6)
    # Finger holes
    holes = [(230, 220), (280, 210), (330, 220), (250, 270), (300, 270)]
    for h in holes:
        draw_circle(d, h, 14, fill="#1E293B", outline="#86EFAC", width=4)
    finalize(img, name)

def gen_gerudo_card(name="item_gerudo_card.png"):
    img = create_base()
    d = ImageDraw.Draw(img)
    # Golden Gerudo membership token/card
    d.rounded_rectangle([100, 130, 412, 382], radius=32, fill="#B45309", outline="#F59E0B", width=14)
    d.rounded_rectangle([125, 155, 387, 357], radius=20, fill="#78350F", outline="#D97706", width=6)
    # Gerudo symbol / crest in gold
    draw_circle(d, (256, 230), 45, fill="#F59E0B", outline="#FEF08A", width=6)
    d.polygon([(256, 270), (220, 330), (292, 330)], fill="#FEF08A")
    finalize(img, name)

print("Generating Gauntlets, Scales, Wallets, Bags, and Quest Items...")
gen_gauntlets("#F59E0B", "#B45309", True, "gear_goron_bracelet.png")
gen_gauntlets("#94A3B8", "#64748B", False, "gear_silver_gauntlets.png")
gen_gauntlets("#F59E0B", "#D97706", False, "gear_golden_gauntlets.png")

gen_scale("#94A3B8", "#64748B", "scale_silver.png")
gen_scale("#F59E0B", "#D97706", "scale_golden.png")

gen_wallet("#16A34A", "#15803D", "wallet_adults.png")
gen_wallet("#2563EB", "#1D4ED8", "wallet_giants.png")
gen_wallet("#F59E0B", "#D97706", "wallet_tycoons.png")

gen_bag("#16A34A", "Q", "bag_quiver.png")
gen_bag("#DC2626", "B", "bag_bomb.png")
gen_bag("#F59E0B", "S", "bag_bullet.png")

gen_mask("#FEF08A", "mask_keaton.png")
gen_mask("#F8FAFC", "mask_skull.png")
gen_mask("#1E293B", "mask_spooky.png")
gen_mask("#FEF08A", "mask_bunny.png")
gen_mask("#DC2626", "mask_goron.png")
gen_mask("#3B82F6", "mask_zora.png")
gen_mask("#F97316", "mask_gerudo.png")
gen_mask("#FFFFFF", "mask_truth.png")

gen_egg(False, "item_pocket_egg.png")
gen_egg(True, "item_weird_egg.png")
gen_chicken("item_cucco.png")

# Notes for 12 songs
gen_note("#38BDF8", "note_cyan.png")
gen_note("#FBBF24", "note_gold.png")
gen_note("#A855F7", "note_purple.png")
gen_note("#4ADE80", "note_green.png")
gen_note("#F87171", "note_red.png")

gen_fairy_ocarina("item_ocarina_fairy.png")
gen_gerudo_card("item_gerudo_card.png")

print("All extra Switch 2 Remake HD Assets generated successfully!")
