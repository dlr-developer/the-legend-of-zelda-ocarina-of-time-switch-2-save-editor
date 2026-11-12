# Lessons

## 2026-11-09 - Guide content was written for the wrong game version

What happened: the first offline guides (OOTSE-1, OOTSE-3) were written from memory of the original N64/3DS
Ocarina of Time. This editor is for the Switch 2 remake (released 2026-11-05), which moved many collectibles and added
new ones (Fairy Thoughts, password scrub Heart Pieces, relocated Great Fairies). Memory-only drafts were also vague:
writers marked 70-99% of their own entries uncertain.

Evidence: the remake's Heart Piece list differs in about a third of its locations from the original. The first Gold
Skulltula draft had wrong per-area counts.

Rule now: guide content comes from remake sources. Take the facts (locations, requirements, prices, order) from them and
write every sentence in our own words. Never copy sentences or images. Run the overlap check
(no shared run of 11+ words with the source) before committing guide JSON.

## 2026-11-09 - Game art was still in the public history after the first scrub

What happened: before the first push, `assets/ui_hd` (texture-pack art) was removed from history. A second folder,
`assets/ui/` (132 icons, e.g. the original Fairy Ocarina sprite), had been added and deleted in older commits and was
missed, because the scrub only searched for the one folder name. It went public with the repo and the v1.0.0 tag.

Evidence: `git log origin/master --name-only` listed `assets/ui/items/...`; the history was rewritten again, master
force-pushed, and v1.0.0 deleted and re-published from the clean commit.

Rule now: before any push to a public repo or a release, list every path ever committed on the pushed refs
(`git log <refs> --name-only --format="" | sort -u`) and check every binary/image path's origin, not one folder name.
Only generated art (generate_switch2_assets*.py, and the Blender renders from tools/render_icons.py, modelled
from primitives) and our own icon ship in this repo.

## 2026-11-11 - Collectible sync was built on guessed flag hashes

What happened: guide sync for Gold Skulltulas, Pieces of Heart and Fairy Thoughts never worked. The builder kept
adding hashes it could not verify. Skulltulas and loose Heart Pieces are not named fields at all: they live in a
separate list of 64-bit placement IDs after the field table, which the editor never read. One Heart Piece hash pointed
at the wrong frog minigame, and the "song bitfield" `0x628BE485` is not a song bitfield (it reads 15 in every save).

Evidence: reading the game's own placement and GameDataList files gave a table that matches every save exactly
(Skulltula count = tokens; Heart Pieces = what max hearts imply; 80 saves). See `docs/save_format_collectibles.md`.

Rule now: a save-flag hash goes into the editor only with its source (a name from the game's data, or a placement ID)
and a check against a real save. No hash from memory or guessing. Briefs for save-format work cite
`collectible_flags.json` or the doc above instead of asking the builder to find hashes.

## 2026-11-12 - A mutation check wiped an uncommitted fix

What happened: during the v1.3.1 review fix, the lead edited `oot_pause_menu.py`, then ran a mutation check that
broke one line with `sed` and restored the file with `git checkout -- oot_pause_menu.py`. The fix was not committed
yet, so the checkout restored the old code and silently dropped it. It was caught because `git status` showed only
the test file as modified.

Rule now: commit (or stash) a fix before mutation-checking it, and confirm the fix is still in the file afterwards.
