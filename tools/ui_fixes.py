"""Character creation screen (Training Hall Register / Change Name): selection boxes.

The gender list used sprite 0x4F4 (a 16 px box: one kanji, also the name-entry text cursor) and the
alignment list sprite 0x500 (a 32 px box: two kanji), so the box covered "Fe" of "Female" and "Neu" of
"Neutral". Both lists now use the class list's left-column box 0x510 (wide enough for "Alchemist"); at
the same (x, y) it lines up with the list rows (checked in game). The show call is wrapped so the old
boxes (left visible by the name entry / previous step) are hidden first. The class list shows and
hides 0x510 itself every frame, but the steps in between (age, race) never touched the old boxes, so the
creation-screen draw routine (0x0884D160) now hides 0x510 at the start of every frame.

    0x0884D624 / 0x0884D634  addiu a0, zero, 0x4F4  (gender: show / position)  -> 0x510
    0x0884D628               jal 0x0887B144 (show)                           -> jal ui_box_show
    0x0884D76C / 0x0884D77C  addiu a0, zero, 0x500  (alignment: show / position) -> 0x510
    0x0884D770               jal 0x0887B144 (show)                           -> jal ui_box_show
Real hardware: code only (sprite ids and one cave stub).
"""
SHOW = 0x0887B144
DRAW_FN = 0x0884D160             # creation / rename screen draw: addiu sp,-0xC0; sw ra,0x2C(sp)
BOX = 0x510
SITES = ((0x0884D624, 0x0884D628, 0x0884D634, 0x4F4), (0x0884D76C, 0x0884D770, 0x0884D77C, 0x500))


def apply(eb):
    eb.asm_alloc('''
            addiu $sp, $sp, -0x10
            sw $ra, 0($sp)
            sw $a0, 4($sp)
            sw $a1, 8($sp)
            addiu $a0, $zero, 0x4f4
            jal 0x{show:08x}
            move $a1, $zero
            addiu $a0, $zero, 0x500
            jal 0x{show:08x}
            move $a1, $zero
            lw $a0, 4($sp)
            lw $a1, 8($sp)
            lw $ra, 0($sp)
            j 0x{show:08x}
            addiu $sp, $sp, 0x10
        '''.format(show=SHOW), 'ui_box_show')
    for id_at, show_at, pos_at, old in SITES:
        assert eb.u32(id_at) == 0x24040000 | old and eb.u32(pos_at) == 0x24040000 | old
        assert eb.u32(show_at) == 0x0C000000 | (SHOW >> 2) & 0x3ffffff
        eb.w32(id_at, 0x24040000 | BOX)
        eb.w32(pos_at, 0x24040000 | BOX)
        eb.asm(show_at, 'jal 0x%08x' % eb.symbols['ui_box_show'], expect=1)
    # every frame: hide the shared wide box first (the gender / alignment / class code shows it again)
    eb.asm_alloc('''
            addiu $sp, $sp, -0x20
            sw $ra, 0($sp)
            sw $a0, 4($sp)
            sw $a1, 8($sp)
            sw $a2, 0x0c($sp)
            sw $a3, 0x10($sp)
            sw $t0, 0x14($sp)
            sw $t1, 0x18($sp)
            addiu $a0, $zero, 0x{box:x}
            jal 0x{show:08x}
            move $a1, $zero
            lw $a0, 4($sp)
            lw $a1, 8($sp)
            lw $a2, 0x0c($sp)
            lw $a3, 0x10($sp)
            lw $t0, 0x14($sp)
            lw $t1, 0x18($sp)
            lw $ra, 0($sp)
            addiu $sp, $sp, 0x20
            addiu $sp, $sp, -0xc0
            j 0x{back:08x}
            sw $ra, 0x2c($sp)
        '''.format(box=BOX, show=SHOW, back=DRAW_FN + 8), 'ui_draw_entry')
    assert eb.u32(DRAW_FN) == 0x27bdff40 and eb.u32(DRAW_FN + 4) == 0xafbf002c
    eb.asm(DRAW_FN, 'j 0x%08x; nop' % eb.symbols['ui_draw_entry'], expect=2)
