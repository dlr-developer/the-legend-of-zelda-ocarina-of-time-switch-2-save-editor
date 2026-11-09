"""
The Legend of Zelda: Ocarina of Time (Nintendo Switch 2 Remake) - In-Game Pause Menu Interactive UI
Uses authentic Switch 2 Remake HD assets from assets/switch2_ui and renders in-place inside the main window.
"""

import os
import math
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, ImageEnhance, ImageOps

SWITCH2_ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "switch2_ui")

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

class HDTextureManager:
    """Loads and caches Ultra HD Switch 2 Remake textures from assets/switch2_ui."""
    def __init__(self, base_dir=SWITCH2_ASSETS_DIR):
        self.base_dir = base_dir
        self.cache = {}

    def get(self, filename, size=(44, 44), dimmed=False):
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
            dim_alpha = ImageEnhance.Brightness(alpha).enhance(0.30)
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

        self._build_top_nav()
        self._build_hud()

        # Content container for the 3 pause subscreens
        self.content_frame = tk.Frame(self, bg=COLOR_BG)
        self.content_frame.pack(fill="both", expand=True, padx=8, pady=(2, 6))

        self._build_inventory_subscreen()
        self._build_equipment_subscreen()
        self._build_quest_subscreen()

        # Keyboard shortcuts (L / R triggers)
        self.bind("<Left>", lambda e: self.cycle_subscreen(-1))
        self.bind("<Right>", lambda e: self.cycle_subscreen(1))
        self.bind("<q>", lambda e: self.cycle_subscreen(-1))
        self.bind("<e>", lambda e: self.cycle_subscreen(1))

        self.show_subscreen(0)

    # =========================================================================
    # TOP NAVIGATION BAR (Return Button + Subscreen Tabs + Save Button)
    # =========================================================================
    def _build_top_nav(self):
        nav = tk.Frame(self, bg=COLOR_BG, pady=6)
        nav.pack(fill="x", padx=8)

        # 1. Prominent Return to Standard Editor Button
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
        titles = ["[L] ITEMS (INVENTORY)", "[ZL] EQUIPMENT", "[ZR] COLLECTION"]
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
        self.quest_frame.pack_forget()

        if idx == 0:
            self.inv_frame.pack(fill="both", expand=True)
        elif idx == 1:
            self.equip_frame.pack(fill="both", expand=True)
        elif idx == 2:
            self.quest_frame.pack(fill="both", expand=True)

        self.refresh_visuals()

    # =========================================================================
    # MODERN SWITCH 2 HUD (Hearts, Magic Gauge, Rupees, Gold Skulltulas)
    # =========================================================================
    def _build_hud(self):
        hud = tk.Frame(self, bg=COLOR_PANEL_BG, bd=1, relief="ridge", padx=12, pady=6)
        hud.pack(fill="x", padx=8, pady=(0, 4))

        # Hearts Box
        h_box = tk.Frame(hud, bg=COLOR_PANEL_BG)
        h_box.pack(side="left", padx=(0, 16))

        h_top = tk.Frame(h_box, bg=COLOR_PANEL_BG)
        h_top.pack(anchor="w")
        tk.Label(h_top, text="LIFE", font=("Segoe UI", 9, "bold"), fg=COLOR_RED_HEART, bg=COLOR_PANEL_BG).pack(side="left", padx=(0, 6))
        self.hp_label = tk.Label(h_top, text="9/9 Hearts", font=("Segoe UI", 8), fg=COLOR_TEXT_MUTED, bg=COLOR_PANEL_BG)
        self.hp_label.pack(side="left")

        self.hearts_canvas = tk.Canvas(h_box, width=230, height=44, bg=COLOR_PANEL_BG, highlightthickness=0)
        self.hearts_canvas.pack(anchor="w", pady=(1, 0))
        self.hearts_canvas.bind("<Button-1>", self._on_hearts_canvas_click)

        h_btns = tk.Frame(h_box, bg=COLOR_PANEL_BG)
        h_btns.pack(anchor="w", pady=(2, 0))
        tk.Button(h_btns, text="+ Heart", font=("Segoe UI", 7), bg="#334155", fg=COLOR_TEXT, relief="flat", padx=4, command=self._add_heart).pack(side="left", padx=(0, 2))
        tk.Button(h_btns, text="- Heart", font=("Segoe UI", 7), bg="#334155", fg=COLOR_TEXT, relief="flat", padx=4, command=self._sub_heart).pack(side="left", padx=2)
        tk.Button(h_btns, text="Full Heal", font=("Segoe UI", 7, "bold"), bg="#2563EB", fg="#FFF", relief="flat", padx=5, command=self._heal_link).pack(side="left", padx=2)

        self.dd_check_var = tk.BooleanVar(value=self.editor.v_double_defense.get())
        tk.Checkbutton(
            h_btns, text="Double Defense (White Frame)", font=("Segoe UI", 7),
            variable=self.dd_check_var, bg=COLOR_PANEL_BG, fg=COLOR_TEXT, selectcolor=COLOR_PANEL_BG,
            activebackground=COLOR_PANEL_BG, command=self._toggle_double_defense
        ).pack(side="left", padx=(6, 0))

        # Magic Meter Box
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

        # Rupees Box
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

        # Skulltulas Box
        sk_box = tk.Frame(hud, bg=COLOR_PANEL_BG)
        sk_box.pack(side="left", padx=16, fill="y")
        tk.Label(sk_box, text="SKULLTULAS", font=("Segoe UI", 9, "bold"), fg=COLOR_GOLD_LIGHT, bg=COLOR_PANEL_BG).pack(anchor="w")

        sk_disp = tk.Frame(sk_box, bg=COLOR_PANEL_BG)
        sk_disp.pack(anchor="w", pady=(2, 0))
        self.token_icon_lbl = tk.Label(sk_disp, bg=COLOR_PANEL_BG)
        self.token_icon_lbl.pack(side="left", padx=(0, 4))
        self.token_val_lbl = tk.Label(sk_disp, text="0", font=("Segoe UI", 12, "bold"), fg="#FFF", bg=COLOR_PANEL_BG)
        self.token_val_lbl.pack(side="left")
        tk.Label(sk_disp, text=" / 100 Tokens", font=("Segoe UI", 9), fg=COLOR_TEXT_MUTED, bg=COLOR_PANEL_BG).pack(side="left")

        sk_btns = tk.Frame(sk_box, bg=COLOR_PANEL_BG)
        sk_btns.pack(anchor="w", pady=(2, 0))
        tk.Button(sk_btns, text="Max (100)", font=("Segoe UI", 7, "bold"), bg="#D97706", fg="#FFF", relief="flat", padx=4, command=self._max_skulltulas).pack(side="left")
        tk.Button(sk_btns, text="+5", font=("Segoe UI", 7), bg="#334155", fg=COLOR_TEXT, relief="flat", padx=4, command=lambda: self._add_tokens(5)).pack(side="left", padx=2)
        tk.Button(sk_btns, text="-5", font=("Segoe UI", 7), bg="#334155", fg=COLOR_TEXT, relief="flat", padx=4, command=lambda: self._add_tokens(-5)).pack(side="left", padx=2)

    # ------------------ HUD Callbacks ------------------
    def _draw_hearts(self):
        canv = self.hearts_canvas
        canv.delete("all")

        total_hearts = int(self.editor.v_hearts.get() or 3)
        current_hp = int(self.editor.v_hp.get() or 12)
        dd = self.editor.v_double_defense.get()

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
            canv.create_rectangle(x, y, x+heart_size, y+heart_size, fill="#1E293B", outline=border_col, width=1.5 if dd else 1)

            if fill_q > 0:
                h_pct = fill_q / 4.0
                fill_h = int(heart_size * h_pct)
                canv.create_rectangle(x+1, y + heart_size - fill_h, x+heart_size-1, y+heart_size-1, fill=COLOR_RED_HEART, outline="")

            canv.create_text(x + heart_size//2, y + heart_size//2, text=str(i+1), fill="#94A3B8" if fill_q == 0 else "#FFFFFF", font=("Segoe UI", 6))

        hp_str = f"{current_hp/4:.2f}/{total_hearts} Hearts"
        self.hp_label.configure(text=hp_str)

    def _draw_magic(self):
        canv = self.magic_canvas
        canv.delete("all")

        m_str = self.editor.v_magic.get()
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
            cur_mp = int(self.editor.v_magic_points.get() or 0)
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
        total = int(self.editor.v_hearts.get() or 3)
        if 0 <= idx < total:
            new_hp = (idx + 1) * 4
            self.editor.v_hp.set(str(new_hp))
            self.editor._on_hp_change()
            self._draw_hearts()

    def _add_heart(self):
        cur = int(self.editor.v_hearts.get() or 3)
        if cur < 20:
            self.editor.v_hearts.set(str(cur + 1))
            self.editor._on_total_hearts_change()
            self.refresh_visuals()

    def _sub_heart(self):
        cur = int(self.editor.v_hearts.get() or 3)
        if cur > 3:
            self.editor.v_hearts.set(str(cur - 1))
            self.editor._on_total_hearts_change()
            self.refresh_visuals()

    def _heal_link(self):
        self.editor.heal_link()
        self._draw_hearts()

    def _toggle_double_defense(self):
        val = self.dd_check_var.get()
        self.editor.v_double_defense.set(val)
        self._draw_hearts()

    def _cycle_magic(self):
        cur = self.editor.v_magic.get()
        if "None" in cur:
            self.editor.v_magic.set("Standard Magic Meter (24 MP)")
        elif "Standard" in cur:
            self.editor.v_magic.set("Double Magic Meter (48 MP)")
        else:
            self.editor.v_magic.set("None")
        self.editor._on_magic_level_change()
        self._draw_magic()

    def _refill_magic(self):
        self.editor.refill_magic()
        self._draw_magic()

    def _on_magic_canvas_click(self, event):
        m_str = self.editor.v_magic.get()
        max_mp = 48 if "Double" in m_str else (24 if "Standard" in m_str else 0)
        if max_mp > 0:
            pct = max(0.0, min(1.0, (event.x - 3) / 164.0))
            new_mp = int(max_mp * pct)
            self.editor.v_magic_points.set(str(new_mp))
            self.editor._on_mp_change()
            self._draw_magic()

    def _max_rupees(self):
        self.editor._max_rupees_to_wallet()
        self.refresh_visuals()

    def _add_rupees(self, amount):
        cur = int(self.editor.v_rupees.get() or 0)
        wal_label = self.editor.equip_vars["wallet"].get()
        limit = 1000 if "1000" in wal_label else (500 if "500" in wal_label else 200)
        new_val = max(0, min(limit, cur + amount))
        self.editor.v_rupees.set(str(new_val))
        self.refresh_visuals()

    def _max_skulltulas(self):
        self.editor.v_tokens.set("100")
        self.refresh_visuals()

    def _add_tokens(self, amount):
        cur = int(self.editor.v_tokens.get() or 0)
        new_val = max(0, min(100, cur + amount))
        self.editor.v_tokens.set(str(new_val))
        self.refresh_visuals()

    # =========================================================================
    # SUBSCREEN 1: ITEMS (Switch 2 Remake Active Inventory with 5 Bottles)
    # =========================================================================
    def _build_inventory_subscreen(self):
        self.inv_frame = tk.Frame(self.content_frame, bg=COLOR_BG)

        box = tk.Frame(self.inv_frame, bg=COLOR_PANEL_BG, bd=2, relief="ridge", padx=12, pady=8)
        box.pack(fill="both", expand=True)

        tk.Label(box, text="SELECT ITEM - SWITCH 2 REMAKE INVENTORY & 5 BOTTLES", font=("Segoe UI", 11, "bold"), fg=COLOR_GOLD, bg=COLOR_PANEL_BG).pack(pady=(0, 4))
        tk.Label(box, text="Click to toggle item / Right-click to adjust ammo or cycle bottle contents", font=("Segoe UI", 8), fg=COLOR_TEXT_MUTED, bg=COLOR_PANEL_BG).pack(pady=(0, 6))

        grid_frame = tk.Frame(box, bg=COLOR_PANEL_BG)
        grid_frame.pack(expand=True)

        self.inv_slots = {}
        # 4x6 Matrix mapped to Switch 2 Remake HD assets
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

        for r, c, item_id, name, base_hd, ammo_k in self.matrix_defs:
            slot_card = tk.Frame(grid_frame, bg=COLOR_SLOT_BG, bd=1, relief="ridge", width=74, height=74)
            slot_card.grid(row=r, column=c, padx=5, pady=5)
            slot_card.grid_propagate(False)

            canv = tk.Canvas(slot_card, width=70, height=70, bg=COLOR_SLOT_BG, highlightthickness=0)
            canv.pack(fill="both", expand=True)

            self.inv_slots[item_id] = {
                "canvas": canv, "card": slot_card, "name": name,
                "base_hd": base_hd, "ammo_key": ammo_k, "row": r, "col": c
            }

            canv.bind("<Button-1>", lambda e, i=item_id: self._on_inv_slot_click(i))
            canv.bind("<Button-3>", lambda e, i=item_id: self._on_inv_slot_right_click(i))

    def _render_inv_slots(self):
        for item_id, s in self.inv_slots.items():
            canv = s["canvas"]
            canv.delete("all")
            name = s["name"]
            ammo_k = s["ammo_key"]

            owned = False
            hd_file = s["base_hd"]
            sub_text = ""

            if item_id == "hookshot":
                hs_val = self.editor.hookshot_var.get()
                if hs_val == "Longshot":
                    owned = True
                    hd_file = "item_longshot.png"
                    sub_text = "Longshot"
                elif hs_val == "Hookshot":
                    owned = True
                    hd_file = "item_hookshot.png"
                    sub_text = "Hookshot"
                else:
                    owned = False
                    hd_file = "item_hookshot.png"
                    sub_text = "Locked"

            elif item_id == "ocarina":
                has_oot = self.editor.special_item_vars.get(0x589146FF, (tk.BooleanVar(value=False), ""))[0].get()
                has_fairy = self.editor.special_item_vars.get(0x2213F934, (tk.BooleanVar(value=False), ""))[0].get()
                if has_oot:
                    owned = True
                    hd_file = "item_ocarina_of_time.png"
                    sub_text = "Time"
                elif has_fairy:
                    owned = True
                    hd_file = "item_ocarina_of_time.png"
                    sub_text = "Fairy"
                else:
                    owned = False
                    hd_file = "item_ocarina_of_time.png"
                    sub_text = "Locked"

            elif item_id.startswith("bottle_"):
                b_name = self.editor.bottle_vars[item_id].get()
                if b_name == "(Not Acquired / Locked)":
                    owned = False
                    hd_file = "bottle_empty.png"
                    sub_text = "Locked"
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
                    sub_text = b_name.split(" ")[0]

            elif item_id == "child_trade":
                cq = self.editor.child_quest_var.get()
                if cq == "Weird Egg":
                    owned = True
                    hd_file = "item_weird_egg.png"
                    sub_text = "Egg"
                elif cq == "Chicken":
                    owned = True
                    hd_file = "item_cucco.png"
                    sub_text = "Cucco"
                elif cq == "Zelda's Letter":
                    owned = True
                    hd_file = "bottle_rutos_letter.png"
                    sub_text = "Letter"
                else:
                    m_val = self.editor.active_mask_var.get()
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
                        sub_text = m_val.split(" ")[0]
                    else:
                        owned = False
                        hd_file = "item_weird_egg.png"
                        sub_text = "None"

            else:
                for kh, (var, itm_name) in self.editor.special_item_vars.items():
                    if name.lower() in itm_name.lower():
                        owned = var.get()
                        break
                if not owned and ammo_k and ammo_k in self.editor.ammo_vars:
                    v_cnt = int(self.editor.ammo_vars[ammo_k][0].get() or 0)
                    owned = (v_cnt > 0)

            # Modern Chamfered Slot Background
            canv.create_rectangle(2, 2, 68, 68, fill="#0F172A" if not owned else "#1E293B", outline="#334155" if not owned else COLOR_GOLD, width=1.5 if owned else 1)

            photo = self.textures.get(hd_file, size=(48, 48), dimmed=(not owned))
            canv.create_image(35, 30, image=photo)

            if ammo_k and ammo_k in self.editor.ammo_vars and owned:
                cnt = self.editor.ammo_vars[ammo_k][0].get()
                canv.create_text(64, 62, text=str(cnt), fill=COLOR_GOLD_LIGHT, font=("Segoe UI", 9, "bold"), anchor="se")
            elif sub_text:
                canv.create_text(35, 60, text=sub_text[:8], fill=COLOR_TEXT_MUTED if not owned else COLOR_GOLD_LIGHT, font=("Segoe UI", 7, "bold"))

    def _on_inv_slot_click(self, item_id):
        if item_id == "hookshot":
            cur = self.editor.hookshot_var.get()
            if cur == "None": self.editor.hookshot_var.set("Hookshot")
            elif cur == "Hookshot": self.editor.hookshot_var.set("Longshot")
            else: self.editor.hookshot_var.set("None")
            self.refresh_visuals()

        elif item_id == "ocarina":
            oot_var = self.editor.special_item_vars[0x589146FF][0]
            fairy_var = self.editor.special_item_vars[0x2213F934][0]
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
            b_choices = self.editor.bottle_combos[int(item_id[-1])-1]["values"]
            try:
                idx = b_choices.index(cur)
                next_idx = (idx + 1) % len(b_choices)
                self.editor.bottle_vars[item_id].set(b_choices[next_idx])
            except ValueError:
                self.editor.bottle_vars[item_id].set("Empty Bottle")
            self.refresh_visuals()

        elif item_id == "child_trade":
            cur_mask = self.editor.active_mask_var.get()
            masks = ["None", "Bunny Hood", "Keaton Mask", "Skull Mask", "Spooky Mask", "Goron Mask", "Zora Mask", "Gerudo Mask", "Mask of Truth"]
            try:
                n_idx = (masks.index(cur_mask) + 1) % len(masks)
                self.editor.active_mask_var.set(masks[n_idx])
            except ValueError:
                self.editor.active_mask_var.set("Bunny Hood")
            self.refresh_visuals()

        else:
            s = self.inv_slots[item_id]
            for kh, (var, itm_name) in self.editor.special_item_vars.items():
                if s["name"].lower() in itm_name.lower():
                    var.set(not var.get())
                    self.refresh_visuals()
                    return

            ammo_k = s["ammo_key"]
            if ammo_k and ammo_k in self.editor.ammo_vars:
                var, max_val, sb, st = self.editor.ammo_vars[ammo_k]
                cur = int(var.get() or 0)
                if cur == 0:
                    var.set(str(max_val))
                else:
                    var.set("0")
                self.refresh_visuals()

    def _on_inv_slot_right_click(self, item_id):
        s = self.inv_slots[item_id]
        ammo_k = s["ammo_key"]
        if ammo_k and ammo_k in self.editor.ammo_vars:
            var, max_val, sb, st = self.editor.ammo_vars[ammo_k]
            var.set(str(max_val))
            self.refresh_visuals()
        elif item_id.startswith("bottle_"):
            self.editor.bottle_vars[item_id].set("Red Potion (Full Recovery)")
            self.refresh_visuals()

    # =========================================================================
    # SUBSCREEN 2: EQUIPMENT (Weapons, Armor & Upgrades)
    # =========================================================================
    def _build_equipment_subscreen(self):
        self.equip_frame = tk.Frame(self.content_frame, bg=COLOR_BG)

        box = tk.Frame(self.equip_frame, bg=COLOR_PANEL_BG, bd=2, relief="ridge", padx=14, pady=8)
        box.pack(fill="both", expand=True)

        tk.Label(box, text="EQUIPMENT - WEAPONS, SHIELDS, TUNICS & BOOTS", font=("Segoe UI", 11, "bold"), fg=COLOR_GOLD, bg=COLOR_PANEL_BG).pack(pady=(0, 4))

        gear_grid = tk.Frame(box, bg=COLOR_PANEL_BG)
        gear_grid.pack(pady=4)

        self.gear_buttons = {}

        cols_data = [
            ("SWORDS", "sword", [
                ("Kokiri Sword", "sword_kokiri.png"),
                ("Master Sword", "sword_master.png"),
                ("Biggoron's Sword", "sword_biggoron.png")
            ], self.editor.owned_swords),

            ("SHIELDS", "shield", [
                ("Deku Shield", "shield_deku.png"),
                ("Hylian Shield", "shield_hylian.png"),
                ("Mirror Shield", "shield_mirror.png")
            ], self.editor.owned_shields),

            ("TUNICS", "tunic", [
                ("Kokiri Tunic", "tunic_kokiri.png"),
                ("Goron Tunic", "tunic_goron.png"),
                ("Zora Tunic", "tunic_zora.png")
            ], self.editor.owned_tunics),

            ("BOOTS", "boots", [
                ("Kokiri Boots", "boots_kokiri.png"),
                ("Iron Boots", "boots_iron.png"),
                ("Hover Boots", "boots_hover.png")
            ], self.editor.owned_boots),
        ]

        for col_idx, (title, category, items, owned_dict) in enumerate(cols_data):
            col_f = tk.Frame(gear_grid, bg=COLOR_PANEL_BG, padx=8)
            col_f.grid(row=0, column=col_idx, sticky="n")

            tk.Label(col_f, text=title, font=("Segoe UI", 9, "bold"), fg=COLOR_GOLD_LIGHT, bg=COLOR_PANEL_BG).pack(pady=(0, 4))

            for item_name, hd_file in items:
                card = tk.Frame(col_f, bg=COLOR_SLOT_BG, bd=1, relief="ridge", width=170, height=48)
                card.pack(pady=3)
                card.pack_propagate(False)

                canv = tk.Canvas(card, width=166, height=44, bg=COLOR_SLOT_BG, highlightthickness=0)
                canv.pack(fill="both", expand=True)

                self.gear_buttons[item_name] = {
                    "canvas": canv, "card": card, "category": category,
                    "name": item_name, "hd_file": hd_file, "owned_dict": owned_dict
                }

                canv.bind("<Button-1>", lambda e, n=item_name: self._on_gear_click(n))
                canv.bind("<Button-3>", lambda e, n=item_name: self._on_gear_equip(n))
                canv.bind("<Double-Button-1>", lambda e, n=item_name: self._on_gear_equip(n))

        upg_box = tk.LabelFrame(box, text="Upgrades & Capacities (Click to Cycle Tiers)", font=("Segoe UI", 9, "bold"), fg=COLOR_GOLD, bg=COLOR_PANEL_BG, padx=8, pady=6)
        upg_box.pack(fill="x", pady=(10, 0))

        self.upg_badge_canvas = tk.Canvas(upg_box, height=58, bg=COLOR_PANEL_BG, highlightthickness=0)
        self.upg_badge_canvas.pack(fill="x", expand=True)
        self.upg_badge_canvas.bind("<Button-1>", self._on_upgrades_canvas_click)

    def _render_equipment(self):
        for name, g in self.gear_buttons.items():
            canv = g["canvas"]
            canv.delete("all")
            cat = g["category"]
            owned = g["owned_dict"].get(name, tk.BooleanVar(value=False)).get()
            is_equipped = (self.editor.equip_vars[cat].get() == name)

            bg_col = "#1E293B" if owned else "#0F172A"
            bd_col = COLOR_EQUIPPED if is_equipped else (COLOR_GOLD if owned else "#334155")
            canv.create_rectangle(2, 2, 164, 42, fill=bg_col, outline=bd_col, width=2 if is_equipped else 1)

            photo = self.textures.get(g["hd_file"], size=(36, 36), dimmed=(not owned))
            canv.create_image(24, 22, image=photo)

            t_col = "#FFF" if owned else COLOR_TEXT_MUTED
            canv.create_text(48, 16, text=name, fill=t_col, font=("Segoe UI", 8, "bold" if owned else "normal"), anchor="w")

            if is_equipped:
                canv.create_text(48, 30, text="[EQUIPPED]", fill=COLOR_EQUIPPED, font=("Segoe UI", 7, "bold"), anchor="w")
            else:
                canv.create_text(48, 30, text="Click to Own / Right: Equip", fill="#64748B", font=("Segoe UI", 6), anchor="w")

        self._render_upgrade_badges()

    def _render_upgrade_badges(self):
        canv = self.upg_badge_canvas
        canv.delete("all")

        str_val = self.editor.equip_vars["strength"].get()
        str_icon = "gear_golden_gauntlets.png" if "Golden" in str_val else ("gear_silver_gauntlets.png" if "Silver" in str_val else "gear_goron_bracelet.png")

        sc_val = self.editor.equip_vars["scale"].get()
        sc_icon = "scale_golden.png" if "Golden" in sc_val else "scale_silver.png"

        wal_val = self.editor.equip_vars["wallet"].get()
        wal_icon = "wallet_giants.png" if "Giant" in wal_val else ("wallet_tycoons.png" if "1000" in wal_val else "wallet_adults.png")

        q_val = self.editor.equip_vars["quiver"].get()
        q_icon = "bag_quiver.png"

        bb_val = self.editor.equip_vars["bomb_bag"].get()
        bb_icon = "bag_bomb.png"

        badges = [
            ("strength", str_val, str_icon),
            ("scale", sc_val, sc_icon),
            ("wallet", wal_val, wal_icon),
            ("quiver", q_val, q_icon),
            ("bomb_bag", bb_val, bb_icon)
        ]

        for idx, (b_key, b_label, icon_rel) in enumerate(badges):
            x = idx * 165 + 15
            photo = self.textures.get(icon_rel, size=(38, 38), dimmed=False)
            canv.create_image(x + 20, 29, image=photo)
            canv.create_text(x + 46, 22, text=b_key.replace("_", " ").title(), fill=COLOR_GOLD_LIGHT, font=("Segoe UI", 8, "bold"), anchor="w")
            canv.create_text(x + 46, 36, text=b_label.split(" (")[0][:14], fill=COLOR_TEXT_MUTED, font=("Segoe UI", 7), anchor="w")

    def _on_gear_click(self, item_name):
        g = self.gear_buttons[item_name]
        var = g["owned_dict"].get(item_name)
        if var:
            var.set(not var.get())
            self.editor._sync_equipped_options()
            self.refresh_visuals()

    def _on_gear_equip(self, item_name):
        g = self.gear_buttons[item_name]
        cat = g["category"]
        var = g["owned_dict"].get(item_name)
        if var:
            var.set(True)
        self.editor.equip_vars[cat].set(item_name)
        self.editor._sync_equipped_options()
        self.refresh_visuals()

    def _on_upgrades_canvas_click(self, event):
        idx = (event.x - 15) // 165
        keys = ["strength", "scale", "wallet", "quiver", "bomb_bag"]
        if 0 <= idx < len(keys):
            k = keys[idx]
            from oot_save_editor import UPGRADE_CHOICES
            choices = UPGRADE_CHOICES.get(k, [])
            cur = self.editor.equip_vars[k].get()
            try:
                c_idx = choices.index(cur)
                n_idx = (c_idx + 1) % len(choices)
                self.editor.equip_vars[k].set(choices[n_idx])
            except ValueError:
                if choices: self.editor.equip_vars[k].set(choices[0])
            self.refresh_visuals()

    # =========================================================================
    # SUBSCREEN 3: COLLECTION (Sage Medallions, Spiritual Stones & 12 Songs)
    # =========================================================================
    def _build_quest_subscreen(self):
        self.quest_frame = tk.Frame(self.content_frame, bg=COLOR_BG)

        box = tk.Frame(self.quest_frame, bg=COLOR_PANEL_BG, bd=2, relief="ridge", padx=14, pady=8)
        box.pack(fill="both", expand=True)

        tk.Label(box, text="COLLECTION - SAGE MEDALLIONS, STONES & 12 SONGS", font=("Segoe UI", 11, "bold"), fg=COLOR_GOLD, bg=COLOR_PANEL_BG).pack(pady=(0, 4))

        mid_frame = tk.Frame(box, bg=COLOR_PANEL_BG)
        mid_frame.pack(fill="both", expand=True)

        self.celestial_canvas = tk.Canvas(mid_frame, width=320, height=300, bg="#0F172A", highlightthickness=1, highlightbackground="#1E293B")
        self.celestial_canvas.pack(side="left", padx=(0, 14), pady=2)
        self.celestial_canvas.bind("<Button-1>", self._on_celestial_canvas_click)

        songs_box = tk.Frame(mid_frame, bg=COLOR_PANEL_BG)
        songs_box.pack(side="left", fill="both", expand=True)

        tk.Label(songs_box, text="Ocarina Songs (Click to Learn/Unlearn)", font=("Segoe UI", 9, "bold"), fg=COLOR_GOLD_LIGHT, bg=COLOR_PANEL_BG).pack(anchor="w", pady=(0, 4))

        self.songs_canvas = tk.Canvas(songs_box, width=440, height=260, bg="#0F172A", highlightthickness=1, highlightbackground="#1E293B")
        self.songs_canvas.pack(fill="both", expand=True)
        self.songs_canvas.bind("<Button-1>", self._on_songs_canvas_click)

        bot_q = tk.Frame(box, bg=COLOR_PANEL_BG)
        bot_q.pack(fill="x", pady=(6, 0))
        tk.Button(bot_q, text="Learn All 12 Songs", font=("Segoe UI", 8, "bold"), bg="#2563EB", fg="#FFF", relief="flat", padx=8, command=self._learn_all_songs).pack(side="left")
        tk.Button(bot_q, text="Max Dungeon Small Keys", font=("Segoe UI", 8), bg="#334155", fg=COLOR_TEXT, relief="flat", padx=8, command=self._max_dungeon_keys).pack(side="left", padx=8)

    def _render_quest_status(self):
        self._render_celestial_wheel()
        self._render_songs()

    def _render_celestial_wheel(self):
        canv = self.celestial_canvas
        canv.delete("all")

        cx, cy = 160, 140
        # Golden Triforce in Center
        canv.create_polygon(cx, cy-40, cx-35, cy+20, cx+35, cy+20, fill="#232211", outline="#E5C158", width=2)
        canv.create_polygon(cx, cy+20, cx-18, cy-10, cx+18, cy-10, fill="#0F172A", outline="#E5C158")

        # Heart Piece in Center of Triforce
        held_pieces = int(self.editor.v_heart_pieces_total.get() or 0) % 4
        canv.create_oval(cx-14, cy-10, cx+14, cy+18, fill="#1E293B", outline="#475569")
        if held_pieces > 0:
            canv.create_arc(cx-14, cy-10, cx+14, cy+18, start=90, extent=-(held_pieces*90), fill=COLOR_RED_HEART, outline="")
        canv.create_text(cx, cy+28, text=f"{held_pieces}/4 Pieces", fill=COLOR_GOLD_LIGHT, font=("Segoe UI", 7, "bold"))

        # 6 SAGE MEDALLIONS (Switch 2 Remake HD Assets)
        medallion_defs = [
            ("Light", 3419530636, "medallion_light.png", 0),
            ("Forest", 365691062, "medallion_forest.png", 60),
            ("Fire", 102604812, "medallion_fire.png", 120),
            ("Water", 2174697980, "medallion_water.png", 180),
            ("Shadow", 2983818817, "medallion_shadow.png", 240),
            ("Spirit", 3804824368, "medallion_spirit.png", 300)
        ]

        self.celestial_hits = []
        for name, kh, hd_file, deg in medallion_defs:
            rad = math.radians(deg - 90)
            mx = cx + int(92 * math.cos(rad))
            my = cy + int(92 * math.sin(rad))

            owned = self.editor.quest_vars.get(kh, tk.BooleanVar(value=False)).get()
            photo = self.textures.get(hd_file, size=(38, 38), dimmed=(not owned))

            canv.create_oval(mx-20, my-20, mx+20, my+20, fill="#1E293B", outline=COLOR_GOLD if owned else "#334155", width=1.5 if owned else 1)
            canv.create_image(mx, my, image=photo)
            self.celestial_hits.append(("medallion", kh, mx, my, 20))

        # 3 SPIRITUAL STONES (Switch 2 Remake HD Assets)
        stones_defs = [
            ("Emerald", 400473950, "stone_kokiri_emerald.png", cx - 55, cy + 100),
            ("Ruby", 2469600129, "stone_goron_ruby.png", cx, cy + 100),
            ("Sapphire", 1928096277, "stone_zoras_sapphire.png", cx + 55, cy + 100),
        ]

        for name, kh, hd_file, sx, sy in stones_defs:
            owned = self.editor.quest_vars.get(kh, tk.BooleanVar(value=False)).get()
            photo = self.textures.get(hd_file, size=(34, 34), dimmed=(not owned))
            canv.create_oval(sx-18, sy-18, sx+18, sy+18, fill="#1E293B", outline=COLOR_GOLD if owned else "#334155", width=1.5 if owned else 1)
            canv.create_image(sx, sy, image=photo)
            self.celestial_hits.append(("stone", kh, sx, sy, 18))

    def _render_songs(self):
        canv = self.songs_canvas
        canv.delete("all")

        from oot_save_editor import SONGS

        self.song_hits = []
        for idx, (sname, bit_idx, isget_h, event_h, _) in enumerate(SONGS):
            is_warp = (idx >= 6)
            col = idx % 6
            row = 0 if not is_warp else 1
            x = col * 70 + 40
            y = row * 110 + 45

            learned = self.editor.song_vars.get(bit_idx, tk.BooleanVar(value=False)).get()

            canv.create_line(x-28, y+2, x+28, y+2, fill="#334155")
            canv.create_line(x-28, y-4, x+28, y-4, fill="#334155")
            canv.create_line(x-28, y+8, x+28, y+8, fill="#334155")

            note_asset = "note_cyan.png" if is_warp else "note_gold.png"
            photo = self.textures.get(note_asset, size=(32, 32), dimmed=(not learned))
            canv.create_image(x, y, image=photo)

            short_name = sname.replace("Song of ", "").replace(" of ", " ")
            canv.create_text(x, y+24, text=short_name[:10], fill=COLOR_GOLD_LIGHT if learned else COLOR_TEXT_MUTED, font=("Segoe UI", 7, "bold" if learned else "normal"))

            self.song_hits.append((bit_idx, x, y, 22))

    def _on_celestial_canvas_click(self, event):
        for kind, kh, x, y, rad in self.celestial_hits:
            dist = math.hypot(event.x - x, event.y - y)
            if dist <= rad:
                var = self.editor.quest_vars.get(kh)
                if var:
                    var.set(not var.get())
                    self.refresh_visuals()
                return

    def _on_songs_canvas_click(self, event):
        for bit_idx, x, y, rad in self.song_hits:
            dist = math.hypot(event.x - x, event.y - y)
            if dist <= rad:
                var = self.editor.song_vars.get(bit_idx)
                if var:
                    var.set(not var.get())
                    self.refresh_visuals()
                return

    def _learn_all_songs(self):
        self.editor.learn_all_songs()
        self.refresh_visuals()

    def _max_dungeon_keys(self):
        self.editor.max_keys()
        self.refresh_visuals()

    def _on_save_clicked(self):
        self.editor.save()
        self.refresh_visuals()

    def refresh_visuals(self):
        self._draw_hearts()
        self._draw_magic()

        rupees = self.editor.v_rupees.get()
        wal_label = self.editor.equip_vars["wallet"].get()
        limit = 1000 if "1000" in wal_label else (500 if "500" in wal_label else 200)
        self.rupee_val_lbl.configure(text=str(rupees))
        self.rupee_max_lbl.configure(text=f" / {limit}")

        wal_icon = "wallet_giants.png" if limit == 1000 else "wallet_adults.png"
        self.rupee_icon_lbl.configure(image=self.textures.get(wal_icon, size=(24, 24)))

        tokens = self.editor.v_tokens.get()
        self.token_val_lbl.configure(text=str(tokens))
        self.token_icon_lbl.configure(image=self.textures.get("token_skulltula.png", size=(20, 20)))

        self._render_inv_slots()
        self._render_equipment()
        self._render_quest_status()
