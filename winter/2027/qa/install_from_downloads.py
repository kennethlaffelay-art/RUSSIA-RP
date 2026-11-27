"""Exercise opening a downloaded APK with Android's Files and package installer."""
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

APK, VERSION = sys.argv[1:]
PACKAGE = 'com.russiarp.winter27.lights'
name = 'RUSSIA-RP-' + VERSION + '.apk'
evidence = Path('evidence')
evidence.mkdir(exist_ok=True)


def adb(*command, check=True):
    return subprocess.run(['adb', *command], capture_output=True, text=True, check=check).stdout


adb('push', APK, '/sdcard/Download/' + name)
adb('shell', 'input', 'keyevent', 'KEYCODE_WAKEUP')
adb('shell', 'wm', 'dismiss-keyguard')
adb('shell', 'am', 'start', '-W', '-a', 'android.intent.action.VIEW',
    '-d', 'content://com.android.externalstorage.documents/document/primary%3ADownload',
    '-t', 'vnd.android.document/directory')
# Files is the install source. Grant the per-source user setting on this disposable image.
for provider in adb('shell', 'pm', 'list', 'packages').splitlines():
    if provider.strip().endswith('.documentsui'):
        adb('shell', 'appops', 'set', provider.strip().split(':')[1], 'REQUEST_INSTALL_PACKAGES', 'allow')
confirmed = False
seen = []
for attempt in range(35):
    time.sleep(1)
    adb('shell', 'uiautomator', 'dump', '/sdcard/install-view.xml', check=False)
    raw = adb('shell', 'cat', '/sdcard/install-view.xml', check=False)
    if not raw.lstrip().startswith('<?xml'):
        continue
    nodes = list(ET.fromstring(raw).iter('node'))
    labels = [n.get('text', '') for n in nodes if n.get('text')]
    if not seen or labels != seen[-1]:
        print('UI:', labels, flush=True)
        seen.append(labels)
        (evidence / ('ui-' + str(len(seen)) + '.xml')).write_text(raw)
    if confirmed and ('versionName=' + VERSION + '\n') in adb('shell','dumpsys','package',PACKAGE):
        break
    for node in nodes:
        label = node.get('text', '')
        if label == name or label.lower() in ('install', 'update', 'continue'):
            x1,y1,x2,y2 = map(int,re.findall(r'\d+',node.get('bounds', '')))
            if label.lower() in ('install', 'update'):
                confirmed = True
            adb('shell','input','tap',str((x1+x2)//2),str((y1+y2)//2))
            break
else:
    raise RuntimeError('Downloads installation did not reach Android success UI')
if 'versionName=' + VERSION not in adb('shell','dumpsys','package',PACKAGE):
    raise RuntimeError('Expected installed version ' + VERSION)
adb('shell','input','keyevent','KEYCODE_HOME')
print('Installed ' + VERSION + ' through Files and the Android package installer', flush=True)
