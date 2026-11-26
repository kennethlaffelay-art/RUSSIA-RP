"""Build a signed cumulative cache update from the files in a directory."""
import argparse
import base64
import hashlib
import os
import struct
import tempfile
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import pkcs12

def sha(stream):
    digest = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b''):
        digest.update(block)
    return digest.hexdigest()

def build(directory, output, generation, tag, keystore, password_file):
    if generation < 17:
        raise ValueError('Cache generation must start at 17')
    import re
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,95}', tag):
        raise ValueError('Invalid release tag')
    key, _, _ = pkcs12.load_key_and_certificates(keystore.read_bytes(), password_file.read_bytes().rstrip(b'\r\n'))
    output.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in directory.rglob('*') if p.is_file())
    with tempfile.TemporaryDirectory(dir=output) as temp_dir:
        pack = Path(temp_dir) / 'cache.zip'
        with ZipFile(pack, 'w', ZIP_DEFLATED, compresslevel=6) as archive:
            for path in files:
                if path.is_symlink() or not path.resolve().is_relative_to(directory.resolve()):
                    raise ValueError(f'Unexpected symlink: {path}')
                archive.write(path, path.relative_to(directory).as_posix())
        with pack.open('rb') as raw, ZipFile(pack) as archive:
            pack_hash = sha(raw)
            rows = [['RRP1', '16', str(generation), tag, str(pack.stat().st_size), pack_hash]]
            for entry in archive.infolist():
                if any(c in entry.filename for c in '\t\n\r\\:'):
                    raise ValueError(f'Invalid path: {entry.filename}')
                raw.seek(entry.header_offset + 26)
                namesize, extrasize = struct.unpack('<HH', raw.read(4))
                offset = entry.header_offset + 30 + namesize + extrasize
                with archive.open(entry) as stream:
                    rows.append([entry.filename, sha(stream), str(entry.file_size), str(offset), str(entry.compress_size), str(entry.compress_type)])
        payload = ''.join('\t'.join(row) + '\n' for row in rows).encode()
        signature = key.sign(payload, padding.PKCS1v15(), hashes.SHA256())
        channel = Path(temp_dir) / 'channel-v1.rrc'
        channel.write_bytes(base64.b64encode(signature) + b'\n' + payload)
        os.replace(pack, output / ('cache-' + pack_hash + '.zip'))
        os.replace(channel, output / channel.name)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('directory', 'output', 'keystore', 'password_file'):
        parser.add_argument('--' + key.replace('_', '-'), type=Path, required=True)
    parser.add_argument('--generation', required=True, type=int)
    parser.add_argument('--tag', required=True)
    build(**vars(parser.parse_args()))
