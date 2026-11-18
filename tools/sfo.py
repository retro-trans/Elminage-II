"""PARAM.SFO editing: set a UTF-8 string field in place (within the field's max length).

    python tools/sfo.py            # print the fields of the original PARAM.SFO
Used by build.py: title(out_path) writes PARAM.SFO with TITLE = 'Elminage II' (PSP home-menu name).
"""
import os
import struct
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SRC = os.path.join(ROOT, 'work', 'source', 'disc', 'PARAM.SFO')
TITLE = 'Elminage II'


def fields(d):
    ks, ds, n = struct.unpack_from('<III', d, 8)
    for i in range(n):
        ko, fmt, ln, mx, do = struct.unpack_from('<HHIII', d, 20 + i * 16)
        k = d[ks + ko:d.index(b'\0', ks + ko)].decode()
        yield i, k, fmt, ln, mx, ds + do


def set_str(d, key, value):
    d = bytearray(d)
    for i, k, fmt, ln, mx, off in fields(d):
        if k == key:
            assert fmt == 0x204, 'not a UTF-8 string field'
            b = value.encode('utf-8') + b'\0'
            assert len(b) <= mx, 'too long for the field'
            d[off:off + mx] = b + b'\0' * (mx - len(b))
            struct.pack_into('<I', d, 20 + i * 16 + 4, len(b))
            return bytes(d)
    raise KeyError(key)


def title(out_path):
    open(out_path, 'wb').write(set_str(open(SRC, 'rb').read(), 'TITLE', TITLE))
    return out_path


if __name__ == '__main__':
    d = open(SRC, 'rb').read()
    for i, k, fmt, ln, mx, off in fields(d):
        v = d[off:off + ln]
        print(k, struct.unpack('<I', v)[0] if fmt == 0x404 else v.rstrip(b'\0').decode('utf-8', 'replace'))
