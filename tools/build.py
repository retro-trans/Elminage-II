"""Build the patched ISO.

    python tools/build.py 0.1.0 [--notext] [--novwf]

Output: work/output/Elminage II (EN) v<ver>.iso  (+ work/output/current.iso hard link for the emulator)
Older versions are kept only as verified xdelta patches (tools/prune_outputs.py), max 10.
"""
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iso_patch
import mps2
from eboot import Eboot

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ORIG_ISO = os.path.join(ROOT, 'Elminage II - Sousei no Megami to Unmei no Daichi (Japan).iso')
DISC = os.path.join(ROOT, 'work', 'source', 'disc')
OUT = os.path.join(ROOT, 'work', 'output')
BUILD = os.path.join(ROOT, 'work', 'build')


def build(ver, opts):
    t0 = time.time()
    os.makedirs(BUILD, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    repl = {}
    eb = Eboot()
    import patches
    info = patches.apply_all(eb, opts)
    eb_path = os.path.join(BUILD, 'EBOOT.BIN')
    eb.save(eb_path)
    repl['PSP_GAME/SYSDIR/EBOOT.BIN'] = eb_path
    for arc, files in info.get('archives', {}).items():
        d = os.path.join(BUILD, 'arc_' + arc)
        if os.path.isdir(d):
            shutil.rmtree(d)
        os.makedirs(d)
        for name, data in files.items():
            open(os.path.join(d, name), 'wb').write(data)
        out = os.path.join(BUILD, arc + '.BIN')
        mps2.build(os.path.join(DISC, 'USRDIR_%s.BIN' % arc), d, out)
        repl['PSP_GAME/USRDIR/%s.BIN' % arc] = out
    if 'nomovie' not in opts:          # subtitled opening movies (tools/movie_sub.py, same size, in place)
        import movie_sub
        for path, f in movie_sub.built_movies().items():
            repl[path] = f
    import sfo                          # PSP home-menu title (PARAM.SFO TITLE, in place)
    repl['PSP_GAME/PARAM.SFO'] = sfo.title(os.path.join(BUILD, 'PARAM.SFO'))
    iso = os.path.join(OUT, 'Elminage II (EN) v%s.iso' % ver)
    import ppsspp_dbg
    ppsspp_dbg.stop_emulator()          # it keeps current.iso open
    iso_patch.patch(ORIG_ISO, iso, repl)
    cur = os.path.join(OUT, 'current.iso')
    if os.path.exists(cur):
        os.remove(cur)
    try:
        os.link(iso, cur)
    except OSError:
        shutil.copyfile(iso, cur)
    print('built', iso, 'in %.1fs' % (time.time() - t0))
    import prune_outputs
    prune_outputs.main(iso)
    return iso


if __name__ == '__main__':
    ver = sys.argv[1] if len(sys.argv) > 1 else '0.0.0'
    build(ver, set(a.lstrip('-') for a in sys.argv[2:]))
