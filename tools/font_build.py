"""Left-align the ASCII glyphs of FONT10_16.GIM for the VWF (Elminage II).

Elminage II's half-width glyphs are centred in their 10x16 cells ('l' sits in columns 4-5),
so a width table alone leaves gaps on the left of narrow letters. This shifts every glyph
0x21..0x7E to column 0 of its cell (palette indices, nothing redrawn) and writes
work/font/FONT10_16.GIM, which tools/vwf.py measures and the build puts into ANIME.BIN.
Kana cells (0xA1..) are left untouched.

    python tools/font_build.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gim
import vwf


def main():
    raw = open(vwf.FONT_SRC, 'rb').read()
    rgba, idx, _ = gim.decode(raw)
    a = rgba[:, :, 3]
    idx = idx.copy()
    bg = np.bincount(idx.ravel()).argmax()          # the transparent index
    for code in range(0x21, 0x7f):
        i = code - 0x20
        x0, y0 = (i % 25) * 10, (i // 25) * 16
        cols = np.where((a[y0:y0 + 16, x0:x0 + 10] > 0).any(0))[0]
        if not len(cols) or cols.min() == 0:
            continue
        s = int(cols.min())
        cell = idx[y0:y0 + 16, x0:x0 + 10].copy()
        idx[y0:y0 + 16, x0:x0 + 10] = bg
        idx[y0:y0 + 16, x0:x0 + 10 - s] = cell[:, s:]
    os.makedirs(os.path.dirname(vwf.FONT_NEW), exist_ok=True)
    open(vwf.FONT_NEW, 'wb').write(gim.encode_index(raw, idx))
    w = vwf.measure(vwf.FONT_NEW)
    print('wrote', vwf.FONT_NEW, 'widths l=%d i=%d m=%d W=%d space=%d' % (w[ord('l')], w[ord('i')], w[ord('m')], w[ord('W')], w[32]))


if __name__ == '__main__':
    main()
