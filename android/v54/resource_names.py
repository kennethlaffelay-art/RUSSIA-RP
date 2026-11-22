"""Use the original archive spelling for data paths embedded in ELF read-only data and map lists."""
import re
import struct
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
    return bytes(c if c in (47,92) else v for c,v in zip(token,real,strict=True))

def library(src,index):
    is64=src[4]==2
    header=struct.unpack_from('<16sHHIQQQIHHHHHH' if is64 else '<16sHHIIIIIHHHHHH',src)
    section=struct.Struct('<IIQQQQIIQQ' if is64 else '<IIIIIIIIII')
    sections=[section.unpack_from(src,header[6]+i*section.size) for i in range(header[12])]
    names=sections[header[13]]
    named={src[names[4]+s[0]:].split(b'\0',1)[0]:s for s in sections}
    ro=named[b'.rodata']
    out=bytearray(src);start=ro[4];stop=start+ro[5]
    for match in re.finditer(rb'(?:data|anim|models|texdb)[\\/][A-Za-z0-9_.\\/-]+(?=\0)',src[start:stop],re.I):
        key=match[0];fixed=normalize(key,index)
        if fixed!=key:
            i=start+match.start()
            out[i:i+len(key)]=fixed
    assert len(out)==len(src)
    text=named[b'.text']
    assert out[text[4]:text[4]+text[5]]==src[text[4]:text[4]+text[5]]
    return out

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
    for key in ['apk','cache','output']:parser.add_argument(key)
    opts=parser.parse_args()
    out=Path(opts.output)
    with ZipFile(opts.apk) as apk,ZipFile(opts.cache) as archive:
        index=file_index(archive)
        for abi in ('arm64-v8a','armeabi-v7a'):
            for lib in ('libGame.so','libmultiplayer.so'):
                path='lib/'+abi+'/'+lib
                (out/path).parent.mkdir(parents=True,exist_ok=True)
                (out/path).write_bytes(library(apk.read(path),index))
        (out/'assets').mkdir(parents=True,exist_ok=True)
        for config in ('gta','default'):
            raw=archive.read('Rkkdev/data/'+config+'.dat')
            (out/'assets'/('russia-'+config+'.dat')).write_bytes(control(raw,index))
