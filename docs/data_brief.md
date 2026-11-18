# Translator brief — Elminage II data tables (CSV) and EBOOT strings

Read `BASE_RULES.md` and `docs/translation_brief.md` (game context) first. Use `work/glossary/glossary.json`
and the conventions in `work/translation/en/review_notes.md`. About 10,000 cells were already filled from
the Elminage III translation where the Japanese is identical: when you need an established term (class,
race, stat, status, spell, item, monster), look it up in the filled entries of
`work/translation/en/csv/*.json` (fields `jp`, `en`, `status`) and `work/translation/en/eboot.json`, and use
the same English.

## Slice rows (`work/translation/en/data_slices/dslice_NNN.json`)
- `src`: `FILE.CSV:col` (a data-table column) or `EBOOT` (program text: menus, battle and system messages).
- `header`: the column header (what the column is). `row_name`: the item / monster / record the cell
  belongs to. `neighbours` (EBOOT): the strings stored next to it, often the same menu or message family.
- `ids`: every place this Japanese appears; one English serves all of them.
- `max` (CSV): byte budget. The English (ASCII, 1 byte per character) must not exceed it, or the build
  skips the cell. Write the full meaning first; if it does not fit, abbreviate (BASE_RULES), and report.
- `jp`: source. Write the translation in `en`.

## Rules for this text
- Names (items, monsters, spells, places): Title Case, short, consistent with the filled entries and the
  glossary. Item and monster names are usually limited to about 16-20 characters by `max`.
- Descriptions (ITEM_TEXT, MON_TEXT, EVENT_TEXT, HELP_TEXT...): full sentences. Line breaks in the source
  (`\n`) only lay out the Japanese; you may drop or move them. Keep blank-line paragraph breaks.
- EBOOT strings: keep printf placeholders exactly (`%s`, `%d`, `%2d`, `%-8s`...) and their order unless English
  grammar needs a different order (then report it). Keep leading/trailing spaces that pad columns.
  Battle messages like `%s は灰になりました` become `%s was turned to ash.`: the placeholder is a name.
- Do not translate entries that are clearly debug-only or unused labels if you are unsure what they are;
  translate them plainly and mark `note: "debug?"`.
- Plain ASCII only. Full-width symbols used as marks (★ ◆ ○ ● ※ →) may stay if they are part of the source.

## Output
`dslice_NNN.out.json` (same rows, `en` filled, optional `note`) and `dslice_NNN.report.md` (rows examined vs
rows in slice, over-budget rows, new terms, uncertainties). Do not edit any other file. Never print
Japanese to the console; use `PYTHONUTF8=1` for Python. Validate the output (valid JSON, same keys and order,
placeholders and control codes kept, ASCII, `max` respected) before finishing.
