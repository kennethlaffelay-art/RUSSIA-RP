"""Keep the stock menu, Play action and loading Activity; update only the cache release metadata."""
import hashlib
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import zlib
from zipfile import ZipFile

OLD_SHA='f701d99e857a2d9e5fe9127ab00c0161bc71f94c7f8281456af776a33007df9a'
NEW_SHA='1cdd9c76725fdd1ab07f196a9e5fdcafd5c5808ba883f71701cfa5e0d33d77ea'
OLD_SIZE,NEW_SIZE=1488834187,1488865990
BASE_URL='https://github.com/kennethlaffelay-art/RUSSIA-RP/releases/download/'
OLD_TAG='russia-f701d99e857a2d9e5fe9127ab00c0161-b9180d3ebef8'
PREFIX='client-v5-play-'
TAG=PREFIX+NEW_SHA[:len(OLD_TAG)-len(PREFIX)]
def patch(data,old,new,expected):
    if len(new)!=len(old) or data.count(old)!=expected:raise ValueError('Unexpected input layout')
    return data.replace(old,new)
def utf16(s):return s.encode('utf-16le')
def word(v):return struct.pack('<I',v)
def build(source, folder):
    with source.open('rb') as f: assert hashlib.file_digest(f,'sha256').hexdigest()=='e27b60a1670dba072c7b5d4f7e8c0b7317659d3e8973b786e0210ee51444f980'
    folder.mkdir(parents=True,exist_ok=True)
    with ZipFile(source) as z:
        dex=z.read('classes.dex')
        manifest=z.read('AndroidManifest.xml')
    dex=patch(dex,utf16(BASE_URL+OLD_TAG+'/Rkkdev.zip'),utf16(BASE_URL+TAG+'/Rkkdev.zip'),1)
    dex=patch(dex,bytes.fromhex(OLD_SHA),bytes.fromhex(NEW_SHA),1)
    dex=patch(dex,utf16('.russia-cache-'+OLD_SHA[:16]),utf16('.russia-cache-'+NEW_SHA[:16]),2)
    dex=patch(dex,word(OLD_SIZE),word(NEW_SIZE),2)
    dex=patch(dex,word(math.ceil(OLD_SIZE/95)),word(math.ceil(NEW_SIZE/95)),1)
    dex=bytearray(dex)
    dex[12:32]=hashlib.sha1(dex[32:]).digest()
    dex[8:12]=word(zlib.adler32(dex[12:]) & 0xffffffff)
    manifest=bytearray(patch(manifest,utf16('1.6.0'),utf16('1.6.2'),1))
    p=8
    edits=0
    while p<len(manifest):
        typ,header,size=struct.unpack_from('<HHI',manifest,p)
        if typ==1:
            n,_,flags,base,_=struct.unpack_from('<IIIII',manifest,p+8)
            assert flags==0
            strings=[]
            for o in struct.unpack_from(f'<{n}I',manifest,p+header):
                off=p+base+o
                l=struct.unpack_from('<H',manifest,off)[0]
                strings.append(manifest[off+2:off+2+2*l].decode('utf-16le'))
        if typ==258:
            _,elem,start,stride,count=struct.unpack_from('<IIHHH',manifest,p+16)
            if strings[elem]=='manifest':
                for i in range(count):
                    attr=p+16+start+stride*i
                    if strings[struct.unpack_from('<I',manifest,attr+4)[0]]=='versionCode':
                        assert struct.unpack_from('<I',manifest,attr+16)[0]==16
                        struct.pack_into('<I',manifest,attr+16,18)
                        edits+=1
        p+=size
    assert edits==1
    for name,content in [('classes.dex',dex),('AndroidManifest.xml',manifest)]:
        dest=folder/name
        dest.write_bytes(content)
        os.utime(dest,(946684800,946684800))
    unsigned=(folder/'unsigned.apk').resolve()
    shutil.copyfile(source,unsigned)
    subprocess.run(['zip','-qd',str(unsigned),'classes.dex','AndroidManifest.xml'],check=True)
    subprocess.run(['zip','-q','-X','-0',str(unsigned),'classes.dex','AndroidManifest.xml'],cwd=folder,check=True,env=dict(os.environ,TZ='UTC'))
if __name__=='__main__':
    build(Path(sys.argv[1]),Path(sys.argv[2]))
    print(TAG)
