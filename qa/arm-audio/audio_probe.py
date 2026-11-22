import zipfile
from pathlib import Path
import runpy
import texture_index
with zipfile.ZipFile('cache.zip') as archive:
    for item in archive.infolist():
        if not item.filename.startswith('Rkkdev/audio/') or item.is_dir():continue
        prefix,rest=item.filename.split('audio/',1)
        if rest.startswith('CONFIG/'):rest=rest.upper()
        target=Path('seed')/prefix/'AUDIO'/rest
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(archive.read(item))
    gui=Path('seed/Rkkdev/texdb/gui/gui.dxt.toc')
    gui.parent.mkdir(parents=True,exist_ok=True)
    gui.write_bytes(texture_index.table(archive,'gui'))
runpy.run_path('decision_probe.py',run_name='__main__')
