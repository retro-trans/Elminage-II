# Changelog

## 0.8.3 (2026-11-24, test build, not a release)
- Title logo (ANIME/GR01_10303.GIM): the subtitle 双生の女神と運命の大地 now reads "The Twin Goddesses & the
  Land of Destiny" ("Twin Goddesses" as in the script; the "&" takes the place of と between the II's two
  pillars) and the katakana reading above the logo reads "ELMINAGE II". New tools/title_logo.py: both lines
  sat on transparent pixels and are erased to alpha 0 (pillars, flag tip, 'g' tail and pillar bases kept),
  then redrawn in Palatino Linotype Bold (Windows font) in the original colours with a dark outline,
  quantised to the logo's own palette.
- Checked in game (fresh boot of 0.8.3): the title screen (work/ui/title_v083.png); the boot continues into
  the font choice and the opening narration as before.

## 0.8.2 (2026-11-24, test build, not a release)
- Yes / No left in Japanese after "Take it?" (the Jewel Ring in Loipes Cave) and the other prompts of the search
  script 00011-CHOUSA, in all 20 script files. The choice menu (op 0x92) points back at strings that sit before
  it; the parser had already read those bytes as ops, so they were never extracted. tools/scp.py now sweeps
  such a sub-script again with the known string offsets. Only additions: 40 Yes / No strings, nothing lost.
- The Sphinx at Dekor (SCD05 15005.bin) was mostly Japanese: its menu ("What brings you here today?"), all ten
  riddles, its replies and the answers. An empty string between two choice strings stopped the parser
  halfway through that sub-script, so 119 strings were never extracted. A string that does not parse as an op
  right after another string is now read as a string. 72 lines reuse existing translations (floor markers,
  key items, Godshade victories); 47 are new (glossary terms, Sphinx voice as in its translated lines).
- Riddle answers are typed in English: the riddle editor (mode 0x0F) opens on the Latin keyboard where the
  Sphinx's riddles opened on hiragana / katakana; the glyph page of riddles 34001 / 53001 is unchanged. The
  answer is folded to upper case on confirm, so "book", "Book" and "BOOK" all match. Accepted answers use the
  original number of slots: BOOK / TOME; GRAVE / TOMB / GRAVESTONE / TOMBSTONE; TIME / CLOCK; DREAM / DREAMS /
  SLEEP; HAIR REMEMBER (with or without the space, the "Hair remover?" gag); SILK / THREAD / SILK THREAD /
  COCOON / SILKWORM; HAIR / HAIRS / BEARD; NAME; SOUND / SMELL / SCENT / VOICE; MIRROR.
- Event list and monster / item descriptions broke words across lines ("whet / her", "Loipe / s Cave"): the
  game cut them into fixed 28- or 24-byte rows. Ported Elminage III's pixel word wrap (vwf.apply_wrap): whole
  words per row by VWF width (224 px events, 200 px descriptions, HD widths with the HD font), at most 72 bytes
  a row (80-byte row buffers). The event rows' full-width space padding is dropped.
- Checked in game (savestate v080_tavern with the 0.8.2 EBOOT hot-loaded): the event "Adventurer Reg. Exam"
  wraps by words (work/ui/event_wrap_v082.png); in Loipes Cave an injected Sphinx riddle opens the Latin
  keyboard with the English prompt (work/ui/riddle_keyboard_v082.png), "book" typed in lower case reaches
  the compare as ＢＯＯＫ against the answer ＢＯＯＫ. The built SCD05 decodes every new answer, prompt and
  menu line to its English. Not checked in play: "Take it?" in Loipes Cave, the Sphinx itself (late game),
  the monster / item description boxes (none seen yet on the test party), a fresh boot of 0.8.2.
- Real hardware: code and tables in the cave only, no change to the hooked loops' registers or stack frames.

## 0.8.1 (2026-11-22, release)
- Alchemist and Summoner spells were never learned (GitHub issue #1). The spell table parser (0x088DA4B4)
  strcmp's each SPELL.CSV school cell with four EBOOT keys and makes any other value school 4 (enemy only).
  The cells read "Alchem" / "Sum" (6-byte column) but the keys had become "Alchemy" / "Summoner" when those
  strings were reclassified as UI text in 0.1.12, so 46 Alchemist and Summoner spells were enemy-only. The
  keys now read "Alchem" / "Sum". Checked in RAM (table 0x08D53A10, 92-byte records, school at +0x1C):
  v0.8.0 parsed 2 Alchemist / 0 Summoner / 60 enemy-only rows, v0.8.1 25 / 21 / 16.
- Traps aimed at the character who opens the chest: the trap parser (0x088DBAF0) strncmp's TRAP.CSV's target
  cell with the key 当人. The cells stayed Japanese on purpose but the key had become "Self" (same 0.1.12
  reclassification), so those 5 traps took the other target. The key is Japanese again. Not checked in play.
- Why it was missed: the compare-key scan of 0.1.10 covered strcmp-like calls at 0x08817294 / 0x08817114, but
  the CSV parsers also call the plain strcmp at 0x08816F44. Every call to both compare routines was listed
  again with its literal arguments: the Japanese keys are the four schools, 雲の上 (already matched), ○ / ● and
  当人. tools/eboot_text.py COMPARE_KEYS now stops the build if a key and its data cells disagree.
- Existing saves: characters keep the spells they have; whether a later level-up also teaches the spells
  missed at earlier levels was not checked.

## 0.8.0 (2026-11-19, first public release)
- First published build: the 0.1.24 work below plus the fix in this entry, rebuilt as v0.8.0 (numbering
  jumps to 0.8.0 for the first release, as Elminage III).
- Item names left in Japanese: the basic Katana (刀) and Staff (杖) carried by the premade party, and the
  tarot cards Strength, The Tower, The Star and The Moon. Their one-kanji cells were never marked as shown
  in game (extract_csv's "used" check needs 4 bytes) and were skipped. Translated in ITEM.CSV (name),
  ITEM_HELP.CSV and TAROT_TEXT.CSV. The tarot card 魔術師 read "Mage" (the class name); now "The Magician"
  ("Magician" in the 10-byte tarot list), as in Elminage III.
- Other one-kanji cells left as they are on purpose: field labels in the data tables' header rows, element
  and type keys the game compares against (SPELL, MONRAW), and the data-entry helper column of ITEM.CSV.
- Checked in game (fresh boot, savestate v080_tavern): Kanosuke's Katana, Green's Staff
  (work/ui/items_green_v080.png).
- Repository (retro-trans/Elminage-II): tools, docs and the English translation files only (`*.en.json`
  from tools/strip_jp.py). New tools/restore_en.py copies that English back into the working files the
  extract tools write from your own disc. Released as `Elminage2-English-v0.8.0.xdelta` against the
  Japanese ULJM05488 image.

## 0.1.24 (2026-11-18, test build, not a release)
- Shop item category list: "Gauntlets" and "Accessory" ran past the window border. The list's own pointers now
  read "Gloves" and "Access." (eboot_text.PTR_OVERRIDE 0x08960EC8 / 0x08960ED0); the equipment slot names
  elsewhere are unchanged. The equip compare Type column gets "Access." for its two accessory slots
  (0x0896052C / 0x08960530), as in Elminage III, where "Accessory" ran into the Rng label.
- PTR_OVERRIDE strings are now allocated at the end of patches.apply_all (eboot_text.apply_overrides), so they
  do not shift the code cave of the later patches and savestate hot reload keeps working.
- Checked in game: shop category list (work/ui/shop_v0124.png). Equip compare with an accessory not checked.
- Kept: the "RACE" header art over the category column is in the original game (Elminage III keeps it too).
- tools/prune_outputs.py keeps an older ISO that is open in an emulator instead of stopping the build.

## 0.1.23 (2026-11-18, test build, not a release)
- Small label font with drop shadow, ported from Elminage III (v0.8.7-v0.8.10): the 12 px labels redrawn into
  the EL01_000 / EL01_001 / EL02_000 / EL03_000 sheets (status screen, equip, item info, options, save/load,
  map legend) no longer use the game's FONT12_12 (thin, widely spaced letters). They use the hand-drawn
  proportional 12 px font tools/fonts/gr_latin.txt (Getter Robo Daikessen project, project original) with a
  3-pixel black drop shadow and a slight top-to-bottom shade (img_text.FontGR; spec font '12' now means this
  font, the game font is '12game'). Every label fits without squeezing.
- Fuller words where they now fit (same choices as Elminage III): Race, Align, Class, Luck, Type (status /
  equip), Race, Align, Breath, Draw (item info).
- The serif English art labels LV, EP, HP, AC, GP (status screen) and the two AC / HP pairs (item info) are
  erased and redrawn in the same font, so each screen uses one label font.
- Party bar names (and other English drawn with FONT12_12): the Latin cells of FONT12_12 are redrawn in the
  same font, white letter with a black outline and the shade in palette entries 3-14
  (font12.build_sheet -> work/font/FONT12_12.GIM, put into ANIME by vwf.apply12); the 12 px VWF widths are
  measured from the new sheet.
- Checked in game (fresh boot, savestate v0123_tavern): party bar names, status screen (work/ui/status_v0123.png),
  equip screen (work/ui/equip_v0123.png; also shows the 0.1.22 range letter "S"). Item info, options and
  save/load screens not opened. Image data and the VWF width table only.

## 0.1.22 (2026-11-18, test build, not a release)
- Tavern call list class column ("G-Fig"): the class abbreviations (Fig, Mag, Pri, ...) and alignment letters
  G / N / E were still the original full-width strings, drawn in the fixed 16 px pixel cells ("F i g"). They are
  now ASCII, so they use the proportional (VWF / HD) font like the names, as Elminage III does: eboot strings
  0x0896072c ("-"), 0x08960768-0x08960784 (G/N/E), 0x089607e4-0x08960910 (class abbreviations, Mai -> Srv
  for Servant, SAM/KAN/NIN -> Sam/Kan/Nin), and the shop range letters S / M / L (0x08960ed8-0x08960ee8).
  Checked in game: Call Companions list (work/ui/tavern_call_v0122.png). Shop range column not checked.
  Data only (EBOOT strings).

## 0.1.21 (2026-11-18, test build, not a release)
- Character creation: the gender and alignment lists use the class list's wide selection box (sprite 0x510)
  instead of the one- / two-kanji boxes 0x4F4 / 0x500, so the box covers "Female" / "Neutral"
  (tools/ui_fixes.py); the old boxes are hidden, and 0x510 is hidden at the start of every creation-screen
  frame (the age step left it on screen in 0.1.19). Checked in game: gender, alignment, age, class steps.
- Not done: widening the right-hand windows (class names "Gladiator" / "Summoner" touch the frame). Their
  size is not in the window entries of MD02_000.ANM or MD03_002.ANM (both tried in test builds 0.1.19 /
  0.1.20, no change); tools/anm_probe.py added for this search.
- Everything listed under 0.1.19 below.

## 0.1.19 / 0.1.20 (2026-11-18, test builds, superseded by 0.1.21)
- Help line at the bottom scrolls pixel by pixel (ported from Elminage III, tools/vwf.py apply_ticker): the
  original stepped one 2-byte cell (two letters) per 16 px. The window is cut so the last letter ends inside
  the box (Elm II draws it without clipping, x <= 240).
- Character creation / rename panel: sex and alignment show one letter (M/F, G/N/E) so they no longer run into
  the Aln / Age labels; the selection lists keep the full words (name_entry ne_abbrev, panel field draw).
- Age box on character creation read "AgeSet" (two label cells 年齢 + 入力): the second cell is now blank.

## 0.1.18 (2026-11-18, test build, not a release)
- HD font lighter: the glyphs were drawn with a 1 px (4x) outline stroke carried over from Elminage III's
  builder (its source font is thin), which made Console Sans Medium look bold. Now no stroke
  (font_hd.V_STROKE = 0); comparison in work/font/hd_weight_compare.png. HD letters are now a little
  narrower than the pixel font (lower case 7.4 vs 7.8 px average), so wrapping splits fewer pages
  (SCDWMAP 292 -> 256). Checked in game: popup, HD narration.

## 0.1.17 (2026-11-18, test build, not a release)
- HD font sheet is now 4x (40x64 cells, 512x512 4-bit, 12 glyphs per row) instead of 2x, so it stays smooth
  at the 4x rendering resolution players use (2x texels showed as visible blocks). The sheet no longer fits
  ANIME.BIN's disc slot, so FONT10HD.GIM goes into PARTS.BIN instead: the font loader finds sheets by file
  name in any archive (0x088F0CBC formats just '%s'). PARTS.BIN (444 KB -> 578 KB) moves to the end of the ISO;
  ANIME.BIN and FONT10_16.GIM are back to their original contents (the 256x128 trim is gone).
  Checked in game: HD chosen at New Game, narration drawn from the 4x sheet with the right glyphs.

## 0.1.16 (2026-11-18, test build, not a release)
- Opening movies subtitled (USRDIR/MOVIE/OP_01.PMF and OP_02.PMF, the two twin-goddess versions): 9 caption
  cards each (work/movie/captions.json), left-aligned like the Japanese, drawn in Georgia italic over a
  blurred, darkened band that hides the burned-in Japanese. tools/movie_sub.py (ported from Elminage III)
  re-encodes only the GOPs that carry captions (libx264 Main, level 2.1, no B-frames), keeps every frame
  within its original size and pads it with filler NAL units, so the container, PTS/DTS and AU tables are
  unchanged and the files are written in place (tools/pmf.py). Timings measured from the video.
  Not done: the ending movie ED_01.PMF.
- HD font fix: choosing "HD font" changed almost nothing, because the glyph hook's "ASCII only" test read
  the glyph row as an index (< 4) while the routine gets it in pixels (v = 0/16/32/48): only the first sheet
  row (space to 8) used the HD sheet. Now v < 64. Checked in game: the help text switches between the fonts.
- Facility menu buttons widened from 114 to 130 px (town, tavern, inn, shop, temple, training hall
  actions): sheet EL02_001 is rebuilt with 16 px more plain body (img_text 'widen') and the 69 sprite
  records in ANIME/MD02_004.ANM point at the new cells (tools/anm.py; data only, same file size). Every label
  now fits at normal letter spacing: no more squeezed "Temple of Orses", "Uncurse/Repair",
  "Treat/Retrieve", and "Alch. Storage" is "Alchemy Storage" again. Checked in game: tavern, town (both fonts),
  temple; the subtitled opening movie plays in the emulator.

## 0.1.15 (2026-11-18, test build, not a release)
- Name entry ported from Elminage III (tools/name_entry.py): one Latin keyboard page (A-Z, a-z, 0-9,
  punctuation, blank cells type a space, end key "OK"); keys and typed text drawn in the VWF font, the
  cursor box follows the real text width, names are stored as plain ASCII (trailing spaces trimmed).
  Limits doubled for 1-byte letters: name 20, nickname 12, spell name 24 (same record fields).
  Covers registration, Change Name (an existing English name converts back with the cursor at its end),
  the Book of the Next Age character's name, and Options > Battle > Rename Spells. Kept on the original
  keyboard: the two riddle answers (scripts 34001 / 53001 compare box-drawing glyph strings) and the Book of
  the Next Age password. Tested in game: register (name, nickname, back and forth between fields), Change
  Name on Grace, Rename Spells.
- HD font, chosen at New Game (ported from Elminage III): a popup over the first town picture asks for
  "Original pixel font" (default) or "HD font"; stored in script variable 4990 (0 = old save / not asked =
  original). The HD sheet FONT10HD.GIM (new ANIME entry) is a 2x rendering of Console Sans Medium
  (puzzylpiece/console-sans v0.3, SIL OFL 1.1; work/font/consolesans/OFL.txt) at 85% width; the glyph and
  sprite hooks switch to it for ASCII when the variable is 2 (half-width kana stay on the pixel sheet), and
  the VWF width table has an HD half. Word wrap uses the per-letter max of both fonts (+61 page splits in
  SCDWMAP). To keep ANIME.BIN in its disc slot (26 KB slack), FONT10_16.GIM is cut to its used 256x128
  rows and the HD sheet is 2x (512x128, 4-bit) instead of Elminage III's 4x.
- New debug tool tools/hotpatch.py: writes the bytes that changed between two EBOOT builds into the
  running emulator (code patches and the cave), so a savestate can test new code without a replay.
- Real hardware: everything is cave code plus one new archive file; both font sheets stay loaded (+33 KB).

## 0.1.14 (2026-11-18, test build, not a release)
- 12px font (FONT12_12) variable width, ported from Elminage III (tools/vwf.py apply12): English letters drawn
  with this font advance by their ink width instead of 12 px each, so party-bar names no longer overlap.
  Hooks: 0x088F10F8 (full-width glyph draw, j to cave; uses the free stack word 0x10($sp)) and 0x088F0F20
  (space). Only fonts with a 12 px cell are affected; Japanese and the 16px font are unchanged.
- Squeezed button labels (Temple of Orses, Uncurse/Repair, Treat/Retrieve on EL02_001) are now anti-aliased:
  ink and outline are drawn at full width and then narrowed, instead of being cut to one-bit pixels with a
  hard 8-copy outline that made them look bold and jagged next to the other buttons.
- Checked in game: party bar names (tavern, inspect, status), status screen, town menu with the temple
  button normal and selected.

## 0.1.13 (2026-11-18, test build, not a release)
- Review passes (accuracy -> editorial -> proofreading) on the 898 EBOOT strings added in 0.1.12
  (tools/eboot_slices.py check --snap, docs/agent_prompts/eboot_review_notes.md; reports
  work/translation/en/eboot_slices/eslice_NNN_{accuracy,editorial,proof}.md): 6 + 20 + 1 rows changed, all 12
  slices pass every stage.
- Decisions: status abbreviations as on the UI sheet (Cha, Pet; were Chm, Stn); tarot titles use the card names
  ("I. The Mage"); side wording "Party's X" / "Enemy's X", single targets "An ally's" / "An enemy's"; stand-alone
  results start with a capital; "EP" for experience; place names as in the glossary (Bilente's Shop, Dekor Temple
  Ruins, Madrie Church Cemetery); "Barrier" in full; "canceled" (US spelling) everywhere.
- Checked in game: boot, opening, tavern title and menu.

## 0.1.12 (2026-11-18, test build, not a release)
- EBOOT: the old 'name-entry glyph pool' range 0x08958D7C-0x089613BC was far too wide. Only 0x08958D7C-0x08958F7F
  (130 single characters: the name-entry set) stays untranslated; 925 strings after it were real UI text:
  town location titles (the tavern title was still Japanese in game), battle and status messages, status
  abbreviations, item-effect labels, compass modes, errors, debug menus. New tool tools/eboot_slices.py
  (reclass / make / check / merge); 898 strings translated in 12 slices (281 reuse the existing English for the
  same Japanese). Also 61 text strings the reference scan had missed (confirmation prompts, 'Equipped', preset
  names) are written in place.
- Found while translating: three 'strings' were bytes of constants (u32 10,000,000, floats 1.2f / 0.3f) and are
  now 'never'; two slots start on a float's top byte (0x3F '?') and keep the leading '?'; one line
  (0x08954908, 99 bytes) had been split by the scan at its half-width dots and is now one entry.
  Compass modes 'Relics' / 'Altars' fit their 9-byte slots (their code references cannot be repointed).
- Result: 612 strings in place, 691 in the cave, none left out. Printf '%' after a number is '%%'.
- Checked in game: the tavern title shows "Berte's Tavern"; opening and tavern menu OK.
- Not reviewed yet (single translation pass): these EBOOT strings.

## 0.1.11 (2026-11-17, test build, not a release)
- UI textures: the menu buttons, plates and label strips baked into ANIME/EL01_000, EL01_001, EL02_000-003,
  EL03_000, EL03_003, EL03_004 are now English (EL03_001 / EL03_002 have no Japanese). Tools ported from
  Elminage III: tools/img_text.py, tools/ui_regions.py, tools/font12.py (ASCII -> full-width SJIS computed);
  specs and reports in work/ui/specs/, brief docs/ui_image_brief.md; build hook in patches.apply_all (option
  noimg). Godshade type code 'Gs'; Split / Pool Gold on both sheets.
- PSP home-menu title: PARAM.SFO TITLE 'Elminage II' (tools/sfo.py, in place).
- Data: 'Old Aim' (Elminage III reuse) -> 'Oldaim' (glossary / script), 8 cells.
- Checked in game: the tavern menu buttons show in English.

## 0.1.10 (2026-11-17, test build, not a release)
- Data tables (CSV) and EBOOT strings reviewed (accuracy -> editorial -> proofreading). New tool
  tools/data_review.py: review slices built from the current csv/eboot state (status 'new' / 'fit', 1,771 texts
  = 7,819 cells and strings, one row per Japanese + English so an edit lands everywhere), per-stage snapshots and
  checks (codes, printf placeholders, line breaks, ASCII, and no cell pushed over a byte budget it fitted),
  merge back. Prompt additions: docs/agent_prompts/data_review_notes.md. Reports:
  work/translation/en/data_review/rslice_NNN_{accuracy,editorial,proof}.md. 283 texts changed (316 cells).
- Names aligned with the reviewed script and glossary: Chaff (was Kasu), Dekor Ruins, banner (was flag),
  Dodo King, phony / real Ranger, Underworld Gt., Airy Vider, Rondelgius's Banner, Raizam's Whiskers,
  Head of Yr McMahon, Heerdahl's Footbath Hall, floors 1F / B2F, beastfolk. 管理官アルケロン = Supervisor Archelon
  (a different title from 魔術局長 = Director; glossary entry added).
- Credits: staff names in Western order (given name first), byte lengths unchanged.
- Tarot descriptions in one pattern ("The Fool tarot card."); 魔術師 stays "Mage" (shared with the class name).
- Kept on purpose: "Dev." / "Btl" (cells shared with 4-byte ITEM header cells the game compares); quest hint
  47:8 "three" switches (the Japanese hint says three; the script says four); lowercase "demon swd baltagias"
  (its Japanese is hiragana, unlike the real sword).
- Punctuation: commas and periods inside closing quotes (US style) across the reviewed rows.
- Checked in game: boot, opening narration, tavern and Kernel Shop scenes.

## 0.1.9 (2026-11-17, test build, not a release)
- Script review passes complete (BASE_RULES: accuracy -> editorial -> proofreading) on all 69 slices / 5,460 unique
  rows. Each stage snapshots the slices (work/translation/en/review_snapshots/pre_*) and tools/review_check.py
  checks every slice against it (keys, jp, control codes, ASCII); all 69 pass after every stage. Editorial pass:
  727 rows; proofreading: 72 rows plus rechecks of every row the editorial reports flagged for meaning.
  Reports per slice: slices/slice_NNN_{accuracy,editorial,proof}.md.
- Conventions settled during the passes (work/translation/en/review_notes.md): class 狩人 = Ranger (as in the class
  tables); 石碑 = stone tablet; Rondelgius's 旗 = banner; Elpina's 姐さん = Sis; Gurtia's ウフフ = "Hee hee", other
  うふふ = "Ufufu"; Kine "Hyeh hyeh hyeh" / "youngster"; Jeratan's th-lisp; the old-man figure = statue; Costo,
  Hess, Mirco, Zeshrom he/him; Namina still no pronoun; race names lowercase in prose; "All right" (not "Alright");
  cut-off speech follows the source mark. Rows with the same Japanese in different slices use identical English
  (e.g. 010:3055 = 011:3123 p2, 011:3203 = 012:3331, 017:4208 = 018:4268, 041:3074 = 042:3228).
- Redraw chain SCD19:4117-4127 (slices 066/067) checked after each stage. Lecture rows SCD12:3303/3310/3317 encode
  to 1829/1917/1896 bytes (cap 2000).
- EBOOT: 4 strings reused from Elminage III had lost the source's trailing line break, so two system messages ran
  together on one line ("...on the Memory Stick.Starting a new game"); the break is restored. Checked in game:
  the no-save message now shows on two lines; boot through the opening narration OK.
- Not reviewed yet: data tables (CSV) and EBOOT strings (first-pass translation only).

## 0.1.8 (2026-11-16, test build, not a release)
- Data tables and EBOOT strings translated (first pass). All text layers are now English:
  script 44,334 / 44,334 player-visible rows, CSV 15,972 / 15,972 cells the game keeps (0 over budget),
  EBOOT 366 / 366 referenced strings (218 in place, 148 moved to the cave and repointed).
- Which CSV cells the game keeps: a RAM dump at the title (work/emulator/states/ram_title.bin) marks the
  cells whose bytes stay in memory (15,977 of 21,539; designer notes and headers mostly drop out).
- tools/tm_prefill.py: 9,690 cells and strings filled from the Elminage III translation where the Japanese
  is identical (status 'elm3'); one English per Japanese across CSV and EBOOT so strcmp keys stay equal.
- Never written (tm_prefill NEVER / eboot status 'never'): EMPLOY permission marks ○ ●, the parse key 当人,
  the name-entry keyboard table 0x08951498-0x08953998 (296 rows read cell by cell), the name-entry glyph pool
  0x08958D7C-0x089613BC (1,055 cells the editor compares typed characters with; the Elminage III prefill had
  written into 764 of them and was reverted), and 6 binary runs that only looked like text.
- Compare keys found by scanning every strcmp (0x08817294) / strncmp (0x08817114) call with a literal EBOOT
  argument (22 keys). 雲の上: the script line is now 'Above the clouds'; the EBOOT key gets the same English
  and patches.text_checks compares 16 bytes (0x0887FEC8).
- New translation (tools/data_slices.py, docs/data_brief.md, intake tools/dslice_in.py): 26 slices, 2,051
  unique strings (event log, item and monster names and lore, help texts, EBOOT messages).
- Byte budgets: 412 cells (408 reused Elminage III English) exceeded Elminage II's column budgets and were
  shortened by agents (tools fit_slices); a row that serves several columns is accepted when it fits the
  largest, csv_build skips the rest (header copies stay Japanese, not displayed).
- One name pass across script, CSV and EBOOT: Airy Vider (Elm3), hanafuda sword names as in the item table
  (Chaff, Fair Yoshino, Clearly Splendid, Front Sugawara, Five Lights, Light cards), Apasha, the Abyss,
  Jera (not Jela), Godshade for 神影.
- Open (see review_notes.md): budgets are the longest Japanese per column, not the game's field sizes, so
  some names are cramped (MONSTER1 cols 6/7 show e.g. 'Chimra', 'Mizuti'): trace the parser's field sizes;
  description boxes need the pixel word wrap port (Elminage III vwf.apply_wrap); name entry keeps the
  Japanese keyboard (Latin keyboard = port of Elminage III name_entry.py); credits roll mixes name orders.

## 0.1.6 (2026-11-16, test build, not a release)
- Script translation complete (first pass): batches 4-7, slices 030-068, the Semnadoc Cathedral, the ELM
  area and every dungeon chapter event script (SCD01-SCD19). All 5,460 unique rows translated and passed
  tools/slice_in.py; merged into all 44,334 player-visible script rows (0 untranslated; developer test
  scripts 00101-00108 / 99999 excluded).
- Cross-slice consistency by script before each merge (see work/translation/en/review_notes.md): Grand
  Chancellor, arcane experiment, Ultimate / High Mana Source, Strafe Pursuit, sent to the Horizon, the exam /
  certificate series, Ogre Below; honorific rule re-applied; Kine and Namina pronouns removed where the script
  gives no gender (3 rows). Redraw rows that span slices 066/067 checked to match.
- Glossary 489 entries: Zeshrom male, Kathleen female, Eril female, Principal male (script evidence).
- Message buffer: op 0x8B parses into 0x08D11824, 0x800 bytes (next referenced variable at +0x800), so the
  builder's 2,000-byte cap is right. Three lecture rows in SCD12 (slice 054) exceeded it (up to 2,600 bytes)
  and were compressed without dropping content.

## 0.1.5 (2026-11-16, test build, not a release)
- Script translation batch 3: slices 020-029 (800 unique rows, first pass): SAI area (Armitt, Benef, Muse,
  Biren, the management office), GAN area (waiting scenes, Jera / Jeratan, the Blast) and the start of the
  SEM area (Harge: Kine, Tarzen, Namina; Caron). All 800 rows clean. 2,400 of 5,460 unique rows translated.
- Cross-slice consistency by script before the merge: hanafuda sword names translated as in Elminage III
  (Rainy Four Lights, Five Lights, Light cards, Boar-Deer-Butterfly, Chaff) instead of a mix of romanized and
  translated forms; item names identical to Elminage III take its English (Hundred Bamboo Edge, Yasha Princess).
- No honorific where the script does not establish gender: "Lady Kine" -> "Kine" (3 rows), "Lord Semnadoc"
  (a god) -> "Semnadoc" (9 rows); two added "her" for Namina replaced by her name. Lord Mersenne kept
  (male by script evidence).
- Glossary: +12 entries; Benef and Bilente set to male (script evidence); 夜叉姫 -> Yasha Princess.
- work/translation/en/review_notes.md: open items from all translator reports, sorted by review stage.
- SCDWMAP 632,192 / 917,504 bytes. Boot check only: the SAI / GAN / SEM scenes are not reachable without a
  save, so they are not checked in game yet.

## 0.1.4 (2026-11-16, test build, not a release)
- Script translation batch 2: slices 010-019 (800 unique rows, first pass, no review yet): the rest of the
  Bistel town tour (Berte, Rosetta's Inn, Kernel Shop, Orses temple and its services, Queen Ragnastia's
  court), the villains' camp (Urna and her followers), the Training Hall (Miria, Soara) and the first ISF /
  SAI area scenes. All 800 rows passed tools/slice_in.py. 1,600 of 5,460 unique rows now translated.
- tools/slice_in.py accepts box-drawing characters (U+2500-257F): they are Shift-JIS and the full-width
  font draws them (the fake glyph script in slice 017, row 4214).
- Consistency by script: "Alchemy Storehouse" -> "Alchemy Storage" (Elminage III spelling).
- Glossary: +16 entries from batch 2 (Animacie, Forsaken Painting 'Morning of Ruin', Alchemy Storage, Book of
  the Next Age, Rite of Flux, Lady Urna, Holy Ember, Old Compass...); Almite set to male (the old lady's son);
  open: Costo's former post (Finance Minister in the script vs Administration Bureau in the glossary).
- SCDWMAP 614,144 / 917,504 bytes. Projection: 970 untranslated rows left in SCDWMAP, about +50 KB.
- Checked in game: Kernel Shop (Costo, Miria), Rosetta's Inn, Orses temple (Bishop Saines, Sigret) all in
  English; 230 presses through the opening without a crash.
- To check later in game: centred system banners (slices 009, 010, 018), choice prompts over 30 characters.

## 0.1.3 (2026-11-16, test build, not a release)
- Script translation batch 1: slices 000-009 (800 unique rows; first-pass translation only, no review
  passes yet). They cover the shared dungeon scripts (00003-WALK Mirco / House Lenzer events, 00011-CHOUSA,
  009xx floor gimmicks) and the town opening up to the Kernel Shop. tools/slice_in.py checks each slice
  (keys, control codes, ASCII) before it is taken; all 800 rows clean. Merged into 57,448 script slots.
- Developer test scripts 00101-00108 (debug menus) are no longer extracted for translation (tools/slices.py).
- Consistency by script: Gurtia's ヘス様 -> "Hess" (3 rows), since Hess's gender is not established.
- Glossary: +17 entries from batch 1 (terms, forms of address, Almite, Hilde, Silent Beast, Stables, GP...);
  Costo set to male (script + portrait); Saines' position set to bishop (script: 司教).
- Script sizes after batch 1: SCDWMAP 589,568 / 917,504 bytes, largest chapter SCD19 420,864 / 655,360.
  Watch SCDWMAP as the town story is translated.
- Checked in game: Miria's tour, Berte's tavern and the Kernel Shop scene with Costo show in English.
  One emulator run exited early in the opening; a repeat run of the same build played through the
  same point without a problem (not reproduced, watch for it).

## 0.1.2 (2026-11-16, test build, not a release)
- Full pipeline in place: script text (tools/text_build.py), CSV cells (tools/csv_build.py + cell-copy hook
  0x088DF578), EBOOT strings (tools/eboot_text.py + repoint.py), VWF, all ported from Elminage III with
  Elminage II addresses. No CSV or EBOOT English yet; script English = the 41-row pilot (opening, 99101).
- Debug tools ported and documented (docs/debug_tools.md); trace_ops checked on the running game.
- tools/slices.py: 5,569 unique script rows in 70 slices of 80 (dedup across the 20 SCD files, test
  scripts skipped); `merge` writes slice English to every matching script row.
- docs/translation_brief.md for Elminage II; .gitignore (game data and Japanese working files excluded);
  tools/strip_jp.py copied from Elminage III.

## 0.1.1 (2026-11-16, test build)
- FONT10_16: Elminage II centres its half-width glyphs in the 10 px cells, so narrow letters had gaps
  ("p lains", "Bistel 's"). tools/font_build.py left-aligns 0x21..0x7E (palette indices moved, nothing
  redrawn) into work/font/FONT10_16.GIM; vwf.py measures it and the build puts it in ANIME.BIN.
  Checked in game: even spacing in the opening narration.

## 0.1.0 (2026-11-16, first test build)
- VWF (tools/vwf.py): draw string 0x088F0E84 hooks at 0x088F0F14 (space) and 0x088F10D8 (half-width
  advance), message window 0x08885160 / 0x0888516C; only for the 10 px FONT16 half sheet.
- Script text relocation hook on the string parser 0x08883F08 (escape mask without 0x13); chapter scripts
  load into their own 640 KB buffer (loader patch 0x08882ED8), SCDWMAP keeps the original 0xE0000 buffer.
- Memory: the game reserves a fixed 15 MB newlib heap (0x0894A2EC); growing the module by 640 KB alone
  stopped the boot (VRAM stayed empty). patches.shrink_heap lowers the heap by exactly the module growth
  (15360 -> 14464 KB). Measured heap use in the original: 9.95 MB at the title, 10.01 MB in the opening.
  REAL HARDWARE: same layout; heap peak in dungeons and battles is not measured yet.
- Data install: the original installs its archives to SAVEDATA/ULJM05488DATA01 without asking; installed
  copies would replace the patched archives. patches.no_install (0x088F06B0 / 0x088F06BC) always reads the
  disc. Real hardware: loads come from UMD only.
- Pilot: opening narration and the Miria / Berte tavern scene (41 rows of 99101-BIS_TOP_IN). Checked in
  game: English shows, 376 px wrap fits the box, long pages split.
- Test builds 0.0.2-0.0.7 were boot experiments (xdelta patches in work/output/patches).

## 0.0.1 (2026-11-16, groundwork, no build)
- Project set up from the Elminage III toolchain. The portable PPSSPP is in work/emulator/ppsspp: sound off,
  debugger port 56532, env ELM2_PPSSPP_PORT. The tool copies for reference are in tools/elm3_ref/.
- Decrypted EBOOT dumped. The Mps2 archive key was found (the CRC-32 table at 0x08961550). All archives were extracted.
- Ported tools: ppsspp_dbg, mips, mps2, eboot (cave 0x08FE8D00), scp_sig, scp, textcodec, extract_scp,
  extract_eboot, extract_csv. New tool: port_addr.py, which maps Elminage III addresses to Elminage II.
- Script extraction: 70,672 slots (5,571 unique) with byte-exact round trip.
- Addresses for the VM, string parser, message window and draw-string routine are recorded in docs/formats.md.
- Not done yet: glossary, VWF patch, text insertion/relocation hook, debug-tool docs, translation, ISO build.
