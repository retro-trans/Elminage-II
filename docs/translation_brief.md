# Translator brief — Elminage II (PSP) script text

Read `BASE_RULES.md` (project root) first; it is binding. This file adds the game's text format.

## Game context
Elminage II: Sousei no Megami to Unmei no Daichi (Starfish-SD, PSP 2010). A first-person
dungeon-crawler RPG (Wizardry-like). The player's party is a group of adventurers created by the
player; NPCs address the player or the party (君, 君たち, あなた, あなたたち: "you"). The party's
gender and number are never fixed: refer to the party or a party member as "you" / "they".
The hub is the fortress city of Bistel on the Hestrio Continent. Queen Ragnastia has issued a
Decree: Fiona, the Earth Goddess, has lost her sovereignty to an awakened ancient evil spirit.
There is no official English release. Names come from `work/glossary/glossary.json`; use them
exactly. A name not in the glossary: romanize it, keep it consistent within your slice, and list it
in your report under "new names". Elminage III (sequel) spellings were reused where they exist.

## Row fields (slice files `work/translation/en/slices/slice_NNN.json`)
- `kind`: `name` = speaker name box (short!), `msg` = dialogue/narration window,
  `data` = choice prompt, menu choice text or a list item (short), `opXXX` = other UI text.
- `speaker` = the Japanese speaker name of the preceding name box (context only).
- `sub` = the script the row comes from (rows of one scene share it); `key` = id, do not change.
- `jp` = source. Write your translation in `en`.
- Rows are unique lines: a line that occurs in several places appears once, at its first occurrence.

## Control codes (keep exactly, same order)
- `{w}`  wait for a button press, then the text continues on a NEW LINE. Never put `\n` after `{w}`.
- `{p}`  new page (always right after `{w}`). Keep every `{w}` and `{p}` of the source, in the same
  order, so pauses and page breaks land where the Japanese has them.
- `\n`   plain line break. You do not need to reproduce the Japanese `\n`s: English is word-wrapped
  automatically (376 px, about 55 characters per line, 3 lines per page; an over-full page is split
  automatically). Use `\n` only where a break matters (lists, poems, signs).
- `{0C:0001:0001}`, `{0B:0003:0000}`, `{12:0003:0018}` etc. are runtime inserts (names, numbers,
  items). Keep them verbatim; move them where English grammar needs them. A `{0C:...}` insert shows a
  name or word of roughly 8 characters.
- Other `{XX}` codes (e.g. `{0E}`, `{0F}`) are display codes: keep them where they are.
- Japanese quote brackets 「」 -> English double quotes "...". 『』 -> single quotes for named things.
  The full-width space that indents continuation lines inside a quote is dropped.
- Plain ASCII only: straight quotes, `...` for ……, `--` for a dash. No accented letters.

## Length
- `name` rows: keep under ~16 characters.
- `data` rows used as menu choices: keep under ~30 characters.
- `msg`: no hard limit; write the full meaning first (see BASE_RULES), the build wraps it.

## Output
Write the same list of rows to `work/translation/en/slices/slice_NNN.out.json` with `en` filled (add a
`note` field on rows where you made a non-obvious call). Then write `slice_NNN.report.md`: rows
examined vs rows in slice, new names, decisions, uncertainties, rows left untranslated and why.
Do not edit any other file. Never print Japanese text to the console (write files instead, and use
`PYTHONUTF8=1` for Python).
