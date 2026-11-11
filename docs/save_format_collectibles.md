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

## Scarecrow's Song

Read 2026-11-11 from the game's data and checked against Lane's saves before and after teaching the song.

### The notes

UIntArray `0xCC535536` in the main table, 8 slots (`TotalSize: 8` in the GameDataList). Like every array field,
the table value is a file offset; at that offset is a u32 count (8) followed by the 8 u32 values.

Each value is a note from the game's ocarina scale enum (the XLink property "音階" in
`RSDB/XLinkPropertyTable`):

| Value | Note | Value | Note | Value | Note | Value | Note |
|---|---|---|---|---|---|---|---|
| 0 | Rest (empty) | 5 | D♯ | 10 | G♯ | 15 | C♯ |
| 1 | Low B | 6 | E | 11 | A | 16 | High D |
| 2 | Low C | 7 | F | 12 | A♯ | 17 | High D♯ |
| 3 | Low C♯ | 8 | F♯ | 13 | B | 18 | High E |
| 4 | D | 9 | G | 14 | C | 19 | High F |

The five ocarina buttons play D (A button), F (Down), A (Right), B (Left) and High D (Up); this comes from
`GameParameter/MelodyScoreBook`, whose note names hash to "D", "F", "A", "B" and "HighD" and match Zelda's Lullaby,
Epona's Song, Saria's Song and the Song of Time. The other values are those notes bent up or down.

Check: before the song was taught every slot was 0; after, the slots read 7, 11, 7, 11, 7, 11, 7, 11, which is
Down, Right, Down, Right... with no bends.

### Progress flags

| Step | Flags set (named Bools) |
|---|---|
| Song taught to the scarecrow as a child | `AskBonooru_listentothesong` (0xFDF0F4B8), `Askpierre_listentothesong` (0x8C1DA521) |
| Song played back as an adult (learned) | `Bonooru_Talked_Adult` (0xD84AB9A9), `Bonooru_ThatsIt` (0x4E2C4DF8), `IsGet.Item_Melody_ScarecrowSong` (0x5E86FB4D), `HavePlayedGetEvent.Item_Melody_ScarecrowSong` (0x23E7E426) |

The 3-slot UIntArray `0x5630032D` changed at the same time but also changes in saves unrelated to the song, so it is
not part of it. Leave it alone.
