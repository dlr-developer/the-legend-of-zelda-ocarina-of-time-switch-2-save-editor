# Cheats for The Legend of Zelda: Ocarina of Time (64-bit)

A quick guide to using Atmosphère cheat codes with this save editor, your emulator (Lichii / Eden / Ryujinx), or on a modded Nintendo Switch running Atmosphère.

---

## ⚠️ Important Warning

> [!WARNING]
> Cheats modify the game while it is running. A code made for a different game version or build ID can do nothing, crash the game, or corrupt save data. **Always back up your save before using cheats**, and turn cheats off if anything behaves unexpectedly.

---

## ⚙️ How Cheats Work

While the game runs in an emulator or on hardware, player stats (HP, rupees, ammo, coordinates) reside in volatile system RAM. A cheat code instructs the emulator or Atmosphère to continuously write specific values to those memory locations.

* **Cheats do not write directly to your save file.**
* However, if you trigger an in-game save while a cheat is active, its effects (such as 999 rupees or max hearts) are saved permanently into your save file.

---

## 🔍 Build IDs

A cheat code **only works on the exact game build it was designed for**. 

* **The Legend of Zelda: Ocarina of Time (64-bit)**:
  * Title ID: `0400486024DEC000` (alias `04004860224DEC000`)
  * v1.0.0 Main Build ID: `E0F3CCFAF50065AE`

If your emulator updates the game or you are running a different version, codes will need to be updated to match the new build ID.

---

## 🎮 Where Cheat Files Are Installed

| Environment | Cheat File Location |
|---|---|
| **Lichii / Eden / Yuzu Family** | `%APPDATA%\eden\load\0400486024DEC000\OOT Save Editor Cheats\cheats\<build_id>.txt` |
| **Ryujinx** | `mods\contents\0400486024dec000\OOT Save Editor Cheats\cheats\<build_id>.txt` |
| **Nintendo Switch (Atmosphère)** | `atmosphere/contents/0400486024DEC000/cheats/<build_id>.txt` on the SD card |

---

## 🚀 How to Use Cheats in This Editor

1. Click **Back up now…** at the top of the editor window to secure your current save.
2. Open the **Cheats** tab.
3. Check that your game's **Build ID** matches (`E0F3CCFAF50065AE` for v1.0.0).
4. Double-click the cheats you want to activate (a checkmark ✔ will appear).
5. Click **Install to emulator** (or **Export for Switch** to save to an SD card).
6. Start the game/emulator. Enjoy!
