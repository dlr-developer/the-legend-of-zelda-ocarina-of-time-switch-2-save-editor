# Collectibles in progress.sav

How the remake stores Gold Skulltulas, Pieces of Heart and Fairy Thoughts, and where
`collectible_flags.json` comes from. Read 2026-11-11 from the game's v2.0.0 data
(update 131072) and checked against 80 real saves.

## Three kinds of storage

| Kind | Used by | Where it lives |
|---|---|---|
| 64-bit placement key | Gold Skulltulas, loose Pieces of Heart, boss Heart Containers | A sorted list of u64 placement IDs after the field table. Present = set. |
| Struct member Bool | Chests (`IsTreasureBoxOpen`) | Ordinary Bool fields in the main table. The struct maps member name (the decimal placement ID) to the field hash. |
| Named Bool | NPC and minigame rewards, Fairy Thoughts | Ordinary Bool fields, hash = MurmurHash3_32(name). |

`script0.json` only lists the named Bools, which is why sync could not work before: the
Skulltula and loose Heart Piece state is not in the main table at all.

### The 64-bit key list

- Main-table field `0xA3DB7114` (type "Unknown" in `script0.json`) holds the file offset of the list.
- From that offset, read little-endian u64 values until a 0 or the end of the file.
- Values are sorted ascending. Each one is a placement ID (the `Hash` of an actor in `Banc/**/*.bcett.byml`).
- Only set keys are stored, so the list grows as you play (198 keys at 33 tokens, 297 at 58).
- Some old backups (2026-11-08) have stray strings after the terminating 0, written by an
  older editor build. Stop at the 0.

Writing to this list (to grant a collectible) is not implemented and would change the file
size. Treat it as read-only until that is designed and tested in game.

### Gold Skulltulas

The game names each one `IsGoldSkullDead.IsGoldSkullDead_<placement id>` in the
`IsGoldSkullDead` struct, but those Bools are runtime-only (`SaveFileIndex -1`). The saved
state is the placement ID in the 64-bit key list. Check: in every save, the number of
Skulltula IDs present equals `PouchData.Item_Token_Gold.StockNum` (33, 43, 58).

### Pieces of Heart

- Loose pieces (`Obj_Heart_Piece`, `Obj_GerudoValley_Heart_Piece`) use the 64-bit key list.
- Chest pieces (`Obj_TBox_*` with `Drop__DropActor: Obj_Heart_Piece`) use `IsTreasureBoxOpen`.
- Rewards use named flags, e.g. `Npc_Hylia_001_IsGetHeartPiece`, `MiniGame_FrogTenors_StormSong`.

Check: collected pieces = (max hearts − 3 − boss Heart Containers) × 4 + held pieces, where
Heart Containers come from the `Obj_Heart_Container` keys. This holds exactly in all 80 saves.

Fix to the old code: the Song of Storms frog piece used
`MiniGame_FrogTenors_InsectRepellent_ClearAfter`. The right flag is `MiniGame_FrogTenors_StormSong`.

### Fairy Thoughts

The marks are actors `HrlField_Note_NN`; reading one sets `HaveReadHrlField_NoteNN`. There
are 23 distinct marks. The guide lists the Hyrule Field grotto mark (Note 12) twice (child
and adult readings) and has no entry for the Bottom of the Well mark (Note 23).

## Confidence

Every Skulltula maps to exactly one placement (checked: 100 entries, 100 distinct IDs, each
a member of `IsGoldSkullDead`). Matching an entry to a placement used era, room and nearby
objects (soft soil, crates, cracked walls, Pierre spots). Entries marked `"confidence": "low"`
in the JSON could be swapped with another entry in the same area. Your saves cannot tell
these apart because each of those areas is all-collected or all-uncollected.

## Re-deriving it

The game files are not in this repo. To redo the extraction from your own copy:

1. `eden-cli.exe --unpack-nup <game>.nup <out_dir>` (Lichii build) gives a loose RomFS.
2. Decompress `.zs` files with zstd and the dictionaries in `Pack/ZsDic.pack.zs` (a SARC).
3. Parse `Banc/<Area>/*.bcett.byml` (BYML v7) for actor `Gyaml`, `Hash`, `Translate`.
4. Parse `GameData/GameDataList.Product.110.byml` (big-endian BYML) for `Bool64bitKey` and the
   `IsGoldSkullDead` / `IsTreasureBoxOpen` structs.
