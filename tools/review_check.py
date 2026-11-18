"""Check a review stage's in-place edits of the script slices against the stage snapshot.

    python tools/review_check.py pre_accuracy 0 1 2      # compare slices with review_snapshots/pre_accuracy
    python tools/review_check.py pre_accuracy --all

Per slice: row count / keys / jp / kind unchanged; every row's {..} codes equal the source's; English is
ASCII (box-drawing allowed for the Pyroglyph cipher); name rows over 16 characters are listed as warnings.
Prints the number of edited rows. A slice that fails is reported; restore it from the snapshot with
    python tools/review_check.py pre_accuracy --restore N
"""
import json
import os
import re
import shutil
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SL = os.path.join(ROOT, 'work', 'translation', 'en', 'slices')
SNAP = os.path.join(ROOT, 'work', 'translation', 'en', 'review_snapshots')
CODE = re.compile(r'\{[^}]*\}')


def check(stage, n):
    cur_p = os.path.join(SL, 'slice_%03d.json' % n)
    old_p = os.path.join(SNAP, stage, 'slice_%03d.json' % n)
    try:
        cur = json.load(open(cur_p, encoding='utf-8'))
    except ValueError as x:
        return None, ['invalid JSON: %s' % x], []
    old = json.load(open(old_p, encoding='utf-8'))
    probs, warn = [], []
    if [r['key'] for r in cur] != [r['key'] for r in old]:
        probs.append('keys/order changed')
        return None, probs, warn
    edited = 0
    for a, b in zip(old, cur):
        if a['jp'] != b['jp'] or a['kind'] != b['kind']:
            probs.append('%s: jp/kind changed' % b['key'])
            continue
        en = b.get('en') or ''
        if en != a.get('en'):
            edited += 1
        if CODE.findall(en) != CODE.findall(b['jp']):
            probs.append('%s: codes differ' % b['key'])
        if any((ord(c) > 126 and not 0x2500 <= ord(c) <= 0x257f) or (ord(c) < 32 and c != '\n') for c in en):
            probs.append('%s: non-ASCII' % b['key'])
        if b['kind'] == 'name' and len(en) > 16:
            warn.append('%s: name %d chars' % (b['key'], len(en)))
    return edited, probs, warn


def main():
    stage = sys.argv[1]
    args = sys.argv[2:]
    if '--restore' in args:
        n = int(args[args.index('--restore') + 1])
        shutil.copyfile(os.path.join(SNAP, stage, 'slice_%03d.json' % n), os.path.join(SL, 'slice_%03d.json' % n))
        print('restored slice %03d from %s' % (n, stage))
        return
    ns = range(69) if '--all' in args else [int(a) for a in args]
    tot = 0
    for n in ns:
        ed, probs, warn = check(stage, n)
        tot += ed or 0
        flag = 'OK ' if not probs else 'BAD'
        print('%s slice %03d: %s edited, %d problems, %d name warnings' % (flag, n, ed, len(probs), len(warn)))
        for p in probs[:6]:
            print('     ', p)
    print('total edited rows', tot)


if __name__ == '__main__':
    main()
