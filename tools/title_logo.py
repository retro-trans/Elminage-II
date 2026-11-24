"""Title logo (ANIME/GR01_10303.GIM, 480x272, 8-bit indexed with alpha): English for the two lines of
Japanese baked into the Elminage II logo.

  - the katakana reading エルミナージュII above the 'na' -> "ELMINAGE II"
  - the subtitle 双生の女神と運命の大地 under the letters, split by the red II (と sat in the gap between
    its two pillars) -> "The Twin Goddesses" | "&" | "the Land of Destiny" ("Twin Goddesses" as in the
    script)

Both lines sit on transparent pixels, so they are erased to alpha 0 (the pillar columns, the tip of the
II's flag, the 'g' tail and the pillar bases are left alone) and redrawn with a serif TrueType font in the
original colours: a light core over a dark 1 px outline. The result is quantised to the image's own
palette (alpha included), so the GIM layout is unchanged.

    python tools/title_logo.py            # writes work/build/img/GR01_10303.GIM + work/ui/preview/
Needs a Windows serif font (Palatino Linotype Bold, else Georgia Bold / Garamond Bold).
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gim

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
NAME = 'GR01_10303.GIM'
SRC = os.path.join(ROOT, 'work', 'source', 'arc_ANIME', NAME)
OUT = os.path.join(ROOT, 'work', 'build', 'img', NAME)
PREV = os.path.join(ROOT, 'work', 'ui', 'preview', 'GR01_10303.png')
FONTS = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts')
FONT_FILES = ('palab.ttf', 'georgiab.ttf', 'GARABD.TTF')

# erase boxes (x0, y0, x1, y1 inclusive) minus keep boxes
ERASE = [(265, 73, 333, 82), (281, 71, 333, 72), (265, 83, 280, 83),     # katakana + its outline
         (130, 136, 352, 150), (130, 135, 299, 135), (331, 135, 352, 135)]  # subtitle
KEEP = [(219, 130, 236, 160), (246, 130, 264, 160)]                     # the II's two pillars

SUB_COLOR, SUB_OUTLINE = (132, 40, 32), (34, 9, 6)       # subtitle core / outline (sampled, darkened)
KATA_COLOR, KATA_OUTLINE = (214, 196, 182), (33, 25, 19)  # sampled: katakana core / outline


def font(size):
    for f in FONT_FILES:
        p = os.path.join(FONTS, f)
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    raise SystemExit('no serif font found in %s (%s)' % (FONTS, ', '.join(FONT_FILES)))


def text_layer(items):
    """items: (x, y_top, text, size, core, outline, anchor 'l'|'r'|'c', tracking) -> RGBA layer."""
    core = Image.new('L', (480, 272), 0)
    col = Image.new('RGB', (480, 272), 0)
    out = Image.new('L', (480, 272), 0)
    ocol = Image.new('RGB', (480, 272), 0)
    for x, y, s, size, c, oc, anchor, track in items:
        f = font(size)
        w = sum(f.getlength(ch) for ch in s) + track * (len(s) - 1)
        x0 = x - w if anchor == 'r' else x - w / 2 if anchor == 'c' else x
        m = Image.new('L', (480, 272), 0)
        d = ImageDraw.Draw(m)
        top = f.getbbox('H')[1]
        cx = x0
        for ch in s:
            d.text((cx, y - top), ch, font=f, fill=255)
            cx += f.getlength(ch) + track
        ring = m.filter(ImageFilter.MaxFilter(3))
        core.paste(Image.new('L', m.size, 255), mask=m)
        col.paste(Image.new('RGB', m.size, c), mask=m)
        out.paste(Image.new('L', m.size, 255), mask=ring)
        ocol.paste(Image.new('RGB', m.size, oc), mask=ring)
    lay = Image.new('RGBA', (480, 272), (0, 0, 0, 0))
    lay.paste(Image.merge('RGBA', (*ocol.split(), out)), mask=out)
    lay.alpha_composite(Image.merge('RGBA', (*col.split(), core)))
    return lay


def render():
    d = open(SRC, 'rb').read()
    rgba, idx, info = gim.decode(d)
    a = rgba.copy()
    keep = np.zeros(a.shape[:2], bool)
    for x0, y0, x1, y1 in KEEP:
        keep[y0:y1 + 1, x0:x1 + 1] = True
    for x0, y0, x1, y1 in ERASE:
        m = np.zeros(a.shape[:2], bool)
        m[y0:y1 + 1, x0:x1 + 1] = True
        a[m & ~keep] = 0
    img = Image.fromarray(a, 'RGBA')
    img.alpha_composite(text_layer([
        (299, 73, 'ELMINAGE II', 9, KATA_COLOR, KATA_OUTLINE, 'c', 1),
        (216, 137, 'The Twin Goddesses', 11, SUB_COLOR, SUB_OUTLINE, 'r', 0),
        (241, 137, '&', 11, SUB_COLOR, SUB_OUTLINE, 'c', 0),
        (267, 137, 'the Land of Destiny', 11, SUB_COLOR, SUB_OUTLINE, 'l', 0),
    ]))
    new = np.asarray(img)
    # quantise to the image's own palette (RGBA distance); untouched pixels keep their index
    pal = gim.decode(d)[0].reshape(-1, 4)
    _, first = np.unique(idx.ravel(), return_index=True)
    used = idx.ravel()[first]
    colors = pal[first].astype(np.int32)
    out_idx = idx.copy()
    changed = np.any(new != rgba, axis=2)
    ys, xs = np.nonzero(changed)
    px = new[ys, xs].astype(np.int32)
    w = np.array([1, 1, 1, 2])
    dist = (((px[:, None, :] - colors[None, :, :]) * w) ** 2).sum(2)
    out_idx[ys, xs] = used[dist.argmin(1)]
    res = gim.encode_index(d, out_idx)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'wb').write(res)
    os.makedirs(os.path.dirname(PREV), exist_ok=True)
    Image.fromarray(gim.decode(res)[0], 'RGBA').save(PREV)
    return res


def archive_files():
    """{archive: {name: bytes}} for patches.apply_all."""
    return {'ANIME': {NAME: render()}}


if __name__ == '__main__':
    render()
    print(OUT)
    print(PREV)
