"""Check a first launch with the previously verified cache in a disposable Android system."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
import zipfile

import full_check as ui

PKG=ui.PKG
def log(name,**rows): print(name,json.dumps(rows,ensure_ascii=False),flush=True)
def shell(*args,timeout=45):return ui.adb('shell',*args,timeout=timeout)
def state():
    dump=shell('dumpsys','activity','activities')
    for line in dump.splitlines():
        if 'mResumedActivity' in line or 'topResumedActivity=' in line or 'ResumedActivity:' in line:
            if PKG+'/.game.Multiplayer' in line or ui.GAME in line:return 'game'
            if 'MainActivity' in line and PKG in line:return 'menu'
            if 'Downloader' in line and PKG in line:return 'download'
            return 'outside'
    return 'unknown'

def main():
    z=Path('cache.zip'); assert hashlib.file_digest(z.open('rb'),'sha256').hexdigest()=='1cdd9c76725fdd1ab07f196a9e5fdcafd5c5808ba883f71701cfa5e0d33d77ea'
    with zipfile.ZipFile(z) as a:
        names=[n for n in a.namelist() if n not in {'Rkkdev/SAMP/crash_log.log','Rkkdev/SAMP/samp_log.txt'}]
        a.extractall('seed',members=names)
    path=Path('seed/Rkkdev')
    (path/'.russia-cache-1cdd9c76725fdd1a').touch()
    subprocess.run(['adb','push',str(path),'/sdcard/Weik'],stdout=subprocess.DEVNULL,check=True,timeout=900)
    log('CACHE_SEEDED')
    ui.adb('logcat','-c')
    shell('am','start','-W','-n',PKG+'/blackrussia.online.activities.SplashActivity',timeout=120)
    button=None
    for _ in range(34):
        items=ui.nodes()
        notice=ui.resource(items,'message');ok=ui.resource(items,'ok')
        if notice is not None and ok is not None and 'Политик' in notice.get('text',''):
            ui.tap(ok);continue
        # Dismiss only Android's compatibility notice or grant its standard notification prompt.
        dialog=next((n for n in items if n.get('resource-id')=='android:id/button1' and n.get('text','').lower() in ('ok','ок')),None)
        notification=next((n for n in items if n.get('resource-id','').endswith(':id/permission_allow_button')),None)
        immersive=next((n for n in items if n.get('resource-id')=='android:id/ok'),None)
        if immersive is not None and any(n.get('resource-id')=='android:id/immersive_cling_title' for n in items):
            ui.tap(immersive);continue
        if dialog is not None:ui.tap(dialog);continue
        if notification is not None:ui.tap(notification);continue
        button=ui.resource(items,'playButton')
        if button is not None:break
        time.sleep(1)
    if button is None:
        log('MENU_RESOURCES',ids=sorted({n.get('resource-id','') for n in items if n.get('resource-id')}))
        raise RuntimeError('Stock menu did not open: '+state())
    log('MENU_READY',screen=state())
    ui.tap(button)
    started=time.monotonic();last='';opened=False;known=set();num=0
    while time.monotonic()-started<180:
        screen=state()
        if screen!=last:log('SCREEN',screen=screen,after_s=round(time.monotonic()-started));last=screen
        if screen=='game':
            opened=True
            if num<7:
                try:
                    detected=ui.known_ui(ui.capture_words())
                    log('OCR',labels=detected)
                    known.update(detected)
                except (OSError,subprocess.SubprocessError):pass
                num+=1
        if ui.crash():log('PROCESS_CRASH',report=ui.crash());break
        if opened and screen=='game' and time.monotonic()-started>120:break
        time.sleep(3)
    known.update(ui.runtime_labels())
    for name in ('/sdcard/Weik/SAMP/crash_log.log','/sdcard/Weik/reBRClientLog.txt'):
        record=subprocess.run(['adb','exec-out','tail','-c','131072',name],capture_output=True,timeout=10).stdout.decode('utf8','replace')
        # Report only native game frame identifiers generated in this CI session.
        frames=re.findall(r'lib(?:Game|multiplayer|GTASA|samp)\.so\s*\+\s*(?:0x)?[0-9a-fA-F]+',record)
        if frames:log('NATIVE_GAME_FRAMES',frames=frames[-20:])
    log('RESULT',game_opened=opened,final_screen=state(),observed_s=round(time.monotonic()-started),labels=sorted(known),new_crash=bool(ui.crash()))
    if ui.crash() or state()!='game':raise RuntimeError('64-bit game did not stay open')

if __name__=='__main__':main()
