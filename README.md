<div align="center">

<img src="assets/icon.png" alt="App icon: Golden Triforce and Spiritual Stone" width="128">

# The Legend of Zelda: Ocarina of Time Switch Save Editor

**A friendly desktop save editor for *The Legend of Zelda: Ocarina of Time (64-bit)* (Nintendo Switch / Switch 2, Title ID: `0400486024DEC000` / `04004860224DEC000`).**  
Works with saves from **Lichii**, **Eden**, **Ryujinx**, **Yuzu/Suyu/Sudachi/Citron**, and saves dumped from a real Switch running Atmosphère.

[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![Platforms](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)
![Title ID](https://img.shields.io/badge/title%20ID-0400486024DEC000-green.svg)

[Features](#-features) · [How to use](#-how-to-use) · [Tabs & Capabilities](#-tabs--capabilities) · [Cheats](#-cheats) · [FAQ](#-faq)

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
| 🗺️ **Walkthrough & Progress** | Tracks current chapter / dungeon, Heart Pieces found (0/36), and Gold Skulltula tokens (0/100) with direct links to Zelda Dungeon guides |
| 🎮 **Cheats** *(Atmosphère)* | Pre-packaged cheats (Infinite Health, Infinite Magic, 999 Rupees, Moon Jump, Speed Multiplier, Infinite Ammo). Install to emulator in one click or export to SD card |
| 🌗 **Light & Dark Mode** | Clean interface matching system light/dark mode on Windows, macOS, and Linux, including Windows 11 immersive dark title bar |
| 🔍 **Review Before Saving** | Summary window displaying every change (e.g. *Rupees: 370 → 999*) before anything is written |
| 🛟 **Safety & Backups** | Automatic backups before saving, manual backups with notes, restore dialog, and active emulator process detection warning |

---

## 🚀 How to use

> [!IMPORTANT]
> **Close Lichii or your emulator first.** If the emulator is running while save files are modified, it will overwrite your edits upon saving or exiting.

1. **Launch the editor:** Double-click `The Legend of Zelda Ocarina of Time Switch Save Editor.bat` (or run `python oot_save_editor.py`).
2. **Auto-detect or Browse:** The editor automatically detects your save folder in `%APPDATA%\eden\nand\user\save\...`. If your save is in another location, click **Browse…** and select your folder.
3. **Select your save slot:** Choose `Slot 1` through `Slot 6` from the dropdown list.
4. **Make your edits:** Navigate between the tabs to adjust stats, equipment, inventory, or quest flags.
5. **Save Changes:** Click the green **Save changes** button, inspect the change review window, and confirm. An automatic backup will be created in the `backups/` directory before writing.

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

### 5. Walkthrough
* Derives chapter and progress directly from your save state.
* Interactive progress bars for **Heart Pieces** and **Gold Skulltulas**.
* Direct clickable links to Zelda Dungeon guides for each chapter, heart piece, and skulltula location.

### 6. Cheats
* Pre-configured codes for build ID `E0F3CCFAF50065AE` (v1.0.0).
* Double-click any cheat to toggle it on or off.
* Click **Install to emulator** to deploy into your emulator's `load/` or `mods/` directory.

---

## 🔒 Safe By Design

Save files (`progress.sav` and `caption.sav`) are parsed using Nintendo's GameData binary format. Any values or sections you do not modify are written back byte-for-byte exactly as originally generated, preserving all world state, camera, and checkpoint data.
