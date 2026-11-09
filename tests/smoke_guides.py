import os
import sys

# Ensure repo root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from oot_save_editor import OOTEditor


def main():
    app = OOTEditor()
    app.withdraw()

    # Find and select the Guides tab
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

    # Select Heart Pieces guide
    if hasattr(app, "guides_frame") and app.guides_frame:
        app.guides_frame.select_guide("heart_pieces")
    else:
        raise RuntimeError("guides_frame attribute not found on app")

    app.update()
    app.destroy()
    print("Smoke test passed successfully.")


if __name__ == "__main__":
    main()
