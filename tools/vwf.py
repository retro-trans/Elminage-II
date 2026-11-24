"""Variable-width font for half-width (ASCII) text in the 16px font -- Elminage II.

Draw string 0x088F0E84 (font $s5, x $s3, char index $s0, string $fp) advances every
half-width glyph and the space by font[0x14] (= 10 for FONT16). Two hooks replace that
advance with a lookup in a 256-byte width table, only when font[0x14] == 10:
  0x088F0F14  space:      lw v1,0x14(s5); b NEXT; addu s3,s3,v1   -> j vwf_space; nop
  0x088F10D8  half-width: lw v1,0x14(s5); b NEXT; addu s3,s3,v1   -> j vwf_half;  nop
The glyph is still drawn as the full 10px cell (glyphs are left-aligned, cells transparent).

Message window 0x08884E20 draws one character at a time (jal draw @0x08885160 with the
1-2 byte string at $t2 = sp+0x3C) and advances by $s7 (cell width) @0x0888516C.
The wrapper returns the VWF width for ASCII and $s7 for anything else.

REAL HARDWARE: code lives in the EBOOT code cave (tools/eboot.py); no timing-sensitive code.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gim

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
FONT_SRC = os.path.join(ROOT, 'work', 'source', 'arc_ANIME', 'FONT10_16.GIM')
FONT_NEW = os.path.join(ROOT, 'work', 'font', 'FONT10_16.GIM')   # optional redrawn font

DRAW = 0x088F0E84
NEXT_CHAR = 0x088F1118
HOOK_SPACE = 0x088F0F14
HOOK_HALF = 0x088F10D8
MSG_DRAW_CALL = 0x08885160
MSG_ADVANCE = 0x0888516C
SPACING = 1
SPACE_W = 5

TEXT_WIDTHS = None      # widths for the script word-wrap: per-char max of the original and HD glyphs
                        # (set by patches.apply_all), so text fits with either font
HD_WIDTHS = None        # advance widths of the HD glyphs (second half of the EBOOT width table)

# Text font chosen at New Game (tools/text_build.py inject_font_choice): script global variable
# FONT_VAR, 0 = not asked (old saves) / 1 = original pixel font / 2 = HD font. Variables are s16 at
# *(u32 *)0x08C1CDBC + 0x153F4 + 2 * id (5000 of them, cleared at New Game 0x08883D0C; the game's
# own code uses ids up to about 3770).
FONT_VAR = 4990
FONT_HD = 2
VAR_BASE_PTR = 0x08C1CDBC
VAR_OFF = 0x153F4 + 2 * FONT_VAR        # 0x17AF0


def hdchk(reg, lab):
    """asm: reg = 1 if the HD font is selected, else 0 (clobbers $at)."""
    return '''
            lui {r}, 0x08c2
            lw {r}, -0x3244({r})
            beqz {r}, {lab}
            nop
            lui $at, {hi}
            addu {r}, {r}, $at
            lh {r}, {lo}({r})
            addiu {r}, {r}, -{hd}
            sltiu {r}, {r}, 1
        {lab}:
'''.format(r=reg, lab=lab, hi=VAR_OFF >> 16, lo=VAR_OFF & 0xffff, hd=FONT_HD)


def text_widths():
    """Widths for word wrap / fitting: per-char max of both fonts when the HD font is built."""
    return list(TEXT_WIDTHS) if TEXT_WIDTHS is not None else measure()


def font_path():
    return FONT_NEW if os.path.exists(FONT_NEW) else FONT_SRC


def measure(path=None):
    rgba = gim.decode(open(path or font_path(), 'rb').read())[0]
    a = rgba[:, :, 3]
    w = [10] * 256
    for code in range(0x21, 0x7f):
        i = code - 0x20
        x0, y0 = (i % 25) * 10, (i // 25) * 16
        cols = np.where((a[y0:y0 + 16, x0:x0 + 10] > 40).any(0))[0]
        w[code] = int(cols.max()) + 1 + SPACING if len(cols) else SPACE_W
    w[0x20] = SPACE_W
    return w


def text_width(s, widths=None, insert_w=64):
    widths = widths or measure()
    return sum(widths[ord(c)] if ord(c) < 0x80 else 16 for c in s)


def _hilo(v):
    hi = ((v + 0x8000) >> 16) & 0xffff
    lo = v & 0xffff
    return hi, lo - 0x10000 if lo >= 0x8000 else lo


def apply(eb, info):
    path = font_path()
    widths = measure(path)
    if path == FONT_NEW:
        info['archives'].setdefault('ANIME', {})['FONT10_16.GIM'] = open(path, 'rb').read()
    # [0:256] original font, [256:512] HD font (selected at run time, see hdchk)
    tab = eb.alloc(bytes(widths) + bytes(HD_WIDTHS or widths), 'vwf_widths', align=16)
    hi, lo = _hilo(tab)

    # half-width glyph: v1 = width[c] (c = byte at fp+s0) if font[0x14] == 10, else font[0x14]
    eb.asm_alloc(('''
            lw $v1, 0x14($s5)
            addiu $at, $zero, 10
            bne $v1, $at, vwf_h1
            addu $t9, $fp, $s0
            lbu $t9, 0($t9)
''' + hdchk('$t8', 'vwf_h1h') + '''
            sll $t8, $t8, 8
            addu $t9, $t9, $t8
            lui $t8, {hi}
            addiu $t8, $t8, {lo}
            addu $t8, $t8, $t9
            lbu $v1, 0($t8)
        vwf_h1:
            j 0x{nc:08x}
            addu $s3, $s3, $v1
        ''').format(hi=hi, lo=lo, nc=NEXT_CHAR), 'vwf_half')
    eb.asm(HOOK_HALF, 'j 0x%08x; nop' % eb.symbols['vwf_half'], expect=2)

    eb.asm_alloc(('''
            lw $v1, 0x14($s5)
            addiu $at, $zero, 10
            bne $v1, $at, vwf_s1
            nop
''' + hdchk('$t9', 'vwf_s1h') + '''
            sll $t9, $t9, 8
            lui $t8, {hi}
            addiu $t8, $t8, {lo}
            addu $t8, $t8, $t9
            lbu $v1, 0x20($t8)
        vwf_s1:
            j 0x{nc:08x}
            addu $s3, $s3, $v1
        ''').format(hi=hi, lo=lo, nc=NEXT_CHAR), 'vwf_space')
    eb.asm(HOOK_SPACE, 'j 0x%08x; nop' % eb.symbols['vwf_space'], expect=2)

    # message window: draw, then v0 = advance (VWF width for ASCII, s7 otherwise)
    eb.asm_alloc(('''
            addiu $sp, $sp, -0x10
            sw $ra, 0($sp)
            jal 0x{draw:08x}
            sw $t2, 4($sp)
            lw $t2, 4($sp)
            lbu $t9, 0($t2)
            sltiu $at, $t9, 0x80
            beqz $at, vwf_m1
            move $v0, $s7
''' + hdchk('$t8', 'vwf_m1h') + '''
            sll $t8, $t8, 8
            addu $t9, $t9, $t8
            lui $t8, {hi}
            addiu $t8, $t8, {lo}
            addu $t8, $t8, $t9
            lbu $v0, 0($t8)
        vwf_m1:
            lw $ra, 0($sp)
            jr $ra
            addiu $sp, $sp, 0x10
        ''').format(draw=DRAW, hi=hi, lo=lo), 'vwf_msgchar')
    eb.asm(MSG_DRAW_CALL, 'jal 0x%08x' % eb.symbols['vwf_msgchar'], expect=1)
    eb.asm(MSG_ADVANCE, 'addu $s3, $s3, $v0', expect=1)
    info['vwf_widths'] = widths


# ---------------------------------------------------------------------------------------------
# FONT12_12 (party bar names etc.) has no half-width sheet (font[0x2c] == 0): ASCII is converted to
# full-width SJIS and drawn on the full-width path with advance font[4] (12px), so English names come
# out widely spaced. Ported from Elminage III (same routine, other registers: font s5, x s3, y s2,
# index s0, string fp). For fonts with font[4] == 12 and a byte that is a converted ASCII char, draw
# at x - left[c] and advance by adv[c] (font12.metrics()); everything else is unchanged.
#   0x088F10F8  lw t2,4(s5); lw t3,8(s5); move a0,s5; move a1,s3; jal 0x088F115C; move a2,s2;
#               lw v1,4(s5)                       -> j vwf12_draw; nop x6
#   0x088F1114  addu s3,s3,v1                    (join)
#   0x088F0F20  b NEXT; addu s3,s3,v1 (v1 = font[4], space on a font without half-width sheet)
#                                                 -> j vwf12_space; nop
# REAL HARDWARE: code-cave code only; uses the free stack word 0x10($sp) of the 0x50-byte frame.
FW_DRAW = 0x088F10F8
FW_JOIN = 0x088F1114
FW_SPACE = 0x088F0F20
DRAW_CELL = 0x088F115C


def apply12(eb, info=None):
    import font12
    path = font12.build_sheet()          # Latin cells redrawn with the small label font (0.1.23, Elm III v0.8.9)
    if info is not None:
        info['archives'].setdefault('ANIME', {})['FONT12_12.GIM'] = open(path, 'rb').read()
    m = font12.metrics()
    tab = bytearray(256)
    for c in range(0x80):
        left, adv = m.get(c, (0, 12))
        tab[2 * c], tab[2 * c + 1] = left, adv
    v = eb.alloc(bytes(tab), 'vwf12_tab', align=16)
    hi, lo = _hilo(v)
    eb.asm_alloc('''
            lw $t2, 4($s5)
            lw $t3, 8($s5)
            move $a0, $s5
            move $a1, $s3
            sw $t2, 0x10($sp)
            addiu $at, $zero, 12
            bne $t2, $at, fw_draw
            addu $t9, $fp, $s0
            lbu $t8, 0($t9)
            sltiu $at, $t8, 0x80
            beqz $at, fw_draw
            sltiu $at, $t8, 0x21
            bnez $at, fw_draw
            nop
            beqz $s0, fw_ascii
            nop
            lbu $t7, -1($t9)
            sltiu $at, $t7, 0x81
            beqz $at, fw_draw
            nop
        fw_ascii:
            lui $t9, {hi}
            addiu $t9, $t9, {lo}
            sll $t8, $t8, 1
            addu $t9, $t9, $t8
            lbu $t7, 0($t9)
            lbu $t6, 1($t9)
            subu $a1, $s3, $t7
            sw $t6, 0x10($sp)
        fw_draw:
            jal 0x{draw:08x}
            move $a2, $s2
            lw $v1, 0x10($sp)
            j 0x{join:08x}
            nop
        '''.format(hi=hi, lo=lo, draw=DRAW_CELL, join=FW_JOIN), 'vwf12_draw')
    eb.asm(FW_DRAW, 'j 0x%08x; nop; nop; nop; nop; nop; nop' % eb.symbols['vwf12_draw'], expect=7)
    eb.asm_alloc('''
            addiu $at, $zero, 12
            bne $v1, $at, fw_sp
            nop
            lui $t9, {hi}
            addiu $t9, $t9, {lo}
            lbu $v1, 0x41($t9)
        fw_sp:
            j 0x{nc:08x}
            addu $s3, $s3, $v1
        '''.format(hi=hi, lo=lo, nc=NEXT_CHAR), 'vwf12_space')
    eb.asm(FW_SPACE, 'j 0x%08x; nop' % eb.symbols['vwf12_space'], expect=2)


# ---------------------------------------------------------------------------------------------
# HD font (one ISO, chosen at New Game; ported from Elminage III): FONT16 gets a second half-width
# sheet FONT10HD.GIM (in PARTS.BIN), a 4x rendering of the ASCII glyphs from Console Sans (tools/font_hd.py). The
# glyph routine GLYPH_FN (font a0, x a1, y a2, sheet a3, u t0, v t1 (pixels), cell w t2, h t3)
# draws through the generic sprite routine SPRITE_FN (tex, x, y, w, h, u=t1, v=t2, uw=t3,
# [sp+0]=vh). When the HD font is selected (script variable FONT_VAR == 2) the entry hook switches
# a3 from the 1x sheet to the HD sheet for ASCII rows (v < 64) and sets a flag (cleared at the
# single epilogue) that makes SPRITE_FN remap u, v (12 glyphs per row) and scale uw, vh by 4; the screen
# size stays the same.
# Half-width kana (rows 4-7) stay on the 1x sheet. Other sprites never see the flag.
# Real hardware: both sheets stay loaded (+131 KB RAM for the 512x512 4-bit HD sheet); the original
# 1x path is unchanged when the original font is selected.
GLYPH_FN, GLYPH_RET, SPRITE_FN = 0x088F115C, 0x088F13B0, 0x088F22D8
FONT16_CTOR_LIST = (0x0886AD2C, 0x0886AD40)     # lui a3 / addiu a3: half-width sheet list 0x0895565C
FONT10_NAME = 0x0895564C                         # 'FONT10_16.GIM'
HD_FILE = 'FONT10HD.GIM'
HD_ARC = 'PARTS'


def apply_hd(eb, info):
    import struct
    import font_hd
    # The loader finds sheets by file name in any archive (format '%s', 0x088F0CBC). The 4x sheet
    # (512x512 4-bit, 131 KB) does not fit ANIME.BIN's disc slot (26 KB slack), so it goes into the small
    # PARTS.BIN (one file originally), which then moves to the end of the ISO (+0.6 MB).
    info['archives'].setdefault(HD_ARC, {})[HD_FILE] = font_hd.build()
    # FONT16 constructor (0x088F0BAC, called at 0x0886AD48): half-width sheet list
    # [FONT10_16.GIM, NULL] -> [FONT10_16.GIM, FONT10HD.GIM, NULL]; the constructor loads every
    # listed sheet into font[0x30 + 4k], so sheet font[0x2C] + 1 is the HD sheet.
    eb.alloc(HD_FILE.encode('ascii') + bytes(4 - len(HD_FILE) % 4), 'hd_name', align=4)
    eb.alloc(struct.pack('<III', FONT10_NAME, eb.symbols['hd_name'], 0), 'hd_list', align=4)
    hi, lo = _hilo(eb.symbols['hd_list'])
    assert eb.u32(FONT16_CTOR_LIST[0]) == 0x3c070895 and eb.u32(FONT16_CTOR_LIST[1]) == 0x24e7565c
    eb.asm(FONT16_CTOR_LIST[0], 'lui $a3, 0x%x' % hi, expect=1)
    eb.asm(FONT16_CTOR_LIST[1], 'addiu $a3, $a3, %d' % lo, expect=1)
    eb.alloc(bytes(4), 'hd_flag', align=4)
    fh, fl = _hilo(eb.symbols['hd_flag'])
    eb.asm_alloc(('''
            addiu $sp, $sp, -0x40
            sw $ra, 0x3c($sp)
            lui $t9, 0x{fh:x}
            addiu $t9, $t9, {fl}
            sw $zero, 0($t9)
            lw $at, 0x14($a0)
            addiu $v1, $zero, 10
            bne $at, $v1, hd_e_done
            nop
            lw $at, 0x2c($a0)
            bne $at, $a3, hd_e_done
            nop
            sltiu $at, $t1, 64               # t1 = glyph v in pixels: ASCII = rows 0-3 (v < 64)
            beqz $at, hd_e_done
            nop
            lw $at, 0x24($a0)
            addiu $v1, $a3, 1
            slt $at, $v1, $at
            beqz $at, hd_e_done
            nop
''' + hdchk('$v1', 'hd_e_chk') + '''
            beqz $v1, hd_e_done
            nop
            addiu $a3, $a3, 1
            sw $v1, 0($t9)
        hd_e_done:
            j 0x{back:08x}
            nop
        ''').format(fh=fh, fl=fl, back=GLYPH_FN + 8), 'hd_glyph_entry')
    assert eb.u32(GLYPH_FN) == 0x27bdffc0 and eb.u32(GLYPH_FN + 4) == 0xafbf003c
    eb.asm(GLYPH_FN, 'j 0x%08x; nop' % eb.symbols['hd_glyph_entry'], expect=2)
    eb.asm_alloc('''
            lui $t9, 0x{fh:x}
            sw $zero, {fl}($t9)
            jr $ra
            nop
        '''.format(fh=fh, fl=fl), 'hd_glyph_exit')
    assert eb.u32(GLYPH_RET) == 0x03e00008 and eb.u32(GLYPH_RET + 4) == 0x27bd0040
    eb.asm(GLYPH_RET, 'j 0x%08x; addiu $sp, $sp, 0x40' % eb.symbols['hd_glyph_exit'], expect=2)
    if font_hd.SCALE == 4:
        # 4x sheet is repacked 12 glyphs per row: glyph i = (v/16)*25 + u/10 -> (i%12*40, i/12*64)
        remap = '''
            addiu $at, $zero, 16
            div $zero, $t2, $at
            mflo $v1
            addiu $at, $zero, 25
            mult $v1, $at
            mflo $v1
            addiu $at, $zero, 10
            div $zero, $t1, $at
            mflo $v0
            addu $v1, $v1, $v0
            addiu $at, $zero, 12
            div $zero, $v1, $at
            mflo $v0
            mfhi $v1
            addiu $at, $zero, 40
            mult $v1, $at
            mflo $t1
            addiu $at, $zero, 64
            mult $v0, $at
            mflo $t2
'''
        sh = 2
    else:
        remap = '''
            sll $t1, $t1, 1
            sll $t2, $t2, 1
'''
        sh = 1
    eb.asm_alloc(('''
            addiu $sp, $sp, -0x20
            sw $ra, 0x1c($sp)
            lui $at, 0x{fh:x}
            lw $at, {fl}($at)
            beqz $at, hd_s_done
            nop
''' + remap + '''
            bnez $t3, hd_s1
            nop
            move $t3, $a3
        hd_s1:
            sll $t3, $t3, {sh}
            lw $v0, 0x20($sp)
            bnez $v0, hd_s2
            nop
            move $v0, $t0
        hd_s2:
            sll $v0, $v0, {sh}
            sw $v0, 0x20($sp)
        hd_s_done:
            j 0x{back:08x}
            nop
        ''').format(fh=fh, fl=fl, sh=sh, back=SPRITE_FN + 8), 'hd_sprite_entry')
    assert eb.u32(SPRITE_FN) == 0x27bdffe0 and eb.u32(SPRITE_FN + 4) == 0xafbf001c
    eb.asm(SPRITE_FN, 'j 0x%08x; nop' % eb.symbols['hd_sprite_entry'], expect=2)


# ---------------------------------------------------------------------------------------------
# Scrolling help ticker (ported from Elminage III). The original 0x088420C4.. builds a 15-character
# window of 2-byte cells starting at cell (s1 >> 4) % s0 (s1 = elapsed pixels, s0 = cells) and draws it
# at x = s4 - (s1 & 15) (0x0884217C). With 1-byte VWF text that steps two letters per 16 px (jerky).
# Replacement (called at TICKER_HOOK, result: s2 = window string, s1 = pixel shift 0..15 for the
# unchanged x code): W = width of the whole string + a 4-space gap (VWF table, HD half when the HD
# font is on; SJIS pair = 16 px), off = s1 % W; start at the character covering pixel 'off',
# shift = off - its start; copy characters (wrapping) while they end within the box: Elm II has no
# clipping, so the last letter must end by x = TICKER_RIGHT (the original 15 cells ended at s4 + 240).
TICKER_HOOK, TICKER_DRAW = 0x08842114, 0x0884217C
TICKER_RIGHT = 240


def apply_ticker(eb):
    eb.alloc(bytes(128), 'ticker_buf', align=4)
    whi, wlo = _hilo(eb.symbols['vwf_widths'])
    bhi, blo = _hilo(eb.symbols['ticker_buf'])

    # t2 = byte -> t3 = width, t6 = bytes in char (uses at, t9)
    def charw(lab):
        return '''
            addiu $t9, $t2, -0x81
            sltiu $at, $t9, 0x1f
            bnez $at, {l}_w
            sltiu $at, $t2, 0xe0
            beqz $at, {l}_w
            nop
            addu $t3, $t8, $t2
            lbu $t3, 0($t3)
            b {l}_d
            addiu $t6, $zero, 1
        {l}_w:
            addiu $t3, $zero, 16
            addiu $t6, $zero, 2
        {l}_d:
'''.format(l=lab)
    eb.asm_alloc(('''
            lui $t8, {whi}
            addiu $t8, $t8, {wlo}
''' + hdchk('$t9', 'tk_hd') + '''
            sll $t9, $t9, 8
            addu $t8, $t8, $t9
            move $t0, $s2
            move $t1, $zero
            move $a3, $zero                  # trailing spaces
        tk_l1:
            lbu $t2, 0($t0)
            beqz $t2, tk_l1e
            nop
''' + charw('tk_c1') + '''
            addu $t1, $t1, $t3
            addiu $at, $zero, 0x20
            bne $t2, $at, tk_ns
            addiu $a3, $a3, 1
            b tk_l1
            addu $t0, $t0, $t6
        tk_ns:
            move $a3, $zero
            b tk_l1
            addu $t0, $t0, $t6
        tk_l1e:
            beqz $t1, tk_zero
            nop
            addiu $a2, $zero, 4              # a2 = pad spaces so that the loop has a 4-space gap
            subu $a2, $a2, $a3
            bgez $a2, tk_pd
            nop
            move $a2, $zero
        tk_pd:
            lbu $v0, 0x20($t8)               # v0 = space width
            mult $a2, $v0
            mflo $at
            addu $t1, $t1, $at               # total loop width
            divu $zero, $s1, $t1
            mfhi $t4                         # pixel offset in the loop
            move $t0, $s2
            move $t5, $zero
            move $v1, $zero                  # pending pad spaces
        tk_l2:
            lbu $t2, 0($t0)
            beqz $t2, tk_l2p
            nop
''' + charw('tk_c2') + '''
            addu $t7, $t5, $t3
            sltu $at, $t4, $t7
            bnez $at, tk_l2f
            nop
            move $t5, $t7
            b tk_l2
            addu $t0, $t0, $t6
        tk_l2p:                              # offset inside the padding
            move $v1, $a2
            move $t0, $s2
        tk_l2q:
            addu $t7, $t5, $v0
            sltu $at, $t4, $t7
            bnez $at, tk_l2f
            nop
            move $t5, $t7
            addiu $v1, $v1, -1
            bgtz $v1, tk_l2q
            nop
        tk_l2f:
            subu $s1, $t4, $t5               # shift into the first character (0..15)
            lui $a0, {bhi}
            addiu $a0, $a0, {blo}
            move $a1, $a0
            move $t5, $zero
            addiu $t7, $zero, {right}        # t7 = room: right - s4 + shift
            subu $t7, $t7, $s4
            addu $t7, $t7, $s1
        tk_l3:
            bgtz $v1, tk_pad
            nop
            lbu $t2, 0($t0)
            bnez $t2, tk_l3n
            nop
            move $t0, $s2
            move $v1, $a2
            b tk_l3
            nop
        tk_pad:
            addu $t9, $t5, $v0
            sltu $at, $t7, $t9
            bnez $at, tk_l3e
            nop
            addiu $v1, $v1, -1
            addiu $t2, $zero, 0x20
            sb $t2, 0($a1)
            addiu $a1, $a1, 1
            b tk_l3c
            move $t5, $t9
        tk_l3n:
''' + charw('tk_c3') + '''
            addu $t9, $t5, $t3
            sltu $at, $t7, $t9
            bnez $at, tk_l3e
            nop
            sb $t2, 0($a1)
            addiu $at, $zero, 2
            bne $t6, $at, tk_l3s
            nop
            lbu $t9, 1($t0)
            sb $t9, 1($a1)
        tk_l3s:
            addu $a1, $a1, $t6
            addu $t0, $t0, $t6
            addu $t5, $t5, $t3
        tk_l3c:
            subu $t9, $a1, $a0
            sltiu $at, $t9, 120
            bnez $at, tk_l3
            nop
        tk_l3e:
            sb $zero, 0($a1)
            jr $ra
            move $s2, $a0
        tk_zero:
            jr $ra
            move $s1, $zero
        ''').format(whi=whi, wlo=wlo, bhi=bhi, blo=blo, right=TICKER_RIGHT), 'ticker_window')
    assert eb.u32(TICKER_HOOK) == 0x06210003, hex(eb.u32(TICKER_HOOK))      # bgez s1, +3
    eb.asm(TICKER_HOOK, 'jal 0x%08x; nop; j 0x%08x; nop' % (eb.symbols['ticker_window'], TICKER_DRAW), expect=4)


# ---------------------------------------------------------------------------------------------
# Description boxes (ported from Elminage III vwf.apply_wrap). Three loops cut their text into fixed
# byte rows, which split English words ("whet / her", v0.8.1 event list):
#   event list + alchemy (0x088417D4: 10 rows of 28 bytes at x 240; source s0 or s4 + 0x22, both
#   += 0x1C per row; the row gets 16 full-width spaces appended (strcat 0x088417E8) and is cut at
#   28 bytes again in the draw call's delay slot 0x08841814),
#   monster and item text (0x08857508, 0x08857A14): rows of 24 bytes at x 268, s2 = source,
#   s1 = bytes left, until s1 <= 0.
# Each row now comes from wrap_line(dst, src, max_px) -> v0 = bytes consumed: whole words while the
# VWF width (HD widths when the HD font is on) fits max_px, a full-width character counts 16 px and
# may break anywhere, byte 0x0A forces a break, spaces after a break are skipped, and a row never
# takes more than WRAP_MAX_BYTES (the row buffers are 80 bytes on the stack). Pixel limits: events
# 224 px (the original 14 full-width characters), descriptions 200 px (box inner width from x 268).
# The event rows' full-width space padding is dropped (it only filled out the fixed-width rows).
# Real hardware: code in the cave only, same registers and stack frames as the original loops.
WRAP_EVENT, WRAP_EVENT_PX = 0x088417D4, 224
WRAP_EVENT_PAD, WRAP_EVENT_CUT = 0x088417E8, 0x08841814
WRAP_DESC, WRAP_DESC_PX = (0x08857508, 0x08857A14), 200
WRAP_MAX_BYTES = 72


def _expect(eb, va, words):
    got = tuple(eb.u32(va + 4 * i) for i in range(len(words)))
    assert got == tuple(words), 'unexpected code at %08x: %s' % (va, ' '.join('%08x' % w for w in got))


def apply_wrap(eb):
    hi, lo = _hilo(eb.symbols['vwf_widths'])
    eb.asm_alloc((hdchk('$t6', 'wr_hd') + '''
            sll $t6, $t6, 8
            lui $t7, 0x{hi:x}
            addiu $t7, $t7, {lo}
            addu $t6, $t6, $t7
            move $t0, $zero
            move $t1, $zero
            addiu $t2, $zero, -1
        wr_loop:
            addu $t7, $a1, $t0
            lbu $t3, 0($t7)
            beqz $t3, wr_end
            addiu $at, $zero, 0x0a
            beq $t3, $at, wr_nl
            addiu $at, $zero, 0x20
            bne $t3, $at, wr_ns
            nop
            move $t2, $t0
        wr_ns:
            sltiu $at, $t3, 0x81
            bnez $at, wr_hw
            sltiu $at, $t3, 0xa0
            bnez $at, wr_fw
            sltiu $at, $t3, 0xe0
            bnez $at, wr_hw
            sltiu $at, $t3, 0xfd
            beqz $at, wr_hw
            nop
        wr_fw:
            addiu $t4, $zero, 16
            addiu $t5, $zero, 2
            bgtz $t0, wr_fit
            move $t2, $t0
            b wr_fit
            addiu $t2, $zero, -1
        wr_hw:
            addu $t7, $t6, $t3
            lbu $t4, 0($t7)
            addiu $t5, $zero, 1
        wr_fit:
            addu $t7, $t0, $t5
            sltiu $at, $t7, {maxb}
            beqz $at, wr_over
            addu $t7, $t1, $t4
            slt $at, $a2, $t7
            beqz $at, wr_adv
            nop
        wr_over:
            beqz $t0, wr_adv
            addu $t7, $t1, $t4
            blez $t2, wr_hard
            nop
            b wr_skip
            move $v0, $t2
        wr_hard:
            b wr_copy
            move $v0, $t0
        wr_skip:
            addu $t7, $a1, $v0
            lbu $t3, 0($t7)
            addiu $at, $zero, 0x20
            bne $t3, $at, wr_copy
            nop
            b wr_skip
            addiu $v0, $v0, 1
        wr_adv:
            move $t1, $t7
            b wr_loop
            addu $t0, $t0, $t5
        wr_nl:
            b wr_cp0
            addiu $v0, $t0, 1
        wr_end:
            move $v0, $t0
        wr_cp0:
            move $t8, $t0
            b wr_cp
            move $t9, $zero
        wr_copy:
            move $t8, $t2
            bgtz $t2, wr_cp
            move $t9, $zero
            move $t8, $t0
        wr_cp:
            beq $t9, $t8, wr_done
            addu $t7, $a1, $t9
            lbu $t3, 0($t7)
            addu $t7, $a0, $t9
            sb $t3, 0($t7)
            b wr_cp
            addiu $t9, $t9, 1
        wr_done:
            addu $t7, $a0, $t8
            jr $ra
            sb $zero, 0($t7)
        ''').format(hi=hi, lo=lo, maxb=WRAP_MAX_BYTES + 1), 'wrap_line')
    wl = eb.symbols['wrap_line']
    # events / alchemy: the loop advances both source registers by 0x1C, so add (consumed - 0x1C)
    eb.asm_alloc('''
            addiu $sp, $sp, -16
            sw $ra, 0($sp)
            jal 0x{wl:08x}
            nop
            lw $ra, 0($sp)
            addiu $sp, $sp, 16
            addu $s0, $s0, $v0
            addu $s4, $s4, $v0
            addiu $s0, $s0, -0x1c
            jr $ra
            addiu $s4, $s4, -0x1c
        '''.format(wl=wl), 'wrap_event')
    _expect(eb, WRAP_EVENT, (0x0e205ca5, 0x2406001c, 0xa3a0003c))     # jal strncpy; a2 = 28; sb zero
    _expect(eb, WRAP_EVENT_PAD, (0x0e205b63,))                          # jal strcat (full-width spaces)
    _expect(eb, WRAP_EVENT_CUT, (0xa3a0003c,))
    eb.asm(WRAP_EVENT, 'jal 0x%08x; addiu $a2, $zero, %d; nop' % (eb.symbols['wrap_event'], WRAP_EVENT_PX),
           expect=3)
    eb.asm(WRAP_EVENT_PAD, 'nop', expect=1)
    eb.asm(WRAP_EVENT_CUT, 'nop', expect=1)
    for b in WRAP_DESC:
        _expect(eb, b, (0x2a210019,))
        _expect(eb, b + 0x24, (0x0e205ca5, 0x24060018, 0xa3a00028))
        _expect(eb, b + 0x58, (0x2631ffe8, 0x26520018))
        eb.asm(b, '''addiu $a0, $sp, 0x10
                     move $a1, $s2
                     jal 0x{wl:08x}
                     addiu $a2, $zero, {px}
                     addu $s2, $s2, $v0
                     subu $s1, $s1, $v0
                     addiu $s2, $s2, -0x18
                     addiu $s1, $s1, 0x18
                     nop; nop; nop; nop'''.format(wl=wl, px=WRAP_DESC_PX), expect=12)
