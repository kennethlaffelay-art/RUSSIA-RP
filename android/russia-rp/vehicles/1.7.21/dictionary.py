"""Prepare the compression dictionary for the RUSSIA RP 1.7.21 signed update."""
import base64
import hashlib
import json
from pathlib import Path
import struct
import shutil
import sys
from zipfile import ZipFile
import zlib

def with_ranges(source, additions):
    magic, file_size, count = struct.unpack_from('>IQI', source)
    if magic != 0x57533134:
        raise ValueError('Unknown cache delta format')
    ranges = []
    cursor = 16
    for _ in range(count):
        offset, size = struct.unpack_from('>QI', source, cursor)
        cursor += 12
        ranges.append((offset, source[cursor:cursor+size]))
        cursor += size
    if cursor != len(source):
        raise ValueError('Invalid cache delta')
    ranges.extend((offset, base64.b64decode(data)) for offset, data in additions)
    result = bytearray(struct.pack('>IQI', magic, file_size, len(ranges)))
    for offset, data in sorted(ranges):
        result.extend(struct.pack('>QI', offset, len(data)))
        result.extend(data)
    return result

def build(previous, recipe, destination):
    with ZipFile(previous) as apk, previous.open('rb') as source, destination.open('wb') as out:
        shutil.copyfileobj(source, out)
        for row in json.loads(recipe.read_text()):
            data = bytearray(apk.read(row['entry']))
            if row['kind'] == 'append-ranges':
                data = with_ranges(data, row['changes'])
            else:
                for offset, encoded in row['changes']:
                    replacement = base64.b64decode(encoded)
                    data[offset:offset+len(replacement)] = replacement
            if hashlib.sha256(data).hexdigest() != row['sha256']:
                raise ValueError('Component hash mismatch for ' + row['entry'])
            encoder = zlib.compressobj(6, zlib.DEFLATED, -15)
            out.write(encoder.compress(data))
            out.write(encoder.flush())

if __name__ == '__main__':
    build(*map(Path, sys.argv[1:4]))
