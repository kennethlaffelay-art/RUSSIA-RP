from pathlib import Path
from zipfile import ZipFile,ZIP_STORED
import shutil,struct,sys
from dex_edits import move_worker

source,dest=map(Path,sys.argv[1:])
shutil.copyfile(source,dest)
with ZipFile(source) as apk,dest.open('r+b') as out:
    primary=apk.getinfo('classes.dex')
    assert primary.compress_type==ZIP_STORED
    out.seek(primary.header_offset+26)
    filename,extra=struct.unpack('<HH',out.read(4))
    out.seek(primary.header_offset+30+filename+extra)
    out.write(move_worker(apk.read('classes.dex')))
    out.seek(0,2)
    out.write(apk.read('classes4.dex'))
