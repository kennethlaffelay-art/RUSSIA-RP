"""UI-driven test using a throwaway receiver on a clean device. No real report is sent."""
import subprocess,time,re
import full_check as ui

def control(key=None,label=None,attempts=12):
    for _ in range(attempts):
        nodes=ui.nodes()
        for n in nodes:
            if key and n.get('resource-id')==ui.PKG+':id/'+key:return n
            if label and label.lower() in (n.get('text','')+' '+n.get('content-desc','')).lower():return n
        time.sleep(.5)
    raise RuntimeError(f'UI control {key or label} missing, activity={ui.resumed()}')

def start():
    ui.adb('shell','am','start','-W','-n',ui.PKG+'/blackrussia.online.activities.SplashActivity')
    ui.wait_until_play()
    assert ui.facts()==(False,0)

def send(mode):
    ui.tap(control(key='settingsButton'))
    ui.tap(control(label='Отправить крашлог'))
    target=control(label='RRP QA Receiver')
    ui.tap(target)
    for _ in range(10):
        logs=ui.adb('logcat','-d','-s','ShareProbe:I')
        if 'RECEIVED '+mode in logs:
            assert ui.facts()==(False,0)
            print('Verified recipient opened '+mode+' ZIP',flush=True)
            return
        if 'FAILED' in logs:raise RuntimeError(logs[-300:])
        time.sleep(1)
    raise RuntimeError('Chosen receiver did not consume report')

def push(dest,data):
    from pathlib import Path
    Path('fixture.bin').write_bytes(data)
    ui.adb('push','fixture.bin',dest)
def main():
    ui.adb('logcat','-c')
    start()
    send('clean')
    # Seed a tiny invented tombstone while the first session still exists, then relaunch.
    stamp=ui.adb('shell','date','+%s%3N').strip()
    assert stamp.isdigit() and len(stamp)==13
    root='/sdcard/Android/data/'+ui.PKG+'/files/Weik'
    ui.adb('shell','mkdir','-p',root,'/sdcard/Weik')
    push(root+'/crash-native-'+stamp+'.tombstone.pb',b'\x52\x09\x12\x07SIGSEGV')
    push('/sdcard/Weik/reBRClientLog.txt',b'loading TEXDB/test/fixture.dxt.dat\npassword=SECRET_QA\n')
    ui.adb('shell','am','force-stop',ui.PKG)
    start()
    send('crash')
    ui.tap(control(key='monitoringButton'))
    play=control(key='playButton')
    assert ui.facts()==(False,0)
    ui.tap(play)
    for _ in range(50):
        if ui.phase()=='download' and ui.archive_bytes()>0:
            print('Verified stock Play and real GitHub download',flush=True);return
        time.sleep(1)
    raise RuntimeError('No cache bytes on downloader after stock Play')

if __name__=='__main__':main()
