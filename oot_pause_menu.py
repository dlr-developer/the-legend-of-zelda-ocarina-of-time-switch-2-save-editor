"""
The Legend of Zelda: Ocarina of Time (Nintendo Switch 2 Remake) - In-Game Pause Menu Interactive UI
Follows the authentic Switch 2 in-game pause menu structure (Common.blarc: PlusMenu_00,
PaItemMenu_00, PaEquipmentMenu_00, PaCollectMenu_00, ImportantMenu_01, Ocarina_00).
Allows clicking items to activate/own/equip and adjust quantities in two-way sync with the main editor.
"""

import os
import sys
import math
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

try:
    from PIL import Image, ImageTk, ImageEnhance, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

import oot_scarecrow

RESOURCE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
SWITCH2_ASSETS_DIR = os.path.join(RESOURCE_DIR, "assets", "switch2_ui")

# Modern Nintendo Switch 2 Dark Obsidian & Glass Theme Colors
COLOR_BG = "#0B111A"            # Deep obsidian slate
COLOR_PANEL_BG = "#131C28"      # Glass-tinted slate panel
COLOR_SLOT_BG = "#1A2535"       # Recessed slot background
COLOR_SLOT_BORDER = "#2B3A4F"   # Modern border
COLOR_GOLD = "#E5C158"          # Modern Zelda gold
COLOR_GOLD_LIGHT = "#FDE047"    # Bright yellow/gold highlight
COLOR_GREEN_MAGIC = "#10B981"   # Emerald magic green
COLOR_RED_HEART = "#F43F5E"     # Modern life heart red
COLOR_TEXT = "#F1F5F9"          # Clean text
COLOR_TEXT_MUTED = "#94A3B8"    # Modern muted text
COLOR_EQUIPPED = "#10B981"      # Equipped badge emerald green
COLOR_CYAN = "#38BDF8"          # Modern Switch 2 cyan

# Authentic In-Game Song Book Parchment Colors
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

# Song Book Short Names and Arc Order
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
    """Compute (song_name, x, y, radius) positions for the 13 songs on outer and inner arcs.
    Outer arc (7 songs): Zelda's Lullaby, Song of Time, Sun's Song, Song of Storms,
                         Epona's Song, Saria's Song, Scarecrow's Song.
    Inner arc (6 songs): Minuet, Bolero, Serenade, Nocturne, Requiem, Prelude.
    """
    positions = []
    cx = width / 2.0

    # Outer arc: spans about 80% of panel width
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

    # Inner arc: spans about 62% of panel width below the outer arc
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
    """Compute canvas y coordinate for a pitch value on the musical staff.
    Higher pitch value -> higher on the staff (lower canvas y).
    Pitch 4 ("L") sits at staff_bot_y, pitch 16 ("X") sits at staff_top_y.
    """
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



class HDTextureManager:
    """Loads and caches Ultra HD Switch 2 Remake textures from assets/switch2_ui."""
    def __init__(self, base_dir=SWITCH2_ASSETS_DIR):
        self.base_dir = base_dir
        self.cache = {}

    def get(self, filename, size=(44, 44), dimmed=False):
        if not PIL_AVAILABLE:
            return None
        key = (filename, size, dimmed)
        if key in self.cache:
            return self.cache[key]

        full_path = os.path.join(self.base_dir, filename)
        if not os.path.exists(full_path):
            img = Image.new("RGBA", size, (30, 41, 59, 200))
        else:
            try:
                img = Image.open(full_path).convert("RGBA")
                img = img.resize(size, Image.Resampling.LANCZOS)
            except Exception:
                img = Image.new("RGBA", size, (30, 41, 59, 200))

        if dimmed:
            alpha = img.split()[-1]
            gray = ImageOps.grayscale(img).convert("RGBA")
            enhancer = ImageEnhance.Brightness(gray)
            dim_img = enhancer.enhance(0.25)
            dim_alpha = ImageEnhance.Brightness(alpha).enhance(0.28)
            dim_img.putalpha(dim_alpha)
            photo = ImageTk.PhotoImage(dim_img)
        else:
            photo = ImageTk.PhotoImage(img)

        self.cache[key] = photo
        return photo


class OOTTextureMenuFrame(tk.Frame):
    """Full In-Game Pause Menu Frame for the Switch 2 Remake."""
    def __init__(self, parent, editor):
        super().__init__(parent, bg=COLOR_BG)
        self.editor = editor
        self.textures = HDTextureManager()
        self.active_subscreen = 0  # 0: Items, 1: Equipment, 2: Collection
        self.selected_song_id = "Zelda's Lullaby"

        self._build_top_nav()
        self._build_hud()

        # Content container for the 3 pause subscreens
        self.content_frame = tk.Frame(self, bg=COLOR_BG)
        self.content_frame.pack(fill="both", expand=True, padx=10, pady=(2, 4))

        self._build_inventory_subscreen()
        self._build_equipment_subscreen()
        self._build_collection_subscreen()

        # Bottom info bar (game's Pa_Info panel)
        self._build_info_bar()

        # Keyboard shortcuts (L / R triggers)
        self.bind("<Left>", lambda e: self.cycle_subscreen(-1))
        self.bind("<Right>", lambda e: self.cycle_subscreen(1))
        self.bind("<q>", lambda e: self.cycle_subscreen(-1))
        self.bind("<e>", lambda e: self.cycle_subscreen(1))
        self.bind("<Q>", lambda e: self.cycle_subscreen(-1))
        self.bind("<E>", lambda e: self.cycle_subscreen(1))

        self.show_subscreen(0)

    # =========================================================================
    # TOP NAVIGATION BAR (Return Button + Subscreen Tabs + Save Button)
    # =========================================================================
    def _build_top_nav(self):
        nav = tk.Frame(self, bg=COLOR_BG, pady=6)
        nav.pack(fill="x", padx=10)

        # 1. Return to Standard Editor Button
        ret_btn = tk.Button(
            nav, text="[B] Return to Editor", font=("Segoe UI", 9, "bold"),
            bg="#2563EB", fg="#FFF", activebackground="#1D4ED8", relief="flat", padx=14, pady=4,
            command=self.editor.switch_to_standard_view, cursor="hand2"
        )
        ret_btn.pack(side="left")

        # 2. Switch 2 Remake L / R Subscreen Switcher
        tabs_box = tk.Frame(nav, bg=COLOR_BG)
        tabs_box.pack(side="left", expand=True)

        tk.Button(
            tabs_box, text="[L] Previous", font=("Segoe UI", 8, "bold"), bg="#1E293B", fg=COLOR_CYAN,
            activebackground=COLOR_CYAN, activeforeground="#000", relief="flat", padx=8, pady=3,
            command=lambda: self.cycle_subscreen(-1), cursor="hand2"
        ).pack(side="left", padx=3)

        self.subscreen_btns = []
        titles = ["[L] 1. ITEMS", "2. EQUIPMENT", "3. COLLECTION [R]"]
        for idx, t in enumerate(titles):
            btn = tk.Button(
                tabs_box, text=f"  {t}  ", font=("Segoe UI", 9, "bold"),
                bg="#1E293B", fg=COLOR_TEXT_MUTED, activebackground=COLOR_GOLD,
                activeforeground="#000", relief="flat", padx=12, pady=4,
                command=lambda i=idx: self.show_subscreen(i), cursor="hand2"
            )
            btn.pack(side="left", padx=2)
            self.subscreen_btns.append(btn)

        tk.Button(
            tabs_box, text="Next [R]", font=("Segoe UI", 8, "bold"), bg="#1E293B", fg=COLOR_CYAN,
            activebackground=COLOR_CYAN, activeforeground="#000", relief="flat", padx=8, pady=3,
            command=lambda: self.cycle_subscreen(1), cursor="hand2"
        ).pack(side="left", padx=3)

        # 3. Quick Save Button
        tk.Button(
            nav, text="[+] Save Changes", font=("Segoe UI", 9, "bold"),
            bg="#059669", fg="#FFF", activebackground="#047857", relief="flat", padx=14, pady=4,
            command=self._on_save_clicked, cursor="hand2"
        ).pack(side="right")

    def cycle_subscreen(self, delta):
        new_idx = (self.active_subscreen + delta) % 3
        self.show_subscreen(new_idx)

    def show_subscreen(self, idx):
        self.active_subscreen = idx
        for i, b in enumerate(self.subscreen_btns):
            if i == idx:
                b.configure(bg=COLOR_GOLD, fg="#0F172A")
            else:
                b.configure(bg="#1E293B", fg=COLOR_TEXT_MUTED)

        self.inv_frame.pack_forget()
        self.equip_frame.pack_forget()
        self.collection_frame.pack_forget()

        if idx == 0:
            self.inv_frame.pack(fill="both", expand=True)
            self.set_info("Items: Left-click to toggle/cycle owned • Mouse wheel or +/- to change quantity • Right-click for options")
        elif idx == 1:
            self.equip_frame.pack(fill="both", expand=True)
            self.set_info("Equipment: Left-click to own/unown • Right-click or double-click to equip")
        elif idx == 2:
            self.collection_frame.pack(fill="both", expand=True)
            self.set_info("Collection: Left-click to toggle story items & songs • Hover songs to view notes on staff")

        self.refresh_visuals()

    # =========================================================================
    # BOTTOM INFO BAR (Game's Pa_Info panel)
    # =========================================================================
    def _build_info_bar(self):
        info_frame = tk.Frame(self, bg=COLOR_PANEL_BG, bd=1, relief="ridge", padx=12, pady=5)
        info_frame.pack(fill="x", padx=10, pady=(2, 6))

        tk.Label(info_frame, text="INFO", font=("Segoe UI", 8, "bold"), fg=COLOR_GOLD, bg=COLOR_PANEL_BG).pack(side="left", padx=(0, 8))
        self.info_label = tk.Label(info_frame, text="", font=("Segoe UI", 9), fg=COLOR_TEXT, bg=COLOR_PANEL_BG, anchor="w")
        self.info_label.pack(side="left", fill="x", expand=True)

    def set_info(self, text):
        if hasattr(self, "info_label"):
            self.info_label.configure(text=text)

    # =========================================================================
    # MODERN SWITCH 2 HUD (Hearts, Magic Gauge, Rupees - Skulltula moved to Collection)
    # =========================================================================
    def _build_hud(self):
        hud = tk.Frame(self, bg=COLOR_PANEL_BG, bd=1, relief="ridge", padx=12, pady=5)
        hud.pack(fill="x", padx=10, pady=(0, 4))

        # 1. Hearts Box
        h_box = tk.Frame(hud, bg=COLOR_PANEL_BG)
        h_box.pack(side="left", padx=(0, 16))

        h_top = tk.Frame(h_box, bg=COLOR_PANEL_BG)
        h_top.pack(anchor="w")
        tk.Label(h_top, text="LIFE", font=("Segoe UI", 9, "bold"), fg=COLOR_RED_HEART, bg=COLOR_PANEL_BG).pack(side="left", padx=(0, 6))
        self.hp_label = tk.Label(h_top, text="3/3 Hearts", font=("Segoe UI", 8), fg=COLOR_TEXT_MUTED, bg=COLOR_PANEL_BG)
        self.hp_label.pack(side="left")

        self.hearts_canvas = tk.Canvas(h_box, width=230, height=44, bg=COLOR_PANEL_BG, highlightthickness=0)
        self.hearts_canvas.pack(anchor="w", pady=(1, 0))
        self.hearts_canvas.bind("<Button-1>", self._on_hearts_canvas_click)

        h_btns = tk.Frame(h_box, bg=COLOR_PANEL_BG)
        h_btns.pack(anchor="w", pady=(2, 0))
        tk.Button(h_btns, text="+ Heart", font=("Segoe UI", 7), bg="#334155", fg=COLOR_TEXT, relief="flat", padx=4, command=self._add_heart).pack(side="left", padx=(0, 2))
        tk.Button(h_btns, text="- Heart", font=("Segoe UI", 7), bg="#334155", fg=COLOR_TEXT, relief="flat", padx=4, command=self._sub_heart).pack(side="left", padx=2)
        tk.Button(h_btns, text="Full Heal", font=("Segoe UI", 7, "bold"), bg="#2563EB", fg="#FFF", relief="flat", padx=5, command=self._heal_link).pack(side="left", padx=2)

        dd_val = self.editor.v_double_defense.get() if hasattr(self.editor, "v_double_defense") else False
        self.dd_check_var = tk.BooleanVar(value=dd_val)
        tk.Checkbutton(
            h_btns, text="Double Defense (White Frame)", font=("Segoe UI", 7),
            variable=self.dd_check_var, bg=COLOR_PANEL_BG, fg=COLOR_TEXT, selectcolor=COLOR_PANEL_BG,
            activebackground=COLOR_PANEL_BG, command=self._toggle_double_defense
        ).pack(side="left", padx=(6, 0))

        # 2. Magic Meter Box
        m_box = tk.Frame(hud, bg=COLOR_PANEL_BG)
        m_box.pack(side="left", padx=12, fill="y")

        m_top = tk.Frame(m_box, bg=COLOR_PANEL_BG)
        m_top.pack(anchor="w")
        tk.Label(m_top, text="MAGIC", font=("Segoe UI", 9, "bold"), fg=COLOR_GREEN_MAGIC, bg=COLOR_PANEL_BG).pack(side="left", padx=(0, 6))
        self.magic_label = tk.Label(m_top, text="Standard", font=("Segoe UI", 8), fg=COLOR_TEXT_MUTED, bg=COLOR_PANEL_BG)
        self.magic_label.pack(side="left")

        self.magic_canvas = tk.Canvas(m_box, width=170, height=22, bg=COLOR_PANEL_BG, highlightthickness=0)
        self.magic_canvas.pack(anchor="w", pady=(4, 2))
        self.magic_canvas.bind("<Button-1>", self._on_magic_canvas_click)

        m_btns = tk.Frame(m_box, bg=COLOR_PANEL_BG)
        m_btns.pack(anchor="w")
        tk.Button(m_btns, text="Cycle Meter", font=("Segoe UI", 7), bg="#334155", fg=COLOR_TEXT, relief="flat", padx=4, command=self._cycle_magic).pack(side="left", padx=(0, 2))
        tk.Button(m_btns, text="Refill MP", font=("Segoe UI", 7, "bold"), bg="#059669", fg="#FFF", relief="flat", padx=5, command=self._refill_magic).pack(side="left", padx=2)

        # 3. Rupees Box
        r_box = tk.Frame(hud, bg=COLOR_PANEL_BG)
        r_box.pack(side="left", padx=16, fill="y")
        tk.Label(r_box, text="RUPEES", font=("Segoe UI", 9, "bold"), fg=COLOR_GOLD, bg=COLOR_PANEL_BG).pack(anchor="w")

        r_disp = tk.Frame(r_box, bg=COLOR_PANEL_BG)
        r_disp.pack(anchor="w", pady=(2, 0))
        self.rupee_icon_lbl = tk.Label(r_disp, bg=COLOR_PANEL_BG)
        self.rupee_icon_lbl.pack(side="left", padx=(0, 4))
        self.rupee_val_lbl = tk.Label(r_disp, text="0", font=("Segoe UI", 12, "bold"), fg="#FFF", bg=COLOR_PANEL_BG)
        self.rupee_val_lbl.pack(side="left")
        self.rupee_max_lbl = tk.Label(r_disp, text=" / 500", font=("Segoe UI", 9), fg=COLOR_TEXT_MUTED, bg=COLOR_PANEL_BG)
        self.rupee_max_lbl.pack(side="left")

        r_btns = tk.Frame(r_box, bg=COLOR_PANEL_BG)
        r_btns.pack(anchor="w", pady=(2, 0))
        tk.Button(r_btns, text="Max Wallet", font=("Segoe UI", 7, "bold"), bg="#D97706", fg="#FFF", relief="flat", padx=4, command=self._max_rupees).pack(side="left")
        tk.Button(r_btns, text="+50", font=("Segoe UI", 7), bg="#334155", fg=COLOR_TEXT, relief="flat", padx=4, command=lambda: self._add_rupees(50)).pack(side="left", padx=2)
        tk.Button(r_btns, text="-50", font=("Segoe UI", 7), bg="#334155", fg=COLOR_TEXT, relief="flat", padx=4, command=lambda: self._add_rupees(-50)).pack(side="left", padx=2)

    # ------------------ HUD Callbacks ------------------
    def _draw_hearts(self):
        canv = self.hearts_canvas
        canv.delete("all")

        total_hearts = safe_int(self.editor.v_hearts.get() if hasattr(self.editor, "v_hearts") else 3, default=3)
        current_hp = safe_int(self.editor.v_hp.get() if hasattr(self.editor, "v_hp") else 12, default=12)
        dd = self.editor.v_double_defense.get() if hasattr(self.editor, "v_double_defense") else False

        heart_size = 18
        spacing = 20

        for i in range(total_hearts):
            row = i // 10
            col = i % 10
            x = col * spacing + 4
            y = row * spacing + 4

            full_val = (i + 1) * 4
            if current_hp >= full_val:
                fill_q = 4
            elif current_hp <= i * 4:
                fill_q = 0
            else:
                fill_q = current_hp - (i * 4)

            border_col = "#FFFFFF" if dd else "#450A0A"
            canv.create_rectangle(x, y, x + heart_size, y + heart_size, fill="#1E293B", outline=border_col, width=1.5 if dd else 1)

            if fill_q > 0:
                h_pct = fill_q / 4.0
                fill_h = int(heart_size * h_pct)
                canv.create_rectangle(x + 1, y + heart_size - fill_h, x + heart_size - 1, y + heart_size - 1, fill=COLOR_RED_HEART, outline="")

            canv.create_text(x + heart_size // 2, y + heart_size // 2, text=str(i + 1), fill="#94A3B8" if fill_q == 0 else "#FFFFFF", font=("Segoe UI", 6))

        hp_str = f"{current_hp / 4:.2f}/{total_hearts} Hearts"
        self.hp_label.configure(text=hp_str)

    def _draw_magic(self):
        canv = self.magic_canvas
        canv.delete("all")

        m_str = self.editor.v_magic.get() if hasattr(self.editor, "v_magic") else "None"
        if "Double" in m_str:
            max_mp = 48
            tier_name = "Double Magic (48 MP)"
        elif "Standard" in m_str:
            max_mp = 24
            tier_name = "Standard Magic (24 MP)"
        else:
            max_mp = 0
            tier_name = "No Magic Acquired"

        self.magic_label.configure(text=tier_name)

        canv.create_rectangle(2, 2, 168, 20, fill="#0F172A", outline="#334155", width=1)
        if max_mp > 0:
            cur_mp = safe_int(self.editor.v_magic_points.get() if hasattr(self.editor, "v_magic_points") else 0, default=0)
            cur_mp = max(0, min(max_mp, cur_mp))
            pct = cur_mp / max_mp
            fill_w = int(164 * pct)
            if fill_w > 0:
                canv.create_rectangle(3, 3, 3 + fill_w, 19, fill=COLOR_GREEN_MAGIC, outline="")
            canv.create_text(85, 11, text=f"{cur_mp} / {max_mp} MP", fill="#FFFFFF", font=("Segoe UI", 8, "bold"))
        else:
            canv.create_text(85, 11, text="Locked", fill="#64748B", font=("Segoe UI", 8))

    def _on_hearts_canvas_click(self, event):
        col = (event.x - 4) // 20
        row = (event.y - 4) // 20
        idx = row * 10 + col
        total = safe_int(self.editor.v_hearts.get() if hasattr(self.editor, "v_hearts") else 3, default=3)
        if 0 <= idx < total:
            new_hp = (idx + 1) * 4
            if hasattr(self.editor, "v_hp"):
                self.editor.v_hp.set(str(new_hp))
            if hasattr(self.editor, "_on_hp_change"):
                self.editor._on_hp_change()
            self._draw_hearts()

    def _add_heart(self):
        cur = safe_int(self.editor.v_hearts.get() if hasattr(self.editor, "v_hearts") else 3, default=3)
        if cur < 20:
            if hasattr(self.editor, "v_hearts"):
                self.editor.v_hearts.set(str(cur + 1))
            if hasattr(self.editor, "_on_total_hearts_change"):
                self.editor._on_total_hearts_change()
            self.refresh_visuals()

    def _sub_heart(self):
        cur = safe_int(self.editor.v_hearts.get() if hasattr(self.editor, "v_hearts") else 3, default=3)
        if cur > 3:
            if hasattr(self.editor, "v_hearts"):
                self.editor.v_hearts.set(str(cur - 1))
            if hasattr(self.editor, "_on_total_hearts_change"):
                self.editor._on_total_hearts_change()
            self.refresh_visuals()

    def _heal_link(self):
        if hasattr(self.editor, "heal_link"):
            self.editor.heal_link()
        elif hasattr(self.editor, "v_hp") and hasattr(self.editor, "v_hearts"):
            tot = safe_int(self.editor.v_hearts.get(), default=3)
            self.editor.v_hp.set(str(tot * 4))
        self._draw_hearts()

    def _toggle_double_defense(self):
        val = self.dd_check_var.get()
        if hasattr(self.editor, "v_double_defense"):
            self.editor.v_double_defense.set(val)
        self._draw_hearts()

    def _cycle_magic(self):
        cur = self.editor.v_magic.get() if hasattr(self.editor, "v_magic") else "None"
        if "None" in cur:
            self.editor.v_magic.set("Standard Magic Meter (24 MP)")
            if hasattr(self.editor, "v_magic_points"):
                self.editor.v_magic_points.set("24")
        elif "Standard" in cur:
            self.editor.v_magic.set("Double Magic Meter (48 MP)")
            if hasattr(self.editor, "v_magic_points"):
                self.editor.v_magic_points.set("48")
        else:
            self.editor.v_magic.set("None")
            if hasattr(self.editor, "v_magic_points"):
                self.editor.v_magic_points.set("0")
        if hasattr(self.editor, "_on_magic_level_change"):
            self.editor._on_magic_level_change()
        self._draw_magic()

    def _refill_magic(self):
        if hasattr(self.editor, "refill_magic"):
            self.editor.refill_magic()
        elif hasattr(self.editor, "v_magic") and hasattr(self.editor, "v_magic_points"):
            m = self.editor.v_magic.get()
            self.editor.v_magic_points.set("48" if "Double" in m else ("24" if "Standard" in m else "0"))
        self._draw_magic()

    def _on_magic_canvas_click(self, event):
        m_str = self.editor.v_magic.get() if hasattr(self.editor, "v_magic") else "None"
        max_mp = 48 if "Double" in m_str else (24 if "Standard" in m_str else 0)
        if max_mp > 0:
            pct = max(0.0, min(1.0, (event.x - 3) / 164.0))
            new_mp = int(max_mp * pct)
            if hasattr(self.editor, "v_magic_points"):
                self.editor.v_magic_points.set(str(new_mp))
            if hasattr(self.editor, "_on_mp_change"):
                self.editor._on_mp_change()
            self._draw_magic()

    def _max_rupees(self):
        if hasattr(self.editor, "_max_rupees_to_wallet"):
            self.editor._max_rupees_to_wallet()
        else:
            wal_label = self.editor.equip_vars.get("wallet", tk.StringVar()).get()
            limit = 1000 if "1000" in wal_label else (500 if "500" in wal_label else 200)
            self.editor.v_rupees.set(str(limit))
        self.refresh_visuals()

    def _add_rupees(self, amount):
        cur = safe_int(self.editor.v_rupees.get(), default=0)
        wal_label = self.editor.equip_vars.get("wallet", tk.StringVar()).get()
        limit = 1000 if "1000" in wal_label else (500 if "500" in wal_label else 200)
        new_val = max(0, min(limit, cur + amount))
        self.editor.v_rupees.set(str(new_val))
        self.refresh_visuals()

    def _on_save_clicked(self):
        if hasattr(self.editor, "save"):
            self.editor.save()
        self.refresh_visuals()

    # =========================================================================
    # QUANTITY & CAPACITY HELPERS
    # =========================================================================
    def get_ammo_capacity(self, key):
        """Return the maximum allowed capacity for an ammo or counter key."""
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
        """Adjust quantity for ammo or counter items, clamping between 0 and current capacity."""
        cap = self.get_ammo_capacity(key)
        if key == "tokens":
            cur = safe_int(self.editor.v_tokens.get(), default=0)
            new_val = max(0, min(cap, cur + delta))
            self.editor.v_tokens.set(str(new_val))
        elif key == "heart_pieces":
            tot = safe_int(self.editor.v_heart_pieces_total.get(), default=0)
            cur_held = tot % 4
            new_held = max(0, min(3, cur_held + delta))
            base_h = (tot // 4) * 4
            new_tot = base_h + new_held
            self.editor.v_heart_pieces_total.set(str(new_tot))
            if hasattr(self.editor, "_recalc_hearts_from_components"):
                self.editor._recalc_hearts_from_components()
            elif hasattr(self.editor, "v_heart_pieces_held"):
                self.editor.v_heart_pieces_held.set(str(new_held))
        elif key in self.editor.ammo_vars:
            var = self.editor.ammo_vars[key][0]
            cur = safe_int(var.get(), default=0)
            new_val = max(0, min(cap, cur + delta))
            var.set(str(new_val))
            # Slingshot / Bow ammo items stay owned when quantity changes,
            # and if ammo is raised > 0, make sure the weapon is unlocked.
            if key == "arrows" and new_val > 0:
                if 0x938D56BF in self.editor.special_item_vars:
                    self.editor.special_item_vars[0x938D56BF][0].set(True)
            elif key == "seeds" and new_val > 0:
                if 0x80D34CE9 in self.editor.special_item_vars:
                    self.editor.special_item_vars[0x80D34CE9][0].set(True)
        self.refresh_visuals()

    def set_quantity_max(self, key):
        """Set an ammo or counter item to its maximum capacity."""
        cap = self.get_ammo_capacity(key)
        if key == "tokens":
            self.editor.v_tokens.set(str(cap))
        elif key == "heart_pieces":
            tot = safe_int(self.editor.v_heart_pieces_total.get(), default=0)
            base_h = (tot // 4) * 4
            self.editor.v_heart_pieces_total.set(str(base_h + 3))
            if hasattr(self.editor, "_recalc_hearts_from_components"):
                self.editor._recalc_hearts_from_components()
            elif hasattr(self.editor, "v_heart_pieces_held"):
                self.editor.v_heart_pieces_held.set("3")
        elif key in self.editor.ammo_vars:
            self.editor.ammo_vars[key][0].set(str(cap))
            if key == "arrows" and cap > 0 and 0x938D56BF in self.editor.special_item_vars:
                self.editor.special_item_vars[0x938D56BF][0].set(True)
            elif key == "seeds" and cap > 0 and 0x80D34CE9 in self.editor.special_item_vars:
                self.editor.special_item_vars[0x80D34CE9][0].set(True)
        self.refresh_visuals()

    def set_quantity_empty(self, key):
        """Empty an ammo item (0), keeping weapon ownership intact."""
        if key == "tokens":
            self.editor.v_tokens.set("0")
        elif key == "heart_pieces":
            tot = safe_int(self.editor.v_heart_pieces_total.get(), default=0)
            base_h = (tot // 4) * 4
            self.editor.v_heart_pieces_total.set(str(base_h))
            if hasattr(self.editor, "_recalc_hearts_from_components"):
                self.editor._recalc_hearts_from_components()
            elif hasattr(self.editor, "v_heart_pieces_held"):
                self.editor.v_heart_pieces_held.set("0")
        elif key in self.editor.ammo_vars:
            self.editor.ammo_vars[key][0].set("0")
        self.refresh_visuals()

    def prompt_set_quantity(self, key):
        """Prompt user with simpledialog to set exact quantity."""
        cap = self.get_ammo_capacity(key)
        cur = 0
        if key == "tokens":
            cur = safe_int(self.editor.v_tokens.get(), default=0)
        elif key == "heart_pieces":
            cur = safe_int(self.editor.v_heart_pieces_total.get(), default=0) % 4
        elif key in self.editor.ammo_vars:
            cur = safe_int(self.editor.ammo_vars[key][0].get(), default=0)
        val = simpledialog.askinteger("Set Amount", f"Enter amount (0-{cap}):", parent=self, minvalue=0, maxvalue=cap, initialvalue=cur)
        if val is not None:
            if key == "tokens":
                self.editor.v_tokens.set(str(val))
            elif key == "heart_pieces":
                tot = safe_int(self.editor.v_heart_pieces_total.get(), default=0)
                base_h = (tot // 4) * 4
                self.editor.v_heart_pieces_total.set(str(base_h + val))
                if hasattr(self.editor, "_recalc_hearts_from_components"):
                    self.editor._recalc_hearts_from_components()
                elif hasattr(self.editor, "v_heart_pieces_held"):
                    self.editor.v_heart_pieces_held.set(str(val))
            elif key in self.editor.ammo_vars:
                self.editor.ammo_vars[key][0].set(str(val))
                if key == "arrows" and val > 0 and 0x938D56BF in self.editor.special_item_vars:
                    self.editor.special_item_vars[0x938D56BF][0].set(True)
                elif key == "seeds" and val > 0 and 0x80D34CE9 in self.editor.special_item_vars:
                    self.editor.special_item_vars[0x80D34CE9][0].set(True)
            self.refresh_visuals()

    def _show_quantity_menu(self, event, key):
        """Right-click menu: Max, Empty, Set amount..."""
        cap = self.get_ammo_capacity(key)
        m = tk.Menu(self, tearoff=0, bg=COLOR_PANEL_BG, fg=COLOR_TEXT, activebackground=COLOR_GOLD, activeforeground="#000")
        m.add_command(label=f"Max ({cap})", command=lambda: self.set_quantity_max(key))
        m.add_command(label="Empty (0)", command=lambda: self.set_quantity_empty(key))
        m.add_separator()
        m.add_command(label="Set amount...", command=lambda: self.prompt_set_quantity(key))
        m.tk_popup(event.x_root, event.y_root)

    def _handle_wheel(self, event, key):
        """Wheel adjusts by 1; Shift+Wheel adjusts by 10."""
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

    # =========================================================================
    # SUBSCREEN 1: ITEMS (4x6 Authentic PaItemMenu Grid)
    # =========================================================================
    def _build_inventory_subscreen(self):
        self.inv_frame = tk.Frame(self.content_frame, bg=COLOR_BG)

        self.inv_box = tk.Frame(self.inv_frame, bg=COLOR_PANEL_BG, bd=2, relief="ridge", padx=14, pady=10)
        self.inv_box.pack(fill="both", expand=True)

        tk.Label(self.inv_box, text="SELECT ITEM - INVENTORY (24 SLOTS)", font=("Segoe UI", 11, "bold"), fg=COLOR_GOLD, bg=COLOR_PANEL_BG).pack(pady=(0, 2))
        tk.Label(self.inv_box, text="Click to toggle/cycle owned • Mouse wheel or +/- to change quantity • Right-click for options", font=("Segoe UI", 8), fg=COLOR_TEXT_MUTED, bg=COLOR_PANEL_BG).pack(pady=(0, 8))

        self.inv_grid_frame = tk.Frame(self.inv_box, bg=COLOR_PANEL_BG)
        self.inv_grid_frame.pack(expand=True)

        self.inv_slots = {}
        # 4x6 Matrix mapped to Switch 2 Remake HD assets (exact matrix_defs order)
        self.matrix_defs = [
            # Row 0
            (0, 0, "sticks", "Deku Sticks", "item_deku_stick.png", "sticks"),
            (0, 1, "nuts", "Deku Nuts", "item_deku_nut.png", "nuts"),
            (0, 2, "bombs", "Bombs", "item_bomb.png", "bombs"),
            (0, 3, "bow", "Fairy Bow", "item_bow.png", "arrows"),
            (0, 4, "fire_arrows", "Fire Arrow", "arrow_fire.png", None),
            (0, 5, "dins_fire", "Din's Fire", "spell_dins_fire.png", None),

            # Row 1
            (1, 0, "slingshot", "Fairy Slingshot", "item_slingshot.png", "seeds"),
            (1, 1, "ocarina", "Ocarina of Time", "item_ocarina_of_time.png", None),
            (1, 2, "bombchus", "Bombchus", "item_bombchu.png", "bombchus"),
            (1, 3, "hookshot", "Hookshot Upgrade", "item_hookshot.png", None),
            (1, 4, "ice_arrows", "Ice Arrow", "arrow_ice.png", None),
            (1, 5, "farores_wind", "Farore's Wind", "spell_farores_wind.png", None),

            # Row 2
            (2, 0, "boomerang", "Boomerang", "item_boomerang.png", None),
            (2, 1, "lens_of_truth", "Lens of Truth", "item_lens_of_truth.png", None),
            (2, 2, "magic_beans", "Magic Beans", "item_magic_beans.png", "beans"),
            (2, 3, "megaton_hammer", "Megaton Hammer", "item_hammer.png", None),
            (2, 4, "light_arrows", "Light Arrow", "arrow_light.png", None),
            (2, 5, "nayrus_love", "Nayru's Love", "spell_nayrus_love.png", None),

            # Row 3 (Authentic Switch 2 Remake: 5 Dedicated Bottles + Child Trade / Mask)
            (3, 0, "bottle_1", "Bottle 1", "bottle_empty.png", None),
            (3, 1, "bottle_2", "Bottle 2", "bottle_empty.png", None),
            (3, 2, "bottle_3", "Bottle 3", "bottle_empty.png", None),
            (3, 3, "bottle_4", "Bottle 4", "bottle_empty.png", None),
            (3, 4, "bottle_5", "Bottle 5", "bottle_empty.png", None),
            (3, 5, "child_trade", "Child Quest Item / Mask", "item_weird_egg.png", None),
        ]

        initial_slot_size = 96
        self._current_inv_slot_size = initial_slot_size

        for r, c, item_id, name, base_hd, ammo_k in self.matrix_defs:
            slot_card = tk.Frame(self.inv_grid_frame, bg=COLOR_SLOT_BG, bd=1, relief="ridge", width=initial_slot_size, height=initial_slot_size)
            slot_card.grid(row=r, column=c, padx=6, pady=5)
            slot_card.grid_propagate(False)

            canv = tk.Canvas(slot_card, width=initial_slot_size - 4, height=initial_slot_size - 4, bg=COLOR_SLOT_BG, highlightthickness=0)
            canv.pack(fill="both", expand=True)

            self.inv_slots[item_id] = {
                "canvas": canv, "card": slot_card, "name": name,
                "base_hd": base_hd, "ammo_key": ammo_k, "row": r, "col": c
            }

            canv.bind("<Button-1>", lambda e, i=item_id: self._on_inv_slot_click(i))
            canv.bind("<Enter>", lambda e, i=item_id: self._on_inv_slot_hover(i))
            canv.bind("<Leave>", lambda e: self.set_info("Items: Left-click to toggle/cycle owned • Mouse wheel or +/- to change quantity • Right-click for options"))

            if ammo_k:
                canv.bind("<Button-3>", lambda e, k=ammo_k: self._show_quantity_menu(e, k))
                canv.bind("<MouseWheel>", lambda e, k=ammo_k: self._handle_wheel(e, k))
                canv.bind("<Shift-MouseWheel>", lambda e, k=ammo_k: self._handle_wheel(e, k))
                canv.bind("<Button-4>", lambda e, k=ammo_k: self._handle_wheel(e, k))
                canv.bind("<Button-5>", lambda e, k=ammo_k: self._handle_wheel(e, k))
            elif item_id.startswith("bottle_"):
                canv.bind("<Button-3>", lambda e, i=item_id: self._on_bottle_right_click(e, i))
            elif item_id == "child_trade":
                canv.bind("<Button-3>", lambda e: self._on_child_trade_right_click(e))

        self.inv_box.bind("<Configure>", self._update_inv_slot_sizes)

    def _calc_inv_slot_size(self):
        h = self.inv_box.winfo_height() if hasattr(self, "inv_box") else 0
        if h <= 1:
            if hasattr(self, "winfo_height") and self.winfo_height() > 1:
                h = self.winfo_height() - 160
            else:
                h = 700  # Default height at 1400x950
        scale_size = int(84 + (h - 550) * 0.065)
        return max(84, min(110, scale_size))

    def _update_inv_slot_sizes(self, event=None):
        if not hasattr(self, "inv_box") or not hasattr(self, "inv_slots"):
            return
        slot_size = self._calc_inv_slot_size()
        if getattr(self, "_current_inv_slot_size", None) == slot_size:
            return
        self._current_inv_slot_size = slot_size
        pad_x = max(4, min(8, int(slot_size * 0.07)))
        pad_y = max(4, min(8, int(slot_size * 0.06)))
        for item_id, s in self.inv_slots.items():
            card = s["card"]
            card.configure(width=slot_size, height=slot_size)
            card.grid_configure(padx=pad_x, pady=pad_y)
        self._render_inv_slots()

    def _render_inv_slots(self):
        for item_id, s in self.inv_slots.items():
            canv = s["canvas"]
            canv.delete("all")
            ammo_k = s["ammo_key"]

            owned = False
            hd_file = s["base_hd"]
            sub_text = ""

            if item_id == "hookshot":
                hs_val = self.editor.hookshot_var.get() if hasattr(self.editor, "hookshot_var") else "None"
                if hs_val == "Longshot":
                    owned = True
                    hd_file = "item_longshot.png"
                    sub_text = "Long"
                elif hs_val == "Hookshot":
                    owned = True
                    hd_file = "item_hookshot.png"
                    sub_text = "Hook"
                else:
                    owned = False
                    hd_file = "item_hookshot.png"
                    sub_text = ""

            elif item_id == "ocarina":
                oot_var = self.editor.special_item_vars.get(0x54E2A3D1, (tk.BooleanVar(value=False), ""))[0].get() if hasattr(self.editor, "special_item_vars") else False
                fairy_var = self.editor.special_item_vars.get(0xB7DF60F1, (tk.BooleanVar(value=False), ""))[0].get() if hasattr(self.editor, "special_item_vars") else False
                if oot_var:
                    owned = True
                    hd_file = "item_ocarina_of_time.png"
                    sub_text = "Time"
                elif fairy_var:
                    owned = True
                    hd_file = "item_ocarina_fairy.png"
                    sub_text = "Fairy"
                else:
                    owned = False
                    hd_file = "item_ocarina_of_time.png"
                    sub_text = ""

            elif item_id.startswith("bottle_"):
                b_name = self.editor.bottle_vars.get(item_id, tk.StringVar(value="(Not Acquired / Locked)")).get()
                if b_name == "(Not Acquired / Locked)":
                    owned = False
                    hd_file = "bottle_empty.png"
                    sub_text = ""
                else:
                    owned = True
                    if "Fairy" in b_name: hd_file = "bottle_fairy.png"
                    elif "Red Potion" in b_name: hd_file = "bottle_red_potion.png"
                    elif "Green Potion" in b_name: hd_file = "bottle_green_potion.png"
                    elif "Blue Potion" in b_name: hd_file = "bottle_blue_potion.png"
                    elif "Blue Fire" in b_name: hd_file = "bottle_blue_fire.png"
                    elif "Poe" in b_name or "Big Poe" in b_name: hd_file = "bottle_poe.png"
                    elif "Ruto" in b_name or "Letter" in b_name: hd_file = "bottle_rutos_letter.png"
                    elif "Milk" in b_name or "Half" in b_name: hd_file = "bottle_milk.png"
                    else: hd_file = "bottle_empty.png"
                    sub_text = b_name.split(" ")[0][:6]

            elif item_id == "child_trade":
                cq = self.editor.child_quest_var.get() if hasattr(self.editor, "child_quest_var") else "None"
                if cq == "Weird Egg":
                    owned = True
                    hd_file = "item_weird_egg.png"
                    sub_text = "Egg"
                elif cq in ("Chicken", "Pocket Egg"):
                    owned = True
                    hd_file = "item_cucco.png"
                    sub_text = "Cucco"
                elif cq == "Zelda's Letter":
                    owned = True
                    hd_file = "bottle_rutos_letter.png"
                    sub_text = "Letter"
                else:
                    m_val = self.editor.active_mask_var.get() if hasattr(self.editor, "active_mask_var") else "None"
                    if m_val != "None":
                        owned = True
                        m_map = {
                            "Keaton Mask": "mask_keaton.png",
                            "Skull Mask": "mask_skull.png",
                            "Spooky Mask": "mask_spooky.png",
                            "Bunny Hood": "mask_bunny.png",
                            "Goron Mask": "mask_goron.png",
                            "Zora Mask": "mask_zora.png",
                            "Gerudo Mask": "mask_gerudo.png",
                            "Mask of Truth": "mask_truth.png",
                        }
                        hd_file = m_map.get(m_val, "mask_bunny.png")
                        sub_text = m_val.split(" ")[0][:6]
                    else:
                        owned = False
                        hd_file = "item_weird_egg.png"
                        sub_text = ""

            elif item_id == "bow":
                owned = self.editor.special_item_vars.get(0x938D56BF, (tk.BooleanVar(value=False), ""))[0].get()
                hd_file = "item_bow.png"
            elif item_id == "slingshot":
                owned = self.editor.special_item_vars.get(0x80D34CE9, (tk.BooleanVar(value=False), ""))[0].get()
                hd_file = "item_slingshot.png"
            else:
                # Other special items or pure ammo items
                for kh, (var, itm_name) in getattr(self.editor, "special_item_vars", {}).items():
                    if s["name"].lower() in itm_name.lower():
                        owned = var.get()
                        break
                if not owned and ammo_k and ammo_k in getattr(self.editor, "ammo_vars", {}):
                    v_cnt = safe_int(self.editor.ammo_vars[ammo_k][0].get(), default=0)
                    owned = (v_cnt > 0)

            # Slot background & dim outline when not owned, gold border when owned
            slot_size = getattr(self, "_current_inv_slot_size", 96)
            cw = canv.winfo_width()
            ch = canv.winfo_height()
            if cw <= 1:
                cw = slot_size - 4
            if ch <= 1:
                ch = slot_size - 4

            bg_col = "#1E293B" if owned else "#0F172A"
            bd_col = COLOR_GOLD if owned else COLOR_SLOT_BORDER
            canv.create_rectangle(2, 2, cw - 2, ch - 2, fill=bg_col, outline=bd_col, width=1.5 if owned else 1)

            img_dim = max(38, int(cw * 0.58))
            photo = self.textures.get(hd_file, size=(img_dim, img_dim), dimmed=(not owned))
            if photo:
                canv.create_image(cw // 2, int(ch * 0.42), image=photo)

            # Quantity badge (like game's T_ItemNum pane) for ammo items
            if ammo_k and ammo_k in getattr(self.editor, "ammo_vars", {}):
                cnt = self.editor.ammo_vars[ammo_k][0].get()
                bh = 17
                by2 = ch - 4
                by1 = by2 - bh
                # Quantity badge at bottom-right
                qx2 = cw - 4
                qx1 = max(38, qx2 - 32)
                canv.create_rectangle(qx1, by1, qx2, by2, fill="#0F172A", outline="#334155")
                canv.create_text((qx1 + qx2) // 2, (by1 + by2) // 2, text=str(cnt), fill=COLOR_GOLD_LIGHT if owned else COLOR_TEXT_MUTED, font=("Segoe UI", 8, "bold"))
                # Mini +/- buttons drawn on canvas
                canv.create_rectangle(4, by1, 18, by2, fill="#1E293B", outline="#334155")
                canv.create_text(11, (by1 + by2) // 2, text="-", fill=COLOR_TEXT, font=("Segoe UI", 9, "bold"))
                canv.create_rectangle(20, by1, 34, by2, fill="#1E293B", outline="#334155")
                canv.create_text(27, (by1 + by2) // 2, text="+", fill=COLOR_TEXT, font=("Segoe UI", 8, "bold"))
            elif sub_text and owned:
                canv.create_text(cw // 2, ch - 10, text=sub_text, fill=COLOR_GOLD_LIGHT, font=("Segoe UI", 7, "bold"))

    def _on_inv_slot_hover(self, item_id):
        s = self.inv_slots.get(item_id, {})
        name = s.get("name", item_id)
        ammo_k = s.get("ammo_key")
        info = f"{name}"
        if ammo_k and ammo_k in getattr(self.editor, "ammo_vars", {}):
            cnt = self.editor.ammo_vars[ammo_k][0].get()
            cap = self.get_ammo_capacity(ammo_k)
            info += f" — Count: {cnt} / {cap} (Use +/- buttons or mouse wheel)"
        elif item_id == "hookshot":
            hs = self.editor.hookshot_var.get() if hasattr(self.editor, "hookshot_var") else "None"
            info += f" — Tier: {hs} (Click to cycle None -> Hookshot -> Longshot)"
        elif item_id == "ocarina":
            oot = self.editor.special_item_vars.get(0x54E2A3D1, (tk.BooleanVar(value=False), ""))[0].get()
            fairy = self.editor.special_item_vars.get(0xB7DF60F1, (tk.BooleanVar(value=False), ""))[0].get()
            cur = "Ocarina of Time" if oot else ("Fairy Ocarina" if fairy else "None")
            info += f" — Current: {cur} (Click to cycle)"
        elif item_id.startswith("bottle_"):
            b = self.editor.bottle_vars.get(item_id, tk.StringVar()).get()
            info += f" — Content: {b} (Click to cycle contents)"
        elif item_id == "child_trade":
            cq = self.editor.child_quest_var.get() if hasattr(self.editor, "child_quest_var") else "None"
            m = self.editor.active_mask_var.get() if hasattr(self.editor, "active_mask_var") else "None"
            cur = cq if cq != "None" else m
            info += f" — Active: {cur} (Click to cycle quest items & masks)"
        self.set_info(info)

    def _on_inv_slot_click(self, item_id):
        # Check if click was in mini +/- buttons on canvas
        s = self.inv_slots.get(item_id)
        if s and s["ammo_key"]:
            ammo_k = s["ammo_key"]
            canv = s["canvas"]
            try:
                x = canv.winfo_pointerx() - canv.winfo_rootx()
                y = canv.winfo_pointery() - canv.winfo_rooty()
            except Exception:
                x, y = -1, -1
            slot_size = getattr(self, "_current_inv_slot_size", 96)
            ch = canv.winfo_height()
            if ch <= 1:
                ch = slot_size - 4
            bh = 17
            by2 = ch - 4
            by1 = by2 - bh
            if (by1 <= y <= by2) or (52 <= y <= 68):
                if 4 <= x <= 18:
                    self.change_quantity(ammo_k, -1)
                    return
                elif 20 <= x <= 34:
                    self.change_quantity(ammo_k, 1)
                    return

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
            cur = self.editor.bottle_vars[item_id].get()
            bottle_idx = int(item_id[-1]) - 1
            if hasattr(self.editor, "bottle_combos") and bottle_idx < len(self.editor.bottle_combos):
                b_choices = self.editor.bottle_combos[bottle_idx]["values"]
            else:
                b_choices = ["(Not Acquired / Locked)", "Empty Bottle", "Red Potion", "Green Potion", "Blue Potion", "Fairy", "Fish", "Blue Fire", "Bug", "Poe", "Big Poe", "Lon Lon Milk", "Ruto's Letter"]
            try:
                idx = b_choices.index(cur)
                next_idx = (idx + 1) % len(b_choices)
                self.editor.bottle_vars[item_id].set(b_choices[next_idx])
            except ValueError:
                self.editor.bottle_vars[item_id].set("Empty Bottle")
            self.refresh_visuals()

        elif item_id == "child_trade":
            # Cycle through child trade items then masks
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

        else:
            s = self.inv_slots[item_id]
            for kh, (var, itm_name) in getattr(self.editor, "special_item_vars", {}).items():
                if s["name"].lower() in itm_name.lower():
                    var.set(not var.get())
                    self.refresh_visuals()
                    return

            ammo_k = s["ammo_key"]
            if ammo_k and ammo_k in getattr(self.editor, "ammo_vars", {}):
                var = self.editor.ammo_vars[ammo_k][0]
                cur = safe_int(var.get(), default=0)
                cap = self.get_ammo_capacity(ammo_k)
                if cap == 0:
                    var.set("0")
                else:
                    var.set("0" if cur > 0 else str(cap))
                self.refresh_visuals()

    def _on_bottle_right_click(self, event, item_id):
        m = tk.Menu(self, tearoff=0, bg=COLOR_PANEL_BG, fg=COLOR_TEXT, activebackground=COLOR_GOLD, activeforeground="#000")
        choices = ["(Not Acquired / Locked)", "Empty Bottle", "Red Potion", "Green Potion", "Blue Potion", "Fairy", "Fish", "Blue Fire", "Bug", "Poe", "Big Poe", "Lon Lon Milk", "Ruto's Letter"]
        for c in choices:
            m.add_command(label=c, command=lambda ch=c: (self.editor.bottle_vars[item_id].set(ch), self.refresh_visuals()))
        m.tk_popup(event.x_root, event.y_root)

    def _on_child_trade_right_click(self, event):
        m = tk.Menu(self, tearoff=0, bg=COLOR_PANEL_BG, fg=COLOR_TEXT, activebackground=COLOR_GOLD, activeforeground="#000")
        m.add_command(label="None", command=lambda: (self.editor.child_quest_var.set("None"), self.editor.active_mask_var.set("None"), self.refresh_visuals()))
        m.add_separator()
        m.add_command(label="Weird Egg", command=lambda: (self.editor.child_quest_var.set("Weird Egg"), self.editor.active_mask_var.set("None"), self.refresh_visuals()))
        m.add_command(label="Zelda's Letter", command=lambda: (self.editor.child_quest_var.set("Zelda's Letter"), self.editor.active_mask_var.set("None"), self.refresh_visuals()))
        m.add_separator()
        for mask_name in ["Keaton Mask", "Skull Mask", "Spooky Mask", "Bunny Hood", "Goron Mask", "Zora Mask", "Gerudo Mask", "Mask of Truth"]:
            m.add_command(label=mask_name, command=lambda mn=mask_name: (self.editor.child_quest_var.set("None"), self.editor.active_mask_var.set(mn), self.refresh_visuals()))
        m.tk_popup(event.x_root, event.y_root)

    # =========================================================================
    # SUBSCREEN 2: EQUIPMENT (3x3 Gear Grid, Boots Row & Child Masks Row)
    # =========================================================================
    def _build_equipment_subscreen(self):
        self.equip_frame = tk.Frame(self.content_frame, bg=COLOR_BG)

        box = tk.Frame(self.equip_frame, bg=COLOR_PANEL_BG, bd=2, relief="ridge", padx=14, pady=10)
        box.pack(fill="both", expand=True)

        tk.Label(box, text="EQUIPMENT - WEAPONS, SHIELDS, TUNICS, BOOTS & MASKS", font=("Segoe UI", 11, "bold"), fg=COLOR_GOLD, bg=COLOR_PANEL_BG).pack(pady=(0, 2))
        tk.Label(box, text="Left-click to own/unown • Right-click or double-click to equip • Badges indicate Child / Adult usability", font=("Segoe UI", 8), fg=COLOR_TEXT_MUTED, bg=COLOR_PANEL_BG).pack(pady=(0, 8))

        center_frame = tk.Frame(box, bg=COLOR_PANEL_BG)
        center_frame.pack(expand=True)

        self.gear_buttons = {}

        # 1. 3x3 Gear Grid: Swords (row 0), Shields (row 1), Tunics (row 2)
        grid_3x3_data = [
            # Row 0: Swords
            [("Kokiri Sword", "sword", "sword_kokiri.png", "Child", self.editor.owned_swords),
             ("Master Sword", "sword", "sword_master.png", "Adult", self.editor.owned_swords),
             ("Biggoron's Sword", "sword", "sword_biggoron.png", "Adult", self.editor.owned_swords)],
            # Row 1: Shields
            [("Deku Shield", "shield", "shield_deku.png", "Child", self.editor.owned_shields),
             ("Hylian Shield", "shield", "shield_hylian.png", "Child / Adult", self.editor.owned_shields),
             ("Mirror Shield", "shield", "shield_mirror.png", "Adult", self.editor.owned_shields)],
            # Row 2: Tunics
            [("Kokiri Tunic", "tunic", "tunic_kokiri.png", "Child / Adult", self.editor.owned_tunics),
             ("Goron Tunic", "tunic", "tunic_goron.png", "Adult", self.editor.owned_tunics),
             ("Zora Tunic", "tunic", "tunic_zora.png", "Adult", self.editor.owned_tunics)],
        ]

        g3_frame = tk.LabelFrame(center_frame, text="Weapons, Shields & Tunics (3x3 Gear Grid)", font=("Segoe UI", 9, "bold"), fg=COLOR_GOLD, bg=COLOR_PANEL_BG, padx=8, pady=4)
        g3_frame.pack(pady=4)

        for r_idx, row_items in enumerate(grid_3x3_data):
            for c_idx, (name, cat, hd_file, era, owned_dict) in enumerate(row_items):
                card = tk.Frame(g3_frame, bg=COLOR_SLOT_BG, bd=1, relief="ridge", width=180, height=48)
                card.grid(row=r_idx, column=c_idx, padx=5, pady=4)
                card.grid_propagate(False)

                canv = tk.Canvas(card, width=176, height=44, bg=COLOR_SLOT_BG, highlightthickness=0)
                canv.pack(fill="both", expand=True)

                self.gear_buttons[name] = {
                    "canvas": canv, "card": card, "category": cat,
                    "name": name, "hd_file": hd_file, "era": era, "owned_dict": owned_dict
                }

                canv.bind("<Button-1>", lambda e, n=name: self._on_gear_click(n))
                canv.bind("<Button-3>", lambda e, n=name: self._on_gear_equip(n))
                canv.bind("<Double-Button-1>", lambda e, n=name: self._on_gear_equip(n))
                canv.bind("<Enter>", lambda e, n=name, er=era: self.set_info(f"{n} — Usable by: {er} (Left-click own/unown, Right-click equip)"))
                canv.bind("<Leave>", lambda e: self.set_info("Equipment: Left-click to own/unown • Right-click or double-click to equip"))

        # 2. Boots Row (Kokiri Boots always owned, Iron Boots, Hover Boots)
        boots_data = [
            ("Kokiri Boots", "boots", "boots_kokiri.png", "Child / Adult", self.editor.owned_boots),
            ("Iron Boots", "boots", "boots_iron.png", "Adult", self.editor.owned_boots),
            ("Hover Boots", "boots", "boots_hover.png", "Adult", self.editor.owned_boots),
        ]

        b_frame = tk.LabelFrame(center_frame, text="Boots (Kokiri Boots Default / Always Owned)", font=("Segoe UI", 9, "bold"), fg=COLOR_GOLD, bg=COLOR_PANEL_BG, padx=8, pady=4)
        b_frame.pack(fill="x", pady=4)

        b_sub = tk.Frame(b_frame, bg=COLOR_PANEL_BG)
        b_sub.pack(anchor="center")

        for c_idx, (name, cat, hd_file, era, owned_dict) in enumerate(boots_data):
            card = tk.Frame(b_sub, bg=COLOR_SLOT_BG, bd=1, relief="ridge", width=180, height=48)
            card.grid(row=0, column=c_idx, padx=5, pady=2)
            card.grid_propagate(False)

            canv = tk.Canvas(card, width=176, height=44, bg=COLOR_SLOT_BG, highlightthickness=0)
            canv.pack(fill="both", expand=True)

            self.gear_buttons[name] = {
                "canvas": canv, "card": card, "category": cat,
                "name": name, "hd_file": hd_file, "era": era, "owned_dict": owned_dict
            }

            canv.bind("<Button-1>", lambda e, n=name: self._on_gear_click(n))
            canv.bind("<Button-3>", lambda e, n=name: self._on_gear_equip(n))
            canv.bind("<Double-Button-1>", lambda e, n=name: self._on_gear_equip(n))
            canv.bind("<Enter>", lambda e, n=name, er=era: self.set_info(f"{n} — Usable by: {er} (Left-click own/unown, Right-click equip)"))
            canv.bind("<Leave>", lambda e: self.set_info("Equipment: Left-click to own/unown • Right-click or double-click to equip"))

        # 3. Masks Row (Child Masks: Keaton, Skull, Spooky, Bunny, Goron, Zora, Gerudo, Mask of Truth)
        masks_data = [
            ("Keaton Mask", "mask_keaton.png"),
            ("Skull Mask", "mask_skull.png"),
            ("Spooky Mask", "mask_spooky.png"),
            ("Bunny Hood", "mask_bunny.png"),
            ("Goron Mask", "mask_goron.png"),
            ("Zora Mask", "mask_zora.png"),
            ("Gerudo Mask", "mask_gerudo.png"),
            ("Mask of Truth", "mask_truth.png"),
        ]

        m_frame = tk.LabelFrame(center_frame, text="Masks (Happy Mask Shop - Child Era)", font=("Segoe UI", 9, "bold"), fg=COLOR_GOLD, bg=COLOR_PANEL_BG, padx=8, pady=4)
        m_frame.pack(fill="x", pady=4)

        m_sub = tk.Frame(m_frame, bg=COLOR_PANEL_BG)
        m_sub.pack(anchor="center")

        self.mask_cards = {}
        for c_idx, (m_name, hd_file) in enumerate(masks_data):
            card = tk.Frame(m_sub, bg=COLOR_SLOT_BG, bd=1, relief="ridge", width=68, height=64)
            card.grid(row=0, column=c_idx, padx=4, pady=2)
            card.grid_propagate(False)

            canv = tk.Canvas(card, width=64, height=60, bg=COLOR_SLOT_BG, highlightthickness=0)
            canv.pack(fill="both", expand=True)

            self.mask_cards[m_name] = {"canvas": canv, "card": card, "hd_file": hd_file}

            canv.bind("<Button-1>", lambda e, mn=m_name: self._on_mask_click(mn))
            canv.bind("<Button-3>", lambda e, mn=m_name: self._on_mask_click(mn))
            canv.bind("<Enter>", lambda e, mn=m_name: self.set_info(f"{mn} — Era: Child (Click to equip/borrow)"))
            canv.bind("<Leave>", lambda e: self.set_info("Equipment: Left-click to own/unown • Right-click or double-click to equip"))

    def _render_equipment(self):
        # 1. Weapons, Shields, Tunics, Boots
        for name, g in self.gear_buttons.items():
            canv = g["canvas"]
            canv.delete("all")
            cat = g["category"]
            owned = g["owned_dict"].get(name, tk.BooleanVar(value=(name == "Kokiri Boots"))).get()
            if name == "Kokiri Boots":
                owned = True  # Kokiri boots are always owned
            is_equipped = (self.editor.equip_vars.get(cat, tk.StringVar()).get() == name)

            bg_col = "#1E293B" if owned else "#0F172A"
            bd_col = COLOR_EQUIPPED if is_equipped else (COLOR_GOLD if owned else COLOR_SLOT_BORDER)
            canv.create_rectangle(2, 2, 174, 42, fill=bg_col, outline=bd_col, width=2 if is_equipped else 1)

            photo = self.textures.get(g["hd_file"], size=(34, 34), dimmed=(not owned))
            if photo:
                canv.create_image(22, 22, image=photo)

            t_col = "#FFF" if owned else COLOR_TEXT_MUTED
            canv.create_text(44, 14, text=name, fill=t_col, font=("Segoe UI", 8, "bold" if owned else "normal"), anchor="w")

            # Era Badge (P_Era style)
            era_text = g["era"]
            badge_bg = "#1E3A8A" if era_text == "Adult" else ("#065F46" if era_text == "Child" else "#374151")
            canv.create_rectangle(44, 25, 44 + len(era_text)*6 + 10, 39, fill=badge_bg, outline="")
            canv.create_text(49, 32, text=era_text, fill="#E2E8F0", font=("Segoe UI", 6, "bold"), anchor="w")

            if is_equipped:
                canv.create_text(168, 22, text="EQUIPPED", fill=COLOR_EQUIPPED, font=("Segoe UI", 7, "bold"), anchor="e")

        # 2. Child Masks
        cur_mask = self.editor.active_mask_var.get() if hasattr(self.editor, "active_mask_var") else "None"
        for m_name, mc in self.mask_cards.items():
            canv = mc["canvas"]
            canv.delete("all")
            is_active = (cur_mask == m_name)

            canv.create_rectangle(2, 2, 62, 58, fill="#1E293B" if is_active else "#0F172A",
                                  outline=COLOR_EQUIPPED if is_active else COLOR_SLOT_BORDER,
                                  width=2 if is_active else 1)

            photo = self.textures.get(mc["hd_file"], size=(32, 32), dimmed=(not is_active))
            if photo:
                canv.create_image(32, 22, image=photo)

            canv.create_text(32, 46, text=m_name.split(" ")[0][:7], fill=COLOR_GOLD_LIGHT if is_active else COLOR_TEXT_MUTED, font=("Segoe UI", 6, "bold"))
            if is_active:
                canv.create_rectangle(4, 4, 18, 14, fill=COLOR_EQUIPPED, outline="")
                canv.create_text(11, 9, text="ON", fill="#000", font=("Segoe UI", 5, "bold"))

    def _on_gear_click(self, item_name):
        if item_name == "Kokiri Boots":
            # Kokiri boots are always owned; click equips them
            self._on_gear_equip(item_name)
            return
        g = self.gear_buttons[item_name]
        var = g["owned_dict"].get(item_name)
        if var:
            var.set(not var.get())
            if hasattr(self.editor, "_sync_equipped_options"):
                self.editor._sync_equipped_options()
            self.refresh_visuals()

    def _on_gear_equip(self, item_name):
        g = self.gear_buttons[item_name]
        cat = g["category"]
        var = g["owned_dict"].get(item_name)
        if var:
            var.set(True)
        if cat in self.editor.equip_vars:
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

    # =========================================================================
    # SUBSCREEN 3: COLLECTION (Ocarinas, Blessings, Counters, Upgrades, Bags,
    # Important Items panel & 13 Songs with Staff)
    # =========================================================================
    def _build_collection_subscreen(self):
        self.collection_frame = tk.Frame(self.content_frame, bg=COLOR_BG)

        box = tk.Frame(self.collection_frame, bg=COLOR_PANEL_BG, bd=2, relief="ridge", padx=12, pady=6)
        box.pack(fill="both", expand=True)

        tk.Label(box, text="COLLECTION - UPGRADES, ARTIFACTS, STONES, MEDALLIONS & SONGS", font=("Segoe UI", 11, "bold"), fg=COLOR_GOLD, bg=COLOR_PANEL_BG).pack(pady=(0, 2))

        # Top strip of groups: Ocarinas, Great Fairy Blessings, Counters, Upgrades, Bags
        top_groups = tk.Frame(box, bg=COLOR_PANEL_BG)
        top_groups.pack(fill="x", pady=(2, 6))

        # 1. Ocarinas group
        oc_box = tk.LabelFrame(top_groups, text="Ocarinas", font=("Segoe UI", 8, "bold"), fg=COLOR_GOLD, bg=COLOR_PANEL_BG, padx=4, pady=2)
        oc_box.pack(side="left", padx=3, fill="y")
        self.ocarina_canvases = {}
        for oc_id, oc_name, oc_hash, oc_file in [
            ("fairy", "Fairy Ocarina", 0xB7DF60F1, "item_ocarina_fairy.png"),
            ("time", "Ocarina of Time", 0x54E2A3D1, "item_ocarina_of_time.png")
        ]:
            c = tk.Canvas(oc_box, width=54, height=54, bg=COLOR_SLOT_BG, highlightthickness=0)
            c.pack(side="left", padx=2)
            self.ocarina_canvases[oc_id] = {"canvas": c, "name": oc_name, "hash": oc_hash, "file": oc_file}
            c.bind("<Button-1>", lambda e, h=oc_hash: self._toggle_special_item(h))
            c.bind("<Enter>", lambda e, n=oc_name: self.set_info(f"{n} (Click to toggle owned)"))
            c.bind("<Leave>", lambda e: self.set_info("Collection: Left-click to toggle story items & songs"))

        # 2. Great Fairy Blessings group
        gf_box = tk.LabelFrame(top_groups, text="Great Fairy", font=("Segoe UI", 8, "bold"), fg=COLOR_GOLD, bg=COLOR_PANEL_BG, padx=4, pady=2)
        gf_box.pack(side="left", padx=3, fill="y")
        self.blessing_canvases = {}
        for b_id, b_name, b_file in [
            ("magic", "Magic Meter", "spell_farores_wind.png"),
            ("double_magic", "Double Magic", "spell_dins_fire.png"),
            ("double_defense", "Double Defense", "heart_full_dd.png")
        ]:
            c = tk.Canvas(gf_box, width=54, height=54, bg=COLOR_SLOT_BG, highlightthickness=0)
            c.pack(side="left", padx=2)
            self.blessing_canvases[b_id] = {"canvas": c, "name": b_name, "file": b_file}
            c.bind("<Button-1>", lambda e, bid=b_id: self._on_blessing_click(bid))
            c.bind("<Enter>", lambda e, n=b_name: self.set_info(f"Great Fairy Blessing: {n} (Click to toggle)"))
            c.bind("<Leave>", lambda e: self.set_info("Collection: Left-click to toggle story items & songs"))

        # 3. Counters group (Skulltula Tokens + Pieces of Heart held 0-3)
        cnt_box = tk.LabelFrame(top_groups, text="Counters", font=("Segoe UI", 8, "bold"), fg=COLOR_GOLD, bg=COLOR_PANEL_BG, padx=4, pady=2)
        cnt_box.pack(side="left", padx=3, fill="y")

        # Skulltula token counter card
        tok_card = tk.Frame(cnt_box, bg=COLOR_SLOT_BG, bd=1, relief="ridge", width=92, height=54)
        tok_card.pack(side="left", padx=3)
        tok_card.pack_propagate(False)
        self.tok_canvas = tk.Canvas(tok_card, width=90, height=36, bg=COLOR_SLOT_BG, highlightthickness=0)
        self.tok_canvas.pack(fill="x")
        tok_bar = tk.Frame(tok_card, bg=COLOR_SLOT_BG)
        tok_bar.pack(fill="x")
        tk.Button(tok_bar, text="-", font=("Segoe UI", 6, "bold"), bg="#334155", fg=COLOR_TEXT, relief="flat", padx=2, command=lambda: self.change_quantity("tokens", -1)).pack(side="left", padx=1)
        tk.Button(tok_bar, text="+", font=("Segoe UI", 6, "bold"), bg="#334155", fg=COLOR_TEXT, relief="flat", padx=2, command=lambda: self.change_quantity("tokens", 1)).pack(side="left", padx=1)
        tk.Button(tok_bar, text="Max", font=("Segoe UI", 6), bg="#D97706", fg="#FFF", relief="flat", padx=2, command=lambda: self.set_quantity_max("tokens")).pack(side="left", padx=1)
        self.tok_canvas.bind("<Button-3>", lambda e: self._show_quantity_menu(e, "tokens"))
        self.tok_canvas.bind("<MouseWheel>", lambda e: self._handle_wheel(e, "tokens"))
        self.tok_canvas.bind("<Shift-MouseWheel>", lambda e: self._handle_wheel(e, "tokens"))
        self.tok_canvas.bind("<Enter>", lambda e: self.set_info("Gold Skulltula Tokens (0-100) — Use +/- buttons, mouse wheel, or right-click"))

        # Heart Piece held (0-3) counter card
        hp_card = tk.Frame(cnt_box, bg=COLOR_SLOT_BG, bd=1, relief="ridge", width=86, height=54)
        hp_card.pack(side="left", padx=3)
        hp_card.pack_propagate(False)
        self.hp_canvas = tk.Canvas(hp_card, width=84, height=36, bg=COLOR_SLOT_BG, highlightthickness=0)
        self.hp_canvas.pack(fill="x")
        hp_bar = tk.Frame(hp_card, bg=COLOR_SLOT_BG)
        hp_bar.pack(fill="x")
        tk.Button(hp_bar, text="-", font=("Segoe UI", 6, "bold"), bg="#334155", fg=COLOR_TEXT, relief="flat", padx=3, command=lambda: self.change_quantity("heart_pieces", -1)).pack(side="left", padx=1)
        tk.Button(hp_bar, text="+", font=("Segoe UI", 6, "bold"), bg="#334155", fg=COLOR_TEXT, relief="flat", padx=3, command=lambda: self.change_quantity("heart_pieces", 1)).pack(side="left", padx=1)
        self.hp_canvas.bind("<Button-3>", lambda e: self._show_quantity_menu(e, "heart_pieces"))
        self.hp_canvas.bind("<MouseWheel>", lambda e: self._handle_wheel(e, "heart_pieces"))
        self.hp_canvas.bind("<Enter>", lambda e: self.set_info("Pieces of Heart Held (0-3) — Use +/- buttons, mouse wheel, or right-click"))

        # 4. Upgrades group (Strength, Scale, Gerudo Card)
        upg_group = tk.LabelFrame(top_groups, text="Upgrades", font=("Segoe UI", 8, "bold"), fg=COLOR_GOLD, bg=COLOR_PANEL_BG, padx=4, pady=2)
        upg_group.pack(side="left", padx=3, fill="y")
        self.upgrade_canvases = {}
        for u_id, u_title in [("strength", "Strength"), ("scale", "Scale"), ("gerudo_card", "Gerudo Card")]:
            c = tk.Canvas(upg_group, width=56, height=54, bg=COLOR_SLOT_BG, highlightthickness=0)
            c.pack(side="left", padx=2)
            self.upgrade_canvases[u_id] = {"canvas": c, "title": u_title}
            c.bind("<Button-1>", lambda e, uid=u_id: self._on_upgrade_click(uid))
            c.bind("<Enter>", lambda e, t=u_title: self.set_info(f"Upgrade: {t} (Click to cycle tiers / toggle)"))
            c.bind("<Leave>", lambda e: self.set_info("Collection: Left-click to toggle story items & songs"))

        # 5. Bags & Capacities group
        bags_group = tk.LabelFrame(top_groups, text="Bags & Capacities", font=("Segoe UI", 8, "bold"), fg=COLOR_GOLD, bg=COLOR_PANEL_BG, padx=4, pady=2)
        bags_group.pack(side="left", padx=3, fill="y")
        self.bag_canvases = {}
        for b_id, b_title, b_file in [
            ("bomb_bag", "Bomb Bag", "bag_bomb.png"),
            ("quiver", "Quiver", "bag_quiver.png"),
            ("bullet_bag", "Seed Bag", "bag_bullet.png"),
            ("stick_bag", "Stick Bag", "item_deku_stick.png"),
            ("nut_bag", "Nut Bag", "item_deku_nut.png"),
            ("wallet", "Wallet", "wallet_giants.png"),
        ]:
            c = tk.Canvas(bags_group, width=54, height=54, bg=COLOR_SLOT_BG, highlightthickness=0)
            c.pack(side="left", padx=2)
            self.bag_canvases[b_id] = {"canvas": c, "title": b_title, "file": b_file}
            c.bind("<Button-1>", lambda e, bid=b_id: self._cycle_bag_tier(bid))
            c.bind("<Enter>", lambda e, t=b_title: self.set_info(f"Capacity Bag: {t} (Click to cycle capacity tiers)"))
            c.bind("<Leave>", lambda e: self.set_info("Collection: Left-click to toggle story items & songs"))

        # Bottom section: Two Panels side by side (Important Items & Song Book)
        bot_panels = tk.Frame(box, bg=COLOR_PANEL_BG)
        bot_panels.pack(fill="both", expand=True, pady=(2, 0))

        # PANEL A: "Important Items" (3 Stones + 6 Medallions, 9 entries like ImportantMenu_01)
        imp_box = tk.LabelFrame(bot_panels, text="Important Items (3 Stones & 6 Medallions)", font=("Segoe UI", 9, "bold"), fg=COLOR_GOLD, bg=COLOR_PANEL_BG, padx=8, pady=6)
        imp_box.pack(side="left", fill="both", padx=(0, 6))

        self.important_slots = {}
        # 9 entries
        imp_items_def = [
            ("Kokiri's Emerald", 0xCBD1E58C, "stone_kokiri_emerald.png", 0, 0),
            ("Goron's Ruby", 0x7D69AD47, "stone_goron_ruby.png", 0, 1),
            ("Zora's Sapphire", 0xB8E3BF45, "stone_zoras_sapphire.png", 0, 2),
            ("Light Medallion", 0x235C7D9A, "medallion_light.png", 1, 0),
            ("Forest Medallion", 0x692D57CB, "medallion_forest.png", 1, 1),
            ("Fire Medallion", 0x5CE254A6, "medallion_fire.png", 1, 2),
            ("Water Medallion", 0x0151A68F, "medallion_water.png", 2, 0),
            ("Shadow Medallion", 0x204D2063, "medallion_shadow.png", 2, 1),
            ("Spirit Medallion", 0x0C7A5FD0, "medallion_spirit.png", 2, 2),
        ]

        imp_grid = tk.Frame(imp_box, bg=COLOR_PANEL_BG)
        imp_grid.pack(side="top", anchor="n", pady=(4, 0))

        for name, kh, hd_file, r, c in imp_items_def:
            card = tk.Frame(imp_grid, bg=COLOR_SLOT_BG, bd=1, relief="ridge", width=80, height=76)
            card.grid(row=r, column=c, padx=4, pady=4)
            card.grid_propagate(False)

            canv = tk.Canvas(card, width=76, height=72, bg=COLOR_SLOT_BG, highlightthickness=0)
            canv.pack(fill="both", expand=True)

            self.important_slots[kh] = {"canvas": canv, "name": name, "file": hd_file, "hash": kh}
            canv.bind("<Button-1>", lambda e, h=kh: self._toggle_quest_item(h))
            canv.bind("<Enter>", lambda e, n=name: self.set_info(f"Important Item: {n} (Click to toggle acquired)"))
            canv.bind("<Leave>", lambda e: self.set_info("Collection: Left-click to toggle story items & songs"))

        # PANEL B: "Song Book" (13 songs on arc + parchment staff panel)
        song_box = tk.LabelFrame(bot_panels, text="Song Book (13 Songs - Hover to View Staff, Click to Learn)", font=("Segoe UI", 9, "bold"), fg=COLOR_GOLD, bg=COLOR_PANEL_BG, padx=8, pady=4)
        song_box.pack(side="left", fill="both", expand=True)

        # Arc canvas for the 13 song icons
        self.song_arc_canvas = tk.Canvas(song_box, height=260, bg=COLOR_PANEL_BG, highlightthickness=0)
        self.song_arc_canvas.pack(fill="x", pady=(0, 2))
        self.song_arc_canvas.bind("<Button-1>", self._on_song_arc_click)
        self.song_arc_canvas.bind("<Motion>", self._on_song_arc_motion)
        self.song_arc_canvas.bind("<Configure>", lambda e: self._render_song_arc())

        # Parchment 5-line staff panel underneath
        self.staff_canvas = tk.Canvas(song_box, height=180, bg=COLOR_PARCHMENT, bd=2, relief="ridge", highlightthickness=1, highlightbackground=COLOR_PARCHMENT_BORDER)
        self.staff_canvas.pack(fill="both", expand=True, pady=(2, 0))
        self.staff_canvas.bind("<Configure>", lambda e: self._render_staff_panel())

    # ------------------ Collection Callbacks ------------------
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
            if "None" in cur:
                self.editor.v_magic.set("Standard Magic Meter (24 MP)")
                if hasattr(self.editor, "v_magic_points"): self.editor.v_magic_points.set("24")
            else:
                self.editor.v_magic.set("None")
                if hasattr(self.editor, "v_magic_points"): self.editor.v_magic_points.set("0")
            if hasattr(self.editor, "_on_magic_level_change"): self.editor._on_magic_level_change()
        elif bid == "double_magic":
            cur = self.editor.v_magic.get() if hasattr(self.editor, "v_magic") else "None"
            if "Double" in cur:
                self.editor.v_magic.set("Standard Magic Meter (24 MP)")
                if hasattr(self.editor, "v_magic_points"): self.editor.v_magic_points.set("24")
            else:
                self.editor.v_magic.set("Double Magic Meter (48 MP)")
                if hasattr(self.editor, "v_magic_points"): self.editor.v_magic_points.set("48")
            if hasattr(self.editor, "_on_magic_level_change"): self.editor._on_magic_level_change()
        elif bid == "double_defense":
            val = not (self.editor.v_double_defense.get() if hasattr(self.editor, "v_double_defense") else False)
            if hasattr(self.editor, "v_double_defense"):
                self.editor.v_double_defense.set(val)
            self.dd_check_var.set(val)
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

    # ------------------ Collection Rendering ------------------
    def _render_collection(self):
        # 1. Ocarinas
        for oc_id, data in self.ocarina_canvases.items():
            canv = data["canvas"]
            canv.delete("all")
            kh = data["hash"]
            owned = self.editor.special_item_vars.get(kh, (tk.BooleanVar(value=False), ""))[0].get() if hasattr(self.editor, "special_item_vars") else False
            canv.create_rectangle(2, 2, 52, 52, fill="#1E293B" if owned else "#0F172A",
                                  outline=COLOR_GOLD if owned else COLOR_SLOT_BORDER, width=1.5 if owned else 1)
            photo = self.textures.get(data["file"], size=(34, 34), dimmed=(not owned))
            if photo:
                canv.create_image(27, 24, image=photo)
            canv.create_text(27, 44, text=data["name"].split(" ")[0], fill=COLOR_GOLD_LIGHT if owned else COLOR_TEXT_MUTED, font=("Segoe UI", 6, "bold"))

        # 2. Blessings
        m_str = self.editor.v_magic.get() if hasattr(self.editor, "v_magic") else "None"
        has_mag = ("Standard" in m_str or "Double" in m_str)
        has_dmag = ("Double" in m_str)
        has_dd = self.editor.v_double_defense.get() if hasattr(self.editor, "v_double_defense") else False

        bless_states = {"magic": has_mag, "double_magic": has_dmag, "double_defense": has_dd}
        for b_id, data in self.blessing_canvases.items():
            canv = data["canvas"]
            canv.delete("all")
            active = bless_states.get(b_id, False)
            canv.create_rectangle(2, 2, 52, 52, fill="#1E293B" if active else "#0F172A",
                                  outline=COLOR_GOLD if active else COLOR_SLOT_BORDER, width=1.5 if active else 1)
            photo = self.textures.get(data["file"], size=(34, 34), dimmed=(not active))
            if photo:
                canv.create_image(27, 24, image=photo)
            canv.create_text(27, 44, text=data["name"].split(" ")[0], fill=COLOR_GOLD_LIGHT if active else COLOR_TEXT_MUTED, font=("Segoe UI", 6, "bold"))

        # 3. Counters
        # Skulltulas
        tc = self.tok_canvas
        tc.delete("all")
        tokens = safe_int(self.editor.v_tokens.get() if hasattr(self.editor, "v_tokens") else 0, default=0)
        photo_sk = self.textures.get("token_skulltula.png", size=(22, 22), dimmed=(tokens == 0))
        if photo_sk:
            tc.create_image(18, 18, image=photo_sk)
        tc.create_text(54, 18, text=f"{tokens}/100", fill=COLOR_GOLD_LIGHT if tokens > 0 else COLOR_TEXT_MUTED, font=("Segoe UI", 9, "bold"))

        # Heart pieces
        hc = self.hp_canvas
        hc.delete("all")
        tot_hp = safe_int(self.editor.v_heart_pieces_total.get() if hasattr(self.editor, "v_heart_pieces_total") else 0, default=0)
        held = tot_hp % 4
        photo_hp = self.textures.get("heart_full.png", size=(20, 20), dimmed=(held == 0))
        if photo_hp:
            hc.create_image(16, 18, image=photo_hp)
        hc.create_text(52, 18, text=f"{held}/4 Held", fill=COLOR_RED_HEART if held > 0 else COLOR_TEXT_MUTED, font=("Segoe UI", 9, "bold"))

        # 4. Upgrades
        str_val = self.editor.equip_vars.get("strength", tk.StringVar()).get()
        str_icon = "gear_golden_gauntlets.png" if "Golden" in str_val else ("gear_silver_gauntlets.png" if "Silver" in str_val else ("gear_goron_bracelet.png" if "Bracelet" in str_val else "gear_goron_bracelet.png"))
        str_owned = (str_val != "None")

        sc_val = self.editor.equip_vars.get("scale", tk.StringVar()).get()
        sc_icon = "scale_golden.png" if "Golden" in sc_val else "scale_silver.png"
        sc_owned = ("Scale" in sc_val)

        card_owned = self.editor.special_item_vars.get(0xFEB4D56B, (tk.BooleanVar(value=False), ""))[0].get() if hasattr(self.editor, "special_item_vars") else False

        upg_data = [
            ("strength", str_icon, str_val.split(" ")[0], str_owned),
            ("scale", sc_icon, sc_val.split(" ")[0], sc_owned),
            ("gerudo_card", "item_gerudo_card.png", "Card", card_owned)
        ]
        for u_id, ic_file, short_txt, owned in upg_data:
            canv = self.upgrade_canvases[u_id]["canvas"]
            canv.delete("all")
            canv.create_rectangle(2, 2, 54, 52, fill="#1E293B" if owned else "#0F172A",
                                  outline=COLOR_GOLD if owned else COLOR_SLOT_BORDER, width=1.5 if owned else 1)
            photo = self.textures.get(ic_file, size=(32, 32), dimmed=(not owned))
            if photo:
                canv.create_image(28, 23, image=photo)
            canv.create_text(28, 44, text=short_txt, fill=COLOR_GOLD_LIGHT if owned else COLOR_TEXT_MUTED, font=("Segoe UI", 6, "bold"))

        # 5. Bags
        for b_id, data in self.bag_canvases.items():
            canv = data["canvas"]
            canv.delete("all")
            val = self.editor.equip_vars.get(b_id, tk.StringVar()).get()
            is_locked = ("Locked" in val or val == "None")
            canv.create_rectangle(2, 2, 52, 52, fill="#0F172A" if is_locked else "#1E293B",
                                  outline=COLOR_SLOT_BORDER if is_locked else COLOR_GOLD, width=1.5 if not is_locked else 1)
            photo = self.textures.get(data["file"], size=(32, 32), dimmed=is_locked)
            if photo:
                canv.create_image(27, 23, image=photo)
            # Short cap label (e.g. 50, 40, 30)
            cap_lbl = val.split("(")[-1].replace(")", "") if "(" in val else val[:5]
            canv.create_text(27, 44, text=cap_lbl, fill=COLOR_GOLD_LIGHT if not is_locked else COLOR_TEXT_MUTED, font=("Segoe UI", 6, "bold"))

        # 6. Important Items (3 Stones + 6 Medallions)
        for kh, data in self.important_slots.items():
            canv = data["canvas"]
            canv.delete("all")
            owned = self.editor.quest_vars.get(kh, tk.BooleanVar(value=False)).get() if hasattr(self.editor, "quest_vars") else False
            canv.create_rectangle(2, 2, 74, 70, fill="#1E293B" if owned else "#0F172A",
                                  outline=COLOR_GOLD if owned else COLOR_SLOT_BORDER, width=1.5 if owned else 1)
            photo = self.textures.get(data["file"], size=(40, 40), dimmed=(not owned))
            if photo:
                canv.create_image(38, 28, image=photo)
            canv.create_text(38, 58, text=data["name"].split(" ")[0], fill=COLOR_GOLD_LIGHT if owned else COLOR_TEXT_MUTED, font=("Segoe UI", 7, "bold"))

        # 7. Song Book Arc & Staff
        self._render_song_arc()
        self._render_staff_panel()

    # ------------------ Song Book (Arc & Staff) ------------------
    def _get_song_list(self):
        """Returns the 13 songs: 12 normal OoT songs + Scarecrow's Song."""
        from oot_save_editor import SONGS
        songs = []
        for sname, bit_idx, isget_h, event_h, sdesc in SONGS:
            learned = self.editor.song_vars.get(bit_idx, tk.BooleanVar(value=False)).get() if hasattr(self.editor, "song_vars") else False
            songs.append({
                "name": sname, "bit_idx": bit_idx, "learned": learned,
                "is_warp": (bit_idx >= 6), "desc": sdesc, "is_scarecrow": False
            })

        # 13th Song: Scarecrow's Song
        sc_state = self.editor.scarecrow_state_var.get() if hasattr(self.editor, "scarecrow_state_var") else "Not taught"
        sc_learned = (sc_state == "Learned")
        songs.append({
            "name": "Scarecrow's Song", "bit_idx": 12, "learned": sc_learned,
            "is_warp": False, "desc": f"State: {sc_state} — Summons Pierre to distant hookshot targets (Click to open editor)",
            "is_scarecrow": True
        })
        return songs

    def _render_song_arc(self, canvas_w=None, canvas_h=None):
        canv = self.song_arc_canvas
        canv.delete("all")
        songs = self._get_song_list()
        songs_by_name = {s["name"]: s for s in songs}

        w = canvas_w if canvas_w is not None else canv.winfo_width()
        h = canvas_h if canvas_h is not None else canv.winfo_height()
        if w <= 1:
            try:
                w = int(canv.cget("width"))
            except Exception:
                w = canv.winfo_reqwidth()
        if w <= 1:
            w = 900
        if h <= 1:
            try:
                h = int(canv.cget("height"))
            except Exception:
                h = canv.winfo_reqheight()
        if h <= 1:
            h = 260

        radius = 28
        positions = compute_song_arc_positions(w, h, radius=radius)
        self.song_hit_boxes = []

        for name, x, y, rad in positions:
            s = songs_by_name.get(name)
            if not s:
                continue
            self._draw_song_circle(canv, s, x, y, rad)
            self.song_hit_boxes.append((s, x, y, rad))

        # Selected song highlight: white ring
        for s, x, y, rad in self.song_hit_boxes:
            if s["name"] == self.selected_song_id:
                canv.create_oval(
                    x - rad - 3, y - rad - 3, x + rad + 3, y + rad + 3,
                    outline="#FFFFFF", width=2
                )
                break

    def _draw_song_circle(self, canv, s, x, y, rad):
        learned = s["learned"]
        is_sel = (s["name"] == self.selected_song_id)

        # Background circle & gold/dim outline
        bg_col = "#1E293B" if learned else "#0F172A"
        bd_col = COLOR_GOLD if learned else "#334155"
        canv.create_oval(
            x - rad, y - rad, x + rad, y + rad,
            fill=bg_col, outline=bd_col, width=2 if learned else 1
        )

        # Icon / Note representation
        if s["is_scarecrow"]:
            note_file = "note_purple.png"
        elif s["is_warp"]:
            note_file = "note_cyan.png"
        else:
            note_file = "note_gold.png"

        photo = self.textures.get(note_file, size=(rad * 2 - 8, rad * 2 - 8), dimmed=(not learned))
        if photo:
            canv.create_image(x, y, image=photo)
        else:
            canv.create_text(
                x, y, text="♪" if not s["is_scarecrow"] else "S",
                fill=COLOR_GOLD_LIGHT if learned else COLOR_TEXT_MUTED,
                font=("Segoe UI", 12, "bold")
            )

        # Short label under circle that never clips
        short_lbl = SONG_SHORT_NAMES.get(s["name"], s["name"])
        lbl_col = COLOR_GOLD_LIGHT if learned else COLOR_TEXT_MUTED
        canv.create_text(
            x, y + rad + 10, text=short_lbl,
            fill=lbl_col, font=("Segoe UI", 8, "bold")
        )

    def _on_song_arc_click(self, event):
        for s, x, y, rad in self.song_hit_boxes:
            dist = math.hypot(event.x - x, event.y - y)
            if dist <= rad:
                self.selected_song_id = s["name"]
                if s["is_scarecrow"]:
                    # Brief: "the Scarecrow entry shows its 8 notes and its state from the OOTSE-11 controls
                    # and clicking it switches the main editor to the Quest tab's Scarecrow panel"
                    if hasattr(self.editor, "switch_to_quest_tab_scarecrow"):
                        self.editor.switch_to_quest_tab_scarecrow()
                    elif hasattr(self.editor, "switch_to_standard_view"):
                        self.editor.switch_to_standard_view()
                        if hasattr(self.editor, "notebook"):
                            self.editor.notebook.select(2)
                else:
                    bit_idx = s["bit_idx"]
                    if hasattr(self.editor, "song_vars") and bit_idx in self.editor.song_vars:
                        var = self.editor.song_vars[bit_idx]
                        var.set(not var.get())
                self.refresh_visuals()
                return

    def _on_song_arc_motion(self, event):
        for s, x, y, rad in self.song_hit_boxes:
            dist = math.hypot(event.x - x, event.y - y)
            if dist <= rad:
                if self.selected_song_id != s["name"]:
                    self.selected_song_id = s["name"]
                    self._render_song_arc()
                    self._render_staff_panel()
                self.set_info(f"Song: {s['name']} — {s['desc']}")
                return

    def _render_staff_panel(self):
        """Draws authentic 5-line staff with note letters at their pitch height on parchment canvas."""
        canv = self.staff_canvas
        canv.delete("all")

        # Find selected song
        songs = self._get_song_list()
        selected_song = next((s for s in songs if s["name"] == self.selected_song_id), songs[0])

        w = canv.winfo_width()
        h = canv.winfo_height()
        if w <= 1:
            try:
                w = int(canv.cget("width"))
            except Exception:
                w = canv.winfo_reqwidth()
        if w <= 1:
            w = 900
        if h <= 1:
            try:
                h = int(canv.cget("height"))
            except Exception:
                h = canv.winfo_reqheight()
        if h <= 1:
            h = 180

        # Background parchment wash
        canv.create_rectangle(0, 0, w, h, fill=COLOR_PARCHMENT, outline="")

        # Title centered at the top
        canv.create_text(
            w / 2.0, 18,
            text=selected_song["name"],
            fill=COLOR_PARCHMENT_TEXT,
            font=("Segoe UI", 11, "bold"),
            anchor="center"
        )

        # 5-line musical staff across full width minus margins, vertically centered
        margin_x = max(36, int(w * 0.05))
        staff_start_x = margin_x
        staff_end_x = w - margin_x
        line_spacing = 13
        cy = h / 2.0
        staff_top_y = cy - 2 * line_spacing
        staff_bot_y = cy + 2 * line_spacing

        # Clef / Side bars
        canv.create_line(staff_start_x, staff_top_y - 4, staff_start_x, staff_bot_y + 4, fill=COLOR_PARCHMENT_LINE, width=2)
        canv.create_line(staff_end_x, staff_top_y - 4, staff_end_x, staff_bot_y + 4, fill=COLOR_PARCHMENT_LINE, width=2)

        for line_i in range(5):
            ly = staff_top_y + line_i * line_spacing
            canv.create_line(staff_start_x, ly, staff_end_x, ly, fill=COLOR_PARCHMENT_LINE, width=1.5)

        # Note pitches and buttons from oot_scarecrow
        is_scarecrow = selected_song["is_scarecrow"]
        note_values = []

        if is_scarecrow:
            sc_state = self.editor.scarecrow_state_var.get() if hasattr(self.editor, "scarecrow_state_var") else "Not taught"
            if hasattr(self.editor, "scarecrow_note_vars"):
                for v in self.editor.scarecrow_note_vars:
                    lbl = v.get()
                    p_val = oot_scarecrow.LABEL_TO_NOTE.get(lbl, 0)
                    note_values.append((p_val, lbl))
            else:
                note_values = [(0, "-")] * 8
            desc = f"Scarecrow's Song: State is '{sc_state}' — Summons Pierre to distant hookshot targets (Click to open editor)"
        else:
            p_list = oot_scarecrow.GAME_SONGS.get(selected_song["name"], [])
            for p_val in p_list:
                lbl = oot_scarecrow.note_label(p_val)
                note_values.append((p_val, lbl))
            desc = selected_song["desc"]

        num_notes = len(note_values)
        if num_notes > 0:
            pad_x = max(40, int(w * 0.06))
            note_span = (staff_end_x - staff_start_x) - 2 * pad_x
            step = note_span / (num_notes - 1) if num_notes > 1 else 0

            btn_colors = {
                "L": "#2563EB",  # Blue
                "R": "#DC2626",  # Red
                "A": "#059669",  # Emerald Green
                "Y": "#D97706",  # Amber/Yellow
                "X": "#7C3AED",  # Purple
            }

            for n_idx, (p_val, raw_lbl) in enumerate(note_values):
                nx = staff_start_x + pad_x + (n_idx * step if num_notes > 1 else note_span / 2.0)
                if p_val == 0 or raw_lbl == "-":
                    canv.create_text(nx, cy, text="—", fill="#78350F", font=("Segoe UI", 16, "bold"))
                    continue

                ny = compute_staff_note_y(p_val, staff_top_y, staff_bot_y)

                is_bent = (p_val not in oot_scarecrow.BUTTON_LABELS)
                btn_letter = oot_scarecrow.BUTTON_LABELS.get(p_val)
                if not btn_letter:
                    closest = min(oot_scarecrow.BUTTON_NOTES, key=lambda b: abs(b - p_val))
                    btn_letter = oot_scarecrow.BUTTON_LABELS.get(closest, "A")

                c_fill = btn_colors.get(btn_letter, "#059669")
                note_rad = 12
                canv.create_oval(
                    nx - note_rad, ny - note_rad, nx + note_rad, ny + note_rad,
                    fill=c_fill, outline="#1E293B", width=1.5
                )
                canv.create_text(nx, ny, text=btn_letter, fill="#FFFFFF", font=("Segoe UI", 9, "bold"))

                if is_bent:
                    canv.create_text(nx, ny - note_rad - 6, text="~", fill="#78350F", font=("Segoe UI", 11, "bold"))

        # One-line description under the staff
        canv.create_text(w / 2.0, h - 16, text=desc, fill=COLOR_PARCHMENT_TEXT, font=("Segoe UI", 9), anchor="center")

    # =========================================================================
    # REFRESH ALL VISUALS
    # =========================================================================
    def refresh_visuals(self):
        """Two-way synchronization refresh called after any change."""
        self._draw_hearts()
        self._draw_magic()

        # Rupees display
        if hasattr(self.editor, "v_rupees"):
            rupees = safe_int(self.editor.v_rupees.get(), default=0)
            wal_label = self.editor.equip_vars.get("wallet", tk.StringVar()).get()
            limit = 1000 if "1000" in wal_label else (500 if "500" in wal_label else 200)
            self.rupee_val_lbl.configure(text=str(rupees))
            self.rupee_max_lbl.configure(text=f" / {limit}")

            wal_icon = "wallet_giants.png" if limit == 1000 else "wallet_adults.png"
            photo_wal = self.textures.get(wal_icon, size=(24, 24))
            if photo_wal:
                self.rupee_icon_lbl.configure(image=photo_wal)

        self._render_inv_slots()
        self._render_equipment()
        self._render_collection()
