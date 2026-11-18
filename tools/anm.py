"""ANIME/*.ANM ('animdata') sprite tables: widen the town/facility menu buttons.

Layout (reversed from MD02_004.ANM): 'animdata', u32 0x20 (texture list offset), u32 record table offset,
u32 next section offset, u32 file size, ... Texture list: 0x100-byte slots with the name ('el02_001.tga').
Record table: 28-byte records (s32 texture slot, u, v, w, h, 0, 0) = source rects on the texture; the
game draws a sprite at the record's w x h.

The facility buttons (sheet EL02_001, used only by MD02_004.ANM) are 114x20 cells at (114*state, 20*row).
work/ui/specs/EL02_001.json ("widen") redraws them 130 px wide at x = 130*state; this rewrites the 69
matching records (u -> 130*state, w -> 130). Same file size; data only (real hardware: no code change).

    python tools/anm.py            # print the button records before/after
"""
import os
import struct

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SRC = os.path.join(ROOT, 'work', 'source', 'arc_ANIME')
WIDEN = [('MD02_004.ANM', 'el02_001.tga', 114, 130)]


def textures(d):
    out = []
    off = struct.unpack_from('<I', d, 8)[0]
    end = struct.unpack_from('<I', d, 12)[0]
    for o in range(off, end, 0x100):
        out.append(d[o:o + 0x100].split(b'\0')[0].decode('ascii', 'replace'))
    return out


def records(d):
    start = struct.unpack_from('<I', d, 12)[0]
    end = struct.unpack_from('<I', d, 16)[0]
    return [(o, list(struct.unpack_from('<7i', d, o))) for o in range(start, end - 27, 28)]


def widen(d, tex_name, old_w, new_w):
    d = bytearray(d)
    slot = textures(d).index(tex_name)
    n = 0
    for o, r in records(d):
        if r[0] == slot and r[3] == old_w:
            assert r[1] % old_w == 0, (hex(o), r)
            r[1] = r[1] // old_w * new_w
            r[3] = new_w
            struct.pack_into('<7i', d, o, *r)
            n += 1
    return bytes(d), n


# Windows to widen: (file, offset of the right-edge placement, extra width in layout units). The placement
# list order is top edge, TR corner, right edge, BR corner, bottom edge, BL corner, left edge, fill.
WINDOWS = []        # (file, right-edge placement offset, extra units). The character-creation side windows are
                    # NOT in MD02_000 / MD03_002 window entries (both tested in 0.1.19 / 0.1.20: no change);
                    # their size comes from elsewhere (open).


def widen_window(d, off, dx):
    d = bytearray(d)
    v = struct.unpack_from('<9i', d, off)
    assert v[4] == 180 and v[1] == 16, (hex(off), v)
    for k, f, add in ((-36, 0, dx), (0, 0, dx), (36, 0, dx), (-72, 7, dx * 25), (72, 7, dx * 25), (180, 7, dx * 10)):
        w = list(struct.unpack_from('<9i', d, off + k))
        w[f] += add
        struct.pack_into('<9i', d, off + k, *w)
    return bytes(d)


def archive_files():
    out = {}
    for name, tex, ow, nw in WIDEN:
        data, n = widen(open(os.path.join(SRC, name), 'rb').read(), tex, ow, nw)
        assert n == 69, (name, n)
        out[name] = data
    for name, off, dx in WINDOWS:
        d = out.get(name) or open(os.path.join(SRC, name), 'rb').read()
        out[name] = widen_window(d, off, dx)
    return {'ANIME': out}


if __name__ == '__main__':
    for name, tex, ow, nw in WIDEN:
        d = open(os.path.join(SRC, name), 'rb').read()
        print(name, textures(d))
        new, n = widen(d, tex, ow, nw)
        print('records changed:', n)
        for (o, a), (_, b) in zip(records(d), records(new)):
            if a != b and a[2] in (0, 60):
                print('  %x %s -> %s' % (o, a[:5], b[:5]))
