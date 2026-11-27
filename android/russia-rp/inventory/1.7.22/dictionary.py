"""Build a zstd dictionary from the exact 1.7.21 Android preview and DEX edits."""
import base64
import hashlib
import json
from pathlib import Path
import shutil
import sys
from zipfile import ZipFile
import zlib

def build(previous, recipe, destination):
    with ZipFile(previous) as apk, previous.open('rb') as source, destination.open('wb') as out:
        shutil.copyfileobj(source,out)
        edit=json.loads(recipe.read_text())
        data=bytearray(apk.read('classes3.dex'))
        for offset, encoded in edit['changes']:
            chunk=base64.b64decode(encoded)
            data[offset:offset+len(chunk)]=chunk
        if hashlib.sha256(data).hexdigest()!=edit['sha256']:
            raise ValueError('Unexpected component')
        encoder=zlib.compressobj(6,zlib.DEFLATED,-15)
        out.write(encoder.compress(data));out.write(encoder.flush())

if __name__=='__main__':
    build(*map(Path,sys.argv[1:4]))
