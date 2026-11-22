"""Drive the stock Play button with the distributed cache and observe actual game milestones."""
import json,re,subprocess,time,zipfile
from pathlib import Path
import full_check as ui
from observe import state
from fresh import nodes
ui.nodes=nodes

def report_cache():
    data=Path('cache.zip')
    import hashlib
    with data.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()=='1cdd9c76725fdd1ab07f196a9e5fdcafd5c5808ba883f71701cfa5e0d33d77ea'
    with zipfile.ZipFile(data) as z:
        names=[n for n in z.namelist() if n not in ('Rkkdev/SAMP/crash_log.log','Rkkdev/SAMP/samp_log.txt','Rkkdev/reBRClientLog.txt')]
        z.extractall('seed',members=names)
    p=Path('seed/Rkkdev');(p/'.russia-cache-1cdd9c76725fdd1a').touch()
    subprocess.run(['adb','push',str(p),'/sdcard/Weik'],stdout=subprocess.DEVNULL,check=True,timeout=900)

def run():
    report_cache()
    ui.adb('logcat','-c')
    ui.adb('shell','am','start','-W','-n',ui.PKG+'/blackrussia.online.activities.SplashActivity',timeout=90)
    button=ui.wait_until_play()
    ui.tap(button)
    started=time.monotonic();last=None;labels=set();seen=set();gamesince=None;maximum=0
    while time.monotonic()-started<200:
        now=state()
        if now!=last:print('ACTIVITY',now,flush=True);last=now
        if now=='game' and gamesince is None:gamesince=time.monotonic()
        proc=subprocess.run(['adb','exec-out','tail','-c','100000','/sdcard/Weik/reBRClientLog.txt'],capture_output=True,timeout=9)
        text=proc.stdout.decode('utf8','replace') if proc.returncode==0 else ''
        if not text:
            text=ui.adb('logcat','-d','-s','AXL:I','*:S',timeout=20)
        scenes=re.findall(r'Open: [^\r\n]*/(WRmap_Arzamas(?:_[0-9]+)?\.ipl)\b',text,re.I)
        for n in scenes:
            if n.lower() in seen:continue
            seen.add(n.lower());print('SCENE',n,flush=True)
        if re.search(r'SIG(?:SEGV|ABRT|BUS)',text):
            print('FATAL_GAME_SIGNAL',flush=True);raise RuntimeError('game log records signal')
        failure=ui.crash()
        if failure:print('PROCESS_CRASH',failure,flush=True);raise RuntimeError('process exited')
        if 'wrmap_arzamas_5.ipl' in seen and now=='game' and time.monotonic()-gamesince>35:break
        if now=='game' and int(time.monotonic()-started)//25>maximum:
            maximum+=1
            try: labels.update(ui.known_ui(ui.capture_words()))
            except (OSError,subprocess.SubprocessError):pass
        time.sleep(3)
    print('MAP_TEST',json.dumps({'scenes':sorted(seen),'game_visible':state()=='game','labels':sorted(labels),'seconds':round(time.monotonic()-started)}),flush=True)
    if not gamesince or state()!='game':raise RuntimeError('Game unavailable')
    if 'wrmap_arzamas_5.ipl' not in seen:raise RuntimeError('Map milestone not observed on this GPU')

if __name__=='__main__': run()
