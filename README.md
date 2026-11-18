# Elminage II — translation project

An open toolchain for translating **Elminage II: Sousei no Megami to Unmei no Daichi**
(PSP, ULJM05488), plus the English translation built with it.

## Contribute

The script, menus, item and monster data, UI artwork and the opening movies are translated,
but the game has not been played through to the end yet, and no human has proofread the
English against the Japanese. If you want to contribute to this project or the next in any
way — be it bug reports, proofreading or playtesting — please join my Discord:

**[discord.gg/nZBZfTDfCP](https://discord.gg/nZBZfTDfCP)**

## Play it

The latest release is **[v0.8.0](https://github.com/retro-trans/Elminage-II/releases/tag/v0.8.0)**,
a full patch for the Japanese release (**ULJM05488**): the whole script, menus, data tables,
interface artwork and the subtitled opening movies are in English, with a variable-width font
and an optional HD font chosen when you start a new game.

### Apply

Use [Retro Trans](https://github.com/retro-trans/retro-trans-tools), or apply the `.xdelta`
with DeltaPatcher or xdelta3. You need your own Japanese disc image.

| Your source image | Patch |
|---|---|
| Japanese release, ULJM05488 | `Elminage2-English-v0.8.0.xdelta` |

Check the source hashes in `README-v0.8.0.txt` if your patcher reports a mismatch; keep
checksum verification enabled.

For example:

```
xdelta3 -d -s "Elminage II - Sousei no Megami to Unmei no Daichi (Japan).iso" Elminage2-English-v0.8.0.xdelta "Elminage II English v0.8.0.iso"
```

A CSO or CHD must be converted back to a plain ISO first.

**Boot the new image fresh.** Old emulator save states keep the previous executable and
scripts; in-game saves (Memory Stick) work across versions.

The patched executable is unencrypted: it runs on PPSSPP and on a PSP with custom firmware.
Do not use the game's data install to Memory Stick: it would load the untranslated archives.
The patch turns the install off.

### Text font

At the start of a new game you choose the text font:

- **Original pixel font** — the default; looks right at 1x and on real hardware.
- **HD font** — a 4x rendering of [Console Sans](https://puzzylpiece.xyz/consolesans/),
  sharp on PPSSPP with a hardware renderer (Vulkan, OpenGL or Direct3D) at 2x or higher
  rendering resolution. It has no benefit with the software renderer.

The choice is stored in your save. Saves made with the untranslated game use the original font.

## Translate it

Fork it to fix the English, or to take the game into another language. The working rules
are in **[BASE_RULES.md](BASE_RULES.md)** and **[docs/translation_brief.md](docs/translation_brief.md)**;
the formats are in **[docs/formats.md](docs/formats.md)**.

```sh
python tools/extract_scp.py          # script strings from your own disc's archives
python tools/extract_csv.py          # data tables
python tools/extract_eboot.py        # executable strings
python tools/restore_en.py           # copy the English from the *.en.json files into them
#   ... edit the "en" fields in work/translation/en/ ...
python tools/build.py 0.8.0          # build work/output/Elminage II (EN) v0.8.0.iso
```

The script stays in place: English goes into the freed string slots and a small hook in the
executable follows the links, so script code never moves.

You need your own copy of the game. This repository contains no disc image, no game data
and no dump of the original Japanese script. The translation files here
(`work/translation/**/*.en.json`) carry only ids, offsets and English; the tools read the
Japanese from the disc you dump yourself.

## What is here

| Path | Contents |
|---|---|
| `tools/` | 51 tools: archive and image codecs, the script VM parser, text insertion, VWF and HD font patches, the Latin name entry, the movie subtitler, the PPSSPP debugger client |
| `work/translation/en/` | the English: 67,872 script strings, 1,327 executable strings, 34 data tables |
| `work/glossary/glossary.en.json` | 490 names and terms |
| `work/ui/specs/` | 9 interface sheets: where each Japanese label sits and its English |
| `work/movie/captions.json` | the opening movies' English captions and timing |
| `docs/formats.md` | archives, scripts, fonts, the name-entry editor, UI sprites and the script variables |
| `docs/debug_tools.md` | the live-debugging tools and the addresses they rely on |
| `BASE_RULES.md` | portable rules for running a project like this |
| `CHANGELOG.md` | every build, what changed, and what broke |

## Using these tools

They expect your own Japanese disc image in the project folder and the files extracted
from it in `work/source/` (`tools/mps2.py` for the archives, then `tools/extract_*.py`).
Python 3.8+, with numpy, Pillow, keystone-engine and capstone; ffmpeg for the movies;
xdelta3 for patches.

```sh
python tools/build.py 0.8.0                   # full build
python tools/ppsspp_dbg.py start work/output/current.iso
python tools/hotpatch.py work/emulator/states/<state>.EBOOT.BIN   # reload the executable into a savestate
```

## Do not sell this

This patch is free. Do not sell it, and do not sell anything made with it - no
pre-patched discs or images, no loaded memory cards or consoles, no paywalled or ad-gated
downloads.

It is an unofficial fan translation of a game Starfish-SD owns. Selling it takes money for
work that was given away, and it is the surest way to get a project like this shut down.

## Credits

We use the [Console Sans font by puzzylpiece](https://puzzylpiece.xyz/consolesans/)
(SIL Open Font License 1.1, see `docs/fonts/ConsoleSans_OFL.txt`) for the HD text font.
Thank you to its creator.

The toolchain is ported from the
[Elminage III translation](https://github.com/retro-trans/Elminage-III), which runs on the
same engine.

| Role | |
|---|---|
| Project lead | binhlt0402 |
| Proofreading | *none yet - see [Status](#status)* |
| Playtesting | binhlt0402 |

Translation passes, tooling and reverse engineering were done with Claude (Anthropic),
directed by binhlt0402. The translation is machine-produced and then edited - see the
release notes for what that means in practice.

## Status

The translation is in progress. `CHANGELOG.md` is the honest record, including the builds
that shipped broken and why.

Every line was machine-translated and then put through separate machine review passes
(accuracy, editorial, proofreading) with a shared glossary. **No human has proofread it
against the Japanese yet.** In-game checks so far cover the opening and both opening movies,
the font choice and both fonts, the town, tavern, shop, Training Hall, character creation
and name entry, the status, item and equip screens, and the first battles; the later chapters
have only been checked by scanning the built files.
