# Elminage II — debug tools

Emulator: portable PPSSPP 1.20.4 in `work/emulator/ppsspp/` (copied from the Elminage III project, no
`installed.txt`, so the memstick lives next to the exe). Config: software renderer, sound off (volume 0),
remote debugger on startup. The debugger port is discovered from the project emulator's PID (override:
env `ELM2_PPSSPP_PORT`); the tool refuses a port shared with another process. Only the emulator whose exe
path is inside this project is ever started or stopped.

**Confirm button is Circle** (Japanese release). Run Python with `PYTHONUTF8=1` (system codepage is GBK).

| Tool | Purpose |
| --- | --- |
| `tools/ppsspp_dbg.py` | start/stop/status, memory r/w, regs, breakpoints, input, VRAM screenshots, RAM dump, savestates |
| `tools/autoplay.py` | boot + press a button on a schedule, screenshots per N presses |
| `tools/hotpatch.py` | hot reload of the EBOOT: writes what changed between the savestate's build and a new one into RAM (not archives or loaded scripts) |
| `tools/trace_ops.py` | log script VM ops (bp 0x0887E22C) and script starts (bp 0x08881D7C). Checked: 0.1.2 opening, id 99101 |
| `tools/trace_files.py` | log archive file lookups (bp 0x088EDE84, a0 = name) — ported, not yet run |
| `tools/call_func.py` | call a game function at the script dispatcher, restore registers — ported, not yet run |
| `tools/membp_pcs.py` | list PCs that read a memory range — ported, not yet run |
| `tools/mips.py` | ELF loader, disassembly (`all_insns` steps over undecodable words), xrefs |
| `tools/port_addr.py` | Elminage III address -> Elminage II candidates (masked instruction match; `near <delta>` mode) |
| `tools/scp_sig.py`, `tools/scp.py` | VM operand signatures from the EBOOT; script parser / coverage check |
| `tools/release.py` | package a release: xdelta (verified round trip), README/CHANGELOG txt, manifest, validation, checksums in work/release/v<ver>/ |
| `tools/prune_outputs.py` | after a build: older ISOs -> verified xdelta patches (max 10), `work/xdelta/xdelta3-3.1.0-x86_64.exe` |

```bash
python tools/ppsspp_dbg.py start work/output/current.iso
python tools/ppsspp_dbg.py shot work/emulator/shots/x.png
python tools/ppsspp_dbg.py reset        # clear breakpoints, resume (after an interrupted script)
python tools/trace_ops.py 40 --press    # 40 VM events, pressing Circle while idle
```

## Addresses (EBOOT v1.01, decrypted ELF)
| Address | Meaning |
| --- | --- |
| 0x0887E22C | script VM dispatcher (a0 ctx, a1 op); ctx+0x528 read ptr, ctx+4 base, ctx+0 sub-script start (format byte) |
| 0x08881D7C | start script (ctx, ptr, id) |
| 0x08883F08 | script string parse/copy — hooked for relocated text (`1B 7D/7A/79` slots, tools/text_build.py) |
| 0x08884E20 | message window renderer; per-char draw 0x08885160, advance 0x0888516C (VWF) |
| 0x088F0E84 | draw string; VWF hooks 0x088F0F14 (space) and 0x088F10D8 (half-width advance) |
| 0x08882E68 | script file loader; patched at 0x08882ED8 (chapters -> own buffer) |
| 0x08C315C0 | script buffer (0xE0000 bytes, counters 0x08D115C0 used / 0x08D115C4 remaining): SCDWMAP only (patched) |
| 0x089573C0 | script file name table (0 = scdwmap.bin, 1..19 = scd01..19.bin) |
| 0x088EDE84 | find file in mounted archives (a0 = name) |
| 0x088F062C | Memory Stick data-install mount check (patched: always read from disc) |
| 0x088DF578 | CSV cell copy (patched: 0x1F/0x1E/0x1D -> , " LF) |
| 0x0894A2EC | `sce_newlib_heap_kb_size` = 15360 (patched down by the module growth) |
| 0x08B66D30 / 34 / 38 | newlib sbrk: current break / heap base / heap end — heap use 9.95 MB at title, 10.01 MB in the opening |
| 0x08FE8D00 | code cave start (= original memsz end); bss after cave + 0x40000 |
| 0x04000000 | VRAM; display framebuffers at +0 and +0x88000 (480x272 RGBA8888, stride 512) |

## Savestates (`work/emulator/states/`)
The project emulator uses the software renderer (screenshots read VRAM at 480x272), so it cannot show how
the HD font looks at a higher rendering resolution; compare sheets offline instead.

A savestate holds the old EBOOT and loaded scripts. EBOOT-only changes: load the state, then
`python tools/hotpatch.py <EBOOT.BIN of the state's build>` (saved next to each state as <state>.EBOOT.BIN; new patches go at the
end of patches.apply_all so the cave layout stays). Archive or script changes still need a fresh boot.
Running a state on a newer disc image also breaks chapters loaded afterwards: the game keeps the archive TOCs
from boot, and the first 0x20 bytes of each file are XORed with a key from its TOC offset / size
(tools/mps2.py), so a chapter whose size changed loads with a garbled header, none of its sub-scripts are
registered (index 0x08C30DC0, count 0x08D115DA) and the debug line "Specified script not found. [01001]"
appears on every step. Seen in 0.8.2 testing (v080_tavern + 0.8.2 image); not a bug of the build.

Riddle test without reaching the riddle (0.8.2): in a dungeon (the editor only runs in the dungeon scene),
break at the script dispatcher 0x0887E22C, write `A2 15 00 01 00 01 00 <prompt off>`, `A3`,
`A2 15 00 00 00 01 00 <prompt off>`, `A4 <answer> 1B 00` after the sub-script base, point ctx+0x528 at it and
set a1 = 0xA2; type the answer and break at 0x088801D4 (strcmp a0 = answer, a1 = typed text).

| State | Build | Place |
| --- | --- | --- |
| jp_tavern_opening | original JP | new game opening, Berte's tavern, Berte speaking (name box + message) |
| v0114_tavern | 0.1.14 | tavern menu after the opening, premade party (hotpatch base: v0114_tavern.EBOOT.BIN) |
| v0115_hd_tavern | 0.1.15 | same place, HD font chosen at New Game (hotpatch base: v0115_hd_tavern.EBOOT.BIN) |
| v0117_hd_narration | 0.1.17 | opening narration, HD font chosen (hotpatch base: v0117_hd_narration.EBOOT.BIN) |
| v0116_tavern | 0.1.16 | same place, original font (set var 4990 = 2 in RAM for HD; hotpatch base: v0116_tavern.EBOOT.BIN) |
| v0123_tavern | 0.1.23 | tavern menu after the opening, premade party, original font (hotpatch base: v0123_tavern.EBOOT.BIN) |
| v080_tavern | 0.8.0 | same place, released build (hotpatch base: v080_tavern.EBOOT.BIN) |

## Memory Stick install
The original game installs its archives to `SAVEDATA/ULJM05488DATA01` (169 MB) without asking. The
emulator memstick here has such an install (made by the original ISO). Patched builds ignore it
(`patches.no_install`); real players who installed from the Japanese disc are safe for the same reason.

## Not built yet (guide steps 5–8)
Safe halt, hot reload of archives and scripts, scene preview and the coverage scan of the built image.
