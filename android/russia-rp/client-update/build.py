"""Build the signed Android updater bootstrap on top of the published 1.7.17 APK."""
import argparse
import copy
from hashlib import sha1, sha256
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
import zlib

ROOT = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'branding'))
from android_xml import Doc

BASE='e69d990afcb08a30283f590144ed5efe9ca89627808099e6c652eb0729a2e4f1'
CERT='076094c7e5bccf60a1d753d40175314b1fe361ef89c3cb366b2910f70637014a'


def dex_version(data):
    b=bytearray(data)
    u=lambda off:struct.unpack_from('<I',b,off)[0]
    def leb(p):
        result=0
        for shift in range(0,35,7):
            x=b[p];p+=1;result|=(x&127)<<shift
            if x<128:return result,p
        raise ValueError('Malformed dex')
    def string(idx):
        _,p=leb(u(u(60)+4*idx))
        return bytes(b[p:b.index(0,p)])
    types, fields=u(68),u(84)
    for p in range(u(100),u(100)+32*u(96),32):
        if string(u(types+4*u(p)))==b'Lcom/wn/blackrussia/BuildConfig;':break
    else:raise ValueError('Missing BuildConfig')
    fields_at, values=u(p+24),u(p+28)
    sizes=[]
    for _ in range(4):
        n,fields_at=leb(fields_at);sizes.append(n)
    names=[];idx=0
    for _ in range(sizes[0]):
        step,fields_at=leb(fields_at);idx+=step
        _,fields_at=leb(fields_at)
        names.append(string(u(fields+8*idx+4)))
    count,pos=leb(values);changed=False
    for name in names[:count]:
        tag=b[pos];pos+=1;kind=tag&31
        width=0 if kind in (30,31) else 1+(tag>>5)
        if name==b'VERSION_CODE':
            assert kind==4 and width==1 and b[pos]==41
            b[pos]=42;changed=True
        pos+=width
    assert changed and b.count(b'\x061.7.17\x00')==1
    b=b.replace(b'\x061.7.17\x00',b'\x061.7.18\x00')
    b[12:32]=sha1(b[32:]).digest()
    struct.pack_into('<I',b,8,zlib.adler32(b[12:])&0xffffffff)
    return bytes(b)


def raw_copy(source,dest,entry):
    # Preserve the original compressed payload of unchanged resources, dex and libraries.
    if entry.flag_bits&8: raise ValueError('Unsupported streaming ZIP entry')
    info=copy.copy(entry)
    source.fp.seek(entry.header_offset)
    header=source.fp.read(30)
    name,extra=struct.unpack_from('<HH',header,26)
    info.header_offset=dest.fp.tell()
    dest.fp.write(header)
    remain=name+extra+entry.compress_size
    while remain:
        chunk=source.fp.read(min(remain,1024*1024))
        if not chunk:raise EOFError(entry.filename)
        dest.fp.write(chunk);remain-=len(chunk)
    dest.start_dir=dest.fp.tell()
    dest.filelist.append(info)
    dest.NameToInfo[info.filename]=info
    dest._didModify=True


def build(a):
    assert sha256(a.base.read_bytes()).hexdigest()==BASE
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=a.output.parent) as tmp:
        tmp=Path(tmp)
        classes=tmp/'classes';classes.mkdir()
        dex=tmp/'dex';dex.mkdir()
        run=lambda *args:subprocess.run(list(map(str,args)),check=True)
        run('java','-m','jdk.compiler/com.sun.tools.javac.Main','-encoding','UTF-8','-source','8','-target','8','-bootclasspath',str(a.platform)+':'+str(a.sdk/'core-lambda-stubs.jar'),'-d',classes,*sorted(ROOT.rglob('stubs/**/*.java')),*sorted((ROOT/'java').rglob('*.java')))
        run(a.sdk/'d8','--release','--min-api','26','--lib',a.platform,'--classpath',classes,'--output',dex,*sorted((classes/'com/russiarp/updates').glob('*.class')))
        with ZipFile(a.base) as z,ZipFile(tmp/'unsigned.apk','w',allowZip64=False) as out:
            m=Doc(z.read('AndroidManifest.xml'))
            root=m.elements()[0]
            assert m.pool.values[root.get('package')]=='com.russiarp.hudx' and root.get('versionCode')==41
            root.set('versionCode',16,42);root.set('versionName',3,m.pool.add('1.7.18'))
            providers=[e for e in m.elements() if e.tag=='provider' and m.pool.values[e.get('name')]=='androidx.core.content.FileProvider']
            assert len(providers)==1 and m.pool.values[providers[0].get('authorities')]=='com.russiarp.hudx.provider'
            providers[0].set('name',3,m.pool.add('com.russiarp.updates.UpdateProvider'))
            edits={'AndroidManifest.xml':m.encode(),'classes3.dex':dex_version(z.read('classes3.dex'))}
            for abi in ('armeabi-v7a','arm64-v8a'):
                n='lib/'+abi+'/libmultiplayer.so';old=z.read(n)
                assert old.count(b'RUSSIA RP 1.7.17%.0s')==1
                edits[n]=old.replace(b'RUSSIA RP 1.7.17%.0s',b'RUSSIA RP 1.7.18%.0s')
            for e in z.infolist():
                if re.fullmatch(r'META-INF/(MANIFEST\.MF|[^/]+\.(RSA|DSA|EC|SF))',e.filename,re.I):continue
                if e.filename in edits:out.writestr(copy.copy(e),edits[e.filename])
                else:raw_copy(z,out,e)
            assert 'classes7.dex' not in z.namelist()
            f=ZipInfo('classes7.dex',(2026,11,26,0,0,0));f.compress_type=ZIP_DEFLATED
            out.writestr(f,(dex/'classes.dex').read_bytes())
        run(a.sdk/'zipalign','-f','-P','16','4',tmp/'unsigned.apk',tmp/'aligned.apk')
        run(a.sdk/'apksigner','sign','--ks',a.keystore,'--ks-pass','file:'+str(a.password_file),'--out',a.output,tmp/'aligned.apk')
        res=subprocess.check_output([a.sdk/'apksigner','verify','--verbose','--print-certs',a.output],text=True)
        assert 'Signer #1 certificate SHA-256 digest: '+CERT in res and 'Verified using v2 scheme (APK Signature Scheme v2): true' in res
        run(a.sdk/'zipalign','-c','-P','16','4',a.output)
        print('Signed APK',a.output,sha256(a.output.read_bytes()).hexdigest())


if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    for name in ('base','sdk','platform','keystore','password-file','output'):
        cli.add_argument('--'+name,required=True,type=Path)
    build(cli.parse_args())
