"""Collect case-sensitive data/model filenames referenced by the client and map definitions."""
import argparse
import re
from collections import defaultdict
from pathlib import Path
from zipfile import ZipFile
def manifest(apk,cache):
    files={i.filename.removeprefix('Rkkdev/').lower(): i.filename.removeprefix('Rkkdev/') for i in cache.infolist() if not i.is_dir()}
    refs=set()
    for abi in ('arm64-v8a','armeabi-v7a'):
        for lib in ('libGame.so','libmultiplayer.so'):
            raw=apk.read(f'lib/{abi}/{lib}')
            for match in re.finditer(rb'[ -~]{4,}', raw):
                refs.add(match.group().decode('ascii').replace('\\','/').removeprefix('%s').lstrip('/'))
    for cfg in ('data/gta.dat','data/default.dat'):
        for line in cache.read('Rkkdev/'+cfg).decode('cp1251').splitlines():
            parts=line.partition('#')[0].split()
            if len(parts)>=2:refs.add(parts[-1].replace('\\','/'))
    result=[]
    for requested in sorted(refs):
        original=files.get(requested.lower())
        if original and requested!=original and original.startswith(('data/','models/','anim/')):
            result.append((original,requested))
    return result
if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for key in ['apk','cache','output']:parser.add_argument(key)
    args=parser.parse_args()
    with ZipFile(args.apk) as apk, ZipFile(args.cache) as cache:
        rows=manifest(apk,cache)
        entries=[]
        for src,dest in rows:
            info=cache.getinfo('Rkkdev/'+src)
            entries.append(f'{src}\t{dest}\t{info.file_size}\t{info.CRC}\n')
    Path(args.output).write_text(''.join(entries))
