"""Scarecrow's Song helper functions and data structures for Switch 2 saves."""

import struct

NOTE_FIELD = 0xCC535536

# Progress flags
# CHILD: AskBonooru_listentothesong 0xFDF0F4B8, Askpierre_listentothesong 0x8C1DA521
CHILD_FLAGS = (0xFDF0F4B8, 0x8C1DA521)

# ADULT: Bonooru_Talked_Adult 0xD84AB9A9, Bonooru_ThatsIt 0x4E2C4DF8,
#        IsGet.Item_Melody_ScarecrowSong 0x5E86FB4D, HavePlayedGetEvent.Item_Melody_ScarecrowSong 0x23E7E426
ADULT_FLAGS = (0xD84AB9A9, 0x4E2C4DF8, 0x5E86FB4D, 0x23E7E426)

FLAG_ASK_BONOORU = 0xFDF0F4B8
FLAG_ASK_PIERRE = 0x8C1DA521
FLAG_BONOORU_TALKED_ADULT = 0xD84AB9A9
FLAG_BONOORU_THATS_IT = 0x4E2C4DF8
FLAG_IS_GET_SCARECROW = 0x5E86FB4D
FLAG_EVENT_SCARECROW = 0x23E7E426

STATES = ("Not taught", "Taught (child)", "Learned")

BUTTON_LABELS = {4: "A", 7: "Down", 11: "Right", 13: "Left", 16: "Up"}
PITCH_NAMES = {
    1: "Low B",
    2: "Low C",
    3: "Low C#",
    4: "D",
    5: "D#",
    6: "E",
    7: "F",
    8: "F#",
    9: "G",
    10: "G#",
    11: "A",
    12: "A#",
    13: "B",
    14: "C",
    15: "C#",
    16: "High D",
    17: "High D#",
    18: "High E",
    19: "High F",
}

# Note enum (0..19) labels built from BUTTON_LABELS and PITCH_NAMES
NOTE_LABELS = {0: "-"}
for _v, _p in PITCH_NAMES.items():
    if _v in BUTTON_LABELS:
        NOTE_LABELS[_v] = BUTTON_LABELS[_v]
    else:
        NOTE_LABELS[_v] = f"{_p} (bent)"

BUTTON_NOTES = [4, 7, 11, 13, 16]
BENT_NOTES = [1, 2, 3, 5, 6, 8, 9, 10, 12, 14, 15, 17, 18, 19]

# Note order in picker: 5 buttons first, then 14 bent notes in enum order
PICKER_ORDER = [4, 7, 11, 13, 16, 1, 2, 3, 5, 6, 8, 9, 10, 12, 14, 15, 17, 18, 19]
PICKER_LABELS = [NOTE_LABELS[v] for v in PICKER_ORDER]

LABEL_TO_NOTE = {label: val for val, label in NOTE_LABELS.items()}

# Game songs from GameParameter/MelodyScoreBook as note values
GAME_SONGS = {
    "Zelda's Lullaby": [13, 16, 11, 13, 16, 11],
    "Epona's Song": [16, 13, 11, 16, 13, 11],
    "Saria's Song": [7, 11, 13, 7, 11, 13],
    "Sun's Song": [11, 7, 16, 11, 7, 16],
    "Song of Time": [11, 4, 7, 11, 4, 7],
    "Song of Storms": [4, 7, 16, 4, 7, 16],
    "Minuet of Forest": [4, 16, 13, 11, 13, 11],
    "Bolero of Fire": [7, 4, 7, 4, 11, 7, 11, 7],
    "Serenade of Water": [4, 7, 11, 11, 13],
    "Nocturne of Shadow": [4, 7, 4, 11, 7, 4],
    "Requiem of Spirit": [13, 11, 11, 4, 13, 11, 7],
    "Prelude of Light": [16, 11, 16, 11, 13, 16],
}


def note_label(val):
    """Return display label for a note value, formatting unknowns as '? (<n>)'."""
    if val in NOTE_LABELS:
        return NOTE_LABELS[val]
    return f"? ({val})"


def read_notes(p_bytes, p_fields):
    """Read 8 note values from progress save buffer.

    Returns list of 8 ints, or None if layout invalid or field missing.
    """
    if p_bytes is None or not p_fields or NOTE_FIELD not in p_fields:
        return None
    val_offset = p_fields[NOTE_FIELD]
    if val_offset < 0 or val_offset + 4 > len(p_bytes):
        return None
    offset_a = struct.unpack_from("<I", p_bytes, val_offset)[0]
    if offset_a < 0 or offset_a + 4 > len(p_bytes):
        return None
    count = struct.unpack_from("<I", p_bytes, offset_a)[0]
    if count != 8:
        return None
    if offset_a + 4 + 8 * 4 > len(p_bytes):
        return None
    notes = [struct.unpack_from("<I", p_bytes, offset_a + 4 + 4 * i)[0] for i in range(8)]
    return notes


def write_notes(p_bytes, p_fields, notes):
    """Write 8 note values in place at offset A+4.

    Returns True on success, False if layout invalid or values out of range (0..19).
    Leaves count and file size unchanged.
    """
    if notes is None or len(notes) != 8:
        return False
    for n in notes:
        if not isinstance(n, int) or n < 0 or n > 19:
            return False
    if p_bytes is None or not p_fields or NOTE_FIELD not in p_fields:
        return False
    val_offset = p_fields[NOTE_FIELD]
    if val_offset < 0 or val_offset + 4 > len(p_bytes):
        return False
    offset_a = struct.unpack_from("<I", p_bytes, val_offset)[0]
    if offset_a < 0 or offset_a + 4 > len(p_bytes):
        return False
    count = struct.unpack_from("<I", p_bytes, offset_a)[0]
    if count != 8:
        return False
    if offset_a + 4 + 8 * 4 > len(p_bytes):
        return False

    for i, n in enumerate(notes):
        struct.pack_into("<I", p_bytes, offset_a + 4 + 4 * i, n)
    return True


def state_from_flags(get):
    """Determine Scarecrow's Song state from save flags getter function."""
    if bool(get(FLAG_IS_GET_SCARECROW)):
        return "Learned"
    if any(bool(get(h)) for h in CHILD_FLAGS):
        return "Taught (child)"
    return "Not taught"


def flag_writes(state):
    """Return dictionary of hash -> 0/1 for all 6 Scarecrow flags for the given state."""
    if state == "Learned":
        return {
            FLAG_ASK_BONOORU: 1,
            FLAG_ASK_PIERRE: 1,
            FLAG_BONOORU_TALKED_ADULT: 1,
            FLAG_BONOORU_THATS_IT: 1,
            FLAG_IS_GET_SCARECROW: 1,
            FLAG_EVENT_SCARECROW: 1,
        }
    elif state in ("Taught (child)", "Taught"):
        return {
            FLAG_ASK_BONOORU: 1,
            FLAG_ASK_PIERRE: 1,
            FLAG_BONOORU_TALKED_ADULT: 0,
            FLAG_BONOORU_THATS_IT: 0,
            FLAG_IS_GET_SCARECROW: 0,
            FLAG_EVENT_SCARECROW: 0,
        }
    else:  # "Not taught"
        return {
            FLAG_ASK_BONOORU: 0,
            FLAG_ASK_PIERRE: 0,
            FLAG_BONOORU_TALKED_ADULT: 0,
            FLAG_BONOORU_THATS_IT: 0,
            FLAG_IS_GET_SCARECROW: 0,
            FLAG_EVENT_SCARECROW: 0,
        }


def _contains_subsequence(seq, sub):
    """Check if sub is a contiguous run inside seq."""
    n = len(seq)
    m = len(sub)
    if m > n:
        return False
    for i in range(n - m + 1):
        if seq[i : i + m] == sub:
            return True
    return False


def validate(state, notes):
    """Validate Scarecrow's Song state and notes.

    Returns (errors list[str], warnings list[str]).
    """
    errors = []
    warnings = []

    if notes is None or len(notes) != 8:
        errors.append(f"Scarecrow's Song must have exactly 8 notes (got {len(notes) if notes else 0}).")
        return errors, warnings

    if state in ("Taught (child)", "Taught", "Learned"):
        empty_slots = [i + 1 for i, n in enumerate(notes) if n == 0]
        if empty_slots:
            slot_names = ", ".join(f"slot {s}" for s in empty_slots)
            errors.append(f"All 8 notes must be non-zero for state '{state}'. Empty slots: {slot_names}.")

    # Check for contiguous runs of game songs
    for song_name, seq in GAME_SONGS.items():
        if _contains_subsequence(notes, seq):
            warnings.append(
                f"Notes contain a contiguous run matching {song_name}."
            )

    return errors, warnings
