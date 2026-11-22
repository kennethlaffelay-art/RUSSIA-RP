"""Use package-specific crash evidence on native Android; system services run independently."""
import re
import full_check as ui
from map_entry import run
def process_crash():
    try: crashes=ui.adb('logcat','-b','crash','-d','-v','brief')
    except Exception:return None
    if '>>> '+ui.PKG+' <<<' in crashes or 'Process: '+ui.PKG+',' in crashes:
        return {'app':ui.PKG}
    return None
ui.crash=process_crash
run()
