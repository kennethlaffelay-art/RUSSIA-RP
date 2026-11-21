"""Regression: opening the client must show its own menu; only Play opens the stock downloader."""
import hashlib
from pathlib import Path
from zipfile import ZipFile
import sys
from prepare_client import BASE_URL,TAG,NEW_SHA,NEW_SIZE

def verify(base,apk,cache):
    with ZipFile(base) as old, ZipFile(apk) as new:
        assert set(new.namelist())==set(old.namelist())
        changed={n for n in new.namelist() if old.read(n)!=new.read(n)}
        assert changed=={'classes.dex','AndroidManifest.xml'},changed
        manifest=new.read('AndroidManifest.xml')
        assert 'ru.russiarp.cache.CacheActivity'.encode('utf-16le') not in manifest
        assert len([n for n in new.namelist() if n.endswith('.dex')])==6
        dex=new.read('classes.dex')
        assert dex.count((BASE_URL+TAG+'/Rkkdev.zip').encode('utf-16le'))==1
        assert bytes.fromhex(NEW_SHA) in dex
        assert new.testzip() is None
    assert cache.stat().st_size==NEW_SIZE
    with cache.open('rb') as s: assert hashlib.file_digest(s,'sha256').hexdigest()==NEW_SHA
    with ZipFile(cache) as z:
        assert z.testzip() is None
        assert all(p.startswith('Rkkdev/') for p in z.namelist())
        assert z.getinfo('Rkkdev/data/timecyc.dat').file_size>0
        assert z.read('Rkkdev/data/script/script.img')==z.read('Rkkdev/SAMP/script.img')
        assert z.read('Rkkdev/data/vehicles.ide')==z.read('Rkkdev/SAMP/vehicles.ide')
    print('Verified original screen resources, archive layout, pinned URL and both payloads.')
if __name__=='__main__':verify(*map(Path,sys.argv[1:]))
