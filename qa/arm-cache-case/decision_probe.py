"""Exercise the original game files using the directory spelling required by the engine."""
import os
import subprocess
import zipfile
from pathlib import Path
import observe
import full_check as ui

def mirror():
    with zipfile.ZipFile('cache.zip') as archive:
        for item in archive.infolist():
            base='Rkkdev/data/Decision/'
            if not item.filename.startswith(base) or item.is_dir():continue
            name=item.filename[len(base):].replace('Allowed/', 'allowed/')
            target=Path('seed/Rkkdev/data/decision')/name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(item))

if __name__=='__main__':
    mirror()
    try:observe.main()
    finally:
        # Inspect game entries from this run only.
        buf=ui.adb('logcat','-d','-s','AXL:I','*:S')
        import re
        for line in buf.splitlines():
            match=re.search(r'Error: file not found \(/storage/emulated/0/Weik/([A-Za-z0-9 ./_+-]+)\)',line)
            if match: print('MISSING_GAME_ASSET',match.group(1))
            if 'gta: 0x' in line:
                print('STACK',line.partition('gta: ')[2][:150])
