"""Find the Elminage II address of code known in Elminage III (same engine, different build).

Both EBOOTs are compiled from closely related sources, so a function keeps its instruction
shape: opcode, registers and small constants match while jal targets, lui/addiu address halves
and branch offsets differ. We compare masked instruction words.

    python tools/port_addr.py 0x0888F074 [0x08897804 ...]     # Elm3 addresses -> Elm2 candidates

Library:
    find(addr3, n=24) -> list of (addr2, score)  best first
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mips import Elf

ELM3_ELF = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'Elminage III',
                        'work', 'source', 'EBOOT.elf')

_e2 = _e3 = None
_words2 = None


def elfs():
    global _e2, _e3, _words2
    if _e2 is None:
        _e2 = Elf()
        _e3 = Elf(ELM3_ELF)
        va, off, fsz, msz = _e2.segs[0]
        _words2 = (va, struct.unpack_from('<%dI' % (fsz // 4), _e2.data, off))
    return _e2, _e3


def mask(w):
    op = w >> 26
    if op in (2, 3):                       # j / jal: keep opcode only
        return w & 0xFC000000
    if op in (4, 5, 6, 7, 0x14, 0x15, 0x16, 0x17) or (op == 1):   # branches: drop offset
        return w & 0xFFFF0000
    if op == 0x0F:                         # lui: drop the immediate
        return w & 0xFFFF0000
    if op in (8, 9, 0x0D, 0x0A, 0x0B, 0x0C, 0x0E, 0x20, 0x21, 0x23, 0x24, 0x25, 0x28, 0x29, 0x2B,
              0x31, 0x39):
        imm = w & 0xFFFF
        # keep small struct offsets / constants, drop what looks like an address low half
        if imm < 0x1000 or imm > 0xF000:
            return w
        return w & 0xFFFF0000
    return w


def find(addr3, n=24, top=5, lo=None, hi=None):
    e2, e3 = elfs()
    pat = [mask(w) for w in struct.unpack('<%dI' % n, e3.read(addr3, 4 * n))]
    va, words = _words2
    first = pat[0]
    res = []
    nw = len(words)
    for i in range(nw - n):
        if mask(words[i]) != first:
            continue
        a = va + 4 * i
        if lo and a < lo or hi and a >= hi:
            continue
        s = 0
        for k in range(1, n):
            if mask(words[i + k]) == pat[k]:
                s += 1
        res.append((a, (s + 1) / n))
    res.sort(key=lambda x: -x[1])
    return res[:top]


def near(addr3, guess, n=16, radius=0x1000, top=3):
    """Score every word position within +-radius bytes of guess (first insn may differ)."""
    e2, e3 = elfs()
    pat = [mask(w) for w in struct.unpack('<%dI' % n, e3.read(addr3, 4 * n))]
    va, words = _words2
    res = []
    for a in range(guess - radius, guess + radius, 4):
        i = (a - va) // 4
        s = sum(1 for k in range(n) if mask(words[i + k]) == pat[k])
        res.append((a, s / n))
    res.sort(key=lambda x: -x[1])
    return res[:top]


if __name__ == '__main__':
    if sys.argv[1] == 'near':      # near <delta> addr3...   (guess = addr3 + delta)
        d = int(sys.argv[2], 16) if not sys.argv[2].startswith('-') else -int(sys.argv[2][1:], 16)
        for a in sys.argv[3:]:
            r = near(int(a, 16), int(a, 16) + d)
            print(a, ' '.join('%08x:%.2f' % x for x in r))
        sys.exit()
    for a in sys.argv[1:]:
        r = find(int(a, 16))
        print(a, ' '.join('%08x:%.2f' % x for x in r))
