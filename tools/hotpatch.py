"""Hot reload of the EBOOT into a running emulator (debug_tools_guide step 6, program part only).

    python tools/hotpatch.py BASE_EBOOT [NEW_EBOOT]

BASE_EBOOT: the EBOOT.BIN of the build the running game / savestate was made with.
NEW_EBOOT:  the new EBOOT.BIN (default: patch a fresh one now, like tools/build.py, without the ISO).
Writes every byte where NEW differs from BASE, except where the running RAM no longer equals BASE
(run-time data: variables, buffers), while the emulator is paused. New bytes past BASE's file size
(code cave growth) are always written.

Cannot update: archives / scripts already loaded, data the game copied into its own structures,
and code already running on a call stack (a hooked function takes effect on its next call).
Keep the cave layout of the old build (append new patches at the end of patches.apply_all) so
the diff stays small.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def segment(path):
    d = open(path, 'rb').read()
    phoff, = struct.unpack_from('<I', d, 0x1c)
    t, off, va, pa, fsz, msz, fl, al = struct.unpack_from('<8I', d, phoff)
    return va, d[off:off + fsz]


def fresh_eboot(path):
    from eboot import Eboot
    import patches
    eb = Eboot()
    patches.apply_all(eb, set())
    eb.save(path)
    return path


def runs(base, new, ram):
    """(offset, bytes) runs to write."""
    import numpy as np
    n = len(new)
    nw = np.frombuffer(new, np.uint8)
    bs = np.zeros(n, np.uint8)
    m = min(n, len(base))
    bs[:m] = np.frombuffer(base, np.uint8)[:m]
    rm = np.frombuffer(bytes(ram[:n]), np.uint8)
    inside = np.arange(n) < len(base)
    want = ((nw != bs) & ((rm == bs) | ~inside)) | (~inside & (rm != nw))
    idx = np.flatnonzero(np.diff(np.concatenate(([0], want.astype(np.int8), [0]))))
    return [(int(a), new[a:b]) for a, b in zip(idx[::2], idx[1::2])]


def main(base_path, new_path=None):
    from ppsspp_dbg import Emu
    if not new_path:
        new_path = os.path.join(ROOT, 'work', 'build', 'EBOOT_hot.BIN')
        fresh_eboot(new_path)
    va, base = segment(base_path)
    va2, new = segment(new_path)
    assert va == va2
    with Emu() as e:
        e.pause()
        ram = e.read(va, len(new))
        rs = runs(base, new, ram)
        import numpy as np
        m = min(len(base), len(new))
        a, b, r = (np.frombuffer(x[:m], np.uint8) for x in (bytes(new), bytes(base), bytes(ram)))
        skipped = int(((a != b) & (r != b)).sum())
        for off, data in rs:
            e.write(va + off, bytes(data))
        e.resume()
    print('wrote %d runs, %d bytes; skipped %d changed bytes that differ in RAM (run-time data)'
          % (len(rs), sum(len(d) for _, d in rs), skipped))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
