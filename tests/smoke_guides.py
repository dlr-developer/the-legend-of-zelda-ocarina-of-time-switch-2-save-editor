import os
import sys

# Ensure repo root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import tests._isolate
from oot_save_editor import OOTEditor


def main():
    app = OOTEditor()
    app.withdraw()

    # 1. Verify Progress & Inspector tab has Story Progress as first sub-tab and selected
    pi_tab_index = None
    for idx, tab_id in enumerate(app.notebook.tabs()):
        if app.notebook.tab(tab_id, "text") == "Progress & Inspector":
            pi_tab_index = idx
            break

    if pi_tab_index is None:
        raise RuntimeError("Progress & Inspector tab not found in notebook")

    app.notebook.select(pi_tab_index)
    if not hasattr(app, "progress_sub_nb"):
        raise RuntimeError("progress_sub_nb attribute not found on app")

    sub_tabs = app.progress_sub_nb.tabs()
    if not sub_tabs or app.progress_sub_nb.tab(sub_tabs[0], "text") != "Story Progress":
        raise RuntimeError("Story Progress sub-tab is not first in Progress & Inspector")

    selected_sub = app.progress_sub_nb.select()
    if selected_sub != sub_tabs[0]:
        raise RuntimeError("Story Progress is not the selected sub-tab on startup")

    if not hasattr(app, "walk_tree") or app.walk_tree is None:
        raise RuntimeError("walk_tree attribute not found on app")

    # 2. Find and select the Guides tab
    guides_tab_index = None
    for idx, tab_id in enumerate(app.notebook.tabs()):
        if app.notebook.tab(tab_id, "text") == "Guides":
            guides_tab_index = idx
            break

    if guides_tab_index is not None:
        app.notebook.select(guides_tab_index)
    elif hasattr(app, "guides_frame"):
        app.notebook.select(app.guides_frame)
    else:
        raise RuntimeError("Guides tab not found in notebook")

    # Verify no 'story' item in guides tree and first guide is selected
    if hasattr(app, "guides_frame") and app.guides_frame:
        if app.guides_frame.guide_tree.exists("story"):
            raise RuntimeError("Guides tree should not contain 'story' item")
        app.guides_frame.select_guide("heart_pieces")
    else:
        raise RuntimeError("guides_frame attribute not found on app")

    app.update()
    app.destroy()
    print("Smoke test passed successfully.")


if __name__ == "__main__":
    main()
