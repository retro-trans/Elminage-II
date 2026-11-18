"""Check translator output and take it into the slice files.

    python tools/slice_in.py 0 1 2 ...        # dry run: report problems per slice
    python tools/slice_in.py --apply 0 1 2    # write en/note of clean rows into slice_NNN.json

Checks per row of slice_NNN.out.json against slice_NNN.json: same key, kind and jp (order kept);
control codes ({..}) identical and in order; English is ASCII; not empty.
Rows that fail are reported and not taken.
"""
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DIR = os.path.join(ROOT, 'work', 'translation', 'en', 'slices')
CODE = re.compile(r'\{[^}]*\}')


def check(n):
    src_p = os.path.join(DIR, 'slice_%03d.json' % n)
    out_p = os.path.join(DIR, 'slice_%03d.out.json' % n)
    if not os.path.exists(out_p):
        return None, ['no output yet']
    src = json.load(open(src_p, encoding='utf-8'))
    try:
        out = json.load(open(out_p, encoding='utf-8'))
    except ValueError as x:
        return None, ['output is not valid JSON (still being written?): %s' % x]
    probs, good = [], {}
    if len(out) != len(src):
        probs.append('row count %d != %d' % (len(out), len(src)))
    by_key = {r.get('key'): r for r in out}
    for r in src:
        o = by_key.get(r['key'])
        if o is None:
            probs.append('%s: missing' % r['key'])
            continue
        if o.get('jp') != r['jp'] or o.get('kind') != r['kind']:
            probs.append('%s: jp/kind changed' % r['key'])
            continue
        # keep a leading/trailing line break when the source has one (banners start with '\n{0E}')
        en = o.get('en') or ''
        if not r['jp'].startswith('\n'):
            en = en.lstrip('\n')
        if not r['jp'].endswith('\n'):
            en = en.rstrip('\n')
        if '\\n' in en and '\\n' not in r['jp']:
            probs.append('%s: literal backslash-n (use a real line break)' % r['key'])
            continue
        if not en.strip():
            probs.append('%s: empty' % r['key'])
            continue
        if CODE.findall(en) != CODE.findall(r['jp']):
            probs.append('%s: control codes differ' % r['key'])
            continue
        # ASCII only, except box-drawing characters (U+2500-257F): they are in Shift-JIS and the game's
        # full-width font draws them (used for the fake glyph script in slice 017).
        if any((ord(c) > 0x7e and not 0x2500 <= ord(c) <= 0x257f) or (ord(c) < 0x20 and c != '\n')
               for c in en):
            probs.append('%s: non-ASCII' % r['key'])
            continue
        good[r['key']] = (en, o.get('note'))
    return (src, good), probs


def main():
    apply = '--apply' in sys.argv
    for a in [x for x in sys.argv[1:] if not x.startswith('--')]:
        n = int(a)
        res, probs = check(n)
        if res is None:
            print('slice %03d: %s' % (n, probs[0]))
            continue
        src, good = res
        print('slice %03d: %d/%d rows clean, %d problems' % (n, len(good), len(src), len(probs)))
        for p in probs[:10]:
            print('   ', p)
        if apply:
            for r in src:
                if r['key'] in good:
                    r['en'], note = good[r['key']]
                    if note:
                        r['note'] = note
            json.dump(src, open(os.path.join(DIR, 'slice_%03d.json' % n), 'w', encoding='utf-8'),
                      ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
