"""Prepare the GitHub asset in the Rkkdev/ format expected by the stock Android downloader."""
import hashlib
from pathlib import Path
import shutil
import struct
import sys
from zipfile import ZipFile, ZipInfo, ZIP_STORED

SOURCE_SHA = 'f701d99e857a2d9e5fe9127ab00c0161bc71f94c7f8281456af776a33007df9a'

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def prepare(source, output):
    if source.resolve() == output.resolve():
        raise ValueError('Choose a new output file')
    if sha(source) != SOURCE_SHA:
        raise ValueError('Wrong source archive')
    shutil.copyfile(source, output)
    old = 'Rkkdev/data/TIMECYC.DAT'
    new = 'Rkkdev/data/timecyc.dat'
    with ZipFile(source) as archive:
        local = archive.getinfo(old).header_offset + 30
        start = archive.start_dir
        count = len(archive.infolist())
        extras = {name: archive.read(original) for name, original in (
            ('Rkkdev/data/script/script.img', 'Rkkdev/SAMP/script.img'),
            ('Rkkdev/data/vehicles.ide', 'Rkkdev/SAMP/vehicles.ide')
        )}
    with output.open('r+b') as stream:
        def replace_name(pos):
            stream.seek(pos)
            if stream.read(len(old)) != old.encode(): raise ValueError('Filename mismatch')
            stream.seek(pos); stream.write(new.encode())
        replace_name(local)
        stream.seek(start)
        matches = 0
        for _ in range(count):
            header = stream.read(46)
            if header[:4] != b'PK\x01\x02': raise ValueError('Unexpected directory record')
            name_len, extra_len, comment_len = struct.unpack_from('<3H', header, 28)
            pos = stream.tell()
            name = stream.read(name_len)
            if name == old.encode():
                replace_name(pos); matches += 1
            stream.seek(pos + name_len + extra_len + comment_len)
        if matches != 1: raise ValueError('Missing central filename')
    with ZipFile(output,'a') as archive:
        for name, data in extras.items():
            if name in archive.namelist(): raise ValueError('Duplicate destination')
            info=ZipInfo(name,(2025,3,29,18,0,0))
            info.create_system=3
            info.external_attr=0o100644 << 16
            archive.writestr(info,data,compress_type=ZIP_STORED)
    return sha(output)

if __name__ == '__main__':
    print(prepare(Path(sys.argv[1]), Path(sys.argv[2])))
