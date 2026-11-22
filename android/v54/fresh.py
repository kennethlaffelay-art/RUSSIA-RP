"""Run a clean install and accept only the emulator's fullscreen tutorial."""
import full_check as ui
import re
original_nodes=ui.nodes
def nodes():
    result=original_nodes()
    if any(n.get('resource-id','').endswith(':id/immersive_cling_title') for n in result):
        ok=next((n for n in result if n.get('resource-id','').endswith(':id/ok')),None)
        if ok is not None:
            ui.tap(ok)
            return []
    return result
ui.nodes=nodes
if __name__=='__main__':
    try:ui.execute()
    finally:
        for line in ui.adb('logcat','-d','-s','AXL:I','*:S').splitlines():
            m=re.search(r'Error: file not found \(/storage/emulated/0/Weik/([A-Za-z0-9 ./_+-]+)\)',line)
            if m: print('MISSING_GAME_ASSET',m.group(1))
            if 'gta: 0x' in line: print('STACK',line.partition('gta: ')[2][:160])
