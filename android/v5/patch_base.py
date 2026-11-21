"""Expand stock payloads for a small, reproducible binary distribution patch."""
from pathlib import Path
import shutil, sys
from zipfile import ZipFile
source, out = map(Path, sys.argv[1:])
shutil.copyfile(source,out)
with ZipFile(source) as apk, out.open('ab') as dest:
    for name in ('classes.dex','AndroidManifest.xml'):
        dest.write(apk.read(name))
