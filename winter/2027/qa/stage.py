"""Prepare the release's exact assets in the disposable Android test volume."""
import hashlib,json,re,struct,sys
from pathlib import Path
from zipfile import ZipFile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from resources import patch_ranges
root,package,channel=map(Path,sys.argv[1:])
with ZipFile(package) as apk,ZipFile(channel) as ch:
    files=json.loads(apk.read('assets/json/weik-cache.json'))['files']
    for n in ch.namelist():
        dest=root/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(ch.read(n))
    prefix='assets/weik-defaults/'
    for member in apk.namelist():
        if not member.startswith(prefix) or member.endswith('/'):continue
        n=member[len(prefix):];data=apk.read(member)
        if n.endswith('.patch'):
            n=n[:-6];dest=root/n;size,ranges=patch_ranges(data);assert dest.stat().st_size==size
            with dest.open('r+b') as f:
                for at,value in ranges:f.seek(at);f.write(value)
        else:
            dest=root/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        if n in files:
            with dest.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==files[n][0],n
    p=root/'SAMP/plates/rp_font.ttf';p.write_bytes(apk.read('assets/russia/plate.ttf'))
p=root/'SAMP/settings.ini';s=p.read_text('latin1')
for key,value in [('name','Russia_Smoke'),('host','127.0.0.1'),('port','7777')]:
    s,n=re.subn(r'(?m)^'+key+r'[ \t]*=[^\r\n]*',key+' = '+value,s);assert n==1
p.write_text(s,'latin1')
