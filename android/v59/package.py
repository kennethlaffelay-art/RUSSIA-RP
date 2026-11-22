"""Build the parallel-installable client from the pinned Android release."""
from pathlib import Path
import re
import struct
import sys
import zipfile

old = 'com.wn.blackrussia'
new = 'com.wn.russiarpfix'
def chunks(data, pos, end):
    while pos < end:
        kind, head, size = struct.unpack_from('<HHI', data, pos)
        assert size >= head >= 8 and pos + size <= end
        yield kind, pos, head, size
        pos += size
    assert pos == end

def manifest(data):
    b = bytearray(data)
    changes = set()
    for kind, pos, head, size in chunks(b, 8, len(b)):
        if kind == 1:
            count, styles, flags, start, _ = struct.unpack_from('<5I', b, pos+8)
            assert not flags & 0x100
            names = []
            for index in range(count):
                offset, = struct.unpack_from('<I', b, pos+head+4*index)
                p = pos+start+offset
                length, = struct.unpack_from('<H', b, p)
                assert length < 32768
                s = bytes(b[p+2:p+2+length*2]).decode('utf-16le')
                names.append(s)
                suffixes = ('', '.provider', '.firebaseinitprovider', '.androidx-startup',
                            '.com.squareup.picasso', '.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION')
                if s in [old+suffix for suffix in suffixes]:
                    v = new+s[len(old):]
                elif s == '1.6.9':
                    v = '1.7.1'
                else:
                    continue
                assert len(v) == len(s)
                b[p+2:p+2+length*2] = v.encode('utf-16le')
                changes.add(s)
        if kind == 0x102:
            _, element, first, stride, count = struct.unpack_from('<IIHHH', b, pos+16)
            if names[element] != 'manifest':
                continue
            for i in range(count):
                p = pos+16+first+stride*i
                if names[struct.unpack_from('<I', b, p+4)[0]] == 'versionCode':
                    assert struct.unpack_from('<I', b, p+16)[0] == 25
                    struct.pack_into('<I', b, p+16, 27)
                    changes.add('versionCode')
    assert {old, old+'.provider', old+'.firebaseinitprovider',old+'.androidx-startup',
            old+'.com.squareup.picasso',old+'.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION','versionCode','1.6.9'} == changes
    return b

def resources(data):
    b = bytearray(data)
    changed = 0
    for kind, pos, head, size in chunks(b, 12, len(b)):
        if kind == 0x200:
            p = pos + 12
            if bytes(b[p:p+256]).decode('utf-16le').rstrip('\0') == old:
                b[p:p+256] = new.encode('utf-16le').ljust(256, b'\0')
                changed += 1
    assert changed == 1
    return b

with zipfile.ZipFile('base.apk') as base, zipfile.ZipFile('rebuilt.apk', 'w') as out:
    assert len(base.namelist())==len(set(base.namelist()))
    for member in base.infolist():
        if re.fullmatch(r'META-INF/(?:MANIFEST\.MF|[^/]+\.(?:SF|RSA|DSA|EC))', member.filename, re.I):
            continue
        data = base.read(member)
        if member.filename == 'AndroidManifest.xml':
            data = manifest(data)
        elif member.filename == 'resources.arsc':
            data = resources(data)
        elif member.filename == 'classes8.dex':
            data = Path('dex/classes.dex').read_bytes()
        elif member.filename == 'classes.dex' and Path('launcher.dex').is_file():
            data = Path('launcher.dex').read_bytes()
        out.writestr(member,data)
