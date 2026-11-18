"""Find which ANM window (frame of corner/edge pieces) is which on the current screen.

    python tools/anm_probe.py list                 # ANM files resident in RAM + their windows
    python tools/anm_probe.py nudge FILE OFFSET DX  # move one window's right column by DX layout units
                                                    # (right corners/edge x += DX, top/bottom edge scale)
The emulator must show the screen. Changes are made in RAM only (reload a savestate afterwards).

Window placements (36 bytes each in the ANM's third section): s32 x, y, layer, rotX, rotY, rotZ, a%, sx%, sy%.
Order: top edge (16,0, sx=(w-32)/4*100), TR corner (w-16,0), right edge (w-16,16, rotY=180, sy), BR corner,
bottom edge (16,h-16, rotX=180, sx), BL corner, left edge (0,16, sy), fill (0,0, sx=w*10, sy=h*10).
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ppsspp_dbg import Emu

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SRC = os.path.join(ROOT, 'work', 'source', 'arc_ANIME')


def windows(d):
    """[(offset of the right-edge entry, w, h)] from an ANM file image."""
    s0, s1 = struct.unpack_from('<II', d, 16)
    out = []
    for o in range(s0, s1 - 35, 36):
        v = struct.unpack_from('<9i', d, o)
        if v[4] == 180 and v[1] == 16 and v[3] == 0 and o + 216 <= s1:
            b = struct.unpack_from('<9i', d, o + 72)
            if b[3] == 180:
                out.append((o, v[0] + 16, b[1] + 16))
    return out


def resident(e):
    """{file name: RAM address} for ANM files whose image is found in RAM."""
    found = {}
    ram = e.read(0x08800000, 0x01800000)
    # loaded copies keep the 'animdata' magic, but header / texture slots are rewritten: match by the
    # placement section instead
    heads = [m for m in range(len(ram)) if False]
    pos, heads = 0, []
    while True:
        i = ram.find(b'animdata', pos)
        if i < 0:
            break
        heads.append(i)
        pos = i + 8
    for name in sorted(os.listdir(SRC)):
        if not name.endswith('.ANM'):
            continue
        d = open(os.path.join(SRC, name), 'rb').read()
        s0 = struct.unpack_from('<I', d, 16)[0]
        probe = d[s0:s0 + 0x200]
        for h in heads:
            if ram[h + s0:h + s0 + 0x200] == probe:
                found[name] = 0x08800000 + h
    return found


def main():
    a = sys.argv[1:]
    with Emu() as e:
        e.pause()
        try:
            res = resident(e)
            if a[0] == 'list':
                for name, addr in res.items():
                    d = open(os.path.join(SRC, name), 'rb').read()
                    print(name, hex(addr), [(hex(o), w, h) for o, w, h in windows(d)])
            elif a[0] == 'nudge':
                name, off, dx = a[1], int(a[2], 16), int(a[3])
                base = res[name]
                for k, f, add in ((-36, 0, dx), (0, 0, dx), (36, 0, dx),          # TR corner, right, BR corner
                                  (-72, 7, dx * 25), (72, 7, dx * 25),         # top / bottom edge scale
                                  (180, 7, dx * 10)):                          # fill scale
                    w = list(struct.unpack('<9i', e.read(base + off + k, 36)))
                    w[f] += add
                    e.write(base + off + k, struct.pack('<9i', *w))
                print('nudged', name, hex(off), dx)
        finally:
            e.resume()


if __name__ == '__main__':
    main()
