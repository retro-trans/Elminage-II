"""EBOOT UI strings missed by the first pass (0.1.12): the old 'glyph pool' range minus the real name-entry
character cells, plus text-like strings the reference scan did not find (confirmation prompts etc.).

    python tools/eboot_slices.py reclass          # eboot.json: 'never' only for the name-entry cells
    python tools/eboot_slices.py make             # work/translation/en/eboot_slices/eslice_NNN.json
    python tools/eboot_slices.py check N... [--snap STAGE]   # validate eslice_NNN.json (or vs a snapshot)
    python tools/eboot_slices.py snap STAGE
    python tools/eboot_slices.py merge [--dry]    # eslice en -> eboot.json (only the listed ids)

Row: {key, ids, refs (code refs + data pointers, summed over ids), len (smallest slot, bytes incl. NUL),
      neighbours, jp, en, note}
Placement (tools/eboot_text.py): English that fits the slot is written in place; longer English moves to the
cave only when the string has references. Rows with refs == 0 must fit: len(en bytes) + 1 <= len.
"""
import glob
import json
import os
import re
import shutil
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
EN = os.path.join(ROOT, 'work', 'translation', 'en')
EB = os.path.join(EN, 'eboot.json')
CSV = os.path.join(EN, 'csv')
OUT = os.path.join(EN, 'eboot_slices')
SIZE = 80
POOL = (0x08958D7C, 0x089613BC)          # old 'never' range
NAME_CELLS = (0x08958D7C, 0x08958F80)    # the real name-entry character cells (single characters)
RODATA_END = 0x08962000                  # above this, 'strings' are binary data
JP = re.compile(r'[぀-ヿ一-鿿]')
KANA = re.compile(r'[぀-ヿ]')
PH = re.compile(r'%[-+ #0]*\d*(?:\.\d+)?[hlL]?[diouxXcsfeEgG%]')
CODE = re.compile(r'\{[^}]*\}')


def addr(x):
    return int(x['id'][3:], 16)


def texty(s):
    ok = sum(1 for c in s if JP.match(c) or c in '　、。！？「」『』（）：・ー～％\n' or 0xff00 <= ord(c) <= 0xffef
             or 32 <= ord(c) < 127)
    return ok == len(s) and (KANA.search(s) or len(re.findall(r'[一-鿿]', s)) >= 2)


def reclass():
    e = json.load(open(EB, encoding='utf-8'))
    n = 0
    for x in e:
        a = addr(x)
        if x.get('status') == 'never' and POOL[0] <= a < POOL[1] and not (NAME_CELLS[0] <= a < NAME_CELLS[1]):
            x['status'] = None
            x['note'] = 'reclassified 0.1.12: UI string (name-entry cells are only 0x08958D7C-0x08958F7F)'
            n += 1
    json.dump(e, open(EB, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('reclassified', n)


def wanted(x):
    if (x.get('en') or '').strip() or x.get('status') == 'never' or not JP.search(x['jp']):
        return False
    a = addr(x)
    if POOL[0] <= a < POOL[1]:
        return True
    return a < RODATA_END and not (x.get('refs') or x.get('ptrs')) and texty(x['jp'])


def make():
    e = sorted(json.load(open(EB, encoding='utf-8')), key=addr)
    tm = {}
    for p in glob.glob(os.path.join(CSV, '*.json')):
        for x in json.load(open(p, encoding='utf-8')):
            if x.get('en'):
                tm.setdefault(x['jp'], x['en'])
    for x in e:
        if x.get('en'):
            tm.setdefault(x['jp'], x['en'])
    groups = {}
    order = []
    for i, x in enumerate(e):
        if not wanted(x):
            continue
        g = groups.get(x['jp'])
        if g is None:
            nb = [(y.get('en') or y['jp']) for y in e[max(0, i - 2):i] + e[i + 1:i + 3]]
            g = groups[x['jp']] = dict(key=x['id'], ids=[], refs=0, len=x.get('len', 0), neighbours=nb,
                                       jp=x['jp'], en=tm.get(x['jp'], ''))
            if g['en']:
                g['note'] = 'prefilled from the existing English for the same Japanese'
            order.append(g)
        g['ids'].append(x['id'])
        g['refs'] += (x.get('refs') or 0) + (x.get('ptrs') or 0)
        g['len'] = min(g['len'], x.get('len', 0))
    os.makedirs(OUT, exist_ok=True)
    for old in glob.glob(os.path.join(OUT, 'eslice_*.json')):
        os.remove(old)
    for s in range(0, len(order), SIZE):
        json.dump(order[s:s + SIZE], open(os.path.join(OUT, 'eslice_%03d.json' % (s // SIZE)), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
    print('%d strings (%d ids, %d prefilled) -> %d slices' % (len(order), sum(len(g['ids']) for g in order),
                                                            sum(1 for g in order if g['en']),
                                                            (len(order) + SIZE - 1) // SIZE))


def slices():
    return sorted(glob.glob(os.path.join(OUT, 'eslice_[0-9][0-9][0-9].json')))


def ok_chars(s):
    return all((32 <= ord(c) < 127) or c == '\n' for c in s)


def check_row(r, old=None):
    en = r.get('en') or ''
    p = []
    if old is not None and (old['jp'] != r['jp'] or old['ids'] != r['ids']):
        return ['jp/ids changed']
    if not en.strip():
        return ['empty']
    if CODE.findall(en) != CODE.findall(r['jp']):
        p.append('{..} codes differ')
    if sorted(x for x in PH.findall(en) if x != '%%') != sorted(PH.findall(r['jp'])):   # %% = literal %
        p.append('placeholders %s -> %s' % (PH.findall(r['jp']), PH.findall(en)))
    if r['jp'].endswith('\n') != en.endswith('\n') or r['jp'].startswith('\n') != en.startswith('\n'):
        p.append('leading/trailing line break differs from jp')
    if '\\n' in en and '\\n' not in r['jp']:
        p.append('literal backslash-n')
    if not ok_chars(en):
        p.append('non-ASCII')
    if not r['refs'] and len(en.encode('ascii', 'replace')) + 1 > r['len']:
        p.append('no references: %d bytes + NUL > slot %d' % (len(en), r['len']))
    return p


def check(ns, stage=None):
    tot = 0
    for p in slices():
        n = int(os.path.basename(p)[7:10])
        if ns and n not in ns:
            continue
        try:
            cur = json.load(open(p, encoding='utf-8'))
        except ValueError as x:
            print('BAD eslice %03d: invalid JSON %s' % (n, x))
            continue
        old = json.load(open(os.path.join(OUT, 'snapshots', stage, os.path.basename(p)), encoding='utf-8')) \
            if stage else [None] * len(cur)
        if stage and [r['key'] for r in cur] != [r['key'] for r in old]:
            print('BAD eslice %03d: keys/order changed' % n)
            continue
        probs, ed = [], 0
        for a, r in zip(old, cur):
            if a is not None and (a.get('en') or '') != (r.get('en') or ''):
                ed += 1
            for q in check_row(r, a):
                probs.append('%s: %s' % (r['key'], q))
        tot += ed
        print('%s eslice %03d: %d rows, %d edited, %d problems' % ('OK ' if not probs else 'BAD', n, len(cur), ed,
                                                                 len(probs)))
        for q in probs[:6]:
            print('     ', q)
    if stage:
        print('total edited rows', tot)


def snap(stage):
    d = os.path.join(OUT, 'snapshots', stage)
    os.makedirs(d, exist_ok=True)
    for p in slices():
        shutil.copyfile(p, os.path.join(d, os.path.basename(p)))
    print('snapshot', stage, len(slices()))


def merge(dry):
    want = {}
    for p in slices():
        for r in json.load(open(p, encoding='utf-8')):
            if (r.get('en') or '').strip() and not check_row(r):
                for i in r['ids']:
                    want[i] = r['en']
    e = json.load(open(EB, encoding='utf-8'))
    n = 0
    for x in e:
        if x['id'] in want and x.get('en') != want[x['id']]:
            x['en'] = want[x['id']]
            x['status'] = 'new'
            n += 1
    if not dry:
        json.dump(e, open(EB, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('%s %d eboot strings' % ('would set' if dry else 'set', n))


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'reclass':
        reclass()
    elif a[0] == 'make':
        make()
    elif a[0] == 'check':
        st = a[a.index('--snap') + 1] if '--snap' in a else None
        check([int(x) for x in a[1:] if x.isdigit()], st)
    elif a[0] == 'snap':
        snap(a[1])
    elif a[0] == 'merge':
        merge('--dry' in a)
