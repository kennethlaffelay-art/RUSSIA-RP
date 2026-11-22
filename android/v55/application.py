from pathlib import Path
import sys
p=Path(sys.argv[1])
s=p.read_text()
before='    invoke-super {p0}, Landroid/app/Application;->onCreate()V\n'
assert s.count(before)==1
p.write_text(s.replace(before,before+'\n    invoke-static {p0}, Lru/russiarp/report/Events;->install(Landroid/app/Application;)V\n'))
