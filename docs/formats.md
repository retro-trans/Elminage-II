# Elminage II (PSP, ULJM05488 v1.01): formats and addresses found so far

Same engine as Elminage III (`../Elminage III`), so its toolchain ports with new addresses.
The Elminage III tools are published in [retro-trans/Elminage-III](https://github.com/retro-trans/Elminage-III)
(a local copy for reference goes in `tools/elm3_ref/`, not committed). `tools/port_addr.py` maps an
Elminage III address to Elminage II by comparing masked instructions. Use `near <delta>` for short functions.
Always run Python with `PYTHONUTF8=1`, because the system codepage is GBK.

## Disc
- `PSP_GAME/SYSDIR/EBOOT.BIN` is encrypted. `BOOT.BIN` is zero-filled. The decrypted ELF was dumped by PPSSPP
  (DumpFileTypes=1) to `work/source/EBOOT.elf`: one PT_LOAD at 0x08804000, filesz 0x362D30, memsz 0x7E4D00.
  The .text section is 0x08804000..0x0893EDF0 and .data is 0x0893FE68..0x08B66D30.
- The archives in `USRDIR` are SCP, ETC, PARTS, BTL, ANIME and 3DPARTS. They use the Mps2 format, the same as Elminage III.
  The XOR key is the standard CRC-32 table at **0x08961550** (`tools/mps2.py`).
  Everything is extracted to `work/source/arc_<NAME>/`.
- ETC holds the same CSV tables as Elminage III (ITEM, MONSTER*, SPELL*, *_TEXT, EMPLOY...). ANIME holds the same fonts
  (FONT16_01..08, FONT10_16, FONT12_12, ...).

## Script VM
| Address | Meaning | Elminage III equivalent |
|---|---|---|
| 0x0887E22C | dispatcher (ctx a0, op a1), jump table 0x08943E38, **256 ops, no `FF xx` prefix** | 0x0888F074 |
| 0x0888147C/80/84 | dispatcher exits (default op = 0x0888147C) | 0x088934A8.. |
| 0x08881600 | read u8 | 0x08893614 |
| 0x08881614 | get decoded arg k | 0x08893664 |
| 0x08881628 | ARGS reader: **2 formats** (see below) | 0x08893678 |
| 0x0888184C | RAW reader | 0x08893808 |
| 0x08881D6C | base + offset resolver | 0x08893D48 |
| 0x08881D7C | start script | 0x08893D58 |
| 0x088821C0 / 0x088821C8 | string start / variable setter | 0x08894270 / 0x08894278 |
| 0x08883F08 | inline string parse/copy (a0 idx, a1 dst, a2 src, a3, t0 &consumed, t1): relocation hook point | 0x08897804 |
| 0x08884E20 | message window renderer (per character) | 0x08898808 |

- Sub-script: byte 0 is a format byte, then 3 bytes, then code (base = off+4). The ARGS reader reads the format byte at `*ctx[0]`:
  if `& 0xC0` is set, the mask is a u16 with 2 bits per argument (u8/s16/u32/var), as in Elminage III;
  otherwise the mask is a u8 with 1 bit per argument (1 = u16, 0 = u8).
- String-offset arguments: 0x8F arg 1, 0x92 arg 1 (choice prompt, with the same entry layout as Elminage III), 0xA2 arg 2.
- Escape codes with 4 operand bytes: 0A 0B 0C 10 11 12 (no 13). **Every byte >= 0x80 is read as a 2-byte character.**
- Coverage: 1603/1625 sub-scripts parse fully. The 22 that fail are all developer tests (00101-TEST-OP-01, 99999-TEST).

## Text drawing (VWF targets)
- Draw string at 0x088F0E84 (Elminage III 0x0891BAF8). Registers: font $s5, x $s3, y $s2, index $s0, half flag $s1.
  There is no clip path. The glyph lookup is 0x088F13B8 and the cell draw is 0x088F115C. The next-character join is at 0x088F1118.
  - Space advance is at 0x088F0F14 (`lw v1,0x14(s5); b next; addu s3,s3,v1`). Hook: `j vwf_space; nop`.
  - Half-width advance is at 0x088F10D8 (`lw v1,0x14(s5); b next; addu s3,s3,v1`). Hook: `j vwf_half; nop`.
    Apply only when font[0x14]==10, the same rule as in Elminage III.
- The message window advance hooks still need to be located inside 0x08884E20. In Elminage III they are at +0x340 and +0x34C.
- `tools/eboot.py`: the code cave starts at 0x08FE8D00, which is the end of memsz.

## Name entry editor
- State *(u32 *)0x08B8AC80: +8 text as 2-byte cells (0x100 bytes), +0x1C7A max cells, +0x1C7C cursor,
  +0x1C7E page (row offset, 6 per page), +0x1F8 character record, +0x1FC mode, +0x22C / +0x230 keyboard
  column / row, +0x108 riddle answer.
- Modes: 0x6D/0x129/0x87 name, 0x6E/0x12A/0x88 nickname (new / Book of the Next Age character / rename),
  0x1D Rename Spells (options), 0x0F riddle answer (script ops 0xA2 start, 0xA4 compare with strcmp; the
  answers in scripts 34001 and 53001 are box-drawing glyph strings from keyboard page 77), 0x128 Book of the
  Next Age password (36 cells). Mode setter 0x0882CD40.
- Keyboard: 15x6 cells per page, row pointers at 0x08953998 (78 pages = 468 rows); row 5 cols 12/13/14 =
  left / right / end. Nickname modes page through the first 4 pages only. Grid draw 0x0884C418, key handler
  0x0884C640, backspace 0x0884C7AC, cursor xy 0x0884C2A8, editor main 0x0884A06C (confirm 0x0884A2BC),
  spell-name confirm 0x08831380. Record fields: name +0x00 (0x14), nickname +0x19 (0x14).
- Patched by tools/name_entry.py (Latin keyboard, ASCII storage; riddle and password keep the original).

## HD font
- FONT16 object: constructor 0x088F0BAC (called 0x0886AD48), half-width sheet list 0x0895565C ([FONT10_16.GIM,
  NULL]; patched to add FONT10HD.GIM). Glyph routine 0x088F115C (font a0, x a1, y a2, sheet a3, u t0 / v t1 in
  pixels, cell w t2, h t3; single epilogue 0x088F13B0) -> sprite routine 0x088F22D8 (u t1, v t2, uw t3,
  [sp+0] vh). Half-width lookup 0x088F13B8: sheet font[0x2C], column (c-0x20)%25, row (c-0x20)/25.
- Script variables: s16 at *(u32 *)0x08C1CDBC + 0x153F4 + 2 * id, 5000 ids (cleared at New Game
  0x08883D0C); setter 0x088821C8. Font choice = id 4990 (tools/vwf.py FONT_VAR).
- Sheets are loaded by bare file name from any archive (0x088F0CBC sprintf '%s' -> loader 0x088F43B0); the
  4x HD sheet FONT10HD.GIM lives in PARTS.BIN.
- Patched by tools/vwf.py apply_hd + tools/font_hd.py; popup injected by tools/text_build.py
  inject_font_choice (SCDWMAP 99101-BIS_TOP_IN.bin +0x0034).

## UI sprite layouts (ANIME/*.ANM, 'animdata')
- Header: 'animdata', u32 0x20 = texture list offset, u32 record table offset, u32 next section, u32 size.
  Texture list: 0x100-byte slots ('el02_001.tga' = sheet EL02_001.GIM). Records: 28 bytes (s32 slot, u, v,
  w, h, 0, 0) = source rects, drawn at w x h. MD02_004.ANM holds the facility buttons (slot 2, 69 records).
- Third section (offset at +0x10, up to +0x14): 36-byte placements (s32 x, y, layer, rotX, rotY, rotZ, a%, sx%,
  sy%) in layout units (about 0.6 screen px). Windows are 9 pieces: TL corner, top edge (16,0, sx=(w-32)*25),
  TR corner, right edge (w-16,16, rotY 180, sy), BR corner, bottom edge, BL corner, left edge, fill
  (sx=(w-16)*10, sy). tools/anm_probe.py nudges one window in RAM to identify it.
- ANM group = index in the name table at 0x08955D74 (MD01_000 = 0, MD02_000 = 4, MD02_001 = 5, ...).
  Character creation: gender box sprite 0x4F4 (also the name-entry text cursor), alignment box 0x500, class
  boxes 0x510 / 0x508 (left / right column, ids at 0x089540F4), race box 0x520, icon grid 0x4EE.
- Menus address sprites by id = group << 8 | index (handles at 0x08C1CA4C; show 0x0887B144,
  position 0x0887ABC0). tools/anm.py; tools/uv_probe.py does not see these sheets (not redrawn from the RAM copy).

## Text inventory (work/translation/en/, Japanese, local only)
- Script: 70,672 slots, all byte-exact on round trip. **5,571 unique strings, about 239k Japanese characters**
  (4,916 msg, 283 name, 266 data, the rest are op strings).
- Only 300 script strings match the Elminage III translation exactly. The story is new text.
- EBOOT: 8,738 Japanese strings, 1,711 of them referenced by code or pointers (`eboot.json`).
- CSV: 21,539 Japanese cells in 33 tables (`csv/`). The `used` flags are only valid for ITEM_TEXT and MON_TEXT, because no
  title-screen RAM dump exists yet (`work/emulator/states/ram_title.bin`). The overlap with Elminage III has not been measured yet.
