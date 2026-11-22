"""Observe release installation, the real Play button, the cache and the first scene."""
import io
import time
from pathlib import Path
import re
import subprocess
import full_check as ui
from fresh import nodes
from PIL import Image

ui.nodes=nodes
package=ui.PKG
game='com.wn.blackrussia.game.Multiplayer'
def label(result):
    Path('world-result.txt').write_text(result+'\n')
    print('WORLD_RESULT', result, flush=True)
def game_visible():
    capture=subprocess.check_output(['adb','exec-out','screencap','-p'],timeout=12)
    im=Image.open(io.BytesIO(capture)).convert('RGB')
    w,h=im.size
    if w<=h:
        return False
    pixels=list(im.crop((w//4,h//4,w*3//4,h*3//4)).resize((40,24)).getdata())
    return sum(max(p)>35 for p in pixels)>len(pixels)*.40 and len(set(pixels))>100
def app_crashed():
    s=ui.adb('logcat','-b','crash','-d','-v','brief')
    if ('>>> '+package+' <<<' in s or 'Process: '+package+',' in s):
        return 'native-crash' if '>>> '+package+' <<<' in s else 'java-crash'
    return None

assert ui.facts()==(False,0)
ui.adb('logcat','-c')
ui.adb('shell','am','start','-W','-n',package+'/blackrussia.online.activities.SplashActivity')
play=ui.wait_until_play()
time.sleep(4)
assert ui.facts()==(False,0) and 'activities.MainActivity' in ui.resumed()
print('MENU_WITHOUT_DOWNLOAD',flush=True)
ui.tap(play)
started=time.monotonic()
download=False
installed=False
game_at=None
last_bytes=0
saw_map=False
first_lit=None
while time.monotonic()-started<500:
    resumed=ui.resumed()
    mark,size=ui.facts()
    if not download and size>0 and 'online.Downloader' in resumed:
        download=True
        print('PLAY_STARTED_STOCK_DOWNLOAD',flush=True)
    if mark and not installed:
        installed=True
        print('CACHE_READY',flush=True)
    if size-last_bytes>256_000_000:
        last_bytes=size
        print('ARCHIVE_MB',size//1_000_000,flush=True)
    crash=app_crashed()
    if crash:
        label(crash)
        break
    if game in resumed:
        if game_at is None:
            game_at=time.monotonic()
            print('GAME_ACTIVITY_ENTERED',flush=True)
        # Inspect only the current synthetic device. Raw log contents stay on it.
        cmd=['adb','shell',"grep -iq 'WRmap_Arzamas.*\\.ipl' /sdcard/Weik/reBRClientLog.txt"]
        saw_map |= subprocess.run(cmd,capture_output=True,timeout=10).returncode==0
        if time.monotonic()-game_at>12 and game_visible() and saw_map:
            if first_lit is None:
                first_lit=time.monotonic()
            elif time.monotonic()-first_lit>=5:
                label('map-files-and-lit-screen')
                break
        else:
            first_lit=None
        if time.monotonic()-game_at>95:
            label('scene-unconfirmed')
            break
    if not download and time.monotonic()-started>100:
        raise RuntimeError('Stock download was not observed after Play')
    time.sleep(2)
else:
    label('entry-timed-out')
assert download, 'did not observe download after Play'
assert installed, 'cache did not complete on the test device'
