<div align="center">

<img src="assets/icon.png" alt="App icon: Golden Triforce and Spiritual Stone" width="128">

# The Legend of Zelda: Ocarina of Time Switch 2 Save Editor

**A friendly desktop save editor for *The Legend of Zelda: Ocarina of Time (64-bit)* (Nintendo Switch 2, Title ID: `0400486024DEC000` / `04004860224DEC000`).**  
Works with saves from **Lichii**, **Eden**, **Ryujinx**, **Yuzu/Suyu/Sudachi/Citron**, and saves dumped from a real Switch 2 running Atmosphère.

[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![Platforms](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)
![Title ID](https://img.shields.io/badge/title%20ID-0400486024DEC000-green.svg)

[Features](#-features) · [Download](#-download) · [How to use](#-how-to-use) · [Where your data lives](#-where-your-data-lives) · [Tabs & Capabilities](#-tabs--capabilities) · [Building from source](#%EF%B8%8F-building-from-source) · [Releasing](#-releasing) · [FAQ](#-faq)

</div>

---

## ✨ Features

| | |
|---|---|
| 💎 **Rupees & Wallets** | Adjust Rupees up to 999 with a **Max** button and select wallet capacity (Child, Adult, Giant, Tycoon) |
| ❤️ **Hearts & Health** | Set current hearts, max heart containers (3 to 20), heart pieces (0–3), and toggle Double Defense (white heart border) |
| 🧙 **Magic Meter** | Toggle Normal Magic, Double Magic, or unlimited magic capacity |
| 🕷️ **Gold Skulltulas** | Set Gold Skulltula token counts directly (0 to 100), with a one-click **Max** button |
| ⚔️ **Equipment & Gear** | Customize swords (Kokiri, Master, Biggoron, Giant's Knife), shields (Deku, Hylian, Mirror), tunics, boots, and strength gauntlets |
| 🎒 **Ammo & Consumables** | Set exact quantities for Arrows, Bombs, Bombchus, Deku Seeds, Deku Sticks, Deku Nuts, and Magic Beans with a **Max All Ammo** shortcut |
| 🍼 **Bottles** | Configure all 4 bottle slots with Red/Green/Blue Potions, Bottled Fairies, Lon Lon Milk, Poes, Big Poes, Blue Fire, Bugs, or Ruto's Letter |
| 🗝️ **Quest Relics & Songs** | Toggle Spiritual Stones (Kokiri Emerald, Goron Ruby, Zora Sapphire), all 6 Sage Medallions, and all 12 Ocarina warp and event songs |
| 🗺️ **Guides & Story Progress** | Offline interactive collectible checklists (Heart Pieces 0/36) with bundled screenshots, filters, and story progression |
| 🎮 **Cheats** *(Atmosphère)* | Pre-packaged cheats (Infinite Health, Infinite Magic, 999 Rupees, Moon Jump, Speed Multiplier, Infinite Ammo). Install to emulator in one click or export to SD card |
| 🌗 **Light & Dark Mode** | Clean interface matching system light/dark mode on Windows, macOS, and Linux, including Windows 11 immersive dark title bar |
| 🔍 **Review Before Saving** | Summary window displaying every change (e.g. *Rupees: 370 → 999*) before anything is written |
| 🛟 **Safety & Backups** | Automatic backups before saving, manual backups with notes, restore dialog, and active emulator process detection warning |

---

## 📥 Download

1. Go to the [Releases](https://github.com/dlr-developer/the-legend-of-zelda-ocarina-of-time-switch-2-save-editor/releases) page and download the latest `OOT-Switch2-Save-Editor-v<version>-windows.zip`.
2. Extract (unzip) the folder anywhere on your computer.
3. Double-click **`OOT-Switch2-Save-Editor.exe`** to launch the editor.

> [!NOTE]
> **Windows SmartScreen Notice:**  
> Windows may display a blue warning screen saying *"Windows protected your PC"*. This occurs because the standalone executable is built fresh from open-source code on GitHub Actions and is not code-signed with an expensive commercial certificate.  
> To proceed, click **"More info"** and then click **"Run anyway"**.

---

## 🚀 How to use

> [!IMPORTANT]
> **Close Lichii or your emulator first.** If the emulator is running while save files are modified, it will overwrite your edits upon saving or exiting.

1. **Launch the editor:** Run the executable or `python oot_save_editor.py`.
2. **Auto-detect or Browse:** The editor automatically detects your save folder in `%APPDATA%\eden\nand\user\save\...` or Ryujinx bis saves. If your save is in another location, click **Browse…** and select your folder.
3. **Select your save slot:** Choose `Slot 1` through `Slot 6` from the dropdown list.
4. **Make your edits:** Navigate between the tabs to adjust stats, equipment, inventory, or quest flags.
5. **Save Changes:** Click the green **Save changes** button, inspect the change review window, and confirm. An automatic backup will be created in your user backups directory before writing.

---

## 💾 Where your data lives

The editor keeps your personal data cleanly separated from the application files so that updating the app never overwrites your backups or settings.

* **Settings & Preferences:**
  * **Windows:** `%APPDATA%\The Legend of Zelda Ocarina of Time Switch 2 Save Editor\settings.json`
  * **Linux / macOS:** `~/.config/The Legend of Zelda Ocarina of Time Switch 2 Save Editor/settings.json`
* **Save Backups:**
  * **Windows:** `%APPDATA%\The Legend of Zelda Ocarina of Time Switch 2 Save Editor\backups`
  * **Linux / macOS:** `~/.config/The Legend of Zelda Ocarina of Time Switch 2 Save Editor/backups`
  * Backups are automatically timestamped and created before saving or restoring. The editor **never moves, deletes, or overwrites** your backups. Click **Open backups folder** in the app to view them in your file manager.
* **Cheat Library:**
  * User-written cheat files live in `%APPDATA%\The Legend of Zelda Ocarina of Time Switch 2 Save Editor\cheats`.
  * On first access, default cheat files are seeded from bundled resources without overwriting user files. If a build ID is not found in your user folder, the editor automatically falls back to bundled cheat codes.
* **Guides:**
  * Bundled guides and screenshots ship with the application. Custom guide overrides can be placed in `%APPDATA%\The Legend of Zelda Ocarina of Time Switch 2 Save Editor\guides`.

### 🧳 Portable Mode
If you prefer to keep everything in one self-contained directory (e.g. on a USB drive or portable gaming setup):
1. Create an empty text file named **`portable.txt`** next to `OOT-Switch2-Save-Editor.exe` (or `oot_save_editor.py`).
2. When this file exists, the editor switches to portable mode and stores all settings, backups, cheats, and custom guides in a **`data/`** folder next to the executable instead of `%APPDATA%`.
3. In portable mode, the automatic migration from legacy `%APPDATA%` folders is skipped so that portable installations never pull data from the host computer.

### 🔄 Automatic Migration of Legacy Data and Backups
If you previously used an older version of the editor that stored data in the legacy Switch Save Editor folder (`%APPDATA%\The Legend of Zelda Ocarina of Time Switch Save Editor`) or in an `APP_DIR/backups` folder:
* On startup, the editor automatically copies missing files into the new user data folder: `settings.json` (only if none exists), `backups/*` folders, `cheats/*` files, and `guides/*` files.
* Original legacy files and folders are **never overwritten, moved, or deleted**.
* Migration runs once, and a status message confirms the number of migrated items. Any existing `APP_DIR/backups` migration also continues to run safely.

---

## 📂 Tabs & Capabilities

### 1. General & Stats
* **Rupees (0–999):** Quick **Max** button sets to 999.
* **Hearts (3–20):** Adjust current hearts and maximum heart containers independently.
* **Pieces of Heart (0–3):** Adjust pieces towards the next full container.
* **Magic Meter:** None, Standard Magic, or Double Magic.
* **Gold Skulltula Tokens (0–100):** Adjust tokens collected.
* **Double Defense:** Toggle the white protective outline on Link's hearts.

### 2. Equipment & Upgrades
* **Swords:** Kokiri Sword, Master Sword, Biggoron's Sword, Giant's Knife.
* **Shields:** Deku Shield, Hylian Shield, Mirror Shield.
* **Tunics:** Kokiri (Green), Goron (Red), Zora (Blue).
* **Boots:** Kokiri Boots, Iron Boots, Hover Boots.
* **Quivers / Bomb Bags / Gauntlets / Scales:** Full progression tiers.

### 3. Inventory & Bottles
* **Consumable Ammo:** Arrows (50), Bombs (40), Bombchus (50), Seeds (50), Sticks (30), Nuts (40), Beans (10).
* **Bottles 1–4:** Choose contents for each bottle slot or click **Fill All with Bottled Fairies**.

### 4. Quest Status & Songs
* **Spiritual Stones:** Kokiri's Emerald, Goron's Ruby, Zora's Sapphire.
* **Medallions:** Light, Forest, Fire, Water, Shadow, Spirit.
* **Songs:** Zelda's Lullaby, Epona's Song, Saria's Song, Sun's Song, Song of Time, Song of Storms, Minuet of Forest, Bolero of Fire, Serenade of Water, Requiem of Spirit, Nocturne of Shadow, Prelude of Light.

### 5. Guides
* **Story Progress:** Shows main storyline chapter progression, objectives, and boss completion derived from quest flags.
* **Offline Collectible Guides:** Checkable, numbered collectible cards (starting with Heart Pieces 1–36) loaded from local JSON data without external website dependencies.
* **Filtering & Status:** Filter cards by collection status (All, Not checked, Checked) and Era (All, Child, Adult, Either), with quick Check All and Uncheck All actions.
* **Per-Save Check State:** Collected checks persist per save slot (or for "no-save") and live-sync with the active save's Heart Pieces counter.
* **Bundled Screenshots:** Guides include offline screenshots for each collectible card.
* **Optional Pillow Support:** Pillow (`PIL`) is optional. When available, images are rendered with smooth Lanczos scaling; when absent, standard Tk photo support is used.

### 6. Cheats
* Pre-configured codes for build ID `E0F3CCFAF50065AE` (v1.0.0).
* Double-click any cheat to toggle it on or off.
* Click **Install to emulator** to deploy into your emulator's `load/` or `mods/` directory.

---

## 🛠️ Building from source

To build the standalone Windows executable and release package yourself:

```bash
# 1. Install build requirements (PyInstaller and Pillow)
pip install -r requirements-build.txt

# 2. Run the release build script
python tools/build_release.py
```

The script packages all necessary assets, guides, schemas, cheats, and notices, creating:
* Standalone executable: `dist/OOT-Switch2-Save-Editor.exe`
* Release zip archive: `dist/OOT-Switch2-Save-Editor-v1.0.0-windows.zip` (containing the exe, `LICENSE`, `THIRD_PARTY_NOTICES.md`, and `README-FIRST.txt`).

---

## 🏷️ Releasing

Releases are published automatically via GitHub Actions upon pushing a version tag or triggering manually:

1. Update `APP_VERSION = "X.Y.Z"` in `oot_save_editor.py`.
2. Commit the change:
   ```bash
   git commit -am "Bump version to vX.Y.Z"
   ```
3. Tag the commit and push:
   ```bash
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```
4. The workflow in `.github/workflows/release.yml` will verify that `APP_VERSION` matches the tag, run tests, build the standalone zip, and create a GitHub Release with notes.

Manual releases can also be triggered via `workflow_dispatch` on GitHub Actions:
* A manual run builds and releases `v<APP_VERSION>` matching the version in `oot_save_editor.py`.
* Note: the workflow will fail if a release for `v<APP_VERSION>` already exists on GitHub. Increment `APP_VERSION` before triggering `workflow_dispatch`.

---

## 🔒 Safe By Design

Save files (`progress.sav` and `caption.sav`) are parsed using Nintendo's GameData binary format. Any values or sections you do not modify are written back byte-for-byte exactly as originally generated, preserving all world state, camera, and checkpoint data.
