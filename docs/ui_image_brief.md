# Brief: translating text baked into UI textures (EL01_* / EL02_* / EL03_* atlases)

The menu buttons, plates and label strips of Elminage II are drawn into 11 texture atlases in
`work/source/arc_ANIME/` (EL01_000, EL01_001, EL02_000 ... EL03_004; 512x512 8-bit palette GIMs except
EL03_001). Every Japanese word on them must become English, drawn with the game's own fonts, without
changing the image size or palette (the game cuts sprites out of the sheet at fixed UV rects).

## Tools (Elminage II paths)
- `python tools/ui_regions.py ANIME/<NAME>.GIM` -> `work/ui/regions/<NAME>.json` + `<NAME>_map.png`
  (2x, numbered opaque sprites). Opaque-sprite detection only; many sheets are one solid block.
- Spec file per atlas: `work/ui/specs/<NAME>.json` = one object {"gim": "ANIME/<NAME>.GIM", "note", "erase",
  "labels", optional "style", "text"}. Format and erase modes: docstring and `erase()` in `tools/img_text.py`
  (black, copy:x, blit:x,y, inpaint, clear, vcopy:y, fill:r,g,b,a); labels {"rect": [x,y,w,h], "en",
  "align", "inset", "pad_l", "pad_r", "dy", "color", "outline", "fonts": [["16",1],["16",0],["12",1],["12",0]],
  "squeeze", "bg"}.
- Render: `PYTHONUTF8=1 python tools/img_text.py work/ui/specs/<NAME>.json` -> `work/build/img/<NAME>.GIM` and
  preview `work/ui/preview/<NAME>.png`. Look at the preview (zoom crops with PIL and Read them) and iterate.
- Fonts: "16" = FONT10_16 (10x16 VWF, the dialogue font), "12" = FONT12_12 (12 px). Buttons usually take 16 px;
  small plates and strips take 12 px. If a word does not fit, use an established abbreviation; "squeeze"
  compresses as a last resort.

## Reference: Elminage III did the same job
Elminage III (`E:\Projects\Elminage III`) has the same atlas names with a different layout and colour scheme:
`work/ui/specs/EL*.json` and `work/ui/specs/EL*.report.md` (method, every jp -> en label, decisions,
risks), source sheets in `work/source/arc/ANIME/`. Reuse its translations of identical words and its method
(clean one reference button with copy:, blit the cleaned art to the other rows/states, then draw labels;
glyph strips: erase with fill:0,0,0,0 and draw 12 px text). Read-only: never write in that folder.

## Terms
Binding: `work/glossary/glossary.json`, `work/translation/en/review_notes.md` (conventions), and the English
already in the game for the same thing: menu and help texts in `work/translation/en/csv/HELP_TEXT.json`,
system strings in `work/translation/en/eboot.json`, place names in the script (Berte's Tavern, Kernel Shop,
Rosetta's Inn, Orses Temple, Training Hall, Bistel Castle, Alchemy Storage ...: grep the slices
`work/translation/en/slices/*.json` for the exact form). Class names as in the class tables (Mage, Priest,
Ranger, ...). Keep the 3 states of a button (selected / normal / disabled) identical in wording.

## Rules
- Erase every Japanese pixel (verify with an erase-only render: labels removed, no Japanese left). Leave
  English already on the sheet (GAME START, MAGIC and SKILLS, ...), icons and numbers alone.
- Stay inside the original word's cell where possible (UV rects are unknown); note any label that extends
  past the original word.
- Never print Japanese to the console (PYTHONUTF8=1; write to files). Do not edit files other than your
  spec(s), report(s) and scratch files with your PREFIX. Do not touch the source GIMs.
- Report `work/ui/specs/<NAME>.report.md`: method, a table of every label (where, jp, en, notes), what was
  kept, risks / in-game checks.
