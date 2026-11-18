"""Check translator output for data slices (CSV cells / EBOOT strings) and take it in.

    python tools/dslice_in.py 0 1 2          # dry run
    python tools/dslice_in.py --apply 0 1 2  # write en/note of clean rows into dslice_NNN.json

Per row of dslice_NNN.out.json against dslice_NNN.json: same key/jp; {..} codes identical and in order;
printf placeholders kept (same multiset; order may change only with %1$-style args, so order is reported);
ASCII (box-drawing and the marks listed in docs/data_brief.md allowed); CSV rows within `max` bytes
(cp932, after the csv_build comma/quote escaping counts 1 byte each); not empty.
"""
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DIR = os.path.join(ROOT, 'work', 'translation', 'en', 'data_slices')
CODE = re.compile(r'\{[^}]*\}')
PH = re.compile(r'%[-+ #0]*\d*(?:\.\d+)?[hlL]?[diouxXcsfeEgG%]')
MARKS = set('★☆◆◇○●※→←↑↓■□△▲▽▼')


_CSVMAX = None


def col_max(r):
    """Largest byte budget among the CSV cells this row serves (None for EBOOT rows)."""
    global _CSVMAX
    if r.get('src') == 'EBOOT':
        return None
    if _CSVMAX is None:
        _CSVMAX = {}
        import glob
        for p in glob.glob(os.path.join(ROOT, 'work', 'translation', 'en', 'csv', '*.json')):
            for x in json.load(open(p, encoding='utf-8')):
                _CSVMAX[x['id']] = x['max']
    return max((_CSVMAX.get(i, 0) for i in r.get('ids', [r['key']])), default=r.get('max'))


def ok_chars(s):
    return all((32 <= ord(c) < 127) or c == '\n' or c in MARKS or 0x2500 <= ord(c) <= 0x257f for c in s)


def check(n):
    sp = os.path.join(DIR, 'dslice_%03d.json' % n)
    op = os.path.join(DIR, 'dslice_%03d.out.json' % n)
    if not os.path.exists(op):
        return None, ['no output yet']
    try:
        out = json.load(open(op, encoding='utf-8'))
    except ValueError as x:
        return None, ['not valid JSON yet: %s' % x]
    src = json.load(open(sp, encoding='utf-8'))
    by = {r.get('key'): r for r in out}
    good, probs, notes = {}, [], []
    for r in src:
        o = by.get(r['key'])
        if o is None or o.get('jp') != r['jp']:
            probs.append('%s: missing or jp changed' % r['key'])
            continue
        # keep a leading/trailing line break when the source has one
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
            probs.append('%s: {..} codes differ' % r['key'])
            continue
        pj, pe = PH.findall(r['jp']), PH.findall(en)
        if sorted(pj) != sorted(pe):
            probs.append('%s: placeholders %s -> %s' % (r['key'], pj, pe))
            continue
        if pj != pe:
            notes.append('%s: placeholder order changed %s -> %s' % (r['key'], pj, pe))
        if not ok_chars(en):
            probs.append('%s: non-ASCII' % r['key'])
            continue
        nb = len(en.replace('\n', ' ').encode('cp932', 'replace'))
        cap = col_max(r)
        if cap and nb > cap:
            probs.append('%s: %d bytes > largest column max %d' % (r['key'], nb, cap))
            continue
        if r.get('max') and nb > r['max']:
            notes.append('%s: %d bytes fits only some columns (smallest max %d); csv_build skips the others'
                         % (r['key'], nb, r['max']))
        good[r['key']] = (en, o.get('note'))
    return (src, good, notes), probs


def main():
    apply = '--apply' in sys.argv
    for a in [x for x in sys.argv[1:] if not x.startswith('--')]:
        n = int(a)
        res, probs = check(n)
        if res is None:
            print('dslice %03d: %s' % (n, probs[0]))
            continue
        src, good, notes = res
        print('dslice %03d: %d/%d clean, %d problems%s' % (n, len(good), len(src), len(probs),
                                                         (', %d notes' % len(notes)) if notes else ''))
        for p in probs[:8] + notes[:4]:
            print('   ', p)
        if apply:
            for r in src:
                if r['key'] in good:
                    r['en'], note = good[r['key']]
                    if note:
                        r['note'] = note
            json.dump(src, open(os.path.join(DIR, 'dslice_%03d.json' % n), 'w', encoding='utf-8'),
                      ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
