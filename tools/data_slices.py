"""Translation slices for CSV cells and EBOOT strings that are still Japanese.

    python tools/data_slices.py make     # work/translation/en/data_slices/dslice_NNN.json
    python tools/data_slices.py merge    # slice en -> every matching csv/eboot entry (one English per Japanese)

Slice row: {key (first id), ids (all ids with this Japanese), src (FILE:col or EBOOT), header, row_name,
            neighbours, max (byte budget, CSV only), jp, en}
- header: the column's header cell (row 0) when it is text; row_name: the English (or Japanese) of the
  first text cell in the same CSV row, e.g. the item or monster the cell belongs to.
- neighbours: for EBOOT strings, the strings stored right before and after (English when known).
Rows are grouped by source so each slice is one table or one stretch of the EBOOT.
"""
import collections
import glob
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CSV = os.path.join(ROOT, 'work', 'translation', 'en', 'csv')
EB = os.path.join(ROOT, 'work', 'translation', 'en', 'eboot.json')
OUT = os.path.join(ROOT, 'work', 'translation', 'en', 'data_slices')
SIZE = 80


def load():
    files = {p: json.load(open(p, encoding='utf-8')) for p in sorted(glob.glob(os.path.join(CSV, '*.json')))}
    eb = json.load(open(EB, encoding='utf-8'))
    return files, eb


def make():
    files, eb = load()
    groups = collections.OrderedDict()
    for p, d in files.items():
        cells = {tuple(map(int, r['id'].split(':')[1:])): r for r in d}
        for r in d:
            if not r.get('used') or r.get('status') == 'never' or (r.get('en') or '').strip():
                continue
            f, row, col = r['id'].split(':')
            row, col = int(row), int(col)
            head = cells.get((0, col))
            name = None
            for c in range(0, col):
                x = cells.get((row, c))
                if x:
                    name = x.get('en') or x['jp']
                    break
            g = groups.setdefault(r['jp'], dict(key=r['id'], ids=[], src='%s:%d' % (f, col),
                                                 header=(head['en'] or head['jp']) if head else '',
                                                 row_name=name or '', max=r['max'], jp=r['jp'], en=''))
            g['ids'].append(r['id'])
            g['max'] = min(g['max'], r['max'])
    ebl = [x for x in eb]
    for i, r in enumerate(ebl):
        if not (r.get('refs') or r.get('ptrs')) or r.get('status') == 'never' or (r.get('en') or '').strip():
            continue
        nb = [(x.get('en') or x['jp']) for x in ebl[max(0, i - 2):i] + ebl[i + 1:i + 3]]
        g = groups.setdefault(r['jp'], dict(key=r['id'], ids=[], src='EBOOT', header='', row_name='',
                                             neighbours=nb, max=None, jp=r['jp'], en=''))
        g['ids'].append(r['id'])
    rows = list(groups.values())
    os.makedirs(OUT, exist_ok=True)
    for s in range(0, len(rows), SIZE):
        json.dump(rows[s:s + SIZE], open(os.path.join(OUT, 'dslice_%03d.json' % (s // SIZE)), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
    by = collections.Counter(r['src'].split(':')[0] for r in rows)
    print(len(rows), 'unique strings ->', (len(rows) + SIZE - 1) // SIZE, 'slices;', by.most_common())


def merge():
    tr = {}
    for p in sorted(glob.glob(os.path.join(OUT, 'dslice_*.json'))):
        if '.out.' in p:
            continue
        for r in json.load(open(p, encoding='utf-8')):
            if (r.get('en') or '').strip():
                tr[r['jp']] = r['en']
    files, eb = load()
    n = 0
    for p, d in files.items():
        ch = False
        for r in d:
            if r.get('used') and r.get('status') != 'never' and r['jp'] in tr and r.get('en') != tr[r['jp']] \
                    and r.get('status') not in ('elm3', 'fixed'):
                r['en'], r['status'] = tr[r['jp']], 'new'
                n += 1
                ch = True
        if ch:
            json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for r in eb:
        if r.get('status') != 'never' and r['jp'] in tr and r.get('en') != tr[r['jp']] \
                and r.get('status') not in ('elm3', 'fixed'):
            r['en'], r['status'] = tr[r['jp']], 'new'
            n += 1
    json.dump(eb, open(EB, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('set', n, 'entries from', len(tr), 'translated strings')


if __name__ == '__main__':
    make() if sys.argv[1:] == ['make'] else merge()
