"""Build RUSSIA RP 1.7.17 from the official 1.7.16 APK (apktool 2.11.1)."""
import argparse
import hashlib
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile

def build(base, apktool, sdk, keystore, password_file, output, xml_module):
    from importlib.util import spec_from_file_location, module_from_spec
    spec = spec_from_file_location('android_xml', xml_module)
    axml = module_from_spec(spec)
    spec.loader.exec_module(axml)
    source = Path(__file__).resolve().parent
    with base.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != '25a6bb1e3db533086ff3c70e8216ad4406d118791742f200021b7a7b3f478f3a':
            raise ValueError('Expected the official RUSSIA RP 1.7.16 APK')
    def run(*args, **kw):
        subprocess.run(list(map(str, args)), check=True, **kw)
    with tempfile.TemporaryDirectory() as temp:
        work = Path(temp)
        decoded, classes, dex = (work / n for n in ('decoded', 'classes', 'dex'))
        classes.mkdir()
        dex.mkdir()
        run('java','-m','jdk.compiler/com.sun.tools.javac.Main','-source','8','-target','8','-d',classes,
            *sorted((source/'stubs').rglob('*.java')), *sorted((source/'java').rglob('*.java')))
        compiled = sorted(p for p in classes.rglob('*.class') if not p.name.startswith('Weik'))
        run(sdk/'d8','--min-api','26','--output',dex,*compiled)
        with ZipFile(base) as archive, ZipFile(work/'input.apk','w') as dest:
            for name in ('AndroidManifest.xml','resources.arsc','classes.dex'):
                dest.writestr(name,archive.read(name))
            dest.writestr('classes2.dex',archive.read('classes3.dex'))
        run('java','-Xmx1100m','-jar',apktool,'d','-f','-r','-j','2',work/'input.apk','-o',decoded)
        with (source/'launcher.patch').open('rb') as patch:
            run('patch','--batch','--fuzz=0','-p1',cwd=decoded,stdin=patch)
        run('java','-Xmx1100m','-jar',apktool,'b','-j','2','--no-apk',decoded)
        with ZipFile(base) as archive, ZipFile(work/'unsigned.apk','w') as dest:
            manifest = axml.Doc(archive.read('AndroidManifest.xml'))
            manifest.elements()[0].set('versionCode',16,41)
            manifest.elements()[0].set('versionName',3,manifest.pool.add('1.7.17'))
            changes = {'AndroidManifest.xml':manifest.encode(),'classes.dex':(decoded/'build/apk/classes.dex').read_bytes(),
                       'classes3.dex':(decoded/'build/apk/classes2.dex').read_bytes(),'classes6.dex':(dex/'classes.dex').read_bytes()}
            for arch in ('armeabi-v7a','arm64-v8a'):
                name='lib/'+arch+'/libmultiplayer.so'
                binary=archive.read(name)
                assert binary.count(b'RUSSIA RP 1.7.16%.0s')==1
                changes[name]=binary.replace(b'RUSSIA RP 1.7.16%.0s',b'RUSSIA RP 1.7.17%.0s')
            for entry in archive.infolist():
                if not re.fullmatch(r'META-INF/[^/]+\.(RSA|DSA|EC|SF|MF)',entry.filename,re.I):
                    dest.writestr(entry,changes[entry.filename] if entry.filename in changes else archive.read(entry))
        run(sdk/'zipalign','-f','-P','16','4',work/'unsigned.apk',work/'aligned.apk')
        run(sdk/'apksigner','sign','--ks',keystore,'--ks-pass','file:'+str(password_file),'--out',output,work/'aligned.apk')
        run(sdk/'apksigner','verify','--verbose',output)
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['base','apktool','sdk','keystore','password_file','output','xml_module']:
        parser.add_argument('--'+name.replace('_','-'), required=True, type=Path)
    build(**vars(parser.parse_args()))
