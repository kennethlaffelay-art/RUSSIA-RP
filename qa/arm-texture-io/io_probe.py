import os,re,runpy,subprocess,time
from pathlib import Path
import full_check
tap=full_check.tap
observer=None
def tap_play(node):
    global observer
    if node.get('resource-id','').endswith(':id/playButton') and observer is None:
        tasks=subprocess.check_output(['docker','top','arm-android','-eo','pid,args'],text=True)
        for line in tasks.splitlines():
            match=re.fullmatch(r'\s*(\d+)\s+com\.wn\.blackrussia\s*',line)
            if match:
                observer=subprocess.Popen(['sudo','-n','strace','-qq','-f','-s','0','-yy','-e','trace=lseek,pread64,read','-o','asset-io.log','-p',match.group(1)],stderr=subprocess.DEVNULL)
                time.sleep(.3)
                break
    return tap(node)
full_check.tap=tap_play
try:runpy.run_path('map_probe.py',run_name='__main__')
finally:
    if observer is not None:subprocess.run(['sudo','kill','-INT',str(observer.pid)],check=False,stderr=subprocess.DEVNULL)
    if Path('asset-io.log').is_file():
        file_reads=[]
        with open('asset-io.log',errors='replace') as stream:
            for row in stream:
                # Output only filenames, offsets and byte counts for texture archives.
                m=re.search(r'\b(lseek|pread64|read)\(\d+<[^>]+/(texdb/[A-Za-z0-9_/.-]+\.dxt\.dat)>,(.+)',row)
                if m:file_reads.append((m[1],m[2],re.sub(r'"[^"]*"','""',m[3])[:100]))
        print('LAST_TEXTURE_READS',file_reads[-20:])
