"""Generate the launcher's file and HTTP Range index for a published Weik ZIP."""
import argparse
import hashlib
import json
import struct
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile


def sha256(stream):
    digest = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b''):
        digest.update(block)
    return digest.hexdigest()


def index(archive, url, generation):
    files = {}
    with archive.open('rb') as raw, ZipFile(archive) as release:
        checksum = sha256(raw)
        for item in release.infolist():
            if item.is_dir():
                continue
            path = PurePosixPath(item.filename)
            if path.parts[0] != 'Weik' or '..' in path.parts or len(path.parts) < 2:
                raise ValueError(item.filename)
            name = str(path.relative_to('Weik'))
            if name in files or item.flag_bits & 1 or item.compress_type not in (ZIP_STORED, ZIP_DEFLATED):
                raise ValueError(name)
            raw.seek(item.header_offset)
            header = raw.read(30)
            if header[:4] != b'PK\x03\x04':
                raise ValueError(name)
            filename_size, extra_size = struct.unpack_from('<HH', header, 26)
            offset = item.header_offset + 30 + filename_size + extra_size
            with release.open(item) as member:
                files[name] = [sha256(member), item.file_size, offset, item.compress_size, item.compress_type]
    return dict(generation=generation, url=url, size=archive.stat().st_size, sha256=checksum, files=files)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('url')
    parser.add_argument('generation', type=int)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = index(args.archive, args.url, args.generation)
    args.output.write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
