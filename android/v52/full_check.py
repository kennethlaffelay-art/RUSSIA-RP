"""Verify opening the menu does not download; tap the real Play control and observe the stock downloader."""
import re,subprocess,time
from xml.etree import ElementTree as ET

PKG='com.wn.blackrussia'
def adb(*args, timeout=16):
    return subprocess.check_output(['adb',*args],text=True,timeout=timeout,stderr=subprocess.STDOUT)
def resumed():
    dump=adb('shell','dumpsys','activity','activities')
    return next((l.strip() for l in dump.splitlines() if 'mResumedActivity' in l or 'topResumedActivity=' in l),'')
def nodes():
    try:
        adb('shell','uiautomator','dump','/sdcard/stock-screen.xml')
        return ET.fromstring(adb('exec-out','cat','/sdcard/stock-screen.xml')).findall('.//node')
    except (ValueError,ET.ParseError,subprocess.SubprocessError):return []
def tap(node):
    x1,y1,x2,y2=map(int,re.findall(r'\d+',node.get('bounds','')))
    adb('shell','input','tap',str((x1+x2)//2),str((y1+y2)//2))
def resource(items,key):
    return next((n for n in items if n.get('resource-id')==PKG+':id/'+key),None)
def archive_bytes():
    result=adb('shell','if [ -f /sdcard/Android/data/com.wn.blackrussia/files/russia-cache-v52/Rkkdev.zip.part ]; then stat -c %s /sdcard/Android/data/com.wn.blackrussia/files/russia-cache-v52/Rkkdev.zip.part; else echo 0; fi')
    return int(result.strip())
def wait_until_play():
    last=''
    for _ in range(45):
        last=resumed()
        failure=crash()
        if failure:
            raise RuntimeError('Startup crash: '+json.dumps(failure))
        if 'online.Downloader' in last or archive_bytes()>0:raise Exception('Unexpected downloader before Play')
        items=nodes()
        # The throwaway emulator has never acknowledged the stock first-launch notice.
        notice=resource(items,'message')
        ok=resource(items,'ok')
        if (ok is not None and notice is not None and 'Политик' in notice.get('text','')
                and 'activities.MainActivity' in last):
            tap(ok)
            time.sleep(1)
            continue
        play=resource(items,'playButton')
        if play is not None and 'activities.MainActivity' in last:return play
        time.sleep(1)
    raise RuntimeError('Main menu could not be observed: '+last)

import hashlib,json,os,struct,tempfile
from pathlib import Path

GAME='com.wn.blackrussia.game.Multiplayer'
MARK='/sdcard/Weik/.russia-cache-1cdd9c76725fdd1a'
STAGED='/sdcard/Android/data/com.wn.blackrussia/files/russia-cache-v52/Rkkdev.zip.part'
POLLS={}

def event(name,**info):
    print(name,json.dumps(info,ensure_ascii=False),flush=True)

def phase():
    r=resumed()
    if GAME in r:return 'game'
    if 'online.Downloader' in r:return 'download'
    if 'activities.MainActivity' in r:return 'menu'
    if 'activities.SplashActivity' in r:return 'splash'
    if 'permissioncontroller' in r:return 'permission'
    return 'outside'

def facts():
    # Report only elapsed time and sizes from this clean emulator, never old cache log contents.
    raw=adb('shell',f'if [ -f {MARK} ]; then echo yes; else echo no; fi; su 0 stat -c %s /data/media/0/{STAGED.removeprefix("/sdcard/")} 2>/dev/null || stat -c %s {STAGED} 2>/dev/null || echo 0')
    parts=raw.split()
    return parts[0]=='yes',int(parts[1])

def crash():
    buf=adb('logcat','-b','crash','-d','-v','brief')
    if PKG not in buf:return None
    signals=re.findall(r'signal\s+\d+\s+\(([A-Z]+)\)',buf)
    java=re.findall(r'\b([\w.]+(?:Exception|Error))\b',buf)
    libs=re.findall(r'#\d+\s+pc\s+[\da-f]+\s+[^\n]*?/([^ /!(]+\.so)\b',buf,re.I)
    verifier=[]
    for line in buf.splitlines():
        if 'java.lang.VerifyError:' in line:
            msg=line.split('java.lang.VerifyError:',1)[1].strip()
            # A verifier message contains bytecode types and the failing method, not user input.
            if 'rejected class' in msg.lower() or 'failed to verify' in msg.lower():
                verifier.append(msg.split('(declaration of')[0].strip()[:1600])
    calls=re.findall(r'\bat ((?:com\.wn\.blackrussia|blackrussia\.online)\.[\w.$<>]+)\(',buf)
    fault=re.findall(r'signal \d+ \(SIG[A-Z]+\), code [^,]+, fault addr [^\s]+',buf)
    gameframes=[l.split(' pc ',1)[1].split(' (BuildId:',1)[0].strip()[:230] for l in buf.splitlines() if ' pc ' in l and re.search(r'#\d+',l)][:12]
    return {'fault':fault[:1],'native_stack':gameframes,'signals':sorted(set(signals)),'exceptions':list(dict.fromkeys(java))[:4],
            'frames':list(dict.fromkeys(libs))[:7],'verifier':verifier[:3],
            'java_calls':list(dict.fromkeys(calls))[:8]}

def capture_words():
    # Screenshots stay inside the throwaway runner. Only known UI labels enter the report.
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/'game.png'
        path.write_bytes(subprocess.check_output(['adb','exec-out','screencap','-p'],timeout=18))
        r=subprocess.run(['tesseract',str(path),'stdout','-l','rus+eng','--psm','11'],capture_output=True,text=True,timeout=20)
        return r.stdout

def known_ui(s):
    keys={
        'password prompt':r'введ[иі]те.{0,28}парол|пароль.{0,30}аккаунта|enter.{0,24}password',
        'authorization':r'авторизац|авторизуй|sign in|log in',
        'registration':r'регистрац|зарегистрир|registration|create an account',
        'character selection':r'выбор персонажа|выберите персонажа|выбор места появления|место спавна',
        'server list':r'выбор сервера|выберите сервер|список серверов|select a server|choose a server',
        'server connected':r'соединение установлено|подключены к серверу|connected to server|connection accepted|connected\. joining the game',
        'connecting':r'подключени[ея] к серверу|соединени[ея] с сервером|connecting to',
        'connection error':r'не удалось подключиться|потеряно соединение|сервер недоступен|не отвечает|server didn.t respond|connection (failed|lost|timed out|refused)|unable to connect',
        'game loading':r'загрузка игры|загрузка мира|loading game|loading world',
    }
    return [k for k,pat in keys.items() if re.search(pat,s,re.I|re.S)]

def new_log_labels():
    # The supplied archive already contains an old log. Inspect only bytes from this run.
    size=adb('shell','if [ -f /sdcard/Weik/SAMP/samp_log.txt ]; then stat -c %s /sdcard/Weik/SAMP/samp_log.txt; else echo 0; fi').strip()
    if not size.isdigit() or int(size) in (0,35707837):return set()
    added=int(size)-35707837 if int(size)>35707837 else int(size)
    data=subprocess.check_output(['adb','exec-out','tail','-c',str(min(added,98304)),'/sdcard/Weik/SAMP/samp_log.txt'],timeout=12)
    return set(known_ui(data.decode('utf-8','replace')+' '+data.decode('cp1251','replace')))

def setup_nickname():
    # Only used if the stock launcher explicitly returns to nickname settings after installation.
    items=nodes()
    nick=resource(items,'editText')
    if nick is None:return False
    tap(nick);time.sleep(1)
    items=nodes(); field=next((n for n in items if n.get('class')=='android.widget.EditText'),None)
    save=resource(items,'save')
    if field is None or save is None:return False
    tap(field)
    adb('shell','input','keyevent','123')
    for _ in range(min(32,len(field.get('text',''))+1)):adb('shell','input','keyevent','67')
    suffix=''.join(chr(97+int(c)) for c in str(int(time.time()))[-6:])
    adb('shell','input','text','Guest_'+suffix)
    tap(save);time.sleep(1)
    return True

def verify_assets():
    expected=json.loads(Path('samples.json').read_text())
    for name,sha in expected.items():
        row=adb('shell','sha256sum','/sdcard/Weik/'+name,timeout=150)
        if row.split()[0]!=sha:raise RuntimeError('Installed asset hash mismatch: '+name)
    event('ASSETS_VERIFIED',files=list(expected))

def execute():
    adb('logcat','-c')
    if facts()!=(False,0):raise RuntimeError('Device already has cache')
    adb('shell','am','start','-W','-a','android.intent.action.MAIN','-c','android.intent.category.LAUNCHER','-n',PKG+'/blackrussia.online.activities.SplashActivity')
    button=wait_until_play()
    if facts()!=(False,0):raise RuntimeError('Download began before Play')
    event('CLEAN_MENU',status='no cache or download before tap')
    is_retry=os.environ.get('SCENARIO')=='resume'
    if is_retry:
        # Simulate a previous installation and storage pressure on this throwaway device.
        adb('shell','mkdir','-p','/sdcard/Weik','/sdcard/Weik.previous')
        adb('shell','touch','/sdcard/Weik.previous/qa-sentinel')
        free=int(adb('shell',"df -k /data | tail -1 | awk '{print $4}'").strip())
        adb('shell','fallocate','-l',str((free-4000000)*1024),'/data/local/tmp/russia-fill',timeout=60)
    tap(button)
    if is_retry:
        for _ in range(40):
            items=nodes(); msg=resource(items,'loadingText'); retry=resource(items,'repeatButton')
            if retry is not None and msg is not None and 'Освободите' in msg.get('text',''):break
            time.sleep(1)
        else: raise RuntimeError('Missing accurate low-space message')
        if facts()[1]!=0:raise RuntimeError('Archive written before disk-space check')
        event('LOW_SPACE_HANDLED', message=msg.get('text',''))
        adb('shell','rm','-f','/data/local/tmp/russia-fill')
        tap(retry)
    cut=False; saved=None; restart=False; last_advance=time.monotonic()
    deadline=time.monotonic()+1100
    largest=0; prev=-1; entered=False; last_phase=None
    while time.monotonic()<deadline:
        mark,size=facts(); where=phase()
        if where!=last_phase:event('ACTIVITY',screen=where);last_phase=where
        if where=='download':entered=True
        if where=='download' and not mark and size==0:
            items=nodes()
            msg=resource(items,'loadingText'); pct=resource(items,'loadingPercent')
            if msg is not None and pct is not None and 'Скачивание' in msg.get('text',''):
                value=re.search(r'([0-9]+)',pct.get('text',''))
                if value: size=int(value.group(1))*1488865990//100
        if size>largest:
            last_advance=time.monotonic()
            largest=size
            band=size//100000000
            if band!=prev:event('ARCHIVE_DOWNLOAD',bytes=size);prev=band
        if is_retry and not cut and size>=int(1488865990*.88) and not mark:
            adb('shell','svc','wifi','disable');adb('shell','svc','data','disable')
            cut=True
            for _ in range(36):
                items=nodes();msg=resource(items,'loadingText');retry=resource(items,'repeatButton')
                if retry is not None and msg is not None and 'прервана' in msg.get('text',''):break
                time.sleep(1)
            else:raise RuntimeError('Network interruption did not expose Retry: '+str(facts()))
            saved=facts()[1]
            match=re.search(r'Скачано (\d+) МБ',msg.get('text',''))
            shown_mb=int(match.group(1)) if match else 0
            if not 0<shown_mb<1489: raise RuntimeError('Partial archive lost')
            event('LATE_NETWORK_ERROR',retained_bytes=saved,message=msg.get('text',''))
            adb('shell','svc','data','enable');adb('shell','svc','wifi','enable')
            for _ in range(18):
                if 'VALIDATED' in adb('shell','dumpsys','connectivity'):break
                time.sleep(1)
            time.sleep(4);tap(retry);last_advance=time.monotonic()
        if mark:break
        if where=='download' and time.monotonic()-last_advance>16:
            items=nodes(); msg=resource(items,'loadingText'); retry=resource(items,'repeatButton')
            if retry is not None and msg is not None:
                raise RuntimeError('Unexpected cache error: '+msg.get('text',''))
        c=crash()
        if c:raise RuntimeError('Crash before cache commit: '+json.dumps(c))
        time.sleep(2)
    else:raise RuntimeError('Cache not committed by time limit')
    event('CACHE_COMMITTED',saw_downloader=entered,largest_observed_download=largest)
    if not entered:raise RuntimeError('Stock downloader not observed')
    if 'HTTP 200; starting offset 0' not in adb('logcat','-d','-s','RussiaCache:I','*:S'):
        raise RuntimeError('Initial download request not confirmed')
    if is_retry:
        resume_log=adb('logcat','-d','-s','RussiaCache:I','*:S')
        offsets=re.findall(r'HTTP 206; starting offset (\d+)',resume_log)
        if not offsets:raise RuntimeError('Missing HTTP 206 on retry')
        actual_offset=int(offsets[-1])
        if saved and saved!=actual_offset or actual_offset//1000000!=shown_mb:raise RuntimeError('Partial download offset mismatch')
        if not adb('shell','ls','/sdcard/Weik.previous/qa-sentinel').strip():raise RuntimeError('Backup changed')
        event('VERIFIED_RANGE_RETRY',offset=actual_offset)
    start=time.monotonic();last_phase=None; game_start=None; labels=set(); nick_attempt=False; note=''; abnormal=None; did_game=False
    game_samples=0
    while time.monotonic()-start<200:
        where=phase()
        if where!=last_phase:event('ENTRY_SCREEN',screen=where);last_phase=where
        c=crash()
        if c:
            abnormal=c;event('NEW_APP_CRASH',**c);break
        if where=='game':
            did_game=True
            if game_start is None:game_start=time.monotonic()
            items=nodes()
            words=' '.join(n.get('text','') for n in items)
            try: words+=' '+capture_words()
            except (OSError,subprocess.SubprocessError):pass
            current=set(known_ui(words)) | new_log_labels()
            if current-labels:event('GAME_UI_LABELS',labels=sorted(current-labels))
            labels.update(current);game_samples+=1
            if current & {'password prompt','registration','authorization','character selection'}:
                note='server or account UI observed; no account data submitted';break
            if 'server list' in current:
                target=next((n for n in items if n.get('text','').strip().lower() in ('подключиться','играть','connect','play') and n.get('enabled')=='true'),None)
                if target is not None and not note:
                    tap(target);note='tapped the visible default server action';event('SERVER_BUTTON_TAPPED')
            if time.monotonic()-game_start>100 and game_samples>=4:break
        elif where=='menu' and not nick_attempt and time.monotonic()-start>6:
            if setup_nickname():
                nick_attempt=True;event('LOCAL_NICKNAME_SET',kind='ephemeral guest')
                button=resource(nodes(),'playButton')
                if button is not None:tap(button)
        elif where=='outside' and did_game and time.monotonic()-start>15:
            time.sleep(3);abnormal=crash();break
        time.sleep(3)
    event('ENTRY_RESULT',game_activity_seen=did_game,ocr_samples=game_samples,
          ui_evidence=sorted(labels),last_screen=phase(),note=note,crash=abnormal)
    verify_assets()
    if abnormal:raise RuntimeError('Native or Java crash during entry')
    if not did_game:raise RuntimeError('Game activity did not open')
    if not labels & {'password prompt','registration','authorization','server connected','character selection'}:
        raise RuntimeError('Server entry unconfirmed by UI')

if __name__=='__main__':
    execute()
