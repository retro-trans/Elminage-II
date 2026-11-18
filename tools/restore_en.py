"""Copy the English from the committed *.en.json files into the working files the extract tools write.

    python tools/extract_scp.py; python tools/extract_csv.py; python tools/extract_eboot.py
    python tools/restore_en.py            # work/translation/**/X.en.json -> X.json ('en', 'status', 'note')

The repository holds only the *.en.json copies (tools/strip_jp.py: ids and English, no Japanese). The
extract tools read your own disc and write X.json with the Japanese and empty English; this fills the
English back in by id. Rows whose id is missing from X.json are reported (different disc or tool version).
"""
import glob
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TR = os.path.join(ROOT, 'work', 'translation')


def main():
    for en_path in sorted(glob.glob(os.path.join(TR, '**', '*.en.json'), recursive=True)):
        if os.sep + 'snapshots' + os.sep in en_path:
            continue
        path = en_path[:-len('.en.json')] + '.json'
        if not os.path.exists(path):
            continue
        en = json.load(open(en_path, encoding='utf-8'))
        work = json.load(open(path, encoding='utf-8'))
        if not (isinstance(en, list) and isinstance(work, list)):
            continue
        by_id = {e['id']: e for e in work if isinstance(e, dict) and 'id' in e}
        n = missing = 0
        for e in en:
            if not isinstance(e, dict) or 'id' not in e:
                continue
            w = by_id.get(e['id'])
            if w is None:
                missing += 1
                continue
            for k in ('en', 'status', 'note'):
                if k in e:
                    w[k] = e[k]
            n += bool(e.get('en'))
        json.dump(work, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('%-60s %6d English%s' % (os.path.relpath(path, ROOT), n,
                                        ', %d ids not found' % missing if missing else ''))


if __name__ == '__main__':
    main()
