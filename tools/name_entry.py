"""Latin name entry with VWF display (Training Hall registration / rename, Rename Spells).
Ported from Elminage III (tools/name_entry.py there); addresses and modes are Elminage II's.

Editor state *(u32 *)0x08B8AC80: +8 text as 2-byte cells (buffer 0x100 bytes), +0x1C7A max cells,
+0x1C7C cursor, +0x1C7E page (row offset, 6 per page), +0x1F8 character record, +0x1FC mode,
+0x22C / +0x230 keyboard column / row. Keyboard: 15x6 cells per page, row pointers at 0x08953998
(78 pages x 6 rows); row 5 columns 12/13/14 = cursor left / right / end (checked by position).
Grid draw 0x0884C418 (cell draw call 0x0884C4D4), key handler 0x0884C640, backspace 0x0884C7AC,
cursor xy 0x0884C2A8 (a0 = &x, a1 = &y), editor main 0x0884A06C, confirm at 0x0884A2BC.

Modes:
  0x6D / 0x129 / 0x87 name (new character / password character / rename), record +0x00 (0x14 bytes)
  0x6E / 0x12A / 0x88 nickname, record +0x19 (0x14 bytes)
  0x1D  Rename Spells (options), 12 cells -> 0x18-byte spell name record (commit 0x08831380)
  0x0F  riddle answer (script ops 0xA2 / 0xA3 / 0xA4): the Sphinx at Dekor (SCD05 15005.bin) opens on page 1
        or 2 (hiragana / katakana), riddles 34001 and 53001 on the box-drawing glyph page 77 -> its own page
        table: the original one with pages 0 and 1 replaced by the Latin page (the glyph pages unchanged).
        The answer stays full-width cells (op 0xA4 strcmp's it with the script's answer); on confirm a-z
        are folded to A-Z and trailing spaces dropped, so the English answers are full-width capitals.
  0x128 Book of the Next Age password (36 cells) -> original keyboard, no conversion

Changes (the editor keeps 2-byte cells, so its own logic is untouched):
  - one Latin page (A-Z, a-z, 0-9, punctuation, blank cells = space) for the Latin modes; the
    page-table users (grid 0x0884C44C/54, key handler 0x0884C73C/40) read the table through a pointer
    that the grid and the key handler set from the mode on entry.
  - grid cells are drawn converted to ASCII (VWF font) and centred in the 16 px slot.
  - the typed text is drawn converted to ASCII (FIELD_DRAW_CALLS).
  - the cursor box follows the VWF width of the text before it (wrapper of 0x0884C2A8).
  - on confirm the buffer is converted to ASCII (trailing spaces trimmed) before the game copies it
    into the record (0x0884A2BC for names / nicknames, 0x088313A0 for spell names).
  - ASCII text in the buffer (an existing English name being edited, or the record copied back
    after backspace on an empty field) is converted back to cells at grid draw, cursor at its end.
  - max cells doubled for the Latin modes (1-byte ASCII in the record: same field size, and about
    the same pixel width as the original full-width limit).
Real hardware: data/code in the cave only, no layout changes.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROWS = [
    'ABCDEFGHIJKLM\',',
    'NOPQRSTUVWXYZ-.',
    'abcdefghijklm!?',
    'nopqrstuvwxyz&:',
    '0123456789()/+#',
    '*@~%$;="    ',          # 12 cells; then <- -> OK
]
# ASCII -> Shift-JIS full-width
FW = {' ': 0x8140, ',': 0x8143, '.': 0x8144, ':': 0x8146, ';': 0x8147, '?': 0x8148, '!': 0x8149,
      '\'': 0x8166, '"': 0x8168, '(': 0x8169, ')': 0x816A, '+': 0x817B, '-': 0x817C, '=': 0x8181,
      '/': 0x815E, '~': 0x8160, '$': 0x8190, '%': 0x8193, '#': 0x8194, '&': 0x8195, '*': 0x8196,
      '@': 0x8197}
for i in range(10):
    FW[chr(0x30 + i)] = 0x824F + i
for i in range(26):
    FW[chr(0x41 + i)] = 0x8260 + i
    FW[chr(0x61 + i)] = 0x8281 + i

STATE = 0x08B8AC80
DRAW_TEXT = 0x0886AB34
GRID_FN, GRID_DRAW_CALL = 0x0884C418, 0x0884C4D4
KEY_FN = 0x0884C640
FIELD_DRAW_CALLS = (0x088C3A00,)       # profile panel fields (name, nickname, race, ...): traced in game
TEXT_HELPER, SPELL_DRAW_CALL = 0x0887ADB0, 0x088391B4   # Rename Spells: typed name (traced in game)
# Profile panel of the Training Hall creation / rename screens: sex and alignment share one row with the
# Aln / Age labels, room for one letter each (the Japanese values were one kanji). The lists keep the words.
PANEL_ABBR = (('Male', 'M'), ('Female', 'F'), ('Good', 'G'), ('Neutral', 'N'), ('Evil', 'E'))
PANEL_MODES = ((0x6D, 0x77), (0x84, 0x8A), (0x128, 0x133))     # editor modes that show that panel
CURSOR_FN = 0x0884C2A8
CURSOR_CALLS = (0x0884C604, 0x0884D3A4, 0x0884E85C)
CONFIRM_AT = 0x0884A2BC                # lui v1,0x8b9; lw v1,-0x5380(v1)  (confirm: non-empty check)
SPELL_CHECK_CALL = 0x088313A0          # jal 0x08849CA0 (spell name non-empty check, mode 0x1D)
SPELL_CHECK_FN = 0x08849CA0
PAGE_TABLE, PAGE_ROWS = 0x08953998, 468
PAGE_REFS = ((0x0884C44C, 0x0884C454, '$v0'), (0x0884C73C, 0x0884C740, '$a0'))
LATIN_MODES = (0x6D, 0x6E, 0x87, 0x88, 0x129, 0x12A, 0x1D)
RIDDLE_MODE, RIDDLE_LATIN_PAGES = 0x0F, 2
# addiu v0, zero, N before 'sh v0, 0x1C7A(..)' (max cells) for the Latin modes
FIELD_LIMITS = ((0x08848AAC, 10), (0x08849084, 10), (0x08849094, 10), (0x0884A5B8, 10),
                (0x0884A7C4, 10), (0x0884A414, 6), (0x08831274, 12))


def hilo(v):
    lo = v & 0xffff
    return ((v + 0x8000) >> 16) & 0xffff, lo - 0x10000 if lo >= 0x8000 else lo


def rows_data():
    out = b''
    for k, r in enumerate(ROWS):
        b = b''.join(struct.pack('>H', FW[c]) for c in r)
        if k == 5:
            b += struct.pack('>HH', 0x81A9, 0x81A8) + b'OK'       # <- -> OK (checked by position)
        assert len(b) == 30, (k, len(b))
        out += b + b'\0\0'
    return out


def latin_check(reg, label):
    """Branch to `label` if mode `reg` is NOT a Latin mode (uses $at)."""
    s = ''
    for m in LATIN_MODES:
        s += '''
            addiu $at, $zero, 0x{m:x}
            beq {r}, $at, {lab}_y
            nop'''.format(m=m, r=reg, lab=label)
    return s + '''
            b {lab}
            nop
        {lab}_y:'''.format(lab=label)


def apply(eb):
    import vwf
    tab = bytearray(2 * 95)
    for c, code in FW.items():
        struct.pack_into('<H', tab, 2 * (ord(c) - 0x20), code)
    eb.alloc(bytes(tab), 'ne_tab', align=4)
    eb.alloc(rows_data(), 'ne_rows', align=4)
    eb.alloc(bytes(192), 'ne_tmp', align=4)
    eb.alloc(bytes(192), 'ne_draw', align=4)   # draw scratch
    dh, dl = hilo(eb.symbols['ne_draw'])
    th, tl = hilo(eb.symbols['ne_tab'])
    mh, ml = hilo(eb.symbols['ne_tmp'])
    wh, wl = hilo(eb.symbols['vwf_widths'])
    sh, sl = hilo(STATE)
    rows = eb.symbols['ne_rows']
    eb.alloc(b''.join(struct.pack('<I', rows + 32 * (k % 6)) for k in range(PAGE_ROWS)), 'ne_pages', align=4)
    eb.alloc(struct.pack('<I', eb.symbols['ne_pages']), 'ne_pagetab', align=4)
    ph, pl = hilo(eb.symbols['ne_pagetab'])
    oh, ol = hilo(PAGE_TABLE)
    nh, nl = hilo(eb.symbols['ne_pages'])
    for lui_at, add_at, reg in PAGE_REFS:
        eb.asm(lui_at, 'lui %s, 0x%x' % (reg, ph), expect=1)
        eb.asm(add_at, 'lw %s, %d(%s)' % (reg, pl, reg), expect=1)

    # riddle mode: the original page table with the hiragana / katakana pages (the Sphinx riddles start
    # there, script op 0xA2 arg 1 = 1 / 2) replaced by the Latin page; the glyph page 77 (riddles 34001,
    # 53001) and the rest stay
    rp = [eb.u32(PAGE_TABLE + 4 * k) for k in range(PAGE_ROWS)]
    for k in range(6 * RIDDLE_LATIN_PAGES):
        rp[k] = rows + 32 * (k % 6)
    eb.alloc(b''.join(struct.pack('<I', v) for v in rp), 'ne_riddle_pages', align=4)
    rh, rl = hilo(eb.symbols['ne_riddle_pages'])

    # set ne_pagetab from the mode of state $t3 (leaf; t3, t4, at)
    def select_table(lab):
        return '''
            lw $t3, 0x1fc($t3)
            lui $t4, 0x{oh:x}
            addiu $t4, $t4, {ol}
            addiu $at, $zero, 0x{rm:x}
            bne $t3, $at, {lab}_nr
            nop
            lui $t4, 0x{rh:x}
            b {lab}_o
            addiu $t4, $t4, {rl}
        {lab}_nr:'''.format(oh=oh, ol=ol, rm=RIDDLE_MODE, rh=rh, rl=rl, lab=lab) + latin_check('$t3', lab + '_o') + '''
            lui $t4, 0x{nh:x}
            addiu $t4, $t4, {nl}
        {lab}_o:
            lui $at, 0x{ph:x}
            sw $t4, {pl}($at)'''.format(nh=nh, nl=nl, ph=ph, pl=pl, lab=lab)

    # fw2hw(a0): full-width ASCII -> ASCII in place (other characters kept). Leaf; t3-t9, v0, v1, at.
    eb.asm_alloc('''
            move $t3, $a0
            move $t4, $a0
            lui $t9, 0x{th:x}
            addiu $t9, $t9, {tl}
        f_l:
            lbu $t5, 0($t3)
            beqz $t5, f_e
            sltiu $at, $t5, 0x80
            bnez $at, f_s
            addiu $t6, $t5, -0xa1
            sltiu $at, $t6, 0x3f
            bnez $at, f_s
            lbu $t6, 1($t3)
            sll $t7, $t5, 8
            or $t7, $t7, $t6
            move $t8, $zero
        f_f:
            sll $v0, $t8, 1
            addu $v0, $t9, $v0
            lhu $v1, 0($v0)
            beq $v1, $t7, f_hit
            addiu $t8, $t8, 1
            sltiu $at, $t8, 95
            bnez $at, f_f
            nop
            sb $t5, 0($t4)
            sb $t6, 1($t4)
            addiu $t3, $t3, 2
            b f_l
            addiu $t4, $t4, 2
        f_hit:
            addiu $v0, $t8, 0x1f
            sb $v0, 0($t4)
            addiu $t3, $t3, 2
            b f_l
            addiu $t4, $t4, 1
        f_s:
            sb $t5, 0($t4)
            addiu $t3, $t3, 1
            b f_l
            addiu $t4, $t4, 1
        f_e:
            jr $ra
            sb $zero, 0($t4)
        '''.format(th=th, tl=tl), 'ne_fw2hw')

    # conv(a0): fw2hw, then trim trailing spaces. Leaf apart from fw2hw (ra saved).
    eb.asm_alloc('''
            addiu $sp, $sp, -0x10
            sw $ra, 0($sp)
            jal 0x{f:08x}
            sw $a0, 4($sp)
            lw $t3, 4($sp)
            move $t4, $t3
        k_l:
            lbu $t5, 0($t3)
            bnez $t5, k_l
            addiu $t3, $t3, 1
            addiu $t3, $t3, -1
        k_b:
            beq $t3, $t4, k_d
            nop
            lbu $t5, -1($t3)
            addiu $at, $zero, 0x20
            bne $t5, $at, k_d
            nop
            addiu $t3, $t3, -1
            b k_b
            sb $zero, 0($t3)
        k_d:
            lw $ra, 0($sp)
            jr $ra
            addiu $sp, $sp, 0x10
        '''.format(f=eb.symbols['ne_fw2hw']), 'ne_conv')

    # hw2fw_copy(a0 dst, a1 src, a2 max cells): ASCII -> full-width cells; multibyte copied; leaf.
    eb.asm_alloc('''
            move $t3, $a1
            move $t4, $a0
            move $t5, $zero
            lui $t9, 0x{th:x}
            addiu $t9, $t9, {tl}
        h_l:
            slt $at, $t5, $a2
            beqz $at, h_e
            nop
            lbu $t6, 0($t3)
            beqz $t6, h_e
            sltiu $at, $t6, 0x80
            beqz $at, h_mb
            addiu $t7, $t6, -0x20
            sltiu $at, $t7, 95
            beqz $at, h_skip
            sll $t7, $t7, 1
            addu $t7, $t9, $t7
            lhu $t7, 0($t7)
            beqz $t7, h_skip
            srl $t8, $t7, 8
            sb $t8, 0($t4)
            sb $t7, 1($t4)
            addiu $t4, $t4, 2
            addiu $t5, $t5, 1
        h_skip:
            b h_l
            addiu $t3, $t3, 1
        h_mb:
            addiu $t7, $t6, -0xa1
            sltiu $at, $t7, 0x3f
            bnez $at, h_skip
            lbu $t7, 1($t3)
            sb $t6, 0($t4)
            sb $t7, 1($t4)
            addiu $t4, $t4, 2
            addiu $t5, $t5, 1
            b h_l
            addiu $t3, $t3, 2
        h_e:
            jr $ra
            sb $zero, 0($t4)
        '''.format(th=th, tl=tl), 'ne_hw2fw_copy')

    # normalize(a0 buf, a1 max cells): if the buffer holds ASCII, convert it back to cells and put
    # the cursor at the end of the text (the game had set it from the byte length / 2)
    eb.asm_alloc('''
            move $t3, $a0
        n_l:
            lbu $t5, 0($t3)
            beqz $t5, n_none
            sltiu $at, $t5, 0x80
            bnez $at, n_conv
            addiu $t6, $t5, -0xa1
            sltiu $at, $t6, 0x3f
            bnez $at, n_conv
            nop
            b n_l
            addiu $t3, $t3, 2
        n_conv:
            addiu $sp, $sp, -0x10
            sw $ra, 0($sp)
            sw $a0, 4($sp)
            sw $a1, 8($sp)
            lui $t3, 0x{mh:x}
            addiu $t3, $t3, {ml}
            move $t4, $a0
            addiu $t6, $t3, 190
        n_c:
            lbu $t5, 0($t4)
            sb $t5, 0($t3)
            beqz $t5, n_cd
            addiu $t4, $t4, 1
            addiu $t3, $t3, 1
            bne $t3, $t6, n_c
            nop
            sb $zero, 0($t3)
        n_cd:
            lw $a0, 4($sp)
            lw $a2, 8($sp)
            lui $a1, 0x{mh:x}
            jal 0x{cp:08x}
            addiu $a1, $a1, {ml}
            lw $ra, 0($sp)
            lw $a0, 4($sp)
            lw $a1, 8($sp)
            addiu $sp, $sp, 0x10
            addiu $t6, $a1, -1
            slt $at, $t5, $t6
            bnez $at, n_cur
            nop
            move $t5, $t6
        n_cur:
            sh $t5, 0x1c74($a0)              # state + 0x1C7C (a0 = state + 8)
        n_none:
            jr $ra
            nop
        '''.format(mh=mh, ml=ml, cp=eb.symbols['ne_hw2fw_copy']), 'ne_normalize')

    # grid function entry: page table for the mode, normalize the buffer (Latin modes), then the 2
    # replaced instructions (addiu sp,-0x30; sw ra,0x1c(sp))
    eb.asm_alloc(('''
            addiu $sp, $sp, -0x10
            sw $ra, 0($sp)
            sw $a0, 4($sp)
            lui $v0, 0x{sh:x}
            lw $v0, {sl}($v0)
            beqz $v0, g_skip
            move $t3, $v0
''' + select_table('g_tab') + '''
            lw $t3, 0x1fc($v0)
''' + latin_check('$t3', 'g_skip') + '''
            lh $a1, 0x1c7a($v0)
            blez $a1, g_skip
            nop
            jal 0x{nm:08x}
            addiu $a0, $v0, 8
        g_skip:
            lw $ra, 0($sp)
            lw $a0, 4($sp)
            addiu $sp, $sp, 0x10
            addiu $sp, $sp, -0x30
            j 0x{back:08x}
            sw $ra, 0x1c($sp)
        ''').format(sh=sh, sl=sl, nm=eb.symbols['ne_normalize'], back=GRID_FN + 8), 'ne_gridfn')
    eb.asm(GRID_FN, 'j 0x%08x; nop' % eb.symbols['ne_gridfn'], expect=2)

    # key handler entry (leaf, ra untouched): page table for the mode, then the 2 replaced
    # instructions (lui v0,0x8b9; lw v1,-0x5380(v0))
    eb.asm_alloc(('''
            lui $v0, 0x{sh:x}
            lw $t3, {sl}($v0)
''' + select_table('k_tab') + '''
            lui $v0, 0x{sh:x}
            j 0x{back:08x}
            lw $v1, {sl}($v0)
        ''').format(sh=sh, sl=sl, back=KEY_FN + 8), 'ne_keyfn')
    eb.asm(KEY_FN, 'j 0x%08x; nop' % eb.symbols['ne_keyfn'], expect=2)

    # draw wrappers: convert the string (a1) then draw; grid cells centred (16 px glyph slot)
    # ne_abbrev(a1 string) -> v0 = short form when the creation panel draws a long sex / alignment word
    strs = b''
    offs = []
    for lo, sh_ in PANEL_ABBR:
        offs.append((len(strs), len(strs) + len(lo) + 1))
        strs += lo.encode() + b'\0' + sh_.encode() + b'\0'
    sbase = eb.alloc(strs, 'ne_abbr_str', align=4)
    eb.alloc(b''.join(struct.pack('<II', sbase + a, sbase + b) for a, b in offs) + bytes(8), 'ne_abbr_tab', align=4)
    ah, al = hilo(eb.symbols['ne_abbr_tab'])
    ranges = ''.join('''
            sltiu $at, $t3, 0x{a:x}
            bnez $at, ab_r{k}
            sltiu $at, $t3, 0x{b:x}
            bnez $at, ab_in
            nop
        ab_r{k}:'''.format(a=a, b=b + 1, k=k) for k, (a, b) in enumerate(PANEL_MODES))
    eb.asm_alloc(('''
            move $v0, $a1
            lui $t3, 0x{sh:x}
            lw $t3, {sl}($t3)
            beqz $t3, ab_done
            nop
            lw $t3, 0x1fc($t3)''' + ranges + '''
            b ab_done
            nop
        ab_in:
            lui $t4, 0x{ah:x}
            addiu $t4, $t4, {al}
        ab_e:
            lw $t6, 0($t4)
            beqz $t6, ab_done
            move $t5, $a1
        ab_c:
            lbu $t7, 0($t5)
            lbu $t8, 0($t6)
            bne $t7, $t8, ab_next
            addiu $t5, $t5, 1
            bnez $t7, ab_c
            addiu $t6, $t6, 1
            b ab_done
            lw $v0, 4($t4)
        ab_next:
            b ab_e
            addiu $t4, $t4, 8
        ab_done:
            jr $ra
            nop
        ''').format(sh=sh, sl=sl, ah=ah, al=al), 'ne_abbrev')

    def wrapper(name, centre):
        cen = '''
            lbu $t5, 0($a1)
            beqz $t5, w_go
            lbu $t6, 1($a1)
            bnez $t6, w_go
            sltiu $at, $t5, 0x80
            beqz $at, w_go
            nop
''' + vwf.hdchk('$t8', 'w_hd') + '''
            sll $t8, $t8, 8
            lui $t9, 0x{wh:x}
            addiu $t9, $t9, {wl}
            addu $t9, $t9, $t8
            addu $t9, $t9, $t5
            lbu $t9, 0($t9)
            addiu $t9, $t9, -16
            subu $t9, $zero, $t9
            sra $t9, $t9, 1
            lw $a3, 0x0c($sp)
            addu $a3, $a3, $t9
            sw $a3, 0x0c($sp)
        w_go:
'''.format(wh=wh, wl=wl) if centre else ''
        eb.asm_alloc(('''
            addiu $sp, $sp, -0x30
            sw $ra, 0($sp)
            sw $a0, 4($sp)
            sw $a1, 8($sp)
            sw $a3, 0x0c($sp)
            sw $t0, 0x10($sp)
            sw $t1, 0x14($sp)
            sw $t2, 0x18($sp)
            sw $a2, 0x1c($sp)
''' + ('' if centre else '''
            jal 0x%08x
            nop
            move $a1, $v0
''' % eb.symbols['ne_abbrev']) + '''
            lui $t3, 0x{dh:x}                # copy (max 190 bytes) to scratch: never convert in place
            addiu $t3, $t3, {dl}
            move $t4, $a1
            addiu $t6, $t3, 190
        w_cp:
            lbu $t5, 0($t4)
            sb $t5, 0($t3)
            beqz $t5, w_cpd
            addiu $t4, $t4, 1
            addiu $t3, $t3, 1
            bne $t3, $t6, w_cp
            nop
            sb $zero, 0($t3)
        w_cpd:
            lui $a0, 0x{dh:x}
            jal 0x{f:08x}
            addiu $a0, $a0, {dl}
            lui $a1, 0x{dh:x}
            addiu $a1, $a1, {dl}
            sw $a1, 8($sp)
''' + cen + '''
            lw $ra, 0($sp)
            lw $a0, 4($sp)
            lw $a1, 8($sp)
            lw $a3, 0x0c($sp)
            lw $t0, 0x10($sp)
            lw $t1, 0x14($sp)
            lw $t2, 0x18($sp)
            lw $a2, 0x1c($sp)
            j 0x{d:08x}
            addiu $sp, $sp, 0x30
        ''').format(f=eb.symbols['ne_fw2hw'], d=DRAW_TEXT, dh=dh, dl=dl), name)
    wrapper('ne_grid_draw', True)
    wrapper('ne_field_draw', False)
    eb.asm(GRID_DRAW_CALL, 'jal 0x%08x' % eb.symbols['ne_grid_draw'], expect=1)
    for c in FIELD_DRAW_CALLS:
        eb.asm(c, 'jal 0x%08x' % eb.symbols['ne_field_draw'], expect=1)
    # Rename Spells field: text helper 0x0887ADB0 (string a2 = a sprintf buffer on the caller's
    # stack, so it is converted in place)
    eb.asm_alloc('''
            addiu $sp, $sp, -0x20
            sw $ra, 0($sp)
            sw $a0, 4($sp)
            sw $a1, 8($sp)
            sw $a2, 0x0c($sp)
            sw $a3, 0x10($sp)
            sw $t0, 0x14($sp)
            sw $t1, 0x18($sp)
            jal 0x{f:08x}
            move $a0, $a2
            lw $ra, 0($sp)
            lw $a0, 4($sp)
            lw $a1, 8($sp)
            lw $a2, 0x0c($sp)
            lw $a3, 0x10($sp)
            lw $t0, 0x14($sp)
            lw $t1, 0x18($sp)
            j 0x{h:08x}
            addiu $sp, $sp, 0x20
        '''.format(f=eb.symbols['ne_fw2hw'], h=TEXT_HELPER), 'ne_spell_draw')
    assert eb.u32(SPELL_DRAW_CALL) == 0x0C000000 | (TEXT_HELPER >> 2) & 0x3ffffff
    eb.asm(SPELL_DRAW_CALL, 'jal 0x%08x' % eb.symbols['ne_spell_draw'], expect=1)
    for at, n in FIELD_LIMITS:
        assert eb.u32(at) == 0x24020000 | n, hex(at)
        eb.w32(at, 0x24020000 | (2 * n))

    # cursor: x = base + VWF width of the cells before the cursor (Latin modes)
    eb.asm_alloc(('''
            addiu $sp, $sp, -0x10
            sw $ra, 0($sp)
            jal 0x{cf:08x}
            sw $a0, 4($sp)
            lw $a0, 4($sp)
            lui $v0, 0x{sh:x}
            lw $v0, {sl}($v0)
            lw $t3, 0x1fc($v0)
''' + latin_check('$t3', 'c_done') + '''
            lh $t4, 0x1c7c($v0)
            blez $t4, c_done
            addiu $t5, $v0, 8
''' + vwf.hdchk('$t8', 'c_hd') + '''
            sll $t8, $t8, 8
            lui $t9, 0x{wh:x}
            addiu $t9, $t9, {wl}
            addu $t9, $t9, $t8
            move $t6, $zero
        c_l:
            lbu $t7, 0($t5)
            beqz $t7, c_sp
            lbu $t8, 1($t5)
            sll $t7, $t7, 8
            or $t7, $t7, $t8
            lui $a1, 0x{th:x}
            addiu $a1, $a1, {tl}
            move $a2, $zero
        c_f:
            lhu $v1, 0($a1)
            beq $v1, $t7, c_hit
            addiu $a2, $a2, 1
            sltiu $at, $a2, 95
            bnez $at, c_f
            addiu $a1, $a1, 2
            b c_n
            addiu $t6, $t6, 16
        c_sp:
            lbu $v1, 0x20($t9)
            b c_n
            addu $t6, $t6, $v1
        c_hit:
            addiu $a2, $a2, 0x1f
            addu $v1, $t9, $a2
            lbu $v1, 0($v1)
            addu $t6, $t6, $v1
        c_n:
            addiu $t4, $t4, -1
            bgtz $t4, c_l
            addiu $t5, $t5, 2
            lh $t4, 0x1c7c($v0)
            sll $t4, $t4, 4
            lw $t7, 0($a0)
            subu $t7, $t7, $t4
            addu $t7, $t7, $t6
            sw $t7, 0($a0)
        c_done:
            lw $ra, 0($sp)
            jr $ra
            addiu $sp, $sp, 0x10
        ''').format(cf=CURSOR_FN, sh=sh, sl=sl, wh=wh, wl=wl, th=th, tl=tl), 'ne_cursor')
    for c in CURSOR_CALLS:
        eb.asm(c, 'jal 0x%08x' % eb.symbols['ne_cursor'], expect=1)

    # confirm (names / nicknames): buffer -> ASCII (Latin modes), then the replaced instructions.
    # v0 must hold the mode afterwards (the code after the non-empty check branches on it).
    # riddle_fold(a0 buf): full-width a-z -> A-Z, trailing full-width spaces removed; other cells (the
    # box-drawing glyphs) untouched. The answers stay full-width cells, compared by op 0xA4 with strcmp.
    eb.asm_alloc('''
            move $t3, $a0
            move $t4, $a0
        r_l:
            lbu $t5, 0($t3)
            beqz $t5, r_t
            sltiu $at, $t5, 0x80
            bnez $at, r_n1
            lbu $t6, 1($t3)
            addiu $at, $zero, 0x82
            bne $t5, $at, r_n2
            addiu $t7, $t6, -0x81
            sltiu $at, $t7, 26
            beqz $at, r_n2
            nop
            addiu $t6, $t6, -0x21
            sb $t6, 1($t3)
        r_n2:
            addiu $at, $zero, 0x81
            bne $t5, $at, r_ns
            addiu $at, $zero, 0x40
            beq $t6, $at, r_sp
            nop
        r_ns:
            addiu $t4, $t3, 2
        r_sp:
            b r_l
            addiu $t3, $t3, 2
        r_n1:
            addiu $t3, $t3, 1
            b r_l
            move $t4, $t3
        r_t:
            jr $ra
            sb $zero, 0($t4)
        ''', 'ne_riddle_fold')

    assert eb.u32(CONFIRM_AT) == 0x3c0308b9 and eb.u32(CONFIRM_AT + 4) == 0x8c63ac80
    eb.asm_alloc(('''
            lw $t3, 0x1fc($s3)
            addiu $at, $zero, 0x{rm:x}
            bne $t3, $at, q_nr
            nop
            jal 0x{rf:08x}
            addiu $a0, $s3, 8
            b q_d
            nop
        q_nr:
''' + latin_check('$t3', 'q_d') + '''
            jal 0x{cv:08x}
            addiu $a0, $s3, 8
        q_d:
            lw $v0, 0x1fc($s3)
            lui $v1, 0x8b9
            j 0x{back:08x}
            lw $v1, -0x5380($v1)
        ''').format(cv=eb.symbols['ne_conv'], back=CONFIRM_AT + 8, rm=RIDDLE_MODE,
                    rf=eb.symbols['ne_riddle_fold']), 'ne_confirm')
    eb.asm(CONFIRM_AT, 'j 0x%08x; nop' % eb.symbols['ne_confirm'], expect=2)

    # confirm (Rename Spells, mode 0x1D): buffer -> ASCII, then the non-empty check
    eb.asm_alloc('''
            addiu $sp, $sp, -0x10
            sw $ra, 0($sp)
            jal 0x{cv:08x}
            addiu $a0, $s0, 8
            lw $ra, 0($sp)
            j 0x{chk:08x}
            addiu $sp, $sp, 0x10
        '''.format(cv=eb.symbols['ne_conv'], chk=SPELL_CHECK_FN), 'ne_confirm_spell')
    assert eb.u32(SPELL_CHECK_CALL) == 0x0C000000 | (SPELL_CHECK_FN >> 2) & 0x3ffffff
    eb.asm(SPELL_CHECK_CALL, 'jal 0x%08x' % eb.symbols['ne_confirm_spell'], expect=1)
