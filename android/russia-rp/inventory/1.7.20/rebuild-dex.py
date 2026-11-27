from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import hashlib,subprocess,sys
from hook import patch

apk,jar,out=map(Path,sys.argv[1:4])
with TemporaryDirectory(dir=out.resolve().parent) as temp:
    temp=Path(temp)
    with ZipFile(apk) as z,ZipFile(temp/'slice.apk','w') as smaller:
        for path in ['AndroidManifest.xml','resources.arsc','classes3.dex']:
            smaller.writestr('classes.dex' if path=='classes3.dex' else path,z.read(path))
    args=['java','-Xmx1400m','-jar',str(jar)]
    subprocess.run([*args,'d','-r','-j','2',temp/'slice.apk','-o',temp/'source'],check=True)
    patch(temp/'source')
    subprocess.run([*args,'b','-j','2','--no-apk',temp/'source'],check=True)
    dex=(temp/'source/build/apk/classes.dex').read_bytes()
    assert hashlib.sha256(dex).hexdigest()=='b879a702ccdf7ee88eb5f3aa431d397e540febabee83ceb4e8e19f993ac7fedd'
    out.write_bytes(dex)
