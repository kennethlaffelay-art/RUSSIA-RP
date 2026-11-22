"""Use package-specific crash evidence on native Android; system services run independently."""
import re,time,json
import full_check as ui
import map_entry as probe
from map_entry import run
def process_crash():
    try: crashes=ui.adb('logcat','-b','crash','-d','-v','brief')
    except Exception:return None
    if '>>> '+ui.PKG+' <<<' in crashes or 'Process: '+ui.PKG+',' in crashes:
        return {'app':ui.PKG}
    return None
ui.crash=process_crash
stock_state=probe.state
last_inspected=0
def status():
    global last_inspected
    state=stock_state()
    if state!='download' or time.monotonic()-last_inspected<18:return state
    last_inspected=time.monotonic()
    items=ui.nodes()
    known={}
    for key in ('loadingText','loadingPercent','repeatButton'):
        n=ui.resource(items,key)
        if n is not None:known[key]=n.get('text','')[:160]
    print('DOWNLOADER_STATUS',json.dumps(known,ensure_ascii=False),flush=True)
    return stock_state()
probe.state=status
run()
