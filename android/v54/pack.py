import os,shutil,struct,subprocess,sys
from pathlib import Path
from zipfile import ZipFile
base,work=map(Path,sys.argv[1:])
work=work.resolve()
with ZipFile(base) as z:
    data=bytearray(z.read('AndroidManifest.xml'))
old='1.6.5'.encode('utf-16le')
assert data.count(old)==1
data=data.replace(old,'1.6.6'.encode('utf-16le'))
pos=8
updated=0
while pos<len(data):
    typ,head,length=struct.unpack_from('<HHI',data,pos)
    if typ==1:
        count,_,flags,start,_=struct.unpack_from('<IIIII',data,pos+8)
        assert flags==0
        names=[]
        for off in struct.unpack_from('<%dI'%count,data,pos+head):
            p=pos+start+off
            n=2*struct.unpack_from('<H',data,p)[0]
            names.append(data[p+2:p+2+n].decode('utf-16le'))
    elif typ==258:
        _,elem,start,stride,count=struct.unpack_from('<IIHHH',data,pos+16)
        if names[elem]=='manifest':
            for i in range(count):
                p=pos+16+start+stride*i
                if names[struct.unpack_from('<I',data,p+4)[0]]=='versionCode':
                    assert struct.unpack_from('<I',data,p+16)[0]==21
                    struct.pack_into('<I',data,p+16,22)
                    updated+=1
    pos+=length
assert updated==1
(work/'AndroidManifest.xml').write_bytes(data)
inputs=['classes8.dex','AndroidManifest.xml']
unsigned=work/'unsigned.apk'
shutil.copyfile(base,unsigned)
subprocess.run(['zip','-qd',str(unsigned),*inputs],check=True)
inputs.extend(['assets/russia-gui.dxt.toc', 'assets/russia-gta.dat', 'assets/russia-default.dat','assets/russia-cloud-record.gz','assets/russia-cloud-index','assets/russia-engine-paths.tsv'])
for name in inputs:os.utime(work/name,(946684800,946684800))
subprocess.run(['zip','-q','-0','-X',str(unsigned),*inputs],cwd=work,env=dict(os.environ,TZ='UTC'),check=True)
