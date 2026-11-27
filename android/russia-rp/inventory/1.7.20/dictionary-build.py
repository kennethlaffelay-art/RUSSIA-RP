import shutil,sys,zlib
from pathlib import Path
base,updated,dest=map(Path,sys.argv[1:4])
with base.open('rb') as old,dest.open('wb') as out:
    shutil.copyfileobj(old,out)
    encoder=zlib.compressobj(6,zlib.DEFLATED,-15)
    out.write(encoder.compress(updated.read_bytes())+encoder.flush())
