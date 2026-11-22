"""Drive the released client on empty storage; observe its cache and game through normal UI."""
import re,time,subprocess
import full_check as ui
from observe import state
from fresh import nodes
ui.nodes=nodes
def failure():
    s=ui.adb('logcat','-b','crash','-d','-v','brief')
    return {'process':ui.PKG} if '>>> '+ui.PKG+' <<<' in s or 'Process: '+ui.PKG+',' in s else None
ui.crash=failure
assert ui.facts()==(False,0)
ui.adb('logcat','-c')
ui.adb('shell','am','start','-W','-n',ui.PKG+'/blackrussia.online.activities.SplashActivity')
button=ui.wait_until_play(); assert ui.facts()==(False,0);ui.tap(button)
seen=set();start=time.monotonic();game=None;last=None;download=False
while time.monotonic()-start<480:
    current=state()
    if current!=last:print('ACTIVITY',current,flush=True);last=current
    if current=='download' and not download and ui.facts()[1]>0:download=True;print('STOCK_DOWNLOAD',flush=True)
    if current=='game' and game is None:game=time.monotonic()
    r=subprocess.run(['adb','exec-out','tail','-c','130000','/sdcard/Weik/reBRClientLog.txt'],capture_output=True,timeout=8)
    s=r.stdout.decode('utf8','replace') if r.returncode==0 else ''
    for n in re.findall(r'Open: [^\r\n]*/(WRmap_Arzamas(?:_[0-9]+)?\.ipl)\b',s,re.I):
        if n.lower() not in seen:seen.add(n.lower());print('SCENE',n,flush=True)
    if 'SIGSEGV' in s or failure():raise RuntimeError('App crashed during stock entry')
    if current=='game' and game and 'wrmap_arzamas_5.ipl' in seen and time.monotonic()-game>25:
        print('CLEAN_ARM_PASS',download,len(seen),flush=True);break
    if game and time.monotonic()-game>125:raise RuntimeError('No later map observed')
    time.sleep(2)
else:raise RuntimeError('Timed out on '+str(last))
