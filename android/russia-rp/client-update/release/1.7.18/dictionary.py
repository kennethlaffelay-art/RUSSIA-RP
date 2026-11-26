# Recreate a compression dictionary from the prior public APK. No signing keys are used.
import json,shutil,sys,zlib
from zipfile import ZipFile
from pathlib import Path
base,edits,out=map(Path,sys.argv[1:])
with base.open('rb') as src,out.open('wb') as dest,ZipFile(base) as z:
    shutil.copyfileobj(src,dest)
    dex=bytearray(z.read('classes3.dex'))
    for offset,hexbytes in json.loads(edits.read_text()):
        b=bytes.fromhex(hexbytes)
        dex[offset:offset+len(b)]=b
    enc=zlib.compressobj(6,zlib.DEFLATED,-15)
    dest.write(enc.compress(dex)+enc.flush())
