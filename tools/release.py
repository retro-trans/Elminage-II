"""Package a release: xdelta patch(es), README/CHANGELOG text, build manifest, validation record, checksums.

    python tools/release.py 0.8.0                 # full patch against the Japanese ISO
    python tools/release.py 0.8.1 --from 0.8.0    # plus an upgrade patch from the published 0.8.0 image

Input:  work/output/Elminage II (EN) v<ver>.iso (tools/build.py), the Japanese ISO in the project folder,
        for --from the old image (work/output/... .iso, or rebuilt from work/output/patches/<name>.xdelta).
Output: work/release/v<ver>/ (Elminage2-English-v<ver>.xdelta, README-v<ver>.txt, CHANGELOG-v<ver>.txt,
        BUILD-MANIFEST.json, VALIDATION.json, SHA1SUMS-v<ver>.txt, SHA256SUMS-v<ver>.txt, SHA256SUMS.txt).
Every patch is decoded again from its exact source image and must match the target size and SHA-256.
The release notes (GitHub body) are written by hand; the text files carry the hashes and instructions.
"""
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prune_outputs import XDELTA, ORIG_ISO, WINDOW, PATCHES

OUT = os.path.join(ROOT, 'work', 'output')
JP_NAME = 'Elminage II - Sousei no Megami to Unmei no Daichi (Japan).iso'
DISC_ID = 'ULJM-05488'
REPO = 'https://github.com/retro-trans/Elminage-II'
DISCORD = 'https://discord.gg/nZBZfTDfCP'


def digest(path, algo):
    h = hashlib.new(algo)
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def built_iso(ver):
    return os.path.join(OUT, 'Elminage II (EN) v%s.iso' % ver)


def old_image(ver, tmp):
    p = built_iso(ver)
    if os.path.exists(p):
        return p
    patch = os.path.join(PATCHES, 'Elminage II (EN) v%s.xdelta' % ver)
    subprocess.run([XDELTA, '-d', '-f', '-B', WINDOW, '-s', ORIG_ISO, patch, tmp], check=True)
    return tmp


def make_patch(src, dst, patch, check):
    subprocess.run([XDELTA, '-e', '-f', '-9', '-B', WINDOW, '-s', src, dst, patch], check=True)
    subprocess.run([XDELTA, '-d', '-f', '-B', WINDOW, '-s', src, patch, check], check=True)
    ok = os.path.getsize(check) == os.path.getsize(dst) and digest(check, 'sha256') == digest(dst, 'sha256')
    os.remove(check)
    if not ok:
        raise SystemExit('patch does not rebuild the target: ' + patch)


def changelog_section(ver):
    text = open(os.path.join(ROOT, 'CHANGELOG.md'), encoding='utf-8').read()
    m = re.search(r'^## %s .*?(?=^## )' % re.escape(ver), text, re.S | re.M)
    return m.group(0).rstrip() + '\n' if m else ''


def main():
    a = sys.argv[1:]
    ver = a[0]
    prev = a[a.index('--from') + 1] if '--from' in a else None
    rel = os.path.join(ROOT, 'work', 'release', 'v' + ver)
    os.makedirs(rel, exist_ok=True)
    target = built_iso(ver)
    t_sha, t_size = digest(target, 'sha256'), os.path.getsize(target)
    check = os.path.join(rel, 'check.iso')
    jobs = [('Elminage2-English-v%s.xdelta' % ver, ORIG_ISO, 'original')]
    tmp_old = os.path.join(rel, 'old.iso')
    if prev:
        jobs.append(('Elminage2-English-v%s-to-v%s.xdelta' % (prev, ver), old_image(prev, tmp_old), prev))
    patches = []
    for name, src, src_ver in jobs:
        p = os.path.join(rel, name)
        make_patch(src, target, p, check)
        patches.append(dict(patch=name, edition='original', language='en', source_version=src_ver,
                            source_format='iso', target_format='iso',
                            source_sha256=digest(src, 'sha256'), source_bytes=os.path.getsize(src),
                            source_md5=digest(src, 'md5'), source_sha1=digest(src, 'sha1'),
                            target_sha256=t_sha, target_bytes=t_size,
                            patch_sha256=digest(p, 'sha256'), patch_bytes=os.path.getsize(p)))
        print('patch', name, patches[-1]['patch_bytes'], 'bytes, verified')
    if os.path.exists(tmp_old):
        os.remove(tmp_old)
    commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    manifest = dict(game_id='elminage-ii', game_name='Elminage II', platform='PSP', version=ver,
                    source_commit=commit, schema_version=1,
                    patches=[{k: v for k, v in p.items() if k not in ('source_md5', 'source_sha1')} for p in patches],
                    package_ids=[dict(platform='PSP', kind='disc-id', id=DISC_ID)])
    mpath = os.path.join(rel, 'BUILD-MANIFEST.json')
    json.dump(manifest, open(mpath, 'w', encoding='utf-8', newline='\n'), indent=2)
    json.dump(dict(schema_version=1, manifest_sha256=digest(mpath, 'sha256'),
                   patches=[dict(patch=p['patch'], roundtrip_verified=True, target_sha256=t_sha) for p in patches]),
              open(os.path.join(rel, 'VALIDATION.json'), 'w', encoding='utf-8', newline='\n'), indent=2)

    title = 'Elminage II English translation v%s' % ver
    lines = [title, '=' * len(title), '',
             'Game: Elminage II: Sousei no Megami to Unmei no Daichi (PSP, Japan, ULJM05488)', '']
    for p in patches:
        src_desc = ('Source image (your own dump of the Japanese UMD, ISO)' if p['source_version'] == 'original'
                    else 'Source image (the published English v%s image)' % p['source_version'])
        lines += ['Patch: %s (xdelta3 / VCDIFF)' % p['patch'], '', src_desc,
                  '  size    %d bytes' % p['source_bytes'], '  MD5     ' + p['source_md5'],
                  '  SHA-1   ' + p['source_sha1'], '  SHA-256 ' + p['source_sha256'], '']
    lines += ['Patched image (output)', '  size    %d bytes' % t_size, '  SHA-256 ' + t_sha, '',
              'How to apply',
              '  Retro Trans (https://github.com/retro-trans/retro-trans-tools), DeltaPatcher, or xdelta3:',
              '    xdelta3 -d -s "%s" %s "Elminage II English v%s.iso"' % (JP_NAME, patches[0]['patch'], ver)]
    if prev:
        lines += ['  or, from v%s:' % prev,
                  '    xdelta3 -d -s "Elminage II English v%s.iso" %s "Elminage II English v%s.iso"'
                  % (prev, patches[1]['patch'], ver)]
    lines += ['  Keep checksum verification on. A CSO/CHD must be converted back to a plain ISO first.', '',
              'Playing',
              '  - Boot the patched image fresh; emulator save states keep the old executable and scripts.',
              '    In-game saves work.',
              '  - At the start of a new game choose the text font: "Original pixel font" (default) or',
              '    "HD font" (for PPSSPP with a hardware renderer at 2x+ rendering resolution).',
              '  - Do not use the game\'s data install to Memory Stick (disabled by the patch): it would',
              '    load the untranslated archives.',
              '  - Runs on PPSSPP, and on a PSP with custom firmware (the executable is unencrypted).', '',
              'Known limits',
              '  - No human proofreading yet; later chapters are verified by scans of the built files,',
              '    not by play.',
              '  - Character creation: the long class names "Gladiator" and "Summoner" touch the right edge',
              '    of their window.',
              '  - The "RACE" header over the item category column in the shop lists is the original',
              '    game\'s English art.',
              '  - Real PSP hardware not tested.', '',
              'This patch is free. Do not sell it or anything made with it.',
              'Discord: ' + DISCORD, 'Source: ' + REPO, '']
    open(os.path.join(rel, 'README-v%s.txt' % ver), 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
    head = 'Elminage II English v%s - changes\n\n' % ver
    open(os.path.join(rel, 'CHANGELOG-v%s.txt' % ver), 'w', encoding='utf-8', newline='\n').write(
        head + changelog_section(ver))

    names = sorted(f for f in os.listdir(rel) if not f.startswith('SHA') and not f.endswith('.md'))
    main_files = [f for f in names if f.endswith('.xdelta') or f in ('BUILD-MANIFEST.json', 'VALIDATION.json')]
    open(os.path.join(rel, 'SHA256SUMS.txt'), 'w', newline='\n').write(
        ''.join('%s  %s\n' % (digest(os.path.join(rel, f), 'sha256'), f) for f in main_files))
    every = names + ['SHA256SUMS.txt']
    open(os.path.join(rel, 'SHA256SUMS-v%s.txt' % ver), 'w', newline='\n').write(
        ''.join('%s  %s\n' % (digest(os.path.join(rel, f), 'sha256'), f) for f in every))
    open(os.path.join(rel, 'SHA1SUMS-v%s.txt' % ver), 'w', newline='\n').write(
        ''.join('%s  %s\n' % (digest(os.path.join(rel, f), 'sha1'), f) for f in every))
    print('release files in', rel)
    for f in sorted(os.listdir(rel)):
        print('  %-48s %10d' % (f, os.path.getsize(os.path.join(rel, f))))


if __name__ == '__main__':
    main()
