"""Build release standalone executable and release zip using PyInstaller."""
import os
import shutil
import subprocess
import sys
import zipfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from oot_save_editor import APP_VERSION


def main():
    dist_dir = os.path.join(REPO_ROOT, "dist")
    build_dir = os.path.join(REPO_ROOT, "build")
    os.makedirs(dist_dir, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--windowed",
        "--name",
        "OOT-Switch2-Save-Editor",
        "--icon",
        os.path.join(REPO_ROOT, "assets", "icon.ico"),
        "--distpath",
        dist_dir,
        "--workpath",
        build_dir,
        "--clean",
        "--noconfirm",
    ]

    add_datas = [
        ("guides", "guides"),
        (os.path.join("assets", "icon.png"), "assets"),
        (os.path.join("assets", "icon.ico"), "assets"),
        (os.path.join("assets", "switch2_ui"), os.path.join("assets", "switch2_ui")),
        ("cheats", "cheats"),
        ("script0.json", "."),
        ("collectible_flags.json", "."),
        ("LICENSE", "."),
        ("THIRD_PARTY_NOTICES.md", "."),
    ]

    for src, dst in add_datas:
        src_path = os.path.join(REPO_ROOT, src)
        cmd.extend(["--add-data", f"{src_path}{os.pathsep}{dst}"])

    try:
        __import__("PIL")
        cmd.extend(["--collect-submodules", "PIL"])
    except ImportError:
        pass

    for mod in ["zstandard", "texture2ddecoder"]:
        try:
            __import__(mod)
            cmd.extend(["--collect-submodules", mod])
        except ImportError:
            sys.exit(f"Missing build dependency {mod}: pip install -r requirements-build.txt")

    cmd.append(os.path.join(REPO_ROOT, "oot_save_editor.py"))

    print(f"Running PyInstaller build for v{APP_VERSION}...")
    res = subprocess.run(cmd, cwd=REPO_ROOT)
    if res.returncode != 0:
        print(f"Error: PyInstaller build failed with exit code {res.returncode}", file=sys.stderr)
        sys.exit(res.returncode)

    # Clean up generated .spec file if present
    spec_file = os.path.join(REPO_ROOT, "OOT-Switch2-Save-Editor.spec")
    if os.path.exists(spec_file):
        try:
            os.remove(spec_file)
        except OSError:
            pass

    exe_name = "OOT-Switch2-Save-Editor.exe" if sys.platform == "win32" else "OOT-Switch2-Save-Editor"
    exe_path = os.path.join(dist_dir, exe_name)
    if not os.path.exists(exe_path):
        print(f"Error: Expected build artifact {exe_path} not found", file=sys.stderr)
        sys.exit(1)

    readme_first = f"""The Legend of Zelda: Ocarina of Time Switch 2 Save Editor v{APP_VERSION}
================================================================================

1. HOW TO RUN
   Double-click OOT-Switch2-Save-Editor.exe to start the application.

2. WINDOWS SMARTSCREEN
   Windows may display a "Windows protected your PC" (SmartScreen) warning
   because this open-source executable is newly built and not code-signed with
   a commercial certificate.
   To run:
     Click "More info" -> Click "Run anyway"

3. WHERE YOUR BACKUPS LIVE
   Backups are stored safely in:
     Windows: %APPDATA%\\The Legend of Zelda Ocarina of Time Switch 2 Save Editor\\backups
     Linux/macOS: ~/.config/The Legend of Zelda Ocarina of Time Switch 2 Save Editor/backups

   Backups are never deleted or overwritten by the editor. You can also view
   and open this folder directly from within the editor via "Open backups folder".

4. PORTABLE MODE
   If you want to keep all data next to the executable (e.g. on a USB drive),
   create an empty file named "portable.txt" in the same folder as
   OOT-Switch2-Save-Editor.exe.
   When portable mode is active, all settings, backups, and custom cheats/guides
   are saved to a "data/" folder next to the executable.
"""

    zip_name = f"OOT-Switch2-Save-Editor-v{APP_VERSION}-windows.zip"
    zip_path = os.path.join(dist_dir, zip_name)
    print(f"Creating release archive: {zip_path}")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(exe_path, arcname=exe_name)
        zf.write(os.path.join(REPO_ROOT, "LICENSE"), arcname="LICENSE")
        zf.write(os.path.join(REPO_ROOT, "THIRD_PARTY_NOTICES.md"), arcname="THIRD_PARTY_NOTICES.md")
        zf.writestr("README-FIRST.txt", readme_first)

    print(f"Build complete: {zip_path}")


if __name__ == "__main__":
    main()
