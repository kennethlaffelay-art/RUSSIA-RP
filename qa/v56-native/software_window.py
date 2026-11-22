from pathlib import Path
import struct,zipfile,subprocess,shutil,os,sys
base=Path(sys.argv[1])
work=Path(sys.argv[2]).resolve()
work.mkdir(exist_ok=True)
with zipfile.ZipFile(base) as z:b=bytearray(z.read('AndroidManifest.xml'))
pos=8;fixed=0
while pos<len(b):
 typ,h,sz=struct.unpack_from('<HHI',b,pos)
 if typ==1:
  count,_,flags,start,_=struct.unpack_from('<5I',b,pos+8);assert flags==0
  strings=[]
  for off in struct.unpack_from('<%dI'%count,b,pos+h):
   p=pos+start+off
   n=struct.unpack_from('<H',b,p)[0]
   strings.append(b[p+2:p+2+2*n].decode('utf-16le'))
 if typ==258:
  _,tag,start,stride,count=struct.unpack_from('<IIHHH',b,pos+16)
  if strings[tag]=='activity':
   attrs={}
   for i in range(count):
    p=pos+16+start+i*stride;attrs[strings[struct.unpack_from('<I',b,p+4)[0]]]=p
   name=struct.unpack_from('<I',b,attrs['name']+16)[0]
   if strings[name]=='com.wn.blackrussia.game.Multiplayer':
    p=attrs['hardwareAccelerated']+16
    assert struct.unpack_from('<I',b,p)[0]==0xffffffff
    struct.pack_into('<I',b,p,0);fixed+=1
 pos+=sz
assert fixed==1
(work/'AndroidManifest.xml').write_bytes(b)
os.utime(work/'AndroidManifest.xml',(946684800,946684800))
dst=work/'unsigned.apk';shutil.copyfile(base,dst)
subprocess.run(['zip','-qd',str(dst),'AndroidManifest.xml'],check=True)
subprocess.run(['zip','-q','-0','-X',str(dst),'AndroidManifest.xml'],cwd=work,env=dict(os.environ,TZ='UTC'),check=True)
