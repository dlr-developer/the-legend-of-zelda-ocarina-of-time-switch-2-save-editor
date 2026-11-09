"""
The Legend of Zelda: Ocarina of Time (Switch 2) - In-Game Pause Menu Interactive UI
Provides an authentic in-game interactive pause screen interface with full two-way
synchronization with the main save editor.
"""

import os
import math
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, ImageEnhance, ImageOps

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "ui")

# Colors matching authentic N64 / Switch pause screens
COLOR_BG = "#0B0E14"            # Deep obsidian pause background
COLOR_PANEL_BG = "#131822"      # Subscreen slate panel background
COLOR_SLOT_BG = "#1A202C"       # Recessed slot background
COLOR_SLOT_BORDER = "#2D3748"   # Slot border
COLOR_GOLD = "#D4AF37"          # Zelda golden text/trim
COLOR_GOLD_LIGHT = "#F6E05E"    # Bright yellow/gold highlight
COLOR_GREEN_MAGIC = "#38A169"   # Magic meter green
COLOR_RED_HEART = "#E53E3E"     # Life heart red
COLOR_BLUE_HUD = "#3182CE"      # Blue accents
COLOR_TEXT = "#E2E8F0"          # Primary text
COLOR_TEXT_MUTED = "#A0AEC0"    # Muted text
COLOR_EQUIPPED = "#48BB78"      # Equipped badge green

class IconManager:
    """Loads and caches authentic OoT sprites, providing normal and dimmed variants."""
    def __init__(self, base_dir=ASSETS_DIR):
        self.base_dir = base_dir
        self.cache = {}
        self.dim_cache = {}

    def get(self, rel_path, size=(40, 40), dimmed=False):
        key = (rel_path, size, dimmed)
        if key in self.cache:
            return self.cache[key]

        full_path = os.path.join(self.base_dir, rel_path)
        if not os.path.exists(full_path):
            # Fallback placeholder if asset missing
            img = Image.new("RGBA", size, (40, 40, 60, 200))
        else:
            try:
                img = Image.open(full_path).convert("RGBA")
                img = img.resize(size, Image.Resampling.LANCZOS)
            except Exception:
                img = Image.new("RGBA", size, (40, 40, 60, 200))

        if dimmed:
            # Create darkened/ghosted version: desaturate and drop brightness to 30%
            alpha = img.split()[-1]
            gray = ImageOps.grayscale(img).convert("RGBA")
            enhancer = ImageEnhance.Brightness(gray)
            dim_img = enhancer.enhance(0.35)
            # Faint transparency
            dim_alpha = ImageEnhance.Brightness(alpha).enhance(0.45)
            dim_img.putalpha(dim_alpha)
            photo = ImageTk.PhotoImage(dim_img)
        else:
            photo = ImageTk.PhotoImage(img)

        self.cache[key] = photo
        return photo


class OOTPauseMenuWindow(tk.Toplevel):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        self.title("The Legend of Zelda: Ocarina of Time — In-Game Pause Menu")
        self.geometry("900x730")
        self.minsize(860, 680)
        self.configure(bg=COLOR_BG)

        self.icons = IconManager()
        self.active_subscreen = 0  # 0: Item Inventory, 1: Equipment, 2: Quest Status

        # Ensure slot is loaded
        if not self.editor.active_slot:
            messagebox.showwarning("No Save Loaded", "Please select and load a save slot in the main editor first.", parent=self)
            self.destroy()
            return

        self._build_header()
        self._build_hud()
        
        # Subscreens container
        self.content_frame = tk.Frame(self, bg=COLOR_BG)
        self.content_frame.pack(fill="both", expand=True, padx=12, pady=(4, 8))

        self._build_inventory_subscreen()
        self._build_equipment_subscreen()
        self._build_quest_subscreen()

        self._build_footer()

        # Keyboard shortcuts (L / R triggers)
        self.bind("<Left>", lambda e: self.cycle_subscreen(-1))
        self.bind("<Right>", lambda e: self.cycle_subscreen(1))
        self.bind("<q>", lambda e: self.cycle_subscreen(-1))
        self.bind("<e>", lambda e: self.cycle_subscreen(1))
        self.bind("<Q>", lambda e: self.cycle_subscreen(-1))
        self.bind("<E>", lambda e: self.cycle_subscreen(1))

        self.show_subscreen(0)
        self.refresh_all_visuals()

    # =========================================================================
    # HEADER & SUBSCREEN NAVIGATION (L / R)
    # =========================================================================
    def _build_header(self):
        hdr = tk.Frame(self, bg=COLOR_BG, pady=6)
        hdr.pack(fill="x", padx=12)

        # L button
        l_btn = tk.Button(
            hdr, text="◀ L (Q)", font=("Segoe UI", 9, "bold"), bg="#1A202C", fg=COLOR_GOLD_LIGHT,
            activebackground=COLOR_GOLD, activeforeground="#000", relief="flat", padx=10, pady=3,
            command=lambda: self.cycle_subscreen(-1)
        )
        l_btn.pack(side="left")

        # Subscreen Tabs
        tab_box = tk.Frame(hdr, bg=COLOR_BG)
        tab_box.pack(side="left", expand=True)

        self.subscreen_btns = []
        titles = ["SELECT ITEM", "EQUIPMENT", "QUEST STATUS"]
        for idx, t in enumerate(titles):
            btn = tk.Button(
                tab_box, text=f"  {t}  ", font=("Segoe UI", 10, "bold"),
                bg="#1A202C", fg=COLOR_TEXT_MUTED, activebackground=COLOR_GOLD,
                activeforeground="#000", relief="flat", padx=14, pady=3,
                command=lambda i=idx: self.show_subscreen(i)
            )
            btn.pack(side="left", padx=4)
            self.subscreen_btns.append(btn)

        # R button
        r_btn = tk.Button(
            hdr, text="R (E) ▶", font=("Segoe UI", 9, "bold"), bg="#1A202C", fg=COLOR_GOLD_LIGHT,
            activebackground=COLOR_GOLD, activeforeground="#000", relief="flat", padx=10, pady=3,
            command=lambda: self.cycle_subscreen(1)
        )
        r_btn.pack(side="right")

    def cycle_subscreen(self, delta):
        new_idx = (self.active_subscreen + delta) % 3
        self.show_subscreen(new_idx)

    def show_subscreen(self, idx):
        self.active_subscreen = idx
        for i, b in enumerate(self.subscreen_btns):
            if i == idx:
                b.configure(bg=COLOR_GOLD, fg="#000")
            else:
                b.configure(bg="#1A202C", fg=COLOR_TEXT_MUTED)

        self.inv_frame.pack_forget()
        self.equip_frame.pack_forget()
        self.quest_frame.pack_forget()

        if idx == 0:
            self.inv_frame.pack(fill="both", expand=True)
        elif idx == 1:
            self.equip_frame.pack(fill="both", expand=True)
        elif idx == 2:
            self.quest_frame.pack(fill="both", expand=True)

    # =========================================================================
    # HUD: HEARTS, MAGIC METER & RUPEES
    # =========================================================================
    def _build_hud(self):
        hud = tk.Frame(self, bg=COLOR_PANEL_BG, bd=1, relief="ridge", padx=10, pady=6)
        hud.pack(fill="x", padx=12, pady=(0, 4))

        # --- LEFT: Life Energy (Hearts) ---
        hearts_box = tk.Frame(hud, bg=COLOR_PANEL_BG)
        hearts_box.pack(side="left", padx=(0, 16))

        h_top_row = tk.Frame(hearts_box, bg=COLOR_PANEL_BG)
        h_top_row.pack(anchor="w")
        tk.Label(h_top_row, text="LIFE", font=("Segoe UI", 9, "bold"), fg=COLOR_RED_HEART, bg=COLOR_PANEL_BG).pack(side="left", padx=(0, 6))
        self.hp_label = tk.Label(h_top_row, text="9 / 9 Hearts (36/36 HP)", font=("Segoe UI", 8), fg=COLOR_TEXT_MUTED, bg=COLOR_PANEL_BG)
        self.hp_label.pack(side="left")

        # Hearts Canvas: 2 rows of 10 hearts
        self.hearts_canvas = tk.Canvas(hearts_box, width=220, height=44, bg=COLOR_PANEL_BG, highlightthickness=0)
        self.hearts_canvas.pack(anchor="w", pady=(2, 0))
        self.hearts_canvas.bind("<Button-1>", self._on_hearts_canvas_click)

        # Heart Action buttons
        h_btn_row = tk.Frame(hearts_box, bg=COLOR_PANEL_BG)
        h_btn_row.pack(anchor="w", pady=(2, 0))
        tk.Button(h_btn_row, text="+ Heart", font=("Segoe UI", 7), bg="#2D3748", fg=COLOR_TEXT, relief="flat", padx=4, command=self._add_heart).pack(side="left", padx=(0, 2))
        tk.Button(h_btn_row, text="- Heart", font=("Segoe UI", 7), bg="#2D3748", fg=COLOR_TEXT, relief="flat", padx=4, command=self._sub_heart).pack(side="left", padx=2)
        tk.Button(h_btn_row, text="Full Heal", font=("Segoe UI", 7, "bold"), bg="#2B6CB0", fg="#FFF", relief="flat", padx=4, command=self._heal_link).pack(side="left", padx=2)

        self.dd_check_var = tk.BooleanVar(value=self.editor.v_double_defense.get())
        dd_cb = tk.Checkbutton(
            h_btn_row, text="Double Defense (White Outline)", font=("Segoe UI", 7),
            variable=self.dd_check_var, bg=COLOR_PANEL_BG, fg=COLOR_TEXT, selectcolor=COLOR_PANEL_BG,
            activebackground=COLOR_PANEL_BG, command=self._toggle_double_defense
        )
        dd_cb.pack(side="left", padx=(6, 0))

        # --- CENTER: Magic Meter ---
        magic_box = tk.Frame(hud, bg=COLOR_PANEL_BG)
        magic_box.pack(side="left", padx=12, fill="y")

        m_top = tk.Frame(magic_box, bg=COLOR_PANEL_BG)
        m_top.pack(anchor="w")
        tk.Label(m_top, text="MAGIC", font=("Segoe UI", 9, "bold"), fg=COLOR_GREEN_MAGIC, bg=COLOR_PANEL_BG).pack(side="left", padx=(0, 6))
        self.magic_label = tk.Label(m_top, text="Standard (24/24 MP)", font=("Segoe UI", 8), fg=COLOR_TEXT_MUTED, bg=COLOR_PANEL_BG)
        self.magic_label.pack(side="left")

        # Magic Gauge Bar
        self.magic_canvas = tk.Canvas(magic_box, width=180, height=18, bg="#0E121A", bd=1, relief="sunken", highlightthickness=0)
        self.magic_canvas.pack(anchor="w", pady=4)
        self.magic_canvas.bind("<Button-1>", self._on_magic_canvas_click)

        m_btn_row = tk.Frame(magic_box, bg=COLOR_PANEL_BG)
        m_btn_row.pack(anchor="w")
        tk.Button(m_btn_row, text="Cycle Meter", font=("Segoe UI", 7), bg="#2D3748", fg=COLOR_TEXT, relief="flat", padx=4, command=self._cycle_magic_meter).pack(side="left", padx=(0, 2))
        tk.Button(m_btn_row, text="Refill Magic", font=("Segoe UI", 7, "bold"), bg="#276749", fg="#FFF", relief="flat", padx=4, command=self._refill_magic).pack(side="left", padx=2)

        # --- RIGHT: Rupees & Skulltula Tokens ---
        wealth_box = tk.Frame(hud, bg=COLOR_PANEL_BG)
        wealth_box.pack(side="right", padx=(8, 0))

        # Rupee row
        r_row = tk.Frame(wealth_box, bg=COLOR_PANEL_BG)
        r_row.pack(anchor="e", pady=1)
        self.rupee_icon_lbl = tk.Label(r_row, bg=COLOR_PANEL_BG)
        self.rupee_icon_lbl.pack(side="left", padx=(0, 4))
        self.rupee_val_lbl = tk.Label(r_row, text="430", font=("Segoe UI", 12, "bold"), fg=COLOR_GOLD_LIGHT, bg=COLOR_PANEL_BG)
        self.rupee_val_lbl.pack(side="left")
        self.rupee_max_lbl = tk.Label(r_row, text=" / 500", font=("Segoe UI", 9), fg=COLOR_TEXT_MUTED, bg=COLOR_PANEL_BG)
        self.rupee_max_lbl.pack(side="left", padx=(0, 6))
        tk.Button(r_row, text="Max", font=("Segoe UI", 7), bg="#2D3748", fg=COLOR_TEXT, relief="flat", padx=4, command=self._max_rupees).pack(side="left")

        # Skulltula row
        tok_row = tk.Frame(wealth_box, bg=COLOR_PANEL_BG)
        tok_row.pack(anchor="e", pady=1)
        self.token_icon_lbl = tk.Label(tok_row, bg=COLOR_PANEL_BG)
        self.token_icon_lbl.pack(side="left", padx=(0, 4))
        self.token_val_lbl = tk.Label(tok_row, text="35", font=("Segoe UI", 11, "bold"), fg="#ECC94B", bg=COLOR_PANEL_BG)
        self.token_val_lbl.pack(side="left")
        tk.Label(tok_row, text=" / 100 Tokens", font=("Segoe UI", 9), fg=COLOR_TEXT_MUTED, bg=COLOR_PANEL_BG).pack(side="left", padx=(0, 6))
        tk.Button(tok_row, text="+5", font=("Segoe UI", 7), bg="#2D3748", fg=COLOR_TEXT, relief="flat", padx=4, command=lambda: self._add_tokens(5)).pack(side="left", padx=(0, 2))
        tk.Button(tok_row, text="100", font=("Segoe UI", 7), bg="#2D3748", fg=COLOR_TEXT, relief="flat", padx=4, command=lambda: self._set_tokens(100)).pack(side="left")

    def _draw_hearts(self):
        self.hearts_canvas.delete("all")
        tot_hearts = int(self.editor.v_hearts.get() or 3)
        cur_quarters = int(self.editor.v_hp.get() or (tot_hearts * 4))
        has_dd = self.editor.v_double_defense.get()

        for i in range(20):
            r = i // 10
            c = i % 10
            x = c * 21 + 10
            y = r * 20 + 10

            if i < tot_hearts:
                # Quarters for this heart: 0 to 4
                q_for_this = max(0, min(4, cur_quarters - i * 4))

                # Double Defense border if active
                if has_dd:
                    self.hearts_canvas.create_oval(x-9, y-8, x+9, y+8, outline="#FFFFFF", width=2)

                # Background container outline
                self.hearts_canvas.create_polygon(
                    x, y+8, x-8, y-1, x-8, y-6, x-3, y-8, x, y-5, x+3, y-8, x+8, y-6, x+8, y-1,
                    fill="#4A1515", outline="#742A2A"
                )

                # Fill heart according to quarters
                if q_for_this > 0:
                    fill_col = "#E53E3E" if q_for_this == 4 else ("#DD6B20" if q_for_this >= 2 else "#C53030")
                    # Draw scaled heart
                    scale = q_for_this / 4.0
                    sx = int(7 * scale)
                    sy = int(7 * scale)
                    self.hearts_canvas.create_polygon(
                        x, y+sy, x-sx, y-1, x-sx, y-sy, x-2, y-sy-1, x, y-sy+2, x+2, y-sy-1, x+sx, y-sy, x+sx, y-1,
                        fill=fill_col, outline=""
                    )
            else:
                # Empty unearned slot
                self.hearts_canvas.create_oval(x-4, y-4, x+4, y+4, outline="#2D3748", fill="#1A202C")

        self.hp_label.configure(text=f"{cur_quarters // 4}.{cur_quarters % 4} / {tot_hearts} Hearts ({cur_quarters}/{tot_hearts*4} HP)")

    def _draw_magic(self):
        self.magic_canvas.delete("all")
        m_str = self.editor.v_magic.get()
        if "Double" in m_str:
            max_mp = 48
            tier_text = "Double Meter (48 MP)"
        elif "Standard" in m_str:
            max_mp = 24
            tier_text = "Standard Meter (24 MP)"
        else:
            max_mp = 0
            tier_text = "None (0 MP)"

        cur_mp = float(self.editor.v_magic_points.get() or 0)
        cur_mp = max(0.0, min(float(max_mp), cur_mp))

        if max_mp > 0:
            pct = cur_mp / max_mp
            fill_w = int(180 * pct)
            self.magic_canvas.create_rectangle(0, 0, fill_w, 18, fill="#38A169", outline="")
            self.magic_canvas.create_rectangle(0, 0, 180, 18, fill="", outline="#48BB78", width=1)
            self.magic_canvas.create_text(90, 9, text=f"{int(cur_mp)} / {max_mp} MP", fill="#FFFFFF", font=("Segoe UI", 8, "bold"))
        else:
            self.magic_canvas.create_text(90, 9, text="No Magic Meter", fill=COLOR_TEXT_MUTED, font=("Segoe UI", 8))

        self.magic_label.configure(text=tier_text)

    def _on_hearts_canvas_click(self, event):
        tot_hearts = int(self.editor.v_hearts.get() or 3)
        # Identify which heart was clicked
        c = event.x // 21
        r = event.y // 20
        idx = r * 10 + c
        if idx < tot_hearts:
            # Set HP up to that heart
            new_hp = (idx + 1) * 4
            self.editor.v_hp.set(str(new_hp))
            self.editor._on_hp_change()
            self._draw_hearts()

    def _add_heart(self):
        tot = int(self.editor.v_hearts.get() or 3)
        if tot < 20:
            self.editor.v_hearts.set(str(tot + 1))
            self.editor._on_total_hearts_change()
            self.refresh_all_visuals()

    def _sub_heart(self):
        tot = int(self.editor.v_hearts.get() or 3)
        if tot > 3:
            self.editor.v_hearts.set(str(tot - 1))
            self.editor._on_total_hearts_change()
            self.refresh_all_visuals()

    def _heal_link(self):
        self.editor.heal_link()
        self.refresh_all_visuals()

    def _toggle_double_defense(self):
        self.editor.v_double_defense.set(self.dd_check_var.get())
        self._draw_hearts()

    def _on_magic_canvas_click(self, event):
        m_str = self.editor.v_magic.get()
        max_mp = 48 if "Double" in m_str else (24 if "Standard" in m_str else 0)
        if max_mp > 0:
            pct = max(0.0, min(1.0, event.x / 180.0))
            new_val = int(round(pct * max_mp))
            self.editor.v_magic_points.set(str(new_val))
            self.editor._on_mp_change()
            self._draw_magic()

    def _cycle_magic_meter(self):
        cur = self.editor.v_magic.get()
        if "None" in cur:
            self.editor.v_magic.set("Standard Magic Meter (24 MP)")
            self.editor.v_magic_points.set("24")
        elif "Standard" in cur:
            self.editor.v_magic.set("Double Magic Meter (48 MP)")
            self.editor.v_magic_points.set("48")
        else:
            self.editor.v_magic.set("None (No Magic Meter)")
            self.editor.v_magic_points.set("0")
        self.editor._on_magic_level_change()
        self.refresh_all_visuals()

    def _refill_magic(self):
        self.editor.refill_magic()
        self.refresh_all_visuals()

    def _max_rupees(self):
        self.editor._max_rupees_to_wallet()
        self.refresh_all_visuals()

    def _add_tokens(self, delta):
        cur = int(self.editor.v_tokens.get() or 0)
        self.editor.v_tokens.set(str(min(100, cur + delta)))
        self.refresh_all_visuals()

    def _set_tokens(self, val):
        self.editor.v_tokens.set(str(val))
        self.refresh_all_visuals()

    # =========================================================================
    # SUBSCREEN 1: ITEM INVENTORY (4×6 Grid)
    # =========================================================================
    def _build_inventory_subscreen(self):
        self.inv_frame = tk.Frame(self.content_frame, bg=COLOR_BG)

        # Main parchment/stone background box
        box = tk.Frame(self.inv_frame, bg=COLOR_PANEL_BG, bd=2, relief="ridge", padx=14, pady=10)
        box.pack(fill="both", expand=True)

        tk.Label(box, text="SELECT ITEM (INVENTORY)", font=("Segoe UI", 11, "bold"), fg=COLOR_GOLD, bg=COLOR_PANEL_BG).pack(pady=(0, 6))

        grid_frame = tk.Frame(box, bg=COLOR_PANEL_BG)
        grid_frame.pack(expand=True)

        self.inv_slots = {}
        # Define 4x6 Item Matrix
        # Row 0
        # (row, col, id, name, icon_getter, toggle_handler, ammo_key)
        self.matrix_defs = [
            # Row 0
            (0, 0, "sticks", "Deku Sticks", "items/deku_sticks/deku_sticks.png", "sticks"),
            (0, 1, "nuts", "Deku Nuts", "items/deku_nuts/deku_nuts.png", "nuts"),
            (0, 2, "bombs", "Bombs", "items/bombs/bombs.png", "bombs"),
            (0, 3, "bow", "Fairy Bow", "items/fairy_bow/fairy_bow.png", "arrows"),
            (0, 4, "fire_arrows", "Fire Arrow", "items/fire_arrows/fire_arrows.png", None),
            (0, 5, "dins_fire", "Din's Fire", "items/dins_fire/dins_fire.png", None),

            # Row 1
            (1, 0, "slingshot", "Fairy Slingshot", "items/fairy_slingshot/fairy_slingshot.png", "seeds"),
            (1, 1, "ocarina", "Ocarina of Time", "items/ocarina/ocarina_of_time.png", None),
            (1, 2, "bombchus", "Bombchus", "items/bombchus/bombchus.png", "bombchus"),
            (1, 3, "hookshot", "Hookshot Upgrade", "items/hookshot/hookshot.png", None),
            (1, 4, "ice_arrows", "Ice Arrow", "items/ice_arrows/ice_arrows.png", None),
            (1, 5, "farores_wind", "Farore's Wind", "items/farores_wind/farores_wind.png", None),

            # Row 2
            (2, 0, "boomerang", "Boomerang", "items/boomerang/boomerang.png", None),
            (2, 1, "lens_of_truth", "Lens of Truth", "items/lens_of_truth/lens_of_truth.png", None),
            (2, 2, "magic_beans", "Magic Beans", "items/magic_beans/magic_beans.png", "beans"),
            (2, 3, "megaton_hammer", "Megaton Hammer", "items/megaton_hammer/megaton_hammer.png", None),
            (2, 4, "light_arrows", "Light Arrow", "items/light_arrows/light_arrows.png", None),
            (2, 5, "nayrus_love", "Nayru's Love", "items/nayrus_love/nayrus_love.png", None),

            # Row 3 (Bottles 1-5 + Child Trade Item / Mask)
            (3, 0, "bottle_1", "Bottle 1", "items/bottle/bottle.png", None),
            (3, 1, "bottle_2", "Bottle 2", "items/bottle/bottle.png", None),
            (3, 2, "bottle_3", "Bottle 3", "items/bottle/bottle.png", None),
            (3, 3, "bottle_4", "Bottle 4", "items/bottle/bottle.png", None),
            (3, 4, "bottle_5", "Bottle 5", "items/bottle/bottle.png", None),
            (3, 5, "child_trade", "Child Quest Item", "items/child_trade_quest/weird_egg.png", None),
        ]

        for r, c, item_id, name, icon_path, ammo_k in self.matrix_defs:
            slot_card = tk.Frame(grid_frame, bg=COLOR_SLOT_BG, bd=1, relief="ridge", width=68, height=68)
            slot_card.grid(row=r, column=c, padx=6, pady=6)
            slot_card.pack_propagate(False)

            canvas = tk.Canvas(slot_card, width=64, height=64, bg=COLOR_SLOT_BG, highlightthickness=0)
            canvas.pack(fill="both", expand=True)

            self.inv_slots[item_id] = {
                "card": slot_card,
                "canvas": canvas,
                "id": item_id,
                "name": name,
                "base_icon": icon_path,
                "ammo_key": ammo_k,
                "r": r, "c": c
            }

            # Binds
            canvas.bind("<Button-1>", lambda e, i_id=item_id: self._on_inv_slot_click(i_id))
            canvas.bind("<Button-3>", lambda e, i_id=item_id: self._on_inv_slot_right_click(i_id))
            canvas.bind("<Enter>", lambda e, i_id=item_id: self._on_slot_hover(i_id, True))
            canvas.bind("<Leave>", lambda e, i_id=item_id: self._on_slot_hover(i_id, False))

        # Bottom info banner
        self.info_banner = tk.Label(box, text="Hover or click any slot to interact. Right-click ammo to adjust quantities.", font=("Segoe UI", 9), fg=COLOR_GOLD_LIGHT, bg=COLOR_PANEL_BG)
        self.info_banner.pack(pady=(8, 2))

    def _render_inv_slots(self):
        for item_id, s in self.inv_slots.items():
            canv = s["canvas"]
            canv.delete("all")
            name = s["name"]
            ammo_k = s["ammo_key"]

            # Determine ownership and icon
            owned = False
            icon_rel = s["base_icon"]
            sub_text = ""

            if item_id == "hookshot":
                hs_val = self.editor.hookshot_var.get()
                if hs_val == "Longshot":
                    owned = True
                    icon_rel = "items/longshot/longshot.png"
                    sub_text = "Longshot"
                elif hs_val == "Hookshot":
                    owned = True
                    icon_rel = "items/hookshot/hookshot.png"
                    sub_text = "Hookshot"
                else:
                    owned = False
                    icon_rel = "items/hookshot/hookshot.png"
                    sub_text = "None"

            elif item_id == "ocarina":
                # Check Fairy Ocarina vs Ocarina of Time
                # Hash 0x2213F934 (Fairy Ocarina), 0x589146FF (Ocarina of Time)
                has_oot = self.editor.special_item_vars.get(0x589146FF, (tk.BooleanVar(value=False), ""))[0].get()
                has_fairy = self.editor.special_item_vars.get(0x2213F934, (tk.BooleanVar(value=False), ""))[0].get()
                if has_oot:
                    owned = True
                    icon_rel = "items/ocarina/ocarina_of_time.png"
                elif has_fairy:
                    owned = True
                    icon_rel = "items/ocarina/fairy_ocarina.png"
                else:
                    owned = False
                    icon_rel = "items/ocarina/ocarina_of_time.png"

            elif item_id.startswith("bottle_"):
                b_name = self.editor.bottle_vars[item_id].get()
                if b_name == "(Not Acquired / Locked)":
                    owned = False
                    icon_rel = "items/bottle/bottle.png"
                    sub_text = "Locked"
                else:
                    owned = True
                    # Map content to icon
                    if "Fairy" in b_name: icon_rel = "items/bottle/contents/fairy.png"
                    elif "Red Potion" in b_name: icon_rel = "items/bottle/contents/red_potion.png"
                    elif "Green Potion" in b_name: icon_rel = "items/bottle/contents/green_potion.png"
                    elif "Blue Potion" in b_name: icon_rel = "items/bottle/contents/blue_potion.png"
                    elif "Fish" in b_name: icon_rel = "items/bottle/contents/fish.png"
                    elif "Blue Fire" in b_name: icon_rel = "items/bottle/contents/blue_fire.png"
                    elif "Bugs" in b_name: icon_rel = "items/bottle/contents/bugs.png"
                    elif "Big Poe" in b_name: icon_rel = "items/bottle/contents/big_poe.png"
                    elif "Poe" in b_name: icon_rel = "items/bottle/contents/poe.png"
                    elif "Ruto" in b_name or "Zelda's Letter" in b_name: icon_rel = "items/bottle/contents/rutos_letter.png"
                    elif "Half" in b_name: icon_rel = "items/bottle/contents/half_milk.png"
                    elif "Milk" in b_name: icon_rel = "items/bottle/contents/milk.png"
                    else: icon_rel = "items/bottle/bottle.png"
                    sub_text = b_name.split(" ")[0]

            elif item_id == "child_trade":
                cq = self.editor.child_quest_var.get()
                if cq == "Weird Egg":
                    owned = True
                    icon_rel = "items/child_trade_quest/weird_egg.png"
                elif cq == "Zelda's Letter":
                    owned = True
                    icon_rel = "items/child_trade_quest/zeldas_letter.png"
                else:
                    # Show active mask if mask is active
                    m_val = self.editor.active_mask_var.get()
                    if m_val != "None":
                        owned = True
                        m_map = {
                            "Keaton Mask": "items/child_trade_quest/keaton_mask.png",
                            "Skull Mask": "items/child_trade_quest/skull_mask.png",
                            "Spooky Mask": "items/child_trade_quest/spooky_mask.png",
                            "Bunny Hood": "items/child_trade_quest/bunny_hood.png",
                            "Goron Mask": "items/child_trade_quest/goron_mask.png",
                            "Zora Mask": "items/child_trade_quest/zora_mask.png",
                            "Gerudo Mask": "items/child_trade_quest/gerudo_mask.png",
                            "Mask of Truth": "items/child_trade_quest/mask_of_truth.png",
                        }
                        icon_rel = m_map.get(m_val, "items/child_trade_quest/bunny_hood.png")
                        sub_text = m_val
                    else:
                        owned = False
                        icon_rel = "items/child_trade_quest/weird_egg.png"
                        sub_text = "None"

            else:
                # Standard items mapped to special_item_vars
                # Find matching hash
                hash_match = None
                for kh, (var, itm_name) in self.editor.special_item_vars.items():
                    if name.lower() in itm_name.lower():
                        hash_match = kh
                        owned = var.get()
                        break
                if not hash_match and ammo_k and ammo_k in self.editor.ammo_vars:
                    # Owned if ammo count > 0 or upgrade bag tier
                    v_cnt = int(self.editor.ammo_vars[ammo_k][0].get() or 0)
                    owned = (v_cnt > 0)

            # Draw background slot bevel
            canv.create_rectangle(2, 2, 62, 62, fill="#121620" if not owned else "#1E2638", outline="#2A344A" if not owned else COLOR_GOLD)

            # Draw Sprite
            photo = self.icons.get(icon_rel, size=(40, 40), dimmed=(not owned))
            canv.create_image(32, 28, image=photo)

            # Ammo counter digit in bottom right
            if ammo_k and ammo_k in self.editor.ammo_vars and owned:
                cnt = self.editor.ammo_vars[ammo_k][0].get()
                canv.create_text(58, 54, text=str(cnt), fill=COLOR_GOLD_LIGHT, font=("Segoe UI", 9, "bold"), anchor="se")
            elif sub_text:
                canv.create_text(32, 54, text=sub_text[:8], fill=COLOR_TEXT_MUTED if not owned else "#FFF", font=("Segoe UI", 7), anchor="s")

    def _on_slot_hover(self, item_id, is_enter):
        s = self.inv_slots[item_id]
        if is_enter:
            s["card"].configure(bd=2, relief="solid")
            self.info_banner.configure(text=f"Selected: {s['name']} — Left-Click: Toggle/Cycle, Right-Click: Adjust")
        else:
            s["card"].configure(bd=1, relief="ridge")
            self.info_banner.configure(text="Hover or click any slot to interact. Right-click ammo to adjust quantities.")

    def _on_inv_slot_click(self, item_id):
        # 1. Hookshot cycle
        if item_id == "hookshot":
            cur = self.editor.hookshot_var.get()
            nxt = "Hookshot" if cur == "None" else ("Longshot" if cur == "Hookshot" else "None")
            self.editor.hookshot_var.set(nxt)

        # 2. Ocarina cycle
        elif item_id == "ocarina":
            v_oot, _ = self.editor.special_item_vars[0x589146FF]
            v_fairy, _ = self.editor.special_item_vars[0x2213F934]
            if not v_fairy.get() and not v_oot.get():
                v_fairy.set(True)
                v_oot.set(False)
            elif v_fairy.get() and not v_oot.get():
                v_fairy.set(True)
                v_oot.set(True)
            else:
                v_fairy.set(False)
                v_oot.set(False)

        # 3. Bottles: Open Visual Bottle Content Picker
        elif item_id.startswith("bottle_"):
            self._open_bottle_picker(item_id)
            return

        # 4. Child Trade / Mask
        elif item_id == "child_trade":
            cq = self.editor.child_quest_var.get()
            nxt = "Weird Egg" if cq == "None" else ("Zelda's Letter" if cq == "Weird Egg" else "None")
            self.editor.child_quest_var.set(nxt)

        # 5. Ammo Items
        elif item_id in ("sticks", "nuts", "bombs", "bow", "slingshot", "bombchus", "magic_beans"):
            ammo_k = self.inv_slots[item_id]["ammo_key"]
            if ammo_k and ammo_k in self.editor.ammo_vars:
                v, max_v, _ = self.editor.ammo_vars[ammo_k]
                cur = int(v.get() or 0)
                if cur == 0:
                    v.set(str(max_v))
                else:
                    v.set("0")
                # Also toggle weapon flag if applicable
                name = self.inv_slots[item_id]["name"]
                for kh, (var, itm_name) in self.editor.special_item_vars.items():
                    if name.lower() in itm_name.lower():
                        var.set(int(v.get()) > 0)
                        break

        # 6. Standard Tools & Spells
        else:
            name = self.inv_slots[item_id]["name"]
            for kh, (var, itm_name) in self.editor.special_item_vars.items():
                if name.lower() in itm_name.lower():
                    var.set(not var.get())
                    break

        self.refresh_all_visuals()

    def _on_inv_slot_right_click(self, item_id):
        s = self.inv_slots[item_id]
        ammo_k = s["ammo_key"]
        if ammo_k and ammo_k in self.editor.ammo_vars:
            v, max_v, _ = self.editor.ammo_vars[ammo_k]
            # Simple count cycle: +5 or loop
            cur = int(v.get() or 0)
            nxt = (cur + 5) if (cur + 5) <= max_v else 0
            v.set(str(nxt))
            self.refresh_all_visuals()

    def _open_bottle_picker(self, bottle_key):
        b_num = int(bottle_key.split("_")[-1])
        cur_val = self.editor.bottle_vars[bottle_key].get()

        dlg = tk.Toplevel(self)
        dlg.title(f"Select Bottle {b_num} Contents")
        dlg.geometry("460x340")
        dlg.configure(bg=COLOR_PANEL_BG)
        dlg.transient(self)
        dlg.grab_set()

        tk.Label(dlg, text=f"BOTTLE {b_num} CONTENTS", font=("Segoe UI", 11, "bold"), fg=COLOR_GOLD, bg=COLOR_PANEL_BG).pack(pady=8)

        grid = tk.Frame(dlg, bg=COLOR_PANEL_BG)
        grid.pack(padx=10, pady=4)

        from oot_save_editor import BOTTLE_CHOICES

        def pick(choice):
            if "Ruto's Letter" in choice:
                if not messagebox.askyesno(
                    "Warning: Story Progression Item",
                    "Ruto's Letter in a bottle can only be delivered once to King Zora to unblock Jabu-Jabu's Belly.\n\n"
                    "Once used or placed, it cannot be emptied or discarded in-game until the event completes.\n\n"
                    "Do you still want to place Ruto's Letter into this bottle?",
                    parent=dlg
                ):
                    return
            self.editor.bottle_vars[bottle_key].set(choice)
            dlg.destroy()
            self.refresh_all_visuals()

        for idx, choice in enumerate(BOTTLE_CHOICES):
            r = idx // 3
            c = idx % 3
            b_btn = tk.Button(
                grid, text=choice, font=("Segoe UI", 8), bg="#2D3748" if choice != cur_val else COLOR_GOLD,
                fg=COLOR_TEXT if choice != cur_val else "#000", activebackground=COLOR_GOLD,
                relief="flat", width=20, pady=4, command=lambda ch=choice: pick(ch)
            )
            b_btn.grid(row=r, column=c, padx=3, pady=3)

    # =========================================================================
    # SUBSCREEN 2: EQUIPMENT
    # =========================================================================
    def _build_equipment_subscreen(self):
        self.equip_frame = tk.Frame(self.content_frame, bg=COLOR_BG)

        box = tk.Frame(self.equip_frame, bg=COLOR_PANEL_BG, bd=2, relief="ridge", padx=16, pady=10)
        box.pack(fill="both", expand=True)

        tk.Label(box, text="EQUIPMENT (WEAPONS, ARMOR & UPGRADES)", font=("Segoe UI", 11, "bold"), fg=COLOR_GOLD, bg=COLOR_PANEL_BG).pack(pady=(0, 6))

        # 4 Gear Columns
        gear_grid = tk.Frame(box, bg=COLOR_PANEL_BG)
        gear_grid.pack(pady=4)

        self.gear_buttons = {}

        cols_data = [
            ("SWORDS", "sword", [
                ("Kokiri Sword", "equipment/swords/kokiri_sword.png"),
                ("Master Sword", "equipment/swords/master_sword.png"),
                ("Biggoron's Sword", "equipment/swords/biggorons_sword.png")
            ], self.editor.owned_swords),

            ("SHIELDS", "shield", [
                ("Deku Shield", "equipment/shields/deku_shield.png"),
                ("Hylian Shield", "equipment/shields/hylian_shield.png"),
                ("Mirror Shield", "equipment/shields/mirror_shield.png")
            ], self.editor.owned_shields),

            ("TUNICS", "tunic", [
                ("Kokiri Tunic", "equipment/tunics/kokiri_tunic.png"),
                ("Goron Tunic", "equipment/tunics/goron_tunic.png"),
                ("Zora Tunic", "equipment/tunics/zora_tunic.png")
            ], self.editor.owned_tunics),

            ("BOOTS", "boots", [
                ("Kokiri Boots", "equipment/boots/kokiri_boots.png"),
                ("Iron Boots", "equipment/boots/iron_boots.png"),
                ("Hover Boots", "equipment/boots/hover_boots.png")
            ], self.editor.owned_boots),
        ]

        for col_idx, (title, category, items, owned_dict) in enumerate(cols_data):
            col_f = tk.Frame(gear_grid, bg=COLOR_PANEL_BG, padx=8)
            col_f.grid(row=0, column=col_idx, sticky="n")

            tk.Label(col_f, text=title, font=("Segoe UI", 9, "bold"), fg=COLOR_GOLD_LIGHT, bg=COLOR_PANEL_BG).pack(pady=(0, 4))

            for item_name, icon_rel in items:
                card = tk.Frame(col_f, bg=COLOR_SLOT_BG, bd=1, relief="ridge", width=160, height=48)
                card.pack(pady=3)
                card.pack_propagate(False)

                canv = tk.Canvas(card, width=156, height=44, bg=COLOR_SLOT_BG, highlightthickness=0)
                canv.pack(fill="both", expand=True)

                self.gear_buttons[item_name] = {
                    "canvas": canv, "card": card, "category": category,
                    "name": item_name, "icon_rel": icon_rel, "owned_dict": owned_dict
                }

                canv.bind("<Button-1>", lambda e, n=item_name: self._on_gear_click(n))
                canv.bind("<Button-3>", lambda e, n=item_name: self._on_gear_equip(n))
                canv.bind("<Double-Button-1>", lambda e, n=item_name: self._on_gear_equip(n))

        # Bottom Upgrades Badges Row
        upg_box = tk.LabelFrame(box, text="Upgrades & Capacities (Click to Cycle Tiers)", font=("Segoe UI", 9, "bold"), fg=COLOR_GOLD, bg=COLOR_PANEL_BG, padx=10, pady=8)
        upg_box.pack(fill="x", pady=(12, 0))

        self.upg_badge_canvas = tk.Canvas(upg_box, height=64, bg=COLOR_PANEL_BG, highlightthickness=0)
        self.upg_badge_canvas.pack(fill="x", expand=True)
        self.upg_badge_canvas.bind("<Button-1>", self._on_upgrades_canvas_click)

    def _render_equipment(self):
        for name, g in self.gear_buttons.items():
            canv = g["canvas"]
            canv.delete("all")
            cat = g["category"]
            owned = g["owned_dict"].get(name, tk.BooleanVar(value=False)).get()
            is_equipped = (self.editor.equip_vars[cat].get() == name)

            # Border
            bg_col = "#1E2638" if owned else "#10141D"
            bd_col = COLOR_EQUIPPED if is_equipped else (COLOR_GOLD if owned else "#2D3748")
            canv.create_rectangle(2, 2, 154, 42, fill=bg_col, outline=bd_col, width=2 if is_equipped else 1)

            # Sprite
            photo = self.icons.get(g["icon_rel"], size=(32, 32), dimmed=(not owned))
            canv.create_image(24, 22, image=photo)

            # Title
            t_col = "#FFF" if owned else COLOR_TEXT_MUTED
            canv.create_text(46, 16, text=name, fill=t_col, font=("Segoe UI", 8, "bold" if owned else "normal"), anchor="w")

            # Equipped badge
            if is_equipped:
                canv.create_text(46, 30, text="★ EQUIPPED", fill=COLOR_EQUIPPED, font=("Segoe UI", 7, "bold"), anchor="w")
            else:
                canv.create_text(46, 30, text="Left: Toggle / Right: Equip", fill="#4A5568", font=("Segoe UI", 6), anchor="w")

        # Render Upgrades Badges
        self._render_upgrade_badges()

    def _render_upgrade_badges(self):
        canv = self.upg_badge_canvas
        canv.delete("all")

        # Badges list: (name, label, icon_rel)
        str_val = self.editor.equip_vars["strength"].get()
        str_icon = "equipment/strength/golden_gauntlets.png" if "Golden" in str_val else ("equipment/strength/silver_gauntlets.png" if "Silver" in str_val else "equipment/strength/goron_bracelet.png")

        sc_val = self.editor.equip_vars["scale"].get()
        sc_icon = "equipment/scale/gold_scale.png" if "Golden" in sc_val else "equipment/scale/silver_scale.png"

        wal_val = self.editor.equip_vars["wallet"].get()
        wal_icon = "equipment/wallet/giants_wallet.png" if "Giant" in wal_val else ("equipment/wallet/adults_wallet.png" if "Adult" in wal_val else "equipment/wallet/basic_wallet.png")

        q_val = self.editor.equip_vars["quiver"].get()
        q_icon = "items/fairy_bow/fairy_bow_upgrade_2.png" if "50" in q_val else ("items/fairy_bow/fairy_bow_upgrade_1.png" if "40" in q_val else "items/fairy_bow/fairy_bow_default.png")

        bb_val = self.editor.equip_vars["bomb_bag"].get()
        bb_icon = "equipment/bomb_bag/bomb_bag_40.png" if "40" in bb_val else ("equipment/bomb_bag/bomb_bag_30.png" if "30" in bb_val else "equipment/bomb_bag/bomb_bag_20.png")

        badges = [
            ("strength", str_val, str_icon),
            ("scale", sc_val, sc_icon),
            ("wallet", wal_val, wal_icon),
            ("quiver", q_val, q_icon),
            ("bomb_bag", bb_val, bb_icon)
        ]

        for idx, (b_key, b_label, icon_rel) in enumerate(badges):
            x = idx * 160 + 20
            photo = self.icons.get(icon_rel, size=(36, 36), dimmed=False)
            canv.create_image(x + 20, 32, image=photo)
            canv.create_text(x + 46, 26, text=b_key.replace("_", " ").title(), fill=COLOR_GOLD_LIGHT, font=("Segoe UI", 8, "bold"), anchor="w")
            canv.create_text(x + 46, 40, text=b_label.split(" (")[0][:14], fill=COLOR_TEXT_MUTED, font=("Segoe UI", 7), anchor="w")

    def _on_gear_click(self, item_name):
        g = self.gear_buttons[item_name]
        var = g["owned_dict"][item_name]
        var.set(not var.get())
        self.editor._sync_equipped_options()
        self.refresh_all_visuals()

    def _on_gear_equip(self, item_name):
        g = self.gear_buttons[item_name]
        cat = g["category"]
        # Ensure it is owned
        g["owned_dict"][item_name].set(True)
        self.editor.equip_vars[cat].set(item_name)
        self.editor._sync_equipped_options()
        self.refresh_all_visuals()

    def _on_upgrades_canvas_click(self, event):
        idx = event.x // 160
        keys = ["strength", "scale", "wallet", "quiver", "bomb_bag"]
        if idx < len(keys):
            k = keys[idx]
            combo = self.editor.equip_vars[k]
            # Cycle through values
            from oot_save_editor import GAUNTLETS, DIVING_SCALES, WALLETS
            if k == "strength":
                vals = [g[0] for g in GAUNTLETS]
            elif k == "scale":
                vals = [s[0] for s in DIVING_SCALES]
            elif k == "wallet":
                vals = [w["label"] for w in WALLETS]
            elif k == "quiver":
                vals = ["None", "Quiver (30)", "Bigger Quiver (40)", "Biggest Quiver (50)"]
            elif k == "bomb_bag":
                vals = ["None", "Bomb Bag (20)", "Bigger Bomb Bag (30)", "Biggest Bomb Bag (40)"]
            else:
                return

            cur = combo.get()
            nxt_idx = (vals.index(cur) + 1) % len(vals) if cur in vals else 0
            combo.set(vals[nxt_idx])
            self.editor._on_bag_or_capacity_changed(k)
            self.refresh_all_visuals()

    # =========================================================================
    # SUBSCREEN 3: QUEST STATUS (Medallions, Stones & Songs)
    # =========================================================================
    def _build_quest_subscreen(self):
        self.quest_frame = tk.Frame(self.content_frame, bg=COLOR_BG)

        box = tk.Frame(self.quest_frame, bg=COLOR_PANEL_BG, bd=2, relief="ridge", padx=16, pady=10)
        box.pack(fill="both", expand=True)

        tk.Label(box, text="QUEST STATUS (MEDALLIONS, STONES & SONGS)", font=("Segoe UI", 11, "bold"), fg=COLOR_GOLD, bg=COLOR_PANEL_BG).pack(pady=(0, 6))

        mid_frame = tk.Frame(box, bg=COLOR_PANEL_BG)
        mid_frame.pack(fill="both", expand=True)

        # Left Column: Medallion Wheel & Stones Canvas
        self.celestial_canvas = tk.Canvas(mid_frame, width=320, height=310, bg="#0C1017", highlightthickness=1, highlightbackground="#1E2638")
        self.celestial_canvas.pack(side="left", padx=(0, 16), pady=4)
        self.celestial_canvas.bind("<Button-1>", self._on_celestial_canvas_click)

        # Right Column: 12 Songs Staves
        songs_box = tk.Frame(mid_frame, bg=COLOR_PANEL_BG)
        songs_box.pack(side="left", fill="both", expand=True)

        tk.Label(songs_box, text="Ocarina Songs (Click to Learn/Unlearn)", font=("Segoe UI", 9, "bold"), fg=COLOR_GOLD_LIGHT, bg=COLOR_PANEL_BG).pack(anchor="w", pady=(0, 4))

        self.songs_canvas = tk.Canvas(songs_box, width=440, height=270, bg="#0C1017", highlightthickness=1, highlightbackground="#1E2638")
        self.songs_canvas.pack(fill="both", expand=True)
        self.songs_canvas.bind("<Button-1>", self._on_songs_canvas_click)

        # Bottom row: Trade Sequence & Keys quick status
        bot_q = tk.Frame(box, bg=COLOR_PANEL_BG)
        bot_q.pack(fill="x", pady=(8, 0))
        tk.Button(bot_q, text="Learn All 12 Songs", font=("Segoe UI", 8, "bold"), bg="#2B6CB0", fg="#FFF", relief="flat", padx=6, command=self._learn_all_songs).pack(side="left")
        tk.Button(bot_q, text="Max Dungeon Small Keys", font=("Segoe UI", 8), bg="#2D3748", fg=COLOR_TEXT, relief="flat", padx=6, command=self._max_dungeon_keys).pack(side="left", padx=6)

    def _render_quest_status(self):
        self._render_celestial_wheel()
        self._render_songs()

    def _render_celestial_wheel(self):
        canv = self.celestial_canvas
        canv.delete("all")

        # Center Triforce outline
        cx, cy = 160, 150
        canv.create_polygon(cx, cy-40, cx-35, cy+20, cx+35, cy+20, fill="#232211", outline="#594F1A", width=2)
        canv.create_polygon(cx, cy+20, cx-18, cy-10, cx+18, cy-10, fill="#0C1017", outline="#594F1A")

        # Heart Piece in Center: 4 quarter wheel
        tot_pieces = int(self.editor.v_heart_pieces_total.get() or 0)
        held_pieces = tot_pieces % 4
        # Draw central heart piece icon
        canv.create_oval(cx-16, cy-12, cx+16, cy+18, fill="#3D1313", outline="#742A2A")
        if held_pieces > 0:
            canv.create_arc(cx-16, cy-12, cx+16, cy+18, start=90, extent=-(held_pieces*90), fill="#E53E3E", outline="")
        canv.create_text(cx, cy+28, text=f"{held_pieces}/4 Pieces", fill=COLOR_GOLD_LIGHT, font=("Segoe UI", 7, "bold"))

        # 6 SAGE MEDALLIONS (Wheel radius 95)
        # Light (Top), Forest, Fire, Water, Shadow, Spirit
        medallion_defs = [
            ("Light", 3419530636, "quest_status/medallions/light_medallion.png", 0),
            ("Forest", 365691062, "quest_status/medallions/forest_medallion.png", 60),
            ("Fire", 102604812, "quest_status/medallions/fire_medallion.png", 120),
            ("Water", 2174697980, "quest_status/medallions/water_medallion.png", 180),
            ("Shadow", 2983818817, "quest_status/medallions/shadow_medallion.png", 240),
            ("Spirit", 3804824368, "quest_status/medallions/spirit_medallion.png", 300)
        ]

        self.celestial_hits = []
        for name, kh, icon_rel, deg in medallion_defs:
            rad = math.radians(deg - 90)
            mx = cx + int(95 * math.cos(rad))
            my = cy + int(95 * math.sin(rad))

            owned = self.editor.quest_vars.get(kh, tk.BooleanVar(value=False)).get()
            photo = self.icons.get(icon_rel, size=(34, 34), dimmed=(not owned))

            canv.create_oval(mx-19, my-19, mx+19, my+19, fill="#161B26", outline=COLOR_GOLD if owned else "#2D3748", width=1)
            canv.create_image(mx, my, image=photo)
            self.celestial_hits.append(("medallion", kh, mx, my, 19))

        # 3 SPIRITUAL STONES (Triangle at bottom)
        stones_defs = [
            ("Emerald", 400473950, "quest_status/spiritual_stones/kokiri_emerald.png", cx - 55, cy + 105),
            ("Ruby", 2469600129, "quest_status/spiritual_stones/gorons_ruby.png", cx, cy + 105),
            ("Sapphire", 1928096277, "quest_status/spiritual_stones/zoras_sapphire.png", cx + 55, cy + 105),
        ]

        for name, kh, icon_rel, sx, sy in stones_defs:
            owned = self.editor.quest_vars.get(kh, tk.BooleanVar(value=False)).get()
            photo = self.icons.get(icon_rel, size=(30, 30), dimmed=(not owned))
            canv.create_oval(sx-17, sy-17, sx+17, sy+17, fill="#161B26", outline=COLOR_GOLD if owned else "#2D3748", width=1)
            canv.create_image(sx, sy, image=photo)
            self.celestial_hits.append(("stone", kh, sx, sy, 17))

    def _render_songs(self):
        canv = self.songs_canvas
        canv.delete("all")

        # 6 Standard Songs (Top 2 rows)
        from oot_save_editor import SONGS

        self.song_hits = []
        for idx, (sname, bit_idx, isget_h, event_h, _) in enumerate(SONGS):
            is_warp = (idx >= 6)
            col = idx % 6
            row = 0 if not is_warp else 1
            x = col * 70 + 40
            y = row * 110 + 45

            # Map to song icon
            s_map = {
                "Zelda's Lullaby": "quest_status/songs/standard/zeldas_lullaby.png",
                "Epona's Song": "quest_status/songs/standard/eponas_song.png",
                "Saria's Song": "quest_status/songs/standard/sarias_song.png",
                "Sun's Song": "quest_status/songs/standard/suns_song.png",
                "Song of Time": "quest_status/songs/standard/song_of_time.png",
                "Song of Storms": "quest_status/songs/standard/song_of_storms.png",
                "Minuet of Forest": "quest_status/songs/warp/minuet_of_forest.png",
                "Bolero of Fire": "quest_status/songs/warp/bolero_of_fire.png",
                "Serenade of Water": "quest_status/songs/warp/serenade_of_water.png",
                "Requiem of Spirit": "quest_status/songs/warp/requiem_of_spirit.png",
                "Nocturne of Shadow": "quest_status/songs/warp/nocturne_of_shadow.png",
                "Prelude of Light": "quest_status/songs/warp/prelude_of_light.png",
            }
            icon_rel = s_map.get(sname, "quest_status/songs/standard/gray_note.png")
            learned = self.editor.song_vars.get(bit_idx, tk.BooleanVar(value=False)).get()

            # Musical stave lines
            canv.create_line(x-28, y+2, x+28, y+2, fill="#2D3748")
            canv.create_line(x-28, y-4, x+28, y-4, fill="#2D3748")
            canv.create_line(x-28, y+8, x+28, y+8, fill="#2D3748")

            # Note circle / icon
            photo = self.icons.get(icon_rel, size=(30, 30), dimmed=(not learned))
            canv.create_image(x, y, image=photo)

            # Song Title
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
                    self.refresh_all_visuals()
                return

    def _on_songs_canvas_click(self, event):
        for bit_idx, x, y, rad in self.song_hits:
            dist = math.hypot(event.x - x, event.y - y)
            if dist <= rad:
                var = self.editor.song_vars.get(bit_idx)
                if var:
                    var.set(not var.get())
                    self.refresh_all_visuals()
                return

    def _learn_all_songs(self):
        self.editor.learn_all_songs()
        self.refresh_all_visuals()

    def _max_dungeon_keys(self):
        self.editor.max_keys()
        self.refresh_all_visuals()

    # =========================================================================
    # FOOTER & SAVE
    # =========================================================================
    def _build_footer(self):
        ftr = tk.Frame(self, bg=COLOR_BG, pady=6)
        ftr.pack(fill="x", padx=12)

        # Primary Save Button
        save_btn = tk.Button(
            ftr, text="★ SAVE & APPLY TO GAME SAVE ★", font=("Segoe UI", 9, "bold"),
            bg="#319795", fg="#FFF", activebackground="#285E61", relief="flat", padx=14, pady=5,
            command=self._save_changes
        )
        save_btn.pack(side="left")

        # Sync button
        tk.Button(
            ftr, text="Sync from Editor", font=("Segoe UI", 8), bg="#2D3748", fg=COLOR_TEXT,
            relief="flat", padx=8, pady=5, command=self.refresh_all_visuals
        ).pack(side="left", padx=8)

        # Close button
        tk.Button(
            ftr, text="Close Pause Menu", font=("Segoe UI", 8), bg="#2D3748", fg=COLOR_TEXT,
            relief="flat", padx=8, pady=5, command=self.destroy
        ).pack(side="right")

    def _save_changes(self):
        # Trigger save on main editor
        self.editor.save()
        self.refresh_all_visuals()

    def refresh_all_visuals(self):
        self._draw_hearts()
        self._draw_magic()

        # Update Rupees
        rupees = self.editor.v_rupees.get()
        wal_label = self.editor.equip_vars["wallet"].get()
        limit = 1000 if "1000" in wal_label else (500 if "500" in wal_label else 200)
        self.rupee_val_lbl.configure(text=str(rupees))
        self.rupee_max_lbl.configure(text=f" / {limit}")

        wal_icon = "equipment/wallet/giants_wallet.png" if limit == 1000 else ("equipment/wallet/adults_wallet.png" if limit == 500 else "equipment/wallet/basic_wallet.png")
        self.rupee_icon_lbl.configure(image=self.icons.get(wal_icon, size=(24, 24)))

        # Update Tokens
        tokens = self.editor.v_tokens.get()
        self.token_val_lbl.configure(text=str(tokens))
        self.token_icon_lbl.configure(image=self.icons.get("quest_status/skulltullas/golden_skulltulla.png", size=(20, 20)))

        # Render Active Subscreen
        self._render_inv_slots()
        self._render_equipment()
        self._render_quest_status()
