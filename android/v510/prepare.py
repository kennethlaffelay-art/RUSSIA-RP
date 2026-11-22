from pathlib import Path
import re
import struct
from zipfile import ZipFile, ZIP_STORED
from sys import argv

def bump(raw):
    old='1.7.1'.encode('utf-16le')
    assert raw.count(old)==1
    b=bytearray(raw.replace(old,'1.7.2'.encode('utf-16le')))
    pos=8
    changed=0
    while pos<len(b):
        kind,head,size=struct.unpack_from('<HHI',b,pos)
        if kind==1:
            cnt,_,flags,start,_=struct.unpack_from('<5I',b,pos+8)
            assert flags&256==0
            names=[]
            for i in range(cnt):
                q=pos+start+struct.unpack_from('<I',b,pos+head+4*i)[0]
                n=struct.unpack_from('<H',b,q)[0]
                names.append(bytes(b[q+2:q+2+n*2]).decode('utf-16le'))
        if kind==0x102:
            _,name,offset,stride,cnt=struct.unpack_from('<IIHHH',b,pos+16)
            if names[name]=='manifest':
                for i in range(cnt):
                    q=pos+16+offset+i*stride
                    if names[struct.unpack_from('<I',b,q+4)[0]]=='versionCode':
                        assert struct.unpack_from('<I',b,q+16)[0]==27
                        struct.pack_into('<I',b,q+16,28);changed+=1
        pos+=size
    assert changed==1
    return b

if __name__=='__main__':
    with ZipFile('base.apk') as src, ZipFile('stage.apk','w') as dest:
        for entry in src.infolist():
            if re.fullmatch(r'META-INF/(?:MANIFEST\.MF|[^/]+\.(?:SF|RSA|DSA|EC))',entry.filename,re.I):continue
            data=src.read(entry)
            if entry.filename=='AndroidManifest.xml':data=bump(data)
            elif entry.filename=='classes8.dex':data=Path('classes.dex').read_bytes()
            dest.writestr(entry,data)
        dest.writestr('assets/russia-project.endpoint',b'10.0.2.2\n7777\n'.ljust(96,b' '),compress_type=ZIP_STORED)
