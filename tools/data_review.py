"""Review slices for the data tables (CSV) and EBOOT strings translated in this project (status 'new' / 'fit').

    python tools/data_review.py make                 # work/translation/en/data_review/rslice_NNN.json (80 rows)
    python tools/data_review.py snap STAGE           # copy the slices to data_review/snapshots/STAGE/
    python tools/data_review.py check STAGE [N...]   # compare slices with the STAGE snapshot (all if no N)
    python tools/data_review.py merge [--dry]        # slice en -> every id in csv/*.json and eboot.json

Rows group cells/strings that share both Japanese and current English (one English per group), so a review
edit lands on every place that text is shown. Elminage III reuse (status 'elm3') is not in these slices.
Row: {key, ids, src, header, row_name, neighbours, max, min_max, jp, en, note}
- max: the largest byte budget among the CSV ids, min_max the smallest; EBOOT rows have none (strings that
  do not fit in place move to the cave).
check (per row): keys/order/jp unchanged; {..} codes and printf placeholders identical (multiset, order
reported); leading/trailing line breaks as in jp; no literal backslash-n; ASCII (+ marks, box drawing); not
empty; the English fits every CSV id that the snapshot English fitted (no new skipped cells).
"""
import collections
import glob
import json
import os
import re
import shutil
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
EN = os.path.join(ROOT, 'work', 'translation', 'en')
CSV = os.path.join(EN, 'csv')
EB = os.path.join(EN, 'eboot.json')
OUT = os.path.join(EN, 'data_review')
SIZE = 80
CODE = re.compile(r'\{[^}]*\}')
PH = re.compile(r'%[-+ #0]*\d*(?:\.\d+)?[hlL]?[diouxXcsfeEgG%]')
MARKS = set('★☆◆◇○●※→←↑↓■□△▲▽▼')


def nbytes(s):
    return len(s.encode('cp932', 'replace'))


def ok_chars(s):
    return all((32 <= ord(c) < 127) or c == '\n' or c in MARKS or 0x2500 <= ord(c) <= 0x257f for c in s)


def load_entries():
    files = {p: json.load(open(p, encoding='utf-8')) for p in sorted(glob.glob(os.path.join(CSV, '*.json')))}
    eb = json.load(open(EB, encoding='utf-8'))
    return files, eb


def meta_index():
    """id -> metadata from the first-pass slices (dslice / fit)."""
    idx = {}
    for p in sorted(glob.glob(os.path.join(EN, 'data_slices', 'dslice_[0-9][0-9][0-9].json')) +
                    glob.glob(os.path.join(EN, 'fit_slices', 'fit_[0-9][0-9][0-9].json'))):
        for r in json.load(open(p, encoding='utf-8')):
            m = {k: r.get(k) for k in ('src', 'header', 'row_name', 'neighbours') if r.get(k)}
            for i in r.get('ids', [r['key']]):
                idx.setdefault(i, m)
    return idx


def make():
    files, eb = load_entries()
    meta = meta_index()
    groups = collections.OrderedDict()
    order = []
    for p, d in files.items():
        for x in d:
            if x.get('status') in ('new', 'fit') and x.get('en'):
                order.append((x['id'], x['jp'], x['en'], x.get('max')))
    for x in eb:
        if x.get('status') in ('new', 'fit') and x.get('en'):
            order.append((x['id'], x['jp'], x['en'], None))
    for i, jp, en, mx in order:
        g = groups.setdefault((jp, en), {'ids': [], 'maxes': []})
        g['ids'].append(i)
        if mx:
            g['maxes'].append(mx)
    rows = []
    for (jp, en), g in groups.items():
        k = g['ids'][0]
        m = meta.get(k, {})
        src = m.get('src') or ('EBOOT' if k.startswith('eb@') else k.rsplit(':', 1)[0])
        r = {'key': k, 'ids': g['ids'], 'src': src, 'header': m.get('header', ''),
             'row_name': m.get('row_name', '')}
        if m.get('neighbours'):
            r['neighbours'] = m['neighbours']
        if g['maxes']:
            r['max'] = max(g['maxes'])
            r['min_max'] = min(g['maxes'])
        r['jp'] = jp
        r['en'] = en
        rows.append(r)
    os.makedirs(OUT, exist_ok=True)
    for old in glob.glob(os.path.join(OUT, 'rslice_*.json')):
        os.remove(old)
    n = 0
    for s in range(0, len(rows), SIZE):
        json.dump(rows[s:s + SIZE], open(os.path.join(OUT, 'rslice_%03d.json' % n), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        n += 1
    print('%d groups (%d ids) in %d slices' % (len(rows), sum(len(r['ids']) for r in rows), n))


def slices():
    return sorted(glob.glob(os.path.join(OUT, 'rslice_[0-9][0-9][0-9].json')))


def snap(stage):
    d = os.path.join(OUT, 'snapshots', stage)
    os.makedirs(d, exist_ok=True)
    for p in slices():
        shutil.copyfile(p, os.path.join(d, os.path.basename(p)))
    print('snapshot %s: %d slices' % (stage, len(slices())))


_MAXES = None


def id_max(i):
    global _MAXES
    if _MAXES is None:
        _MAXES = {}
        for p in glob.glob(os.path.join(CSV, '*.json')):
            for x in json.load(open(p, encoding='utf-8')):
                _MAXES[x['id']] = x.get('max')
    return _MAXES.get(i)


def check_row(a, b):
    """a = snapshot row, b = current row. Returns list of problems."""
    p = []
    if a['jp'] != b['jp'] or a['ids'] != b['ids']:
        return ['jp/ids changed']
    en = b.get('en') or ''
    if not en.strip():
        return ['empty']
    if CODE.findall(en) != CODE.findall(b['jp']):
        p.append('{..} codes differ')
    pj, pe = PH.findall(b['jp']), PH.findall(en)
    if sorted(pj) != sorted(pe):
        p.append('placeholders %s -> %s' % (pj, pe))
    if b['jp'].startswith('\n') != en.startswith('\n') or b['jp'].endswith('\n') != en.endswith('\n'):
        p.append('leading/trailing line break differs from jp')
    if '\\n' in en and '\\n' not in b['jp']:
        p.append('literal backslash-n')
    if not ok_chars(en):
        p.append('non-ASCII')
    nb = nbytes(en.replace('\n', ' '))
    old = a.get('en') or ''
    ob = nbytes(old.replace('\n', ' '))
    for i in b['ids']:
        mx = id_max(i)
        if mx and ob <= mx < nb:
            p.append('%s: %d bytes > max %d (snapshot English fitted)' % (i, nb, mx))
            break
    return p


def check(stage, ns):
    sd = os.path.join(OUT, 'snapshots', stage)
    tot = 0
    for p in slices():
        n = int(os.path.basename(p)[7:10])
        if ns and n not in ns:
            continue
        try:
            cur = json.load(open(p, encoding='utf-8'))
        except ValueError as x:
            print('BAD rslice %03d: invalid JSON %s' % (n, x))
            continue
        old = json.load(open(os.path.join(sd, os.path.basename(p)), encoding='utf-8'))
        if [r['key'] for r in cur] != [r['key'] for r in old]:
            print('BAD rslice %03d: keys/order changed' % n)
            continue
        probs, ed = [], 0
        for a, b in zip(old, cur):
            if (b.get('en') or '') != (a.get('en') or ''):
                ed += 1
            for q in check_row(a, b):
                probs.append('%s: %s' % (b['key'], q))
        tot += ed
        print('%s rslice %03d: %d edited, %d problems' % ('OK ' if not probs else 'BAD', n, ed, len(probs)))
        for q in probs[:6]:
            print('     ', q)
    print('total edited rows', tot)


def merge(dry):
    files, eb = load_entries()
    want = {}
    for p in slices():
        for r in json.load(open(p, encoding='utf-8')):
            for i in r['ids']:
                want[i] = r['en']
    ch = 0
    for p, d in files.items():
        dirty = False
        for x in d:
            if x['id'] in want and x.get('en') != want[x['id']]:
                x['en'] = want[x['id']]
                ch += 1
                dirty = True
        if dirty and not dry:
            json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    dirty = False
    for x in eb:
        if x['id'] in want and x.get('en') != want[x['id']]:
            x['en'] = want[x['id']]
            ch += 1
            dirty = True
    if dirty and not dry:
        json.dump(eb, open(EB, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('%s %d entries' % ('would change' if dry else 'changed', ch))


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'make':
        make()
    elif a[0] == 'snap':
        snap(a[1])
    elif a[0] == 'check':
        check(a[1], [int(x) for x in a[2:]])
    elif a[0] == 'merge':
        merge('--dry' in a)
