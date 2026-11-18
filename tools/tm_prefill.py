"""Prefill CSV cells and EBOOT strings from the Elminage III translation (identical Japanese only).

    python tools/tm_prefill.py          # dry run: counts + a sample written to the scratch report
    python tools/tm_prefill.py --apply  # write en + status into work/translation/en/csv/*.json, eboot.json

Rules
- Only cells the game keeps (csv 'used') and EBOOT strings with code refs or data pointers.
- en = Elminage III English when its Japanese is identical; status 'elm3' (reviewers check these).
- Never touched: compare keys the program strncmp()s against data (NEVER_JP / NEVER_EB).
- Fixed EBOOT keys that must equal script text (FIXED).
- One English per Japanese across CSV and EBOOT (status 'shared'): compare keys such as the spell
  target types (敵全体 ...) are strcmp()ed between EBOOT strings and CSV cells, so both sides must match.
Existing en values are kept.
"""
import glob
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CSV = os.path.join(ROOT, 'work', 'translation', 'en', 'csv')
EB = os.path.join(ROOT, 'work', 'translation', 'en', 'eboot.json')
E3 = os.path.join(ROOT, '..', 'Elminage III', 'work', 'translation', 'en')

NEVER_JP = {'○', '●', '当人'}          # EMPLOY permission marks (strncmp 0x088DAE3C / 0x088DB024), 当人 (0x088DBAF0)
NEVER_EB = {'eb@0895e89c', 'eb@0895e8b4', 'eb@0895e990'}
FIXED = {'eb@08956c00': 'Above the clouds'}   # strncmp with the script line, length patched (patches.text_checks)


def load_tm():
    tm = {}
    for f in glob.glob(os.path.join(E3, '**', '*.json'), recursive=True):
        if f.endswith('.en.json'):
            continue
        try:
            d = json.load(open(f, encoding='utf-8'))
        except Exception:
            continue
        if isinstance(d, dict):
            d = list(d.values())
        for r in d:
            if isinstance(r, dict) and r.get('jp') and (r.get('en') or '').strip():
                tm.setdefault(r['jp'], r['en'])
    return tm


def main(apply):
    tm = load_tm()
    files = {p: json.load(open(p, encoding='utf-8')) for p in sorted(glob.glob(os.path.join(CSV, '*.json')))}
    eb = json.load(open(EB, encoding='utf-8'))
    rows = [(p, r) for p, d in files.items() for r in d if r.get('used')]
    rows += [(EB, r) for r in eb if r.get('refs') or r.get('ptrs')]
    stats = {'elm3': 0, 'shared': 0, 'fixed': 0, 'never': 0, 'kept': 0}
    sample = []
    for p, r in rows:
        if r['jp'] in NEVER_JP or r.get('id') in NEVER_EB:
            r['status'] = 'never'
            stats['never'] += 1
            continue
        if r.get('id') in FIXED:
            r['en'], r['status'] = FIXED[r['id']], 'fixed'
            stats['fixed'] += 1
            continue
        if (r.get('en') or '').strip():
            stats['kept'] += 1
            continue
        if r['jp'] in tm:
            r['en'], r['status'] = tm[r['jp']], 'elm3'
            stats['elm3'] += 1
            if len(sample) < 40:
                sample.append((r['id'], r['en']))
    # one English per Japanese
    m = {}
    for p, r in rows:
        if (r.get('en') or '').strip() and r.get('status') != 'never':
            m.setdefault(r['jp'], r['en'])
    for p, r in rows:
        if not (r.get('en') or '').strip() and r.get('status') != 'never' and r['jp'] in m:
            r['en'], r['status'] = m[r['jp']], 'shared'
            stats['shared'] += 1
    todo = {r['jp'] for p, r in rows if not (r.get('en') or '').strip() and r.get('status') != 'never'}
    print('rows', len(rows), stats, 'unique untranslated', len(todo), 'chars', sum(len(j) for j in todo))
    rep = os.path.join(ROOT, 'work', 'translation', 'en', 'tm_prefill_sample.json')
    json.dump(sample, open(rep, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if apply:
        for p, d in files.items():
            json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        json.dump(eb, open(EB, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('written')


if __name__ == '__main__':
    main('--apply' in sys.argv)
