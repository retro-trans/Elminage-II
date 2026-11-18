"""Translation slices for the script (BASE_RULES: 80 consecutive rows per agent).

The 20 SCD files share most of their text (common dungeon scripts are copied into every file), so
rows are de-duplicated by (kind, jp) in file order: SCDWMAP first (town / story hub), then SCD01..19.
Each unique row keeps the context of its first occurrence (sub-script, speaker, neighbours).

    python tools/slices.py make            # work/translation/en/slices/slice_NNN.json (keeps existing en)
    python tools/slices.py merge [--dry]   # slice 'en' -> every matching row in work/translation/en/scp/*.json
    python tools/slices.py stats

Slice row: {key, kind, speaker, sub, jp, en, note?}. key = "<file>:<row index>" of the first occurrence.
"""
import glob
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SCP = os.path.join(ROOT, 'work', 'translation', 'en', 'scp')
OUT = os.path.join(ROOT, 'work', 'translation', 'en', 'slices')
SIZE = 80
ORDER = ['SCDWMAP'] + ['SCD%02d' % i for i in range(1, 20)]
SKIP_SUBS = ('0010', '99999-TEST')   # developer test scripts 00101-00108 (debug menus) and 99999: never shown to players


def load_scp():
    out = {}
    for f in ORDER:
        out[f] = json.load(open(os.path.join(SCP, f + '.json'), encoding='utf-8'))
    return out


def unique_rows(scp):
    seen = {}
    rows = []
    for f in ORDER:
        for i, r in enumerate(scp[f]):
            if r['id'].startswith(SKIP_SUBS):
                continue
            k = (r['kind'], r['jp'])
            if k in seen:
                continue
            seen[k] = len(rows)
            rows.append(dict(key='%s:%d' % (f, i), kind=r['kind'], speaker=r.get('speaker', ''),
                             sub=r['id'].split('@')[0], jp=r['jp'], en=r.get('en', '')))
    return rows


def make():
    scp = load_scp()
    rows = unique_rows(scp)
    os.makedirs(OUT, exist_ok=True)
    old = {}
    for p in glob.glob(os.path.join(OUT, 'slice_*.json')):
        if p.endswith('.en.json'):
            continue
        for r in json.load(open(p, encoding='utf-8')):
            if r.get('en'):
                old[(r['kind'], r['jp'])] = r
    for r in rows:
        o = old.get((r['kind'], r['jp']))
        if o:
            r['en'] = o['en']
            if o.get('note'):
                r['note'] = o['note']
    n = 0
    for s in range(0, len(rows), SIZE):
        json.dump(rows[s:s + SIZE], open(os.path.join(OUT, 'slice_%03d.json' % (s // SIZE)), 'w',
                                          encoding='utf-8'), ensure_ascii=False, indent=1)
        n += 1
    print('%d unique rows -> %d slices of %d' % (len(rows), n, SIZE))


def merge(dry=False):
    tr = {}
    for p in sorted(glob.glob(os.path.join(OUT, 'slice_*.json'))):
        if p.endswith('.en.json') or '.out.' in p:
            continue
        for r in json.load(open(p, encoding='utf-8')):
            if (r.get('en') or '').strip():
                tr[(r['kind'], r['jp'])] = r['en']
    scp = load_scp()
    changed = 0
    for f, rows in scp.items():
        c = 0
        for r in rows:
            en = tr.get((r['kind'], r['jp']))
            if en is not None and r.get('en') != en:
                r['en'] = en
                c += 1
        changed += c
        if c and not dry:
            json.dump(rows, open(os.path.join(SCP, f + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('%s %d script rows from %d translated unique rows' % ('would set' if dry else 'set', changed, len(tr)))


def stats():
    rows = unique_rows(load_scp())
    done = sum(1 for r in rows if (r['en'] or '').strip())
    print('unique rows %d, translated %d, chars %d' % (len(rows), done, sum(len(r['jp']) for r in rows)))


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'stats'
    if cmd == 'make':
        make()
    elif cmd == 'merge':
        merge('--dry' in sys.argv)
    else:
        stats()
