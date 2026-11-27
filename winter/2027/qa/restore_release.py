"""Reassemble the exact signed APK from the published Lights base and release deltas."""
import base64
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import tarfile
from zipfile import ZipFile
import zlib

import bsdiff4


def restore(base, distribution, version, output):
    source = base.read_bytes()
    encoded = ''.join(p.read_text() for p in sorted(distribution.glob('bundle.*.b64')))
    with tarfile.open(fileobj=io.BytesIO(base64.b64decode(encoded)), mode='r:xz') as archive:
        def member(name):
            return archive.extractfile(name).read()

        config = json.loads(member(f'{version}.json'))
        if hashlib.sha256(source).hexdigest() != config['base']:
            raise ValueError('Unexpected base APK')
        with ZipFile(io.BytesIO(source)) as previous:
            headers = bytearray()
            compressed = {}
            for entry in previous.infolist():
                start = entry.header_offset
                name_size, extra_size = struct.unpack_from('<HH',source,start+26)
                end = start+30+name_size+extra_size
                headers.extend(source[start:end])
                tail = end+entry.compress_size
                compressed[entry.filename] = memoryview(source)[end:tail]
            headers.extend(source[tail:])
            layout = bsdiff4.patch(bytes(headers),base64.b64decode(config['header_delta']))
            built = bytearray()
            at = 0
            while layout[at:at+4] == b'PK\x03\x04':
                method = struct.unpack_from('<H',layout,at+8)[0]
                length = struct.unpack_from('<I',layout,at+18)[0]
                name_size, extra_size = struct.unpack_from('<HH',layout,at+26)
                name = layout[at+30:at+30+name_size].decode('utf-8')
                end = at+30+name_size+extra_size
                built.extend(layout[at:end])
                at = end
                if name in config['changed']:
                    kind, token, level = config['changed'][name]
                    payload = zlib.decompress(member(token+'.bin'))
                    if kind == 'delta':
                        raw = bsdiff4.patch(previous.read(name),payload)
                    elif kind == 'ranges':
                        raw = bytearray(previous.read(name))
                        i = 0
                        while i < len(payload):
                            offset,n = struct.unpack_from('<IH',payload,i)
                            i += 6
                            raw[offset:offset+n] = payload[i:i+n]
                            i += n
                    elif kind == 'full':
                        raw = payload
                    else:
                        raise ValueError('Unknown release delta')
                    if method == 8:
                        encoder = zlib.compressobj(level,zlib.DEFLATED,-15)
                        content = encoder.compress(raw)+encoder.flush()
                    elif method == 0:
                        content = raw
                    else:
                        raise ValueError('Unexpected ZIP compression')
                else:
                    content = compressed[name]
                if len(content) != length:
                    raise ValueError(f'Packed size mismatch: {name}')
                built.extend(content)
            built.extend(layout[at:])
    if hashlib.sha256(built).hexdigest() != config['sha256']:
        raise ValueError('Signed APK hash mismatch')
    output.write_bytes(built)


if __name__ == '__main__':
    restore(Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]), Path(sys.argv[4]))
