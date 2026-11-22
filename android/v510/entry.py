import io, os, re, subprocess, time
from pathlib import Path
from PIL import Image
import full_check as ui
from fresh import nodes
ui.nodes=nodes
pkg=ui.PKG
def call(*args, timeout=12):
    try:
        c=subprocess.run(['adb',*args],capture_output=True,timeout=timeout)
        return c.stdout.decode('utf8','replace') if c.returncode==0 else ''
    except subprocess.TimeoutExpired:
        return ''
def allowed_states():
    r=ui.resumed()
    for key,phrase in [('game','com.wn.blackrussia.game.Multiplayer'),('menu','activities.MainActivity'),('downloader','online.Downloader')]:
        if phrase in r:return key
    return 'other'
def ondevice_cfg():
    from configparser import ConfigParser
    b=call('shell','cat','/sdcard/Weik/SAMP/settings.ini')
    try:
        cfg=ConfigParser(interpolation=None,strict=False,inline_comment_prefixes=('#',';'))
        cfg.read_string(b)
        return cfg.get('client','host',fallback='').strip()=='10.0.2.2' and cfg.get('client','port',fallback='').strip()=='7777'
    except Exception:return False
def surface():
    s=call('shell','cat','/data/data/'+pkg+'/files/russia-diagnostics/surface-state.txt')
    return re.findall(r'(?:[0-9]+s [0-9]+x[0-9]+ shown=(?:true|false)(?: copy=[0-9]+)?(?: lit=[0-9]+/256)?|[0-9]+s surface missing)',s)[-2:]
def screen():
    d=subprocess.run(['adb','exec-out','screencap','-p'],capture_output=True,timeout=12).stdout
    im=Image.open(io.BytesIO(d)).convert('RGB');w,h=im.size
    px=list(im.crop((w//4,h//4,w*3//4,h*3//4)).resize((48,27)).getdata())
    return (w,h,sum(max(p)>35 for p in px),len(set(px)))
def threads(pid):
    if not pid.isdigit():return
    s=call('shell','debuggerd','-b',pid,timeout=18)
    thread=''
    groups={}
    for line in s.splitlines():
        m=re.search(r'^"([^"]+)"',line)
        if m:thread=m.group(1);continue
        if thread not in ('main','MainThread','NVEvent','RenderThread','GameThread','RenderWare') and not any(n in line for n in ('libGame.so','libmultiplayer.so','libEGL.so')):continue
        frame=re.search(r'#(\d+) pc ([0-9a-f]+)\s+(\S+)',line)
        if frame:
            library=frame[3].split('/')[-1].split('!')[-1]
            if not re.fullmatch(r'[A-Za-z0-9_.-]+',library):continue
            groups.setdefault(thread,[]).append((library,frame[2]))
    for i,(name,frames) in enumerate(groups.items()):
        if i>14:break
        print('NATIVE_THREAD',name if name in ('main','MainThread','NVEvent','RenderThread','GameThread','RenderWare') else 'worker',frames[:12],flush=True)
assert ui.facts()==(False,0)
ui.adb('logcat','-c')
ui.adb('shell','am','start','-W','-n',pkg+'/blackrussia.online.activities.SplashActivity')
play=ui.wait_until_play()
assert ui.facts()==(False,0)
print('STAGE_MENU_WITHOUT_DOWNLOAD',flush=True);ui.tap(play)
started=time.monotonic();game=None;last=None;download=installed=opened=False;sample=0;visible=False;stack=False
while time.monotonic()-started<590:
    curr=allowed_states()
    if curr!=last: print('STAGE_ACTIVITY',curr,flush=True);last=curr
    mark,size=ui.facts()
    if not download and size and curr=='downloader': download=True;print('STAGE_DOWNLOADING',flush=True)
    if not installed and mark and ondevice_cfg():installed=True;print('CFG_FIXTURE_CONFIRMED',flush=True)
    if curr=='game' and game is None: game=time.monotonic();opened=True
    if game is not None:
        elapsed=time.monotonic()-game
        if elapsed>=sample*15:
            sample+=1
            log=call('logcat','-d','-s','AXL:I','*:S')
            print('RUNTIME_STAGE',[(k,log.lower().count(k)) for k in ('paths.img','wrmap_arzamas','connection attempt','registered game message handlers','sigsegv','error')],flush=True)
            frame=screen()
            ss=surface()
            print('FRAME_SAMPLE',round(elapsed),frame,ss,flush=True)
            if frame[0]>frame[1] and frame[2]>550 and frame[3]>110 and any(re.search(r'lit=(?:[1-9][0-9]{2}|[4-9][0-9])/256',frag) for frag in ss):visible=True
        if elapsed>45 and not stack:
            threads(call('shell','pidof',pkg).strip().split(' ')[0]);stack=True
        if elapsed>100 or (visible and 'TEST_PLAYER_SPAWNED' in Path('local-server.log').read_text(errors='replace')):break
    if not download and time.monotonic()-started>110:break
    time.sleep(2)
srv=Path('local-server.log').read_text(errors='replace')
udp=Path('local-udp-count.log')
print('RESULT_SUMMARY',dict(download=download,endpoint_installed=installed,game=opened,udp_packets=len(udp.read_text().splitlines()) if udp.exists() else 0,connected='TEST_PLAYER_CONNECTED' in srv,spawned='TEST_PLAYER_SPAWNED' in srv,visible=visible),flush=True)
assert download and installed and opened
