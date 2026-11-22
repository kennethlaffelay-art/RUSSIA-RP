"""Use the archive spelling for paths in the engine's map lists."""
import re
from zipfile import ZipFile

def file_index(cache):
    result={}
    for info in cache.infolist():
        if info.is_dir():continue
        path=info.filename.removeprefix('Rkkdev/').encode('ascii','ignore')
        if path.lower() in result:raise ValueError('Ambiguous archive path')
        result[path.lower()]=path
    return result

def normalize(token,index):
    path=token.replace(b'\\',b'/')
    real=index.get(path.lower())
    if not real or real.startswith((b'audio/',b'data/Decision/')):return token
    if real.startswith(b'texdb/') and real.lower().endswith(b'.img'):
        real=real.upper()
    return bytes(c if c in (47,92) else v for c,v in zip(token,real,strict=True))

def control(data,index):
    # Keep separators, comments, line endings and game directives byte-for-byte.
    def line(row):
        body,sep,comment=row.partition(b'#')
        return re.sub(rb'[A-Za-z0-9_][A-Za-z0-9_.\\/-]*[\\/][A-Za-z0-9_.\\/-]+',lambda m:normalize(m[0],index),body)+sep+comment
    return b''.join(line(row) for row in data.splitlines(keepends=True))

if __name__=='__main__':
    import argparse
    from pathlib import Path
    parser=argparse.ArgumentParser()
    for key in ['cache','output']:parser.add_argument(key)
    opts=parser.parse_args()
    out=Path(opts.output)
    with ZipFile(opts.cache) as archive:
        index=file_index(archive)
        (out/'assets').mkdir(parents=True,exist_ok=True)
        for config in ('gta','default'):
            raw=archive.read('Rkkdev/data/'+config+'.dat')
            (out/'assets'/('russia-'+config+'.dat')).write_bytes(control(raw,index))
