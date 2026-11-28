"""Build an unsigned 1.7.31 for the original signing service."""
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile, ZipInfo

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from package import Doc, edit_catalog, once

BASE_SHA = 'ac2b0163930ffc700f9f98c73425a7f98377babb4f51fae172298b3f2525141c'


def build(base, assets, apktool, output):
    if hashlib.sha256(base.read_bytes()).hexdigest()!=BASE_SHA:
        raise ValueError('Requires the published 1.7.30 APK')
    if hashlib.sha256(apktool.read_bytes()).hexdigest()!='56d59c524fc764263ba8d345754d8daf55b1887818b15cd3b594f555d249e2db':
        raise ValueError('Requires Apktool 2.11.1')
    files = {p.relative_to(assets).as_posix():p for p in (assets/'assets').rglob('*') if p.is_file()}
    dex = ['classes3.dex','classes6.dex']
    with TemporaryDirectory(dir=output.parent) as temp, ZipFile(base) as z:
        tmp = Path(temp).resolve()
        mini, decoded, built = (tmp/n for n in ('mini.apk','decoded','built.apk'))
        with ZipFile(mini,'w') as seed:
            for n in ['AndroidManifest.xml','resources.arsc','classes.dex',*dex]:
                seed.writestr(n,z.read(n))
        def run(*args):
            subprocess.run(['java','-Xmx1g','-jar',str(apktool.resolve()),*map(str,args)],check=True)
        run('d','-r','-j','2',mini,'-o',decoded)
        config = decoded/'smali_classes3/com/wn/blackrussia/BuildConfig.smali'
        config.write_text(once(once(config.read_text(),'VERSION_CODE:I = 0x36','VERSION_CODE:I = 0x37'),
                               '"1.7.30"','"1.7.31"'))
        meta = json.loads((assets/'integration.json').read_bytes())
        edit_catalog(decoded,meta,'    :cond_0\n    const-string v0, "texdb/samp.img"')
        run('b','-j','2',decoded,'-o',built)
        doc = Doc(z.read('AndroidManifest.xml'))
        root = doc.elements()[0]
        assert root.get('versionCode')==54
        root.set('versionCode',16,55)
        root.set('versionName',3,doc.pool.add('1.7.31'))
        with ZipFile(built) as compiled, ZipFile(tmp/'candidate.apk','w') as out:
            def put(name, raw, compression):
                ent = ZipInfo(name,(2026,1,1,0,0,0))
                ent.compress_type = compression
                if compression==0:
                    align = 16384 if name.endswith('.so') else 4
                    pad = (-(out.fp.tell()+30+len(name.encode())+4))%align
                    ent.extra = struct.pack('<HH',0xbeef,pad)+bytes(pad)
                out.writestr(ent,raw)
            for entry in z.infolist():
                n = entry.filename
                if re.fullmatch(r'META-INF/(MANIFEST\.MF|[^/]+\.(SF|RSA|EC|DSA))',n,re.I):
                    continue
                if n in files:
                    raw = files.pop(n).read_bytes()
                elif n in dex:
                    raw = compiled.read(n)
                elif n=='AndroidManifest.xml':
                    raw = doc.encode()
                else:
                    raw = z.read(n)
                    if n.endswith('/libmultiplayer.so'):
                        raw = once(raw,b'RUSSIA RP 1.7.30%.0s',b'RUSSIA RP 1.7.31%.0s')
                put(n,raw,entry.compress_type)
            for n,p in sorted(files.items()):
                put(n,p.read_bytes(),8)
        (tmp/'candidate.apk').replace(output)


if __name__=='__main__':
    build(*map(Path,sys.argv[1:]))
