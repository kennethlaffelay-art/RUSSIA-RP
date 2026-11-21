import os,struct,shutil,subprocess,sys
from pathlib import Path
from zipfile import ZipFile
from dex_edits import fix_game,move_worker
base,cache,folder=map(Path,sys.argv[1:4]);folder=folder.resolve()
with ZipFile(base) as z:
    (folder/'classes.dex').write_bytes(move_worker(z.read('classes.dex')))
    (folder/'classes4.dex').write_bytes(fix_game(z.read('classes4.dex')))
    manifest=bytearray(z.read('AndroidManifest.xml'))
    old='1.6.3'.encode('utf-16le')
    assert manifest.count(old)==1
    manifest=manifest.replace(old,'1.6.4'.encode('utf-16le'))
p=8;updates=0
while p<len(manifest):
    typ,head,size=struct.unpack_from('<HHI',manifest,p)
    if typ==1:
        n,_,flags,baseoff,_=struct.unpack_from('<IIIII',manifest,p+8)
        assert flags==0
        names=[]
        for ofs in struct.unpack_from(f'<{n}I',manifest,p+head):
            pos=p+baseoff+ofs;nbytes=2*struct.unpack_from('<H',manifest,pos)[0]
            names.append(manifest[pos+2:pos+2+nbytes].decode('utf-16le'))
    if typ==258:
        _,elem,start,stride,count=struct.unpack_from('<IIHHH',manifest,p+16)
        if names[elem]=='manifest':
            for i in range(count):
                pos=p+16+start+i*stride
                if names[struct.unpack_from('<I',manifest,pos+4)[0]]=='versionCode':
                    assert struct.unpack_from('<I',manifest,pos+16)[0]==19
                    struct.pack_into('<I',manifest,pos+16,20);updates+=1
    p+=size
assert updates==1
(folder/'AndroidManifest.xml').write_bytes(manifest)
personal={'SAMP/settings.ini','SAMP/graphics.ini','SAMP/sampvoice/svconfig.ini','Adjustable.cfg','gta_sa.set','gtasatelem.set'}
(folder/'assets').mkdir(exist_ok=True)
rows=[]
with ZipFile(cache) as z:
    for i in z.infolist():
        assert i.filename.startswith('Rkkdev/')
        n=i.filename[7:]
        if i.is_dir() or n in {'SAMP/crash_log.log','SAMP/samp_log.txt'}:continue
        assert all(word not in ('.','..','') for word in n.split('/'))
        rows.append(f'{n}\t{i.file_size}\t{i.CRC}\t{int(n in personal)}\n')
assert len(rows)==343
(folder/'assets/russia-cache-v52.tsv').write_text(''.join(rows))
unsigned=folder/'unsigned.apk'
shutil.copyfile(base,unsigned)
inputs=['classes.dex','classes4.dex','AndroidManifest.xml']
subprocess.run(['zip','-qd',str(unsigned),*inputs],check=True)
inputs+=['classes7.dex','classes8.dex','assets/russia-cache-v52.tsv']
for n in inputs:os.utime(folder/n,(946684800,946684800))
subprocess.run(['zip','-q','-0','-X',str(unsigned),*inputs],check=True,cwd=folder,env=dict(os.environ,TZ='UTC'))
