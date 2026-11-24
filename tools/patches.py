"""All EBOOT code patches for Elminage II. apply_all(eb, opts) -> info dict (archives to rebuild).

REAL HARDWARE: the build replaces the encrypted EBOOT.BIN with the patched plain ELF. That runs on
PPSSPP and on a PSP with custom firmware only. All patches are code-cave hooks; no timing changes.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


HEAP_KB = 0x0894A2EC        # sce_newlib_heap_kb_size (15360 = 15 MB, allocated at boot by _sbrk 0x08804664)
ORIG_MEMSZ_END = 0x08FE8D00


def no_install(eb):
    """Never use (or create) the Memory Stick data install (SAVEDATA/ULJM05488DATA01).

    The installed archives are copies of the ORIGINAL archives and would override the patched disc
    files. Mount check 0x088F062C loops over the 5 archives and tests the installed copy; we force
    the 'not installed' branch (flag +8 = 0 -> read from disc) and skip the install step without
    counting the archive as missing, so the game never prompts to install.
    Same patch as Elminage III 0x0891B2F0 / 0x0891B2FC. Real hardware: loads come from UMD only.
    """
    eb.asm(0x088F06B0, 'nop', expect=1)                 # was bnel v0,zero (installed -> use it)
    eb.asm(0x088F06BC, 'j 0x088F07EC; nop', expect=2)   # was beqz s7 (install) ; addiu s4,1


def shrink_heap(eb):
    """The game reserves a fixed 15 MB newlib heap right after the module, which leaves no user
    memory for a larger module (a 640 KB bss growth alone stops the boot). Heap use measured in the
    original game: 9.95 MB at the title, 10.01 MB in the opening (pools are allocated once), so the
    heap is reduced by exactly the module growth, rounded up to 64 KB.
    REAL HARDWARE: same memory layout as PPSSPP; re-measure heap peak in dungeons/battles."""
    end = max(eb.cave_ptr, eb.bss_ptr)
    grow = max(0, end - ORIG_MEMSZ_END)
    grow_kb = ((grow + 0xFFFF) & ~0xFFFF) // 1024
    kb = eb.u32(HEAP_KB)
    assert kb == 15360, kb
    eb.w32(HEAP_KB, kb - grow_kb)
    print('  heap: %d KB -> %d KB (module grows by %d KB)' % (kb, kb - grow_kb, grow // 1024))


def csv_text(eb):
    """CSV cell copy (0x088DF578, Elminage III 0x08909B44): bytes 0x1F, 0x1E and 0x1D, written by
    tools/csv_build.py for English ',', '"' and a line break, are stored as ',', '"' and 0x0A (the game's
    reader splits at every ',' even inside quotes and drops '"'). Hook replaces the delimiter test
    0x088DF620..0x088DF634. Real hardware: cave code only; original data never has 0x1D-0x1F.
    """
    eb.asm_alloc('''
            lb $a2, -0x1544($v0)
            sll $t0, $t1, 24
            sra $t0, $t0, 24
            beq $t0, $a2, cs_end
            nop
            beq $t0, $v1, cs_end
            nop
            addiu $at, $zero, 0x1f
            bne $t0, $at, cs_q
            addiu $at, $zero, 0x1e
            b cs_st
            addiu $t1, $zero, 0x2c
        cs_q:
            bne $t0, $at, cs_n
            addiu $at, $zero, 0x1d
            b cs_st
            addiu $t1, $zero, 0x22
        cs_n:
            bne $t0, $at, cs_st
            nop
            addiu $t1, $zero, 0x0a
        cs_st:
            sb $t1, 0($a0)
            j 0x088df604
            nop
        cs_end:
            j 0x088df638
            nop
        ''', 'csv_cellcopy')
    eb.asm(0x088DF620, 'j 0x%08x; nop' % eb.symbols['csv_cellcopy'], expect=2)


def text_checks(eb):
    """Script op 0x96 parses its string into the message buffer 0x08D11824 and then
    strncmp(buf, eb@08956c00 '雲の上', 6) (0x0887FEB4..0x0887FEC8). The script line is now
    'Above the clouds' and the EBOOT key gets the same English (merge rule), so compare 16 bytes.
    Same patch as Elminage III (0x08890C30)."""
    eb.asm(0x0887FEC8, 'addiu $a2, $zero, 16', expect=1)   # was addiu a2, zero, 6


def apply_all(eb, opts):
    info = {'archives': {}}
    no_install(eb)
    if 'novwf' not in opts:
        import vwf
        if 'nohd' not in opts:
            import font_hd
            vwf.HD_WIDTHS = font_hd.hd_widths()
            if vwf.HD_WIDTHS:            # word wrap must fit either font: per-char max width
                orig = vwf.measure()
                vwf.TEXT_WIDTHS = [max(a, b) for a, b in zip(orig, vwf.HD_WIDTHS)]
        vwf.apply(eb, info)
        vwf.apply12(eb, info)                 # 12px font (party bar names): ink-width advance
    if 'notext' not in opts:
        import text_build
        text_build.apply(eb, info, opts)
        try:
            import csv_build
        except ImportError:
            csv_build = None
        if csv_build:
            csv_build.apply(info)
            csv_text(eb)
        try:
            import eboot_text
        except ImportError:
            eboot_text = None
        if eboot_text:
            for line in eboot_text.apply(eb)[:20]:
                print('   ', line)
            text_checks(eb)
    if 'novwf' not in opts:             # after the text patches: needs vwf_widths, keeps their cave layout
        import name_entry
        name_entry.apply(eb)            # Latin name entry, VWF display, ASCII names
        if vwf.HD_WIDTHS:
            vwf.apply_hd(eb, info)      # HD font sheet + glyph/sprite hooks (chosen at New Game)
        vwf.apply_ticker(eb)            # pixel-smooth scrolling help line
        vwf.apply_wrap(eb)              # word wrap in the event list and the monster / item descriptions
        import ui_fixes
        ui_fixes.apply(eb)              # character creation: wide selection box for gender / alignment
    if 'notext' not in opts:
        import eboot_text
        eboot_text.apply_overrides(eb)  # own strings for single pointers (shop categories, equip compare)
    if 'noimg' not in opts:
        # UI textures with baked Japanese text: work/ui/specs/*.json (tools/img_text.py)
        import img_text
        for arc, files in img_text.archive_files().items():
            info['archives'].setdefault(arc, {}).update(files)
        import title_logo               # title logo: English subtitle and reading (GR01_10303)
        for arc, files in title_logo.archive_files().items():
            info['archives'].setdefault(arc, {}).update(files)
        import anm                      # facility buttons 114 -> 130 px (MD02_004.ANM rects, EL02_001 widen)
        for arc, files in anm.archive_files().items():
            info['archives'].setdefault(arc, {}).update(files)
    shrink_heap(eb)
    return info
