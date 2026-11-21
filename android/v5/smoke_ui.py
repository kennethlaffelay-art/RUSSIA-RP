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
    result=adb('shell','if [ -f /sdcard/Weik.installing/Rkkdev.zip ]; then stat -c %s /sdcard/Weik.installing/Rkkdev.zip; else echo 0; fi')
    return int(result.strip())
def wait_until_play():
    last=''
    for _ in range(45):
        last=resumed()
        if 'online.Downloader' in last or archive_bytes()>0:raise Exception('Unexpected downloader before Play')
        items=nodes()
        play=resource(items,'playButton')
        if play is not None and 'activities.MainActivity' in last:return play
        time.sleep(1)
    raise RuntimeError('Main menu could not be observed: '+last)
def test():
    adb('shell','am','start','-W','-a','android.intent.action.MAIN','-c','android.intent.category.LAUNCHER','-n',PKG+'/blackrussia.online.activities.SplashActivity')
    play=wait_until_play()
    time.sleep(3)
    if archive_bytes()!=0:raise RuntimeError('The archive download started in the menu')
    tap(play)
    for _ in range(35):
        current=resumed()
        items=nodes()
        if 'online.Downloader' in current and resource(items,'loadingPercent') is not None and resource(items,'progressBar') is not None:
            for _ in range(25):
                if archive_bytes()>0:
                    print('Verified: the original menu was idle, and actual bytes arrived on the original loading screen after tapping Play.')
                    return
                time.sleep(1)
            raise RuntimeError('The screen appeared, but archive bytes were not observed')
        time.sleep(1)
    raise RuntimeError('The stock downloader did not appear after Play: '+resumed())
test()
