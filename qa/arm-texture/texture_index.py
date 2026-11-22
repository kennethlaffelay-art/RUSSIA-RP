"""Build the missing GUI offset table from the shipped image records."""
import struct
import re
from pathlib import Path
from zipfile import ZipFile

def table(archive,name):
    base='Rkkdev/texdb/'+name+'/'+name
    names=[line for line in archive.read(base+'.txt').splitlines() if line.startswith(b'"')]
    length=archive.getinfo(base+'.dxt.dat').file_size
    offsets=[length]
    with archive.open(base+'.dxt.dat') as stream:
        pos=0
        for line in names:
            if b'"affiliate=' in line:
                offsets.append(0xffffffff)
                continue
            offsets.append(pos)
            rec=stream.read(12)
            if len(rec)!=12:raise ValueError(name+' record header missing')
            dimensions,size=struct.unpack_from('<II',rec,4)
            width=int(re.search(rb'\bwidth=(\d+)',line).group(1))
            height=int(re.search(rb'\bheight=(\d+)',line).group(1))
            if (width,height)!=(dimensions&0x7fff,(dimensions>>16)&0x7fff):
                raise ValueError(name+' dimension mismatch at '+repr(line.split(b'"')[1]))
            pos+=12+size
            if pos>length:raise ValueError(name+' record outside file')
            stream.seek(pos)
        if pos!=length:raise ValueError(name+' unindexed data')
    return struct.pack('<%dI'%len(offsets),*offsets)

if __name__=='__main__':
    import sys
    with ZipFile(sys.argv[1]) as archive:
        for name in ['txd','mobile','player','menu','samp']:
            assert table(archive,name)==archive.read('Rkkdev/texdb/'+name+'/'+name+'.dxt.toc'), name
        Path(sys.argv[2]).write_bytes(table(archive,'gui'))
