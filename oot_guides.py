"""
The Legend of Zelda: Ocarina of Time (Nintendo Switch 2) - Offline Guides Tab
Provides offline collectible guides (Heart Pieces, etc.) loaded from local JSON,
with numbered checkable cards, bundled screenshots, and save progress tracking.
"""

import os
import sys
import json
import math
import tkinter as tk
from tkinter import ttk, messagebox

# Determine module, resource, and user data paths
from app_paths import APP_NAME, APP_DIR, RESOURCE_DIR, USER_DATA_DIR
from oot_collectibles import SUPPORTED_GUIDES, collected_entries, load_table

# Pillow is optional: guides and app must work without it
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def get_slot_key(slot_dir):
    """Normalize slot path into a settings key, or return 'no-save' if none."""
    if not slot_dir or not str(slot_dir).strip():
        return "no-save"
    return os.path.normpath(os.path.abspath(slot_dir))


def get_checked_entries(settings, slot_key, guide_id):
    """Return a set of checked entry integers for slot_key and guide_id."""
    checks = settings.get("guide_checks", {})
    slot_dict = checks.get(slot_key, {})
    entry_list = slot_dict.get(guide_id, [])
    return set(entry_list)


def set_checked_entries(settings, slot_key, guide_id, checked_entries):
    """Store sorted list of checked entry numbers into settings."""
    if "guide_checks" not in settings:
        settings["guide_checks"] = {}
    if slot_key not in settings["guide_checks"]:
        settings["guide_checks"][slot_key] = {}
    settings["guide_checks"][slot_key][guide_id] = sorted(list(checked_entries))
    return settings


def load_guide_file(filepath, status_callback=None):
    """Load and validate a single guide JSON file.
    A guide JSON needs:
      - 'id' (str)
      - 'title' (str)
      - 'total' (int)
      - 'entries' (list)
    Each entry needs:
      - unique int 'n'
      - 'title' (str)
      - 'steps' (str)

    Returns the parsed dict if valid, or None if invalid.
    """
    fname = os.path.basename(filepath)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        msg = f"Skipping guide file {fname}: {e}"
        if status_callback:
            status_callback(msg)
        return None

    if not isinstance(data, dict):
        msg = f"Skipping guide {fname}: root must be a JSON object"
        if status_callback:
            status_callback(msg)
        return None

    guide_id = data.get("id")
    title = data.get("title")
    total = data.get("total")
    entries = data.get("entries")

    if not isinstance(guide_id, str) or not guide_id.strip():
        msg = f"Skipping guide {fname}: missing or invalid 'id'"
        if status_callback:
            status_callback(msg)
        return None

    if not isinstance(title, str) or not title.strip():
        msg = f"Skipping guide {fname}: missing or invalid 'title'"
        if status_callback:
            status_callback(msg)
        return None

    if not isinstance(total, int) or isinstance(total, bool):
        msg = f"Skipping guide {fname}: missing or invalid 'total'"
        if status_callback:
            status_callback(msg)
        return None

    if not isinstance(entries, list):
        msg = f"Skipping guide {fname}: missing or invalid 'entries' list"
        if status_callback:
            status_callback(msg)
        return None

    seen_n = set()
    for idx, entry in enumerate(entries):
        if not isinstance(entry, dict):
            msg = f"Skipping guide {fname}: entry {idx} is not an object"
            if status_callback:
                status_callback(msg)
            return None

        n = entry.get("n")
        entry_title = entry.get("title")
        steps = entry.get("steps")

        if not isinstance(n, int) or isinstance(n, bool):
            msg = f"Skipping guide {fname}: entry {idx} has invalid 'n'"
            if status_callback:
                status_callback(msg)
            return None

        if n in seen_n:
            msg = f"Skipping guide {fname}: duplicate entry number n={n}"
            if status_callback:
                status_callback(msg)
            return None
        seen_n.add(n)

        if not isinstance(entry_title, str) or not entry_title.strip():
            msg = f"Skipping guide {fname}: entry #{n} has missing or empty 'title'"
            if status_callback:
                status_callback(msg)
            return None

        if not isinstance(steps, str):
            msg = f"Skipping guide {fname}: entry #{n} has missing or invalid 'steps'"
            if status_callback:
                status_callback(msg)
            return None

    return data


def load_guides(resource_dir=None, app_dir=None, status_callback=None):
    """Scans RESOURCE_DIR/guides and USER_DATA_DIR/guides (USER_DATA_DIR wins on duplicate id).
    Returns validated guides sorted by optional 'order' then 'title'.
    """
    if resource_dir is None:
        resource_dir = RESOURCE_DIR
    if app_dir is None:
        app_dir = USER_DATA_DIR

    guides_by_id = {}

    dirs_to_scan = []
    res_guides = os.path.join(resource_dir, "guides")
    if os.path.isdir(res_guides):
        dirs_to_scan.append(res_guides)

    app_guides = os.path.join(app_dir, "guides")
    if os.path.isdir(app_guides) and os.path.normpath(app_guides) != os.path.normpath(res_guides):
        dirs_to_scan.append(app_guides)

    for gdir in dirs_to_scan:
        try:
            entries = sorted(os.listdir(gdir))
        except OSError:
            continue
        for fname in entries:
            if fname.lower().endswith(".json"):
                fpath = os.path.join(gdir, fname)
                guide = load_guide_file(fpath, status_callback=status_callback)
                if guide is not None:
                    guides_by_id[guide["id"]] = guide

    def sort_key(g):
        order = g.get("order")
        order_val = order if isinstance(order, (int, float)) else 999999
        title_val = g.get("title", "").lower()
        return (order_val, title_val)

    return sorted(guides_by_id.values(), key=sort_key)


class GuideCard:
    """Renders a single collectible card inside the scrollable guide view."""

    def __init__(self, parent, entry, guide_id, guides_frame):
        self.parent = parent
        self.entry = entry
        self.guide_id = guide_id
        self.guides_frame = guides_frame
        self.n = entry["n"]
        self.is_checked = False

        palette = guides_frame.palette

        # Outer border frame
        self.border_frame = tk.Frame(parent, bg=palette.get("border", "#d2d6dc"), bd=0)

        # Inner card content frame
        self.card_frame = tk.Frame(self.border_frame, bg=palette.get("surface", "#ffffff"), padx=12, pady=10)
        self.card_frame.pack(fill="both", expand=True, padx=1, pady=1)

        # Top row: Badge, Title, Checkbutton
        self.hdr = tk.Frame(self.card_frame, bg=palette.get("surface", "#ffffff"))
        self.hdr.pack(fill="x")

        self.badge = tk.Label(
            self.hdr,
            text=f" #{self.n} ",
            font=("Segoe UI", 11, "bold"),
            padx=5,
            pady=2,
            bg=palette.get("border", "#d2d6dc"),
            fg=palette.get("muted", "#5c6470")
        )
        self.badge.pack(side="left")

        self.title_lbl = tk.Label(
            self.hdr,
            text=f"  {entry.get('title', '')}",
            font=("Segoe UI", 11, "bold"),
            bg=palette.get("surface", "#ffffff"),
            fg=palette.get("fg", "#1e2229"),
            anchor="w"
        )
        self.title_lbl.pack(side="left", fill="x", expand=True)

        self.check_var = tk.BooleanVar(value=False)
        self.check_btn = ttk.Checkbutton(
            self.hdr,
            text="Collected",
            variable=self.check_var,
            command=self._on_toggle
        )
        self.check_btn.pack(side="right")

        # Shift+Click multiselect & Title click bindings
        self.check_btn.bind("<Shift-Button-1>", self._on_shift_click)
        self.title_lbl.bind("<Button-1>", self._on_title_click)
        self.title_lbl.bind("<Shift-Button-1>", self._on_shift_click)
        self.badge.bind("<Button-1>", self._on_title_click)
        self.badge.bind("<Shift-Button-1>", self._on_shift_click)

        # Sub-header: Area · Era
        area = entry.get("area", "")
        era = entry.get("era", "")
        meta_str = f"{area} · {era}".strip(" ·")
        self.meta_lbl = tk.Label(
            self.card_frame,
            text=meta_str,
            font=("Segoe UI", 9),
            bg=palette.get("surface", "#ffffff"),
            fg=palette.get("muted", "#5c6470"),
            anchor="w"
        )
        self.meta_lbl.pack(fill="x", pady=(2, 0))

        # Additional bindings for responsive clicking
        self.meta_lbl.bind("<Button-1>", self._on_title_click)
        self.meta_lbl.bind("<Shift-Button-1>", self._on_shift_click)
        self.hdr.bind("<Button-1>", self._on_title_click)
        self.hdr.bind("<Shift-Button-1>", self._on_shift_click)

        # Optional: Requires
        requires = entry.get("requires")
        if requires and len(requires) > 0:
            req_str = f"Requires: {', '.join(requires)}"
            self.req_lbl = tk.Label(
                self.card_frame,
                text=req_str,
                font=("Segoe UI", 9, "italic"),
                bg=palette.get("surface", "#ffffff"),
                fg=palette.get("muted", "#5c6470"),
                anchor="w"
            )
            self.req_lbl.pack(fill="x", pady=(2, 0))
        else:
            self.req_lbl = None

        # Steps text
        self.steps_lbl = tk.Label(
            self.card_frame,
            text=entry.get("steps", ""),
            font=("Segoe UI", 9),
            bg=palette.get("surface", "#ffffff"),
            fg=palette.get("fg", "#1e2229"),
            justify="left",
            anchor="w",
            wraplength=600
        )
        self.steps_lbl.pack(fill="x", pady=(6, 0))

        # Optional: Note (with ⚠ in Warn style)
        note = entry.get("note")
        if note:
            self.note_lbl = tk.Label(
                self.card_frame,
                text=f"⚠ {note}",
                font=("Segoe UI", 9, "bold"),
                bg=palette.get("surface", "#ffffff"),
                fg=palette.get("warn", "#d97706"),
                justify="left",
                anchor="w",
                wraplength=600
            )
            self.note_lbl.pack(fill="x", pady=(4, 0))
        else:
            self.note_lbl = None

        # Screenshot area (shows bundled image if present; hidden if absent)
        self.ss_frame = tk.Frame(self.card_frame, bg=palette.get("surface", "#ffffff"))
        self.ss_display = None
        self._refresh_screenshot()

    def set_checked(self, checked, update_guides_frame=True):
        self.is_checked = checked
        self.check_var.set(checked)
        palette = self.guides_frame.palette
        if checked:
            self.badge.configure(bg=palette.get("accent", "#0066cc"), fg="#ffffff")
        else:
            self.badge.configure(bg=palette.get("border", "#d2d6dc"), fg=palette.get("muted", "#5c6470"))

        if update_guides_frame:
            self.guides_frame.on_card_checked_changed(self.guide_id, self.n, checked)

    def _on_toggle(self):
        new_state = self.check_var.get()
        self.set_checked(new_state, update_guides_frame=True)
        self.guides_frame.last_clicked_n = self.n
        self.guides_frame.last_clicked_guide = self.guide_id
        self.guides_frame.last_clicked_state = new_state

    def _on_title_click(self, event=None):
        new_state = not self.check_var.get()
        self.check_var.set(new_state)
        self.set_checked(new_state, update_guides_frame=True)
        self.guides_frame.last_clicked_n = self.n
        self.guides_frame.last_clicked_guide = self.guide_id
        self.guides_frame.last_clicked_state = new_state

    def _on_shift_click(self, event=None):
        self.guides_frame.handle_shift_click(self)
        return "break"

    def _refresh_screenshot(self):
        for w in self.ss_frame.winfo_children():
            w.destroy()

        palette = self.guides_frame.palette
        img_path = self.guides_frame.get_image_path(self.guide_id, self.n)

        photo = None
        if os.path.exists(img_path):
            photo = self.guides_frame.get_thumbnail(img_path)

        if photo:
            self.ss_frame.pack(fill="x", pady=(8, 0))
            self.ss_display = tk.Label(self.ss_frame, image=photo, bg=palette.get("surface", "#ffffff"))
            self.ss_display.image = photo
            self.ss_display.pack(anchor="w")
        else:
            self.ss_display = None
            self.ss_frame.pack_forget()

    def update_wraplength(self, wrap):
        self.steps_lbl.configure(wraplength=wrap)
        if self.note_lbl:
            self.note_lbl.configure(wraplength=wrap)

    def refresh_theme(self, palette):
        self.border_frame.configure(bg=palette.get("border", "#d2d6dc"))
        self.card_frame.configure(bg=palette.get("surface", "#ffffff"))
        self.hdr.configure(bg=palette.get("surface", "#ffffff"))
        self.title_lbl.configure(bg=palette.get("surface", "#ffffff"), fg=palette.get("fg", "#1e2229"))
        self.meta_lbl.configure(bg=palette.get("surface", "#ffffff"), fg=palette.get("muted", "#5c6470"))
        if self.req_lbl:
            self.req_lbl.configure(bg=palette.get("surface", "#ffffff"), fg=palette.get("muted", "#5c6470"))
        self.steps_lbl.configure(bg=palette.get("surface", "#ffffff"), fg=palette.get("fg", "#1e2229"))
        if self.note_lbl:
            self.note_lbl.configure(bg=palette.get("surface", "#ffffff"), fg=palette.get("warn", "#d97706"))
        self.ss_frame.configure(bg=palette.get("surface", "#ffffff"))
        if self.ss_display and isinstance(self.ss_display, tk.Label):
            self.ss_display.configure(bg=palette.get("surface", "#ffffff"))

        if self.is_checked:
            self.badge.configure(bg=palette.get("accent", "#0066cc"), fg="#ffffff")
        else:
            self.badge.configure(bg=palette.get("border", "#d2d6dc"), fg=palette.get("muted", "#5c6470"))

        self._refresh_screenshot()


SAVE_COUNTERS = {
    "heart_pieces": {
        "var_name": "v_heart_pieces_total",
        "total": None,
    },
    "skulltulas": {
        "var_name": "v_tokens",
        "total": 100,
    },
}


class GroupHeading:
    """Header row for a group of cards."""

    def __init__(self, parent, group_name, guides_frame):
        self.parent = parent
        self.group_name = group_name
        self.guides_frame = guides_frame
        palette = guides_frame.palette

        bg = palette.get("bg", "#f4f5f7")
        accent = palette.get("accent", "#0066cc")
        rule_color = palette.get("border", "#d2d6dc")

        self.frame = tk.Frame(parent, bg=bg)

        self.label = tk.Label(
            self.frame,
            text=group_name,
            font=("Segoe UI", 12, "bold"),
            fg=accent,
            bg=bg,
            anchor="w"
        )
        self.label.pack(fill="x", padx=8, pady=(10, 2))

        self.rule = tk.Frame(self.frame, height=1, bg=rule_color)
        self.rule.pack(fill="x", padx=8, pady=(2, 4))

    def refresh_theme(self, palette=None):
        p = palette or self.guides_frame.palette
        bg = p.get("bg", "#f4f5f7")
        accent = p.get("accent", "#0066cc")
        rule_color = p.get("border", "#d2d6dc")

        self.frame.configure(bg=bg)
        self.label.configure(bg=bg, fg=accent)
        self.rule.configure(bg=rule_color)


class GuidesFrame(ttk.Frame):
    """Main Guides tab widget providing left pane guide selector and right pane guide viewer."""

    def __init__(self, parent, app, app_dir=None, resource_dir=None):
        super().__init__(parent)
        self.app = app
        self.app_dir = app_dir or getattr(app, "user_data_dir", getattr(app, "app_dir", USER_DATA_DIR))
        self.resource_dir = resource_dir or getattr(app, "resource_dir", RESOURCE_DIR)

        self.image_cache = {}
        self.cards_by_guide = {}
        self.headings_by_guide = {}
        self.checked_set = set()
        self.current_guide = None
        self.selected_item = None
        self._build_generation = 0
        self._batch_job = None
        self._has_groups = False
        self.BATCH_SIZE = 15
        self.last_clicked_n = None
        self.last_clicked_guide = None
        self.last_clicked_state = None

        # Left pane: Guide selection list
        self.left_pane = ttk.Frame(self, width=230)
        self.left_pane.pack(side="left", fill="y", padx=(0, 6))
        self.left_pane.pack_propagate(False)

        tree_frame = ttk.Frame(self.left_pane)
        tree_frame.pack(fill="both", expand=True)

        self.guide_tree = ttk.Treeview(tree_frame, show="tree", selectmode="browse")
        self.guide_tree.pack(side="left", fill="both", expand=True)

        guide_sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.guide_tree.yview)
        guide_sb.pack(side="right", fill="y")
        self.guide_tree.configure(yscrollcommand=guide_sb.set)
        self.guide_tree.bind("<<TreeviewSelect>>", self._on_guide_tree_select)

        # Right pane: Guide Detail
        self.right_pane = ttk.Frame(self)
        self.right_pane.pack(side="right", fill="both", expand=True)

        # Guide Detail Frame
        self.detail_frame = ttk.Frame(self.right_pane)
        self.detail_frame.pack(fill="both", expand=True)

        # Header: Title, Intro, Source Note, Progress Line
        self.header_frame = ttk.Frame(self.detail_frame)
        self.header_frame.pack(fill="x", pady=(0, 6))

        self.title_label = ttk.Label(self.header_frame, text="", font=("Segoe UI", 13, "bold"))
        self.title_label.pack(anchor="w")

        self.intro_label = ttk.Label(self.header_frame, text="", wraplength=700)
        self.intro_label.pack(anchor="w", pady=(2, 0))

        self.source_label = ttk.Label(self.header_frame, text="", style="Faint.TLabel", wraplength=700)
        self.source_label.pack(anchor="w", pady=(2, 0))

        self.prog_box = ttk.Frame(self.header_frame)
        self.prog_box.pack(anchor="w", pady=(4, 0))

        self.lbl_checked = ttk.Label(self.prog_box, text="", font=("Segoe UI", 10, "bold"))
        self.lbl_checked.pack(side="left")

        self.lbl_save = ttk.Label(self.prog_box, text="", font=("Segoe UI", 10, "bold"))
        self.lbl_save.pack(side="left")

        # Filter bar
        self.filter_frame = ttk.Frame(self.detail_frame)
        self.filter_frame.pack(fill="x", pady=(0, 6))

        ttk.Label(self.filter_frame, text="Status:").pack(side="left", padx=(0, 4))
        self.combo_status = ttk.Combobox(self.filter_frame, values=["All", "Not checked", "Checked"], state="readonly", width=12)
        self.combo_status.set("All")
        self.combo_status.pack(side="left", padx=(0, 10))
        self.combo_status.bind("<<ComboboxSelected>>", lambda e: self._apply_filters(reset_scroll=True))

        ttk.Label(self.filter_frame, text="Era:").pack(side="left", padx=(0, 4))
        self.combo_era = ttk.Combobox(self.filter_frame, values=["All", "Child", "Adult", "Either"], state="readonly", width=10)
        self.combo_era.set("All")
        self.combo_era.pack(side="left", padx=(0, 10))
        self.combo_era.bind("<<ComboboxSelected>>", lambda e: self._apply_filters(reset_scroll=True))

        self.lbl_area = ttk.Label(self.filter_frame, text="Area:")
        self.combo_area = ttk.Combobox(self.filter_frame, state="readonly", width=16)
        self.combo_area.bind("<<ComboboxSelected>>", lambda e: self._apply_filters(reset_scroll=True))

        self.btn_check_all = ttk.Button(self.filter_frame, text="Check all", command=self._check_all)
        self.btn_check_all.pack(side="left", padx=(0, 6))

        self.btn_uncheck_all = ttk.Button(self.filter_frame, text="Uncheck all", command=self._uncheck_all)
        self.btn_uncheck_all.pack(side="left")

        # Scrollable Cards Canvas
        self.cards_container = ttk.Frame(self.detail_frame)
        self.cards_container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(self.cards_container, bd=0, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.cards_container, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.cards_inner = tk.Frame(self.canvas, bg=self.palette.get("bg", "#f4f5f7"))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.cards_inner, anchor="nw")

        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.cards_inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        # Mouse wheel binding (bound globally once at setup, never unbound)
        self.bind_all("<MouseWheel>", self._on_mousewheel)
        self.bind_all("<Button-4>", self._on_mousewheel_linux_up)
        self.bind_all("<Button-5>", self._on_mousewheel_linux_down)

        # Dynamic update listeners for save counters
        for counter_info in SAVE_COUNTERS.values():
            var_name = counter_info["var_name"]
            var = getattr(self.app, var_name, None)
            if isinstance(var, tk.StringVar):
                var.trace_add("write", lambda *a: self._update_progress_header())

        # Load guides and populate
        self.guides = load_guides(
            resource_dir=self.resource_dir,
            app_dir=self.app_dir,
            status_callback=self._on_status_msg
        )
        self.guides_by_id = {g["id"]: g for g in self.guides}

        self._rendered_groups = set()
        self._init_guide_tree()
        if self.guides:
            self._select_guide_initial(self.guides[0]["id"])

        self.bind("<Map>", self._on_frame_mapped)

    def _on_frame_mapped(self, event):
        if event.widget == self:
            self.ensure_cards_built()

    def _select_guide_initial(self, guide_id):
        item_id = f"guide:{guide_id}"
        if self.guide_tree.exists(item_id):
            self.guide_tree.selection_set(item_id)
            self.guide_tree.focus(item_id)
        self.selected_item = item_id
        guide = self.guides_by_id.get(guide_id)
        if guide:
            self.current_guide = guide
            self._update_guide_header_and_controls(guide)

    def _update_guide_header_and_controls(self, guide):
        self.title_label.configure(text=guide.get("title", ""))
        self.intro_label.configure(text=guide.get("intro", ""))
        source_note = guide.get("source_note", "")
        if source_note:
            self.source_label.configure(text=source_note)
            self.source_label.pack(anchor="w", pady=(2, 0))
        else:
            self.source_label.pack_forget()

        # Check for groups and configure Area combobox
        groups = []
        seen = set()
        for e in guide.get("entries", []):
            grp = e.get("group")
            if grp and grp not in seen:
                seen.add(grp)
                groups.append(grp)

        if groups:
            self._has_groups = True
            self.lbl_area.pack(side="left", padx=(0, 4), before=self.btn_check_all)
            self.combo_area.pack(side="left", padx=(0, 10), before=self.btn_check_all)
            self.combo_area["values"] = ["All"] + groups
            self.combo_area.set("All")
        else:
            self._has_groups = False
            self.lbl_area.pack_forget()
            self.combo_area.pack_forget()

        slot_key = self.get_current_slot_key()
        gid = guide["id"]
        self.checked_set = self.get_effective_checked_entries(slot_key, gid)
        self._update_progress_header()

    def ensure_cards_built(self):
        if not self.current_guide:
            if self.guides:
                self.select_guide(self.guides[0]["id"])
            return
        gid = self.current_guide["id"]
        cards = self.cards_by_guide.get(gid)
        if not cards:
            self._load_guide(self.current_guide)

    @property
    def palette(self):
        return getattr(self.app, "palette", {})

    def _on_status_msg(self, msg):
        if hasattr(self.app, "status") and hasattr(self.app.status, "set"):
            self.app.status.set(msg)

    def get_current_slot_key(self):
        active_slot = getattr(self.app, "active_slot", None)
        slot_dir = getattr(active_slot, "slot_dir", None)
        return get_slot_key(slot_dir)

    def get_image_path(self, guide_id, n):
        img_dir = os.path.join(self.resource_dir, "guides", "images", str(guide_id))
        candidates = [f"{n}.png"]
        if PIL_AVAILABLE:
            candidates.extend([f"{n}.jpg", f"{n}.jpeg", f"{n}.webp"])
        for fname in candidates:
            cand_path = os.path.join(img_dir, fname)
            if os.path.exists(cand_path):
                return cand_path
        return os.path.join(img_dir, f"{n}.png")

    def invalidate_image_cache(self, path):
        keys_to_del = [k for k in self.image_cache if k[0] == path]
        for k in keys_to_del:
            del self.image_cache[k]

    def get_thumbnail(self, image_path):
        if not os.path.exists(image_path):
            return None
        try:
            mtime = os.path.getmtime(image_path)
            cache_key = (image_path, mtime)
            if cache_key in self.image_cache:
                return self.image_cache[cache_key]

            if PIL_AVAILABLE:
                with Image.open(image_path) as img:
                    w, h = img.size
                    if w <= 0 or h <= 0:
                        return None
                    scale = min(480 / w, 270 / h, 1.0)
                    new_w = max(1, int(round(w * scale)))
                    new_h = max(1, int(round(h * scale)))
                    thumb = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(thumb)
            else:
                photo = tk.PhotoImage(file=image_path)
                w = photo.width()
                h = photo.height()
                if w <= 0 or h <= 0:
                    return None
                if w > 480 or h > 270:
                    sub_x = math.ceil(w / 480)
                    sub_y = math.ceil(h / 270)
                    sub = max(sub_x, sub_y, 1)
                    photo = photo.subsample(sub, sub)

            self.image_cache[cache_key] = photo
            return photo
        except Exception:
            return None

    def _init_guide_tree(self):
        self.guide_tree.delete(*self.guide_tree.get_children())
        slot_key = self.get_current_slot_key()
        for g in self.guides:
            gid = g["id"]
            checked = self.get_effective_checked_entries(slot_key, gid)
            total = g.get("total", len(g.get("entries", [])))
            self.guide_tree.insert("", "end", iid=f"guide:{gid}", text=f"{g['title']}  {len(checked)}/{total}")

    def refresh_left_list(self):
        slot_key = self.get_current_slot_key()
        for g in self.guides:
            gid = g["id"]
            item_id = f"guide:{gid}"
            if self.guide_tree.exists(item_id):
                checked = self.get_effective_checked_entries(slot_key, gid)
                total = g.get("total", len(g.get("entries", [])))
                self.guide_tree.item(item_id, text=f"{g['title']}  {len(checked)}/{total}")

    def select_guide(self, guide_id):
        item_id = f"guide:{guide_id}"
        if self.guide_tree.exists(item_id):
            self.guide_tree.selection_set(item_id)
            self.guide_tree.focus(item_id)
            self._show_item(item_id)

    def _on_guide_tree_select(self, event):
        sel = self.guide_tree.selection()
        if not sel:
            return
        if not self.winfo_ismapped():
            # Selection events also fire while the Guides tab is hidden (e.g. the initial selection at
            # startup). Only remember the choice; ensure_cards_built() builds it when the tab is shown.
            guide = self.guides_by_id.get(sel[0][len("guide:"):])
            if guide:
                self.selected_item = sel[0]
                self.current_guide = guide
                self._update_guide_header_and_controls(guide)
            return
        self._show_item(sel[0])

    def _show_item(self, item_id):
        self.selected_item = item_id
        if item_id.startswith("guide:"):
            gid = item_id[len("guide:"):]
            guide = self.guides_by_id.get(gid)
            if guide:
                self._load_guide(guide)

    def _load_guide(self, guide):
        self.current_guide = guide
        self._build_generation += 1
        current_gen = self._build_generation

        if self._batch_job is not None:
            try:
                self.after_cancel(self._batch_job)
            except Exception:
                pass
            self._batch_job = None

        self._update_guide_header_and_controls(guide)

        gid = guide["id"]

        # Hide any cards and headings belonging to other guides
        for other_gid, other_cards in self.cards_by_guide.items():
            if other_gid != gid:
                for card in other_cards:
                    card.border_frame.pack_forget()
        for other_gid, other_headings in self.headings_by_guide.items():
            if other_gid != gid:
                for heading in other_headings.values():
                    heading.frame.pack_forget()

        entries = guide.get("entries", [])
        cards = self.cards_by_guide.setdefault(gid, [])
        self.headings_by_guide.setdefault(gid, {})

        if len(cards) == 0:
            self._rendered_groups = set()
            start = 0
            if len(entries) > 0:
                end = min(self.BATCH_SIZE, len(entries))
                canvas_width = self.canvas.winfo_width()
                wrap = max(240, canvas_width - 50) if canvas_width > 100 else 600
                new_cards = []
                for i in range(start, end):
                    entry = entries[i]
                    card = GuideCard(self.cards_inner, entry, gid, self)
                    card.update_wraplength(wrap)
                    card.set_checked(entry["n"] in self.checked_set, update_guides_frame=False)
                    cards.append(card)
                    new_cards.append(card)

                self._append_batch_cards(gid, new_cards)
                self.canvas.yview_moveto(0.0)

                if len(cards) < len(entries):
                    self._batch_job = self.after(1, lambda: self._build_next_batch(gid, current_gen))
        else:
            for card in cards:
                card.set_checked(card.n in self.checked_set, update_guides_frame=False)
            self._apply_filters(reset_scroll=True)
            if len(cards) < len(entries):
                self._batch_job = self.after(1, lambda: self._build_next_batch(gid, current_gen))

    def _build_next_batch(self, gid, gen):
        if gen != self._build_generation:
            return
        if not self.current_guide or self.current_guide.get("id") != gid:
            return
        if not self.winfo_exists():
            return

        entries = self.current_guide.get("entries", [])
        cards = self.cards_by_guide.get(gid, [])
        start = len(cards)
        if start >= len(entries):
            self._batch_job = None
            return

        end = min(start + self.BATCH_SIZE, len(entries))
        canvas_width = self.canvas.winfo_width()
        wrap = max(240, canvas_width - 50) if canvas_width > 100 else 600
        new_cards = []
        for i in range(start, end):
            entry = entries[i]
            card = GuideCard(self.cards_inner, entry, gid, self)
            card.update_wraplength(wrap)
            card.set_checked(entry["n"] in self.checked_set, update_guides_frame=False)
            cards.append(card)
            new_cards.append(card)

        self._append_batch_cards(gid, new_cards)

        if len(cards) < len(entries):
            self._batch_job = self.after(1, lambda: self._build_next_batch(gid, gen))
        else:
            self._batch_job = None

    def _card_matches_filters(self, card):
        status_filter = self.combo_status.get()
        era_filter = self.combo_era.get()
        area_filter = self.combo_area.get() if (hasattr(self, "combo_area") and getattr(self, "_has_groups", False)) else "All"

        if status_filter == "Checked" and not card.is_checked:
            return False
        if status_filter == "Not checked" and card.is_checked:
            return False

        card_era = card.entry.get("era", "")
        if era_filter != "All" and era_filter != card_era:
            return False

        card_group = card.entry.get("group", "")
        if area_filter != "All" and area_filter != card_group:
            return False

        return True

    def _append_batch_cards(self, gid, new_cards):
        if not self.current_guide or self.current_guide.get("id") != gid:
            return
        has_groups = getattr(self, "_has_groups", False)
        headings = self.headings_by_guide.setdefault(gid, {})
        if not hasattr(self, "_rendered_groups") or self._rendered_groups is None:
            self._rendered_groups = set()

        for card in new_cards:
            if self._card_matches_filters(card):
                grp = card.entry.get("group")
                if has_groups and grp and grp not in self._rendered_groups:
                    if grp not in headings:
                        headings[grp] = GroupHeading(self.cards_inner, grp, self)
                    headings[grp].frame.pack(fill="x", expand=True, padx=8, pady=(10, 4))
                    self._rendered_groups.add(grp)
                card.border_frame.pack(fill="x", expand=True, padx=8, pady=5)

    def _update_progress_header(self):
        if not self.current_guide:
            return
        checked_count = len(self.checked_set)
        total = self.current_guide.get("total", len(self.current_guide.get("entries", [])))
        self.lbl_checked.configure(text=f"Checked: {checked_count} / {total}")

        counter_type = self.current_guide.get("save_counter")
        counter_config = SAVE_COUNTERS.get(counter_type)

        if counter_config and getattr(self.app, "active_slot", None):
            var_name = counter_config["var_name"]
            max_val = counter_config.get("total") or total
            var = getattr(self.app, var_name, None)
            try:
                save_val = int(var.get()) if var else 0
            except (ValueError, TypeError):
                save_val = 0
            self.lbl_save.configure(text=f"  ·  Save file: {save_val} / {max_val}")
            if save_val != checked_count:
                self.lbl_save.configure(style="Warn.TLabel")
            else:
                self.lbl_save.configure(style="TLabel")
            self.lbl_save.pack(side="left")
        else:
            self.lbl_save.pack_forget()

    def handle_shift_click(self, clicked_card):
        """Handle Shift+Click batch range selection across guide checkboxes."""
        gid = clicked_card.guide_id
        current_state = clicked_card.check_var.get()

        # If no previous click in this guide or invalid anchor, toggle this card and establish anchor
        if getattr(self, "last_clicked_guide", None) != gid or getattr(self, "last_clicked_n", None) is None:
            target_state = not current_state
            clicked_card.check_var.set(target_state)
            clicked_card.set_checked(target_state, update_guides_frame=True)
            self.last_clicked_n = clicked_card.n
            self.last_clicked_guide = gid
            self.last_clicked_state = target_state
            return

        start_n = self.last_clicked_n
        end_n = clicked_card.n

        target_state = not current_state

        low_n = min(start_n, end_n)
        high_n = max(start_n, end_n)

        # Update checked_set for all entries in the range
        entries = self.current_guide.get("entries", []) if self.current_guide else []
        for e in entries:
            en = e.get("n")
            if en is not None and low_n <= en <= high_n:
                if target_state:
                    self.checked_set.add(en)
                else:
                    self.checked_set.discard(en)

        # Update all instantiated card widgets in range
        cards = self.cards_by_guide.get(gid, [])
        for c in cards:
            if low_n <= c.n <= high_n:
                c.check_var.set(target_state)
                c.set_checked(target_state, update_guides_frame=False)

        slot_key = self.get_current_slot_key()
        set_checked_entries(self.app.settings, slot_key, gid, self.checked_set)
        if hasattr(self.app, "store_settings") and callable(self.app.store_settings):
            self.app.store_settings()
        else:
            try:
                from oot_save_editor import store_settings
                store_settings(self.app.settings)
            except Exception:
                pass

        self._update_progress_header()
        self._update_tree_count(gid)

        if self.combo_status.get() != "All":
            self._apply_filters(reset_scroll=False)

        self.last_clicked_n = clicked_card.n
        self.last_clicked_guide = gid
        self.last_clicked_state = target_state

    def get_effective_checked_entries(self, slot_key, gid):
        """Returns union of user-saved checks and auto-checked in-game achievements."""
        saved = get_checked_entries(self.app.settings, slot_key, gid)
        auto = self.compute_auto_checked_entries(gid)
        merged = saved | auto
        if merged != saved:
            set_checked_entries(self.app.settings, slot_key, gid, merged)
            if hasattr(self.app, "store_settings") and callable(self.app.store_settings):
                self.app.store_settings()
            else:
                try:
                    from oot_save_editor import store_settings
                    store_settings(self.app.settings)
                except Exception:
                    pass
        return merged

    def compute_auto_checked_entries(self, guide_id):
        """Inspect the current save slot in self.app and return a set of entry numbers (n)
        that have been completed in-game.
        """
        app = self.app
        s = getattr(app, "active_slot", None)
        if not s or not getattr(s, "loaded", False):
            return set()

        if guide_id in SUPPORTED_GUIDES:
            return collected_entries(
                guide_id,
                getattr(s, "key64", set()),
                lambda h: s.get(h, 0),
                load_table(),
            )

        auto = set()

        # Song data: mapping of song bit index -> (isget_hash, event_hash)
        song_metadata = {
            0: (0x01C20002, 0x2CD669E8),  # 1. Zelda's Lullaby
            1: (None, 0xDB8433F7),        # 3. Epona's Song
            2: (0xD3F8BFCC, 0x3A33F18D),  # 2. Saria's Song
            3: (0x65F28F50, 0xBE4E744F),  # 5. Song of Time
            4: (0x4B415FBB, 0xCF7DAD5C),  # 4. Sun's Song
            5: (0x2B39DD4F, 0x9E1EFBA1),  # 6. Song of Storms
            6: (0xDC0A0B54, 0xD02715E1),  # 7. Minuet of the Forest
            7: (0x49041AB9, 0x40361247),  # 9. Bolero of Fire
            8: (0x3FA63986, 0x85114AE5),  # 10. Serenade of Water
            9: (0x802A36A8, 0x9E4C93F4),  # 12. Requiem of Spirit
            10: (0xC2FB95F4, 0xD0D30EF6), # 11. Nocturne of Shadow
            11: (0x0895A9FF, 0xEF7B5505), # 8. Prelude of Light
        }

        def has_song(bit_idx):
            if hasattr(app, "song_vars") and bit_idx in app.song_vars:
                try:
                    if app.song_vars[bit_idx].get():
                        return True
                except Exception:
                    pass
            if bit_idx in song_metadata:
                isget_h, event_h = song_metadata[bit_idx]
                if isget_h and s.get(isget_h, 0):
                    return True
                if event_h and s.get(event_h, 0):
                    return True
            if bit_idx == 4:
                # Sun's Song: Royal Family Tomb clear, open, and break flags
                if s.get(0x4B415FBB, 0) or s.get(0xCF7DAD5C, 0) or s.get(0x3EAC8ADA, 0) or s.get(0x51E2E4B1, 0):
                    return True
            if bit_idx == 13:
                # Scarecrow's Song
                if s.get(0x3A4126EC, 0) or s.get(0xFDF0F4B8, 0) or s.get(0x8C1DA521, 0):
                    return True
            return False

        def has_quest(kh):
            if hasattr(app, "quest_vars") and kh in app.quest_vars:
                try:
                    return bool(app.quest_vars[kh].get())
                except Exception:
                    pass
            return bool(s.get(kh, 0))

        def has_sword(name):
            if hasattr(app, "owned_swords") and name in app.owned_swords:
                try:
                    return bool(app.owned_swords[name].get())
                except Exception:
                    pass
            sword_map = {
                "Kokiri Sword": 0xEEB495B9,
                "Master Sword": 0xF1C45294,
                "Giant's Knife": 0x396A5C02,
                "Biggoron's Sword": 0xB0B3E399,
            }
            return bool(s.get(sword_map.get(name, 0), 0))

        def has_shield(name):
            if hasattr(app, "owned_shields") and name in app.owned_shields:
                try:
                    return bool(app.owned_shields[name].get())
                except Exception:
                    pass
            shield_map = {
                "Deku Shield": 0x7CA64F23,
                "Hylian Shield": 0x08BEFD3A,
                "Mirror Shield": 0xF58E0E2F,
            }
            return bool(s.get(shield_map.get(name, 0), 0))

        def has_tunic(name):
            if hasattr(app, "owned_tunics") and name in app.owned_tunics:
                try:
                    return bool(app.owned_tunics[name].get())
                except Exception:
                    pass
            tunic_map = {
                "Kokiri Tunic": 0x84BA0D24,
                "Goron Tunic": 0x21ECBD19,
                "Zora Tunic": 0xB816AF94,
            }
            return bool(s.get(tunic_map.get(name, 0), 0))

        def has_boot(name):
            if hasattr(app, "owned_boots") and name in app.owned_boots:
                try:
                    return bool(app.owned_boots[name].get())
                except Exception:
                    pass
            boot_map = {
                "Iron Boots": 0x2BAD189A,
                "Hover Boots": 0xC9220366,
            }
            return bool(s.get(boot_map.get(name, 0), 0))

        def get_capacity(group):
            if hasattr(app, "capacity_vars") and group in app.capacity_vars:
                try:
                    return int(app.capacity_vars[group].get())
                except (ValueError, TypeError):
                    pass
            cap_hashes = {
                "seeds": 0xAE8CC742,
                "nuts": 0x735B00F7,
                "sticks": 0x457616B0,
                "bombs": 0xE753508B,
                "arrows": 0x418DB791,
            }
            if group in cap_hashes:
                val = s.get(cap_hashes[group], 0)
                if val:
                    return val
            if group == "wallet":
                if s.get(0xAFA4BB52, 0) or s.get(0xCDCC9ADD, 0):
                    return 1000
                if s.get(0x2D2C874B, 0) or s.get(0x9086A22E, 0):
                    return 500
                return 200
            # Check equip_vars for labels with numbers
            if hasattr(app, "equip_vars"):
                label_map = {
                    "wallet": ["wallet"], "arrows": ["quiver"], "bombs": ["bomb_bag"],
                    "seeds": ["bullet_bag"], "sticks": ["stick_bag"], "nuts": ["nut_bag"]
                }
                for k in label_map.get(group, []):
                    if k in app.equip_vars:
                        txt = str(app.equip_vars[k].get())
                        import re
                        m = re.findall(r"\d+", txt)
                        if m:
                            try: return int(m[-1])
                            except Exception: pass
            return 0

        # 1. SONGS
        if guide_id == "songs":
            if has_song(0): auto.add(1)   # Zelda's Lullaby
            if has_song(2): auto.add(2)   # Saria's Song
            if has_song(1): auto.add(3)   # Epona's Song
            if has_song(4): auto.add(4)   # Sun's Song
            if has_song(3): auto.add(5)   # Song of Time
            if has_song(5): auto.add(6)   # Song of Storms
            if has_song(6): auto.add(7)   # Minuet of the Forest
            if has_song(11): auto.add(8)  # Prelude of Light
            if has_song(7): auto.add(9)   # Bolero of Fire
            if has_song(8): auto.add(10)  # Serenade of Water
            if has_song(10): auto.add(11) # Nocturne of Shadow
            if has_song(9): auto.add(12)  # Requiem of Spirit
            if has_song(13): auto.add(13) # Scarecrow's Song

        # 2. TUNICS
        elif guide_id == "tunics":
            auto.add(1)  # Hero's Clothes / Kokiri Tunic (always available)
            if has_tunic("Goron Tunic") or s.get(0xAEF28373, 0) or s.get(0xAE5611AF, 0): auto.add(2)
            if has_tunic("Zora Tunic") or s.get(0x27EB8574, 0) or s.get(0x4F5A929C, 0): auto.add(3)

        # 3. WALLETS
        elif guide_id == "wallets":
            cap = get_capacity("wallet")
            if cap >= 500 or s.get(0x2D2C874B, 0) or s.get(0x9086A22E, 0): auto.add(1)
            if cap >= 1000 or s.get(0xAFA4BB52, 0) or s.get(0xCDCC9ADD, 0): auto.add(2)

        # 4. BOMB BAGS
        elif guide_id == "bomb_bags":
            cap = get_capacity("bombs")
            if cap >= 30 or s.get(0xE5FF45AA, 0): auto.add(1)
            if cap >= 40 or s.get(0xBD3CA2C6, 0): auto.add(2)

        # 5. QUIVERS
        elif guide_id == "quivers":
            cap = get_capacity("arrows")
            if cap >= 40 or s.get(0x3BB370E1, 0): auto.add(1)
            if cap >= 50 or s.get(0xD331C7DA, 0) or s.get(0x7C6E3B6B, 0): auto.add(2)

        # 6. DEKU SEED BAG
        elif guide_id == "deku_seed_bag":
            cap = get_capacity("seeds")
            if cap >= 40 or s.get(0x9A30A9E5, 0): auto.add(1)
            if cap >= 50 or s.get(0x7B9673F5, 0): auto.add(2)

        # 7. DEKU STICKS
        elif guide_id == "deku_sticks":
            cap = get_capacity("sticks")
            if cap >= 20 or s.get(0x41DB7AB5, 0): auto.add(1)
            if cap >= 30 or s.get(0x48E53698, 0): auto.add(2)

        # 8. DEKU NUTS
        elif guide_id == "deku_nuts":
            cap = get_capacity("nuts")
            if cap >= 30 or s.get(0xEAA1785E, 0): auto.add(1)
            if cap >= 40 or s.get(0xD60E4B23, 0): auto.add(2)

        # 9. BOTTLES
        elif guide_id == "bottles":
            bottle_hashes = [0xD53CE3A7, 0xFCA29A04, 0x893216A1, 0x5324F9D3, 0xC92B16BE]
            owned_bottles = sum(1 for h in bottle_hashes if s.get(h, 0) > 0)
            if hasattr(app, "bottles"):
                app_owned = 0
                for b in app.bottles:
                    val = b["var"].get() if "var" in b else ""
                    if val and val != "Empty" and val != "None":
                        app_owned += 1
                owned_bottles = max(owned_bottles, app_owned)
            if s.get(0x084DA83F, 0) > 0: auto.add(2)  # Lon Lon Super Cucco
            if s.get(0x7A7961C3, 0) > 0: auto.add(3)  # Kakariko Cucco Lady
            if has_quest(0xB8E3BF45) or s.get(0xB8E3BF45, 0) or s.get(0x35639356, 0): auto.add(4)  # Ruto's letter
            for idx in range(1, owned_bottles + 1):
                if idx <= 5: auto.add(idx)

        # 10. GREAT FAIRIES
        elif guide_id == "great_fairies":
            spells = getattr(app, "spells_vars", {})
            has_dins = (spells.get("Din's Fire").get() if "Din's Fire" in spells else False) or s.get(0xB796C16D, 0) or s.get(0x196E812D, 0) or s.get(0x4FB5C095, 0)
            if has_dins: auto.add(1)  # Din's Fire
            has_farores = (spells.get("Farore's Wind").get() if "Farore's Wind" in spells else False) or s.get(0x47F2CA87, 0) or s.get(0x43734D88, 0) or s.get(0x9B335772, 0)
            if has_farores: auto.add(2)  # Farore's Wind
            has_nayrus = (spells.get("Nayru's Love").get() if "Nayru's Love" in spells else False) or s.get(0xF0828CD0, 0) or s.get(0x4E7D65E1, 0) or s.get(0x960963E8, 0)
            if has_nayrus: auto.add(3)  # Nayru's Love
            m_val = app.v_magic.get() if hasattr(app, "v_magic") else ""
            if m_val in ("Single (48)", "Double (96)") or s.get(0x5E671D92, 0) or s.get(0xB130AC73, 0) or s.get(0x12D63A97, 0) >= 24 or s.get(0x76B18200, 0) >= 24:
                auto.add(4)  # Magic Spin / 24 MP
            if m_val == "Double (96)" or s.get(0x5F043856, 0) or s.get(0x87CA3826, 0) or s.get(0x12D63A97, 0) >= 48 or s.get(0x76B18200, 0) >= 48:
                auto.add(5)  # Doubled Magic / 48 MP
            has_def = (app.v_double_defense.get() if hasattr(app, "v_double_defense") else False) or s.get(0x9A826FAB, 0) or s.get(0x944B88BE, 0) or s.get(0x8D0F04D6, 0)
            if has_def:
                auto.add(6)  # Doubled Defense / Halved Damage

        # 11. KAKARIKO CUCCOS
        elif guide_id == "kakariko_cuccos":
            if s.get(0x7A7961C3, 0) > 0 or s.get(0x893216A1, 0) > 0:
                for n in range(1, 8):
                    auto.add(n)

        # 13. ALL ITEMS
        elif guide_id == "items":
            auto.add(1)   # Kokiri Tunic
            if has_sword("Kokiri Sword"): auto.add(2)
            if has_shield("Deku Shield"): auto.add(3)
            if s.get(0xB9494411, 0) > 0 or get_capacity("sticks") >= 10: auto.add(4)
            if s.get(0xF30D9F54, 0) > 0 or get_capacity("nuts") >= 20: auto.add(5)
            if s.get(0x80D34CE9, 0) > 0: auto.add(6)   # Fairy Slingshot
            if has_quest(0xCBD1E58C): auto.add(7)      # Kokiri Emerald
            if s.get(0xB7DF60F1, 0) > 0: auto.add(8)   # Fairy Ocarina
            if s.get(0x6BE5C3B0, 0) > 0 or s.get(0x409540C5, 0) > 0: auto.add(10)  # Zelda's Letter
            if get_capacity("seeds") >= 40: auto.add(12)
            if get_capacity("seeds") >= 50: auto.add(13)
            if get_capacity("sticks") >= 20: auto.add(14)
            if get_capacity("sticks") >= 30: auto.add(15)
            if has_shield("Hylian Shield"): auto.add(16)
            if get_capacity("wallet") >= 500: auto.add(18)
            if s.get(0xD1317941, 0) or s.get(0xA08F47BE, 0): auto.add(19)  # Goron Bracelet
            if s.get(0xB0A1BF51, 0) or get_capacity("bombs") >= 20: auto.add(20)
            if has_quest(0x7D69AD47): auto.add(21)      # Goron Ruby
            if s.get(0xB796C16D, 0) or s.get(0x196E812D, 0): auto.add(22)  # Din's Fire
            if s.get(0x5E671D92, 0) or s.get(0x12D63A97, 0) >= 24: auto.add(23)   # Magic
            if s.get(0xDF7C517A, 0) > 0 or s.get(0x5AB49C8E, 0) > 0: auto.add(24) # Bombchu
            if get_capacity("nuts") >= 30: auto.add(26)
            if get_capacity("nuts") >= 40: auto.add(27)
            if get_capacity("bombs") >= 30: auto.add(28)
            if get_capacity("bombs") >= 40: auto.add(29)
            if s.get(0x4A6B8851, 0) > 0: auto.add(30)   # Magic Beans
            if s.get(0x1240044B, 0) > 0: auto.add(31)   # Silver Scale
            if s.get(0x47F2CA87, 0) or s.get(0x43734D88, 0): auto.add(33) # Farore's Wind
            if s.get(0xA1D76D31, 0) > 0: auto.add(34)   # Boomerang
            if has_quest(0xB8E3BF45): auto.add(35)      # Zora Sapphire
            if get_capacity("wallet") >= 1000: auto.add(36)
            if s.get(0x54E2A3D1, 0) > 0: auto.add(37)   # Ocarina of Time
            if s.get(0x49D1C374, 0) > 0: auto.add(38)   # Lens of Truth
            auto.add(39)                                # Hero's Clothes
            if has_sword("Master Sword"): auto.add(40)
            if has_quest(0x235C7D9A): auto.add(41)      # Light Medallion
            if s.get(0xDB8433F7, 0) or has_song(1): auto.add(42)  # Epona
            if s.get(0x8573D2CD, 0) > 0 or s.get(0x8499EA34, 0) > 0 or s.get(0x075C539A, 0) > 0: auto.add(43) # Hookshot
            if s.get(0x938D56BF, 0) > 0: auto.add(44)   # Fairy Bow
            if has_quest(0x692D57CB): auto.add(45)      # Forest Medallion
            if get_capacity("arrows") >= 40: auto.add(46)
            if has_tunic("Goron Tunic"): auto.add(48)
            if s.get(0x1AAFDB66, 0) > 0: auto.add(49)   # Megaton Hammer
            if has_quest(0x5CE254A6): auto.add(50)      # Fire Medallion
            if s.get(0x5F043856, 0) or s.get(0x12D63A97, 0) >= 48: auto.add(51) # Doubled Magic
            if has_boot("Iron Boots"): auto.add(52)
            if has_tunic("Zora Tunic"): auto.add(53)
            if s.get(0x8499EA34, 0) > 0 or s.get(0x27BE1283, 0) > 0: auto.add(54) # Longshot
            if has_quest(0x0151A68F): auto.add(55)      # Water Medallion
            if s.get(0x5E529AB9, 0) > 0: auto.add(56)   # Fire Arrow
            if s.get(0x4AEB140A, 0) > 0: auto.add(57)   # Golden Scale
            if has_sword("Biggoron's Sword"): auto.add(58)
            if has_boot("Hover Boots"): auto.add(59)
            if has_quest(0x204D2063): auto.add(60)      # Shadow Medallion
            if has_quest(0xFEB4D56B) or s.get(0xFEB4D56B, 0): auto.add(61)  # Gerudo Card
            if get_capacity("arrows") >= 50: auto.add(62)
            if s.get(0x40735A8D, 0) > 0: auto.add(63)   # Ice Arrow
            if s.get(0xF0828CD0, 0) or s.get(0x4E7D65E1, 0): auto.add(64) # Nayru's Love
            if s.get(0x0012B8C0, 0) > 0: auto.add(65)   # Silver Gauntlets
            if has_shield("Mirror Shield"): auto.add(66)
            if has_quest(0x0C7A5FD0): auto.add(67)      # Spirit Medallion
            if s.get(0xBFB285C8, 0) > 0: auto.add(68)   # Light Arrow
            if s.get(0x40AE1183, 0) > 0: auto.add(69)   # Golden Gauntlets
            if s.get(0x9A826FAB, 0) or s.get(0x944B88BE, 0): auto.add(70) # Doubled Defense
            if s.get(0x51EC97B3, 0) > 0: auto.add(71)   # Heart Pieces
            if s.get(0x04735978, 0) > 0: auto.add(72)   # Tokens

        # 14. HOW TO
        elif guide_id == "how_to":
            if get_capacity("arrows") >= 40 or s.get(0x3BB370E1, 0): auto.add(4)
            if s.get(0x19E5A36B, 0) or s.get(0x5AB49C8E, 0):
                auto.add(17); auto.add(18); auto.add(19)
            if s.get(0x165E7CA, 0) or s.get(0x51D89EF0, 0): auto.add(30)
            if s.get(0x51D89EF0, 0) or s.get(0x07DE3E6F, 0): auto.add(31)
            if s.get(0x07DE3E6F, 0) or s.get(0x58C9BC78, 0): auto.add(32)
            if s.get(0x58C9BC78, 0) or s.get(0xA862D276, 0): auto.add(33)
            if s.get(0xA862D276, 0) or s.get(0x2815C82A, 0): auto.add(34)
            if s.get(0x2815C82A, 0) or s.get(0x897CF7EB, 0): auto.add(35)
            if s.get(0x897CF7EB, 0) or s.get(0x919EA324, 0): auto.add(36)
            if s.get(0x919EA324, 0) or s.get(0x5C41A6B1, 0): auto.add(37)
            if s.get(0x5C41A6B1, 0) or s.get(0xDED8E8D3, 0): auto.add(38)
            if s.get(0xDED8E8D3, 0) or s.get(0xB0B3E399, 0): auto.add(39)

        # 15. STORY GUIDE
        elif guide_id == "story_guide":
            has_emerald = has_quest(0xCBD1E58C)
            has_ruby = has_quest(0x7D69AD47)
            has_sapphire = has_quest(0xB8E3BF45)
            has_light = has_quest(0x235C7D9A)
            has_forest = has_quest(0x692D57CB)
            has_fire = has_quest(0x5CE254A6)
            has_water = has_quest(0x0151A68F)
            has_shadow = has_quest(0x204D2063)
            has_spirit = has_quest(0x0C7A5FD0)

            if has_sword("Kokiri Sword"):
                for n in range(1, 8): auto.add(n)
            if has_emerald:
                for n in range(8, 21): auto.add(n)
            if has_song(0) or s.get(0x6BE5C3B0, 0):
                for n in range(21, 31): auto.add(n)
            if has_song(1): auto.add(31)
            if s.get(0x6BE5C3B0, 0) or has_ruby or has_song(2): auto.add(32)
            if has_song(4):
                auto.add(33); auto.add(34); auto.add(35)
            if has_shield("Hylian Shield"): auto.add(36)
            if has_song(2) or s.get(0xD1317941, 0):
                for n in range(37, 45): auto.add(n)
            if has_ruby:
                for n in range(45, 58): auto.add(n)
            if s.get(0x1240044B, 0) or has_sapphire:
                for n in range(58, 68): auto.add(n)
            if has_sapphire:
                for n in range(68, 83): auto.add(n)
            if has_light or has_sword("Master Sword"):
                for n in range(83, 85): auto.add(n)
            if s.get(0x8573D2CD, 0) or s.get(0x075C539A, 0) or s.get(0x8499EA34, 0) or has_song(6):
                for n in range(85, 93): auto.add(n)
            if has_forest:
                for n in range(93, 108): auto.add(n)
            if has_tunic("Goron Tunic"):
                auto.add(108); auto.add(109)
            if has_song(7):
                auto.add(110); auto.add(111)
            if s.get(0x1AAFDB66, 0) > 0: auto.add(117)
            if has_fire:
                for n in range(108, 122): auto.add(n)
            if has_boot("Iron Boots") or has_song(8):
                for n in range(122, 128): auto.add(n)
            if s.get(0x8499EA34, 0) > 0 or s.get(0x27BE1283, 0) > 0: auto.add(134)
            if has_water:
                for n in range(128, 140): auto.add(n)
            if has_song(5):
                auto.add(139); auto.add(140)
            if s.get(0x49D1C374, 0) > 0:
                for n in range(140, 145): auto.add(n)
            if has_song(10):
                for n in range(145, 150): auto.add(n)
            if has_boot("Hover Boots"): auto.add(156)
            if has_shadow:
                for n in range(145, 162): auto.add(n)
            if has_quest(0xFEB4D56B) or s.get(0xFEB4D56B, 0):
                for n in range(162, 166): auto.add(n)
            if has_song(9):
                for n in range(166, 168): auto.add(n)
            if s.get(0x0012B8C0, 0) > 0: auto.add(169)
            if has_shield("Mirror Shield"): auto.add(171)
            if has_spirit:
                for n in range(168, 173): auto.add(n)
            if s.get(0xBFB285C8, 0) > 0: auto.add(174)
            if s.get(0x40AE1183, 0) > 0: auto.add(175)

        return auto

    def on_card_checked_changed(self, guide_id, n, checked):
        if checked:
            self.checked_set.add(n)
        else:
            self.checked_set.discard(n)

        slot_key = self.get_current_slot_key()
        set_checked_entries(self.app.settings, slot_key, guide_id, self.checked_set)

        if hasattr(self.app, "store_settings") and callable(self.app.store_settings):
            self.app.store_settings()
        else:
            try:
                from oot_save_editor import store_settings
                store_settings(self.app.settings)
            except Exception:
                pass

        self._update_progress_header()
        self._update_tree_count(guide_id)
        if self.combo_status.get() != "All":
            self._apply_filters(reset_scroll=False)

    def _update_tree_count(self, guide_id):
        guide = self.guides_by_id.get(guide_id)
        if not guide:
            return
        slot_key = self.get_current_slot_key()
        checked = get_checked_entries(self.app.settings, slot_key, guide_id)
        total = guide.get("total", len(guide.get("entries", [])))
        item_id = f"guide:{guide_id}"
        if self.guide_tree.exists(item_id):
            self.guide_tree.item(item_id, text=f"{guide['title']}  {len(checked)}/{total}")

    def on_slot_changed(self):
        """Called when save slot changes or is reloaded."""
        self.refresh_left_list()
        if self.current_guide:
            slot_key = self.get_current_slot_key()
            gid = self.current_guide["id"]
            self.checked_set = self.get_effective_checked_entries(slot_key, gid)
            if gid in self.cards_by_guide:
                for card in self.cards_by_guide[gid]:
                    card.set_checked(card.n in self.checked_set, update_guides_frame=False)
                if self.cards_by_guide[gid] and self.combo_status.get() != "All":
                    self._apply_filters(reset_scroll=False)
            self._update_progress_header()

    def _apply_filters(self, reset_scroll=False):
        if not self.current_guide:
            return
        gid = self.current_guide["id"]

        # Capture current scroll position before modifying pack layout if keeping position
        prev_scroll = None
        if not reset_scroll:
            try:
                yview = self.canvas.yview()
                if yview:
                    prev_scroll = yview[0]
            except Exception:
                prev_scroll = None

        cards = self.cards_by_guide.get(gid, [])
        headings = self.headings_by_guide.setdefault(gid, {})

        for card in cards:
            card.border_frame.pack_forget()
        for heading in headings.values():
            heading.frame.pack_forget()

        self._rendered_groups = set()
        has_groups = getattr(self, "_has_groups", False)

        for card in sorted(cards, key=lambda c: c.n):
            if self._card_matches_filters(card):
                grp = card.entry.get("group")
                if has_groups and grp and grp not in self._rendered_groups:
                    if grp not in headings:
                        headings[grp] = GroupHeading(self.cards_inner, grp, self)
                    headings[grp].frame.pack(fill="x", expand=True, padx=8, pady=(10, 4))
                    self._rendered_groups.add(grp)
                card.border_frame.pack(fill="x", expand=True, padx=8, pady=5)

        self.cards_inner.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        if reset_scroll or prev_scroll is None:
            self.canvas.yview_moveto(0.0)
        else:
            self.canvas.yview_moveto(prev_scroll)

    def _check_all(self):
        if not self.current_guide:
            return
        gid = self.current_guide["id"]
        status_filter = self.combo_status.get()
        era_filter = self.combo_era.get()
        area_filter = self.combo_area.get() if (hasattr(self, "combo_area") and getattr(self, "_has_groups", False)) else "All"

        entries = self.current_guide.get("entries", [])
        for entry in entries:
            n = entry["n"]
            match_status = True
            if status_filter == "Checked" and n not in self.checked_set:
                match_status = False
            elif status_filter == "Not checked" and n in self.checked_set:
                match_status = False

            card_era = entry.get("era", "")
            match_era = True if (era_filter == "All" or era_filter == card_era) else False

            card_group = entry.get("group", "")
            match_area = True if (area_filter == "All" or area_filter == card_group) else False

            if match_status and match_era and match_area:
                self.checked_set.add(n)

        for card in self.cards_by_guide.get(gid, []):
            card.set_checked(card.n in self.checked_set, update_guides_frame=False)

        slot_key = self.get_current_slot_key()
        set_checked_entries(self.app.settings, slot_key, gid, self.checked_set)
        if hasattr(self.app, "store_settings") and callable(self.app.store_settings):
            self.app.store_settings()
        else:
            try:
                from oot_save_editor import store_settings
                store_settings(self.app.settings)
            except Exception:
                pass

        self._update_progress_header()
        self._update_tree_count(gid)
        self._apply_filters(reset_scroll=False)

    def _uncheck_all(self):
        if not self.current_guide:
            return
        gid = self.current_guide["id"]
        guide_title = self.current_guide.get("title", "this guide")
        if not messagebox.askyesno("Uncheck All", f"Uncheck all entries in '{guide_title}'?", parent=self):
            return

        status_filter = self.combo_status.get()
        era_filter = self.combo_era.get()
        area_filter = self.combo_area.get() if (hasattr(self, "combo_area") and getattr(self, "_has_groups", False)) else "All"

        entries = self.current_guide.get("entries", [])
        for entry in entries:
            n = entry["n"]
            match_status = True
            if status_filter == "Checked" and n not in self.checked_set:
                match_status = False
            elif status_filter == "Not checked" and n in self.checked_set:
                match_status = False

            card_era = entry.get("era", "")
            match_era = True if (era_filter == "All" or era_filter == card_era) else False

            card_group = entry.get("group", "")
            match_area = True if (area_filter == "All" or area_filter == card_group) else False

            if match_status and match_era and match_area:
                self.checked_set.discard(n)

        for card in self.cards_by_guide.get(gid, []):
            card.set_checked(card.n in self.checked_set, update_guides_frame=False)

        slot_key = self.get_current_slot_key()
        set_checked_entries(self.app.settings, slot_key, gid, self.checked_set)
        if hasattr(self.app, "store_settings") and callable(self.app.store_settings):
            self.app.store_settings()
        else:
            try:
                from oot_save_editor import store_settings
                store_settings(self.app.settings)
            except Exception:
                pass

        self._update_progress_header()
        self._update_tree_count(gid)
        self._apply_filters(reset_scroll=False)

    def refresh_theme(self, palette=None):
        """Re-colors all custom widgets to match the current theme palette."""
        p = palette or self.palette
        self.canvas.configure(bg=p.get("bg", "#f4f5f7"))
        self.cards_inner.configure(bg=p.get("bg", "#f4f5f7"))
        for cards in self.cards_by_guide.values():
            for card in cards:
                card.refresh_theme(p)
        for headings in self.headings_by_guide.values():
            for heading in headings.values():
                heading.refresh_theme(p)

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)
        wrap = max(240, event.width - 50)
        self.intro_label.configure(wraplength=max(300, event.width - 20))
        self.source_label.configure(wraplength=max(300, event.width - 20))
        if self.current_guide and self.current_guide["id"] in self.cards_by_guide:
            for card in self.cards_by_guide[self.current_guide["id"]]:
                card.update_wraplength(wrap)

    def _is_guides_tab_visible(self):
        """Check if the Guides tab / frame is currently visible."""
        if not self.winfo_exists():
            return False
        cur = self.master
        while cur is not None:
            if isinstance(cur, ttk.Notebook):
                try:
                    if cur.select() != str(self):
                        return False
                except Exception:
                    pass
                break
            cur = getattr(cur, "master", None)
        return True

    def _should_scroll(self, event):
        """Verify pointer is over canvas or a descendant and Guides tab is visible."""
        if not self._is_guides_tab_visible():
            return False
        if not self.canvas.winfo_exists():
            return False
        try:
            widget = self.winfo_containing(event.x_root, event.y_root)
        except Exception:
            return False
        if widget is None:
            return False

        cur = widget
        while cur is not None:
            if cur == self.canvas:
                return True
            cur = getattr(cur, "master", None)
        return False

    def _on_mousewheel(self, event):
        if not self._should_scroll(event):
            return
        if sys.platform == "darwin":
            delta = -1 * event.delta
        else:
            delta = int(-1 * (event.delta / 120)) if event.delta else 0
            if delta == 0 and event.delta != 0:
                delta = -1 if event.delta > 0 else 1
        if delta:
            self.canvas.yview_scroll(delta, "units")

    def _on_mousewheel_linux_up(self, event):
        if not self._should_scroll(event):
            return
        self.canvas.yview_scroll(-1, "units")

    def _on_mousewheel_linux_down(self, event):
        if not self._should_scroll(event):
            return
        self.canvas.yview_scroll(1, "units")

    def destroy(self):
        """Cancel pending background batch jobs before destroying widget hierarchy."""
        if getattr(self, "_batch_job", None) is not None:
            try:
                self.after_cancel(self._batch_job)
            except Exception:
                pass
            self._batch_job = None
        super().destroy()
