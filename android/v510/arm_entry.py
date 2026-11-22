"""Observe startup of the game on an ARM64 guest with the exact distribution cache."""
import re, time, subprocess
from pathlib import Path
import full_check as ui
from fresh import nodes
ui.nodes=nodes
pkg=ui.PKG

def adb(*args,timeout=12):
    c=subprocess.run(['adb',*args],capture_output=True,timeout=timeout)
    return c.stdout.decode(errors='replace') if c.returncode==0 else ''

def report():
    log=adb('logcat','-d','-s','AXL:*','*:S',timeout=20)
    # Only application function names, module-relative offsets and cache resource paths.
    paths=[]; frames=[]
    for line in log.splitlines():
        lower=line.lower()
        if ('open:' in lower or 'file not found' in lower) and '/weik/' in lower:
            v=lower.split('/weik/',1)[1].strip(' )')
            if re.fullmatch(r'[a-z0-9_ ./-]+\.(?:img|ide|ipl|col|txd|dat|toc)',v):paths.append(v)
        m=re.search(r'gta: (0x[0-9a-f]+)\]\s*([_a-zA-Z0-9:<>]*)',line,re.I)
        if m:frames.append(m.groups())
    print('MAP_LAST_FILES',paths[-12:],flush=True)
    print('NATIVE_GAME_FRAMES',frames[-24:],flush=True)
    d=adb('logcat','-d','-b','crash',timeout=20)
    app=False
    for line in d.splitlines():
        if '>>> ' in line:app=('>>> '+pkg+' <<<' in line)
        if not app:continue
        signal=re.search(r'signal (\d+ \(SIG\w+\)), code [^,]+',line)
        if signal:print('NATIVE_SIGNAL',signal[0],flush=True)
        f=re.search(r'#(\d+) pc ([0-9a-f]+)\s+(\S+)',line)
        if f and int(f[1])<24:
            print('NATIVE_SYSTEM_FRAME',f[1],f[3].split('/')[-1],f[2],flush=True)
        if 'Scudo ERROR: corrupted chunk header' in line:print('NATIVE_ALLOCATOR_ERROR',flush=True)
    print('NATIVE_APP_SIGSEGV',bool(re.search(r'sigsegv', log,re.I)),flush=True)

ui.adb('logcat','-c')
ui.adb('shell','am','start','-W','-n',pkg+'/blackrussia.online.activities.SplashActivity')
play=ui.wait_until_play()
stage=ui.STAGED
ui.adb('shell','mkdir','-p',stage.rsplit('/',1)[0])
subprocess.run(['adb','push','cache.zip',stage],stdout=subprocess.DEVNULL,check=True,timeout=340)
ui.tap(play)
t=time.monotonic();ingame=None
while time.monotonic()-t<300:
    curr=ui.resumed()
    if 'com.wn.blackrussia.game.Multiplayer' in curr and ingame is None:
        ingame=time.monotonic(); print('STAGE_NATIVE_GAME',flush=True)
    dump=adb('logcat','-d','-s','AXL:I','*:S')
    if ('sigsegv' in dump.lower() or 'sigabrt' in dump.lower() or ('>>> '+pkg+' <<<') in adb('logcat','-b','crash','-d')):
        time.sleep(4);break
    if ingame is not None and time.monotonic()-ingame>40:break
    time.sleep(1)
report()
