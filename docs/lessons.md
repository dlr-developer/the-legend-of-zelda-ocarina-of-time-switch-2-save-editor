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
Only generated art (generate_switch2_assets*.py) and our own icon ship in this repo.
