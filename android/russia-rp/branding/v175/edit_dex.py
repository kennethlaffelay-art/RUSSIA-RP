import re,sys
from pathlib import Path
def update(decoded):
    cls=decoded/'smali_classes3/com/wn/blackrussia'
    choose=cls/'game/ui/BrChooseServer.smali'
    s=choose.read_text()
    body=Path(__file__).with_name('list.smali').read_text().rstrip()
    s,n=re.subn(r'^\.method private final buildServerList\(\)V.*?^\.end method$',lambda _:body,s,flags=re.M|re.S)
    assert n==1
    choose.write_text(s)
    cfg=cls/'BuildConfig.smali'
    s=cfg.read_text();assert 'VERSION_CODE:I = 0x1c' in s or 'VERSION_CODE:I = 0x1d' in s
    cfg.write_text(s.replace('VERSION_CODE:I = 0x1c','VERSION_CODE:I = 0x1d').replace('"1.7.4"','"1.7.5"'))
if __name__=='__main__':update(Path(sys.argv[1]))
