from pathlib import Path
from zipfile import ZipFile
import os,struct,shutil,subprocess,sys

def version(data):
    old='1.6.8'.encode('utf-16le')
    assert data.count(old)==1
    b=bytearray(data.replace(old,'1.6.9'.encode('utf-16le')))
    pos=8; changed=0
    while pos<len(b):
        kind,head,size=struct.unpack_from('<HHI',b,pos)
        if kind==1:
            count,_,flags,start,_=struct.unpack_from('<5I',b,pos+8)
            assert flags==0
            names=[]
            for off in struct.unpack_from('<%dI'%count,b,pos+head):
                p=pos+start+off
                length=2*struct.unpack_from('<H',b,p)[0]
                names.append(b[p+2:p+2+length].decode('utf-16le'))
        if kind==258:
            _,elem,start,stride,count=struct.unpack_from('<IIHHH',b,pos+16)
            if names[elem]=='manifest':
                for i in range(count):
                    p=pos+16+start+stride*i
                    if names[struct.unpack_from('<I',b,p+4)[0]]=='versionCode':
                        assert struct.unpack_from('<I',b,p+16)[0]==24
                        struct.pack_into('<I',b,p+16,25);changed+=1
        pos+=size
    assert changed==1
    return b

if __name__=='__main__':
    base,folder=map(Path,sys.argv[1:])
    folder=folder.resolve()
    files=['classes4.dex','classes9.dex','AndroidManifest.xml']
    with ZipFile(base) as z:
        (folder/'AndroidManifest.xml').write_bytes(version(z.read('AndroidManifest.xml')))
    for path in files:
        os.utime(folder/path,(946684800,946684800))
    unsigned=folder/'unsigned.apk'
    shutil.copyfile(base,unsigned)
    subprocess.run(['zip','-qd',str(unsigned),*files],check=True)
    subprocess.run(['zip','-q','-0','-X',str(unsigned),*files],cwd=folder,check=True,env=dict(os.environ,TZ='UTC'))
