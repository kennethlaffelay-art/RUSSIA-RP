from pathlib import Path
from zipfile import ZipFile
import shutil,sys
source,dest=map(Path,sys.argv[1:])
shutil.copyfile(source,dest)
with ZipFile(source) as apk,dest.open('ab') as out:
    out.write(apk.read('classes4.dex'))
