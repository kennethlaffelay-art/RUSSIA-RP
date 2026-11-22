import runpy,zipfile
from pathlib import Path
with zipfile.ZipFile('cache.zip') as archive:
    for row in Path('paths.tsv').read_text().splitlines():
        original,requested=row.split('\t')
        target=Path('seed/Rkkdev')/requested
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(archive.read('Rkkdev/'+original))
runpy.run_path('audio_probe.py',run_name='__main__')
