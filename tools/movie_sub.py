"""English captions for the opening movies (USRDIR/MOVIE/OP_01.PMF, OP_02.PMF), container layout kept.
Ported from Elminage III.

    python tools/movie_sub.py [OP_01 ...]   # -> work/build/movie/<name>.PMF (+ work/movie/<name>_preview.mp4)

Source movies: work/movie/<name>.pmf (copied from the ISO). Captions: work/movie/captions.json
(movies -> items; English only, the Japanese transcript is local in captions_jp.json).

1. Decode the GOPs that carry captions (ffmpeg) and draw the English from work/movie/captions.json over
   a blurred, darkened band that hides the burned-in Japanese.
2. Re-encode each of those GOPs alone with libx264 (Main, level 2.1, no B-frames, IDR at the GOP start,
   one AUD per frame, constant QP), strip SEI, and pick the lowest QP at which every frame is no
   larger than the original frame (minus room for a filler NAL).
3. Pad every new access unit with an H.264 filler NAL (type 12) to exactly the original size, so all
   PES packets, PTS/DTS and the per-GOP AU-size tables (stream 0xBF) stay valid; write the new ES
   into the original container (tools/pmf.py). Real hardware: standard Main-profile AVC as before.
"""
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pmf

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
WORK = os.path.join(ROOT, 'work', 'movie')
OUT_DIR = os.path.join(ROOT, 'work', 'build', 'movie')
MOVIES = ('OP_01', 'OP_02')
W, H, FPS = 480, 272, 30000 / 1001
QPS = [16, 18, 20, 22, 24, 26, 28, 30, 33, 36, 40, 45, 51]


def nal_units(b):
    """Split Annex-B bytes into NAL units (with their 4-byte start codes normalised)."""
    out, i, n = [], 0, len(b)
    starts = []
    while True:
        j = b.find(b'\x00\x00\x01', i)
        if j < 0:
            break
        starts.append(j)
        i = j + 3
    for k, s in enumerate(starts):
        e = starts[k + 1] if k + 1 < len(starts) else n
        while e > s and b[e - 1] == 0 and k + 1 < len(starts):
            e -= 1
        out.append(b'\x00\x00\x00\x01' + b[s + 3:e])
    return out


def split_aus(es):
    aus, cur = [], []
    for nal in nal_units(es):
        t = nal[4] & 0x1F
        if t == 9 and cur:
            aus.append(b''.join(cur))
            cur = []
        if t == 6:                      # SEI (x264 version string etc.)
            continue
        cur.append(nal)
    if cur:
        aus.append(b''.join(cur))
    return aus


def filler(n):
    assert n == 0 or n >= 6
    return b'' if n == 0 else b'\x00\x00\x00\x01\x0c' + b'\xff' * (n - 6) + b'\x80'


class Captions:
    def __init__(self, cfg):
        self.cfg = cfg
        self.f_line = {}
        self.f_small = ImageFont.truetype(cfg['font_small'], 12)
        self.f_name = ImageFont.truetype(cfg['font_name'], 21)

    def font(self, size):
        if size not in self.f_line:
            self.f_line[size] = ImageFont.truetype(self.cfg['font_line'], size)
        return self.f_line[size]

    def alpha(self, it, t):
        f = self.cfg['fade']
        if t < it['t0'] or t > it['t1']:
            return 0.0
        return max(0.0, min(1.0, (t - it['t0']) / f, (it['t1'] - t) / f))

    def apply(self, frame, t):
        img = Image.fromarray(frame)
        for it in self.cfg['items']:
            a = self.alpha(it, t)
            if a <= 0:
                continue
            x0, y0, x1, y1 = it['box']
            # band: blurred + darkened copy of the box, feathered mask
            band = img.filter(ImageFilter.GaussianBlur(7))
            band = Image.eval(band, lambda v: int(v * 0.30))
            mask = Image.new('L', img.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle([x0, y0, x1, y1], radius=10, fill=255)
            mask = mask.filter(ImageFilter.GaussianBlur(5))
            mask = Image.eval(mask, lambda v: int(v * a))
            img = Image.composite(band, img, mask)
            # text layer with soft shadow
            txt = Image.new('RGBA', img.size, (0, 0, 0, 0))
            d = ImageDraw.Draw(txt)
            if 'plate' in it:
                small, name = it['plate']
                cx = (x0 + x1) // 2
                d.text((cx, y0 + 18), small, font=self.f_small, fill=(235, 235, 225, 255), anchor='ms')
                d.text((cx, y1 - 14), name, font=self.f_name, fill=(255, 255, 255, 255), anchor='ms')
            else:
                f = self.font(it.get('size', 14))
                lh = f.size + 5
                n = len(it['lines'])
                cy = (y0 + y1) / 2 - (n - 1) * lh / 2
                cx = (x0 + x1) // 2
                left = it.get('align') == 'left'
                for k, line in enumerate(it['lines']):
                    if left:
                        d.text((x0 + 8, cy + k * lh), line, font=f, fill=(255, 255, 250, 255), anchor='lm')
                    else:
                        d.text((cx, cy + k * lh), line, font=f, fill=(255, 255, 250, 255), anchor='mm')
            sh = txt.split()[3].filter(ImageFilter.GaussianBlur(1.6))
            shadow = Image.new('RGBA', img.size, (0, 0, 0, 0))
            shadow.putalpha(Image.eval(sh, lambda v: int(min(255, v * 1.6) * a)))
            txt.putalpha(Image.eval(txt.split()[3], lambda v: int(v * a)))
            base = img.convert('RGBA')
            base.alpha_composite(shadow)
            base.alpha_composite(txt)
            img = base.convert('RGB')
        return np.array(img)


def encode_gop(frames, qp, qplist=None):
    n = len(frames)
    params = ('keyint=%d:min-keyint=%d:scenecut=0:bframes=0:ref=2:aud=1:qp=%d:'
              'repeat-headers=1:info=0' % (n, n, qp))
    if qplist is not None:                  # per-frame QP (x264 qpfile)
        qf = os.path.join(WORK, 'qpfile.txt')
        open(qf, 'w').write(''.join('%d %s %d\n' % (k, 'I' if k == 0 else 'P', q) for k, q in enumerate(qplist)))
        params += ':qpfile=qpfile.txt'          # relative: ffmpeg runs in WORK (no drive colon)
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
           '-s', '%dx%d' % (W, H), '-r', '30000/1001', '-i', '-', '-c:v', 'libx264',
           '-profile:v', 'main', '-level', '2.1', '-pix_fmt', 'yuv420p', '-color_range', 'tv',
           '-colorspace', 'smpte170m', '-color_primaries', 'smpte170m', '-color_trc', 'smpte170m',
           '-x264-params', params, '-f', 'h264', '-']
    es = subprocess.run(cmd, input=frames.tobytes(), capture_output=True, check=True, cwd=WORK).stdout
    return split_aus(es)


def build_movie(name, cfg):
    src = os.path.join(WORK, name + '.pmf')
    out = os.path.join(OUT_DIR, name + '.PMF')
    items = cfg['movies'][name]
    cap = Captions(dict(cfg, items=items))
    m = pmf.Pmf(src)
    orig_aus, _ = m.aus()
    starts, c = [], 0
    for g in m.gops:
        starts.append(c)
        c += len(g)
    t_lo = min(it['t0'] for it in items)
    t_hi = max(it['t1'] for it in items)
    gops = [i for i, s in enumerate(starts)
            if s / FPS < t_hi and (s + len(m.gops[i])) / FPS > t_lo]
    first = starts[gops[0]]
    last = starts[gops[-1]] + len(m.gops[gops[-1]])
    print('%s: re-encoding GOPs %d-%d (frames %d-%d, %.1f-%.1f s)' % (name, gops[0], gops[-1], first, last - 1,
                                                                      first / FPS, last / FPS))
    new_aus = list(orig_aus)
    for g in gops:
        s, n = starts[g], len(m.gops[g])
        sizes = m.gops[g]
        ts = [(s + k) / FPS for k in range(n)]
        if not any(cap.alpha(it, t) > 0 for it in items for t in ts):
            continue
        # every GOP starts with an IDR frame: decode it on its own
        raw = subprocess.run(['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-f', 'h264',
                              '-i', '-', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                             input=b''.join(orig_aus[s:s + n]), capture_output=True, check=True).stdout
        chunk = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
        assert len(chunk) == n, (g, len(chunk), n)
        chunk = np.stack([cap.apply(chunk[k], ts[k]) for k in range(n)])
        # near-duplicate frames in the original (tiny AUs) must stay exact repeats so x264 emits
        # all-skip frames that fit the original size
        for k in range(1, n):
            if sizes[k] < 400:
                chunk[k] = chunk[k - 1]
        fits = lambda aus: all(len(a) == sz or len(a) + 6 <= sz for a, sz in zip(aus, sizes))
        for qp in QPS:
            aus = encode_gop(chunk, qp)
            assert len(aus) == n, (g, len(aus), n)
            if fits(aus):
                break
        else:
            raise SystemExit('GOP %d does not fit even at QP %d' % (g, QPS[-1]))
        if qp >= 28:                        # one tight frame forced a coarse QP: refine per frame
            ql = [18] * n
            for _ in range(400):
                cand = encode_gop(chunk, 18, ql)
                over = [k for k, (a, sz) in enumerate(zip(cand, sizes)) if not (len(a) == sz or len(a) + 6 <= sz)]
                if not over:
                    aus, qp = cand, 'per-frame %d-%d' % (min(ql), max(ql))
                    break
                for k in over:
                    ql[k] = min(51, ql[k] + 3)
        for k, (a, sz) in enumerate(zip(aus, sizes)):
            new_aus[s + k] = a + filler(sz - len(a))
            assert len(new_aus[s + k]) == sz
        print('  GOP %2d: %2d frames, QP %s' % (g, n, qp), flush=True)
    es = b''.join(new_aus)
    os.makedirs(OUT_DIR, exist_ok=True)
    m.write(out, es)
    print('wrote', out)
    es_path = os.path.join(WORK, name + '_en.mps')
    open(es_path, 'wb').write(open(out, 'rb').read()[2048:])
    subprocess.run(['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-y', '-ss', str(first / FPS), '-t',
                    str((last - first) / FPS), '-i', es_path, '-an', '-c:v', 'libx264', '-crf', '18',
                    os.path.join(WORK, name + '_preview.mp4')], check=True)
    return out


def built_movies():
    """{ISO path: built file} for build.py (only movies already built by this tool)."""
    out = {}
    for n in MOVIES:
        p = os.path.join(OUT_DIR, n + '.PMF')
        if os.path.exists(p):
            out['PSP_GAME/USRDIR/MOVIE/%s.PMF' % n] = p
    return out


def main(names):
    cfg = json.load(open(os.path.join(WORK, 'captions.json'), encoding='utf-8'))
    for n in names or MOVIES:
        build_movie(n, cfg)


if __name__ == '__main__':
    main(sys.argv[1:])
