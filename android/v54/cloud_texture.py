"""Complete the originally transparent cloud texture's mip chain."""
from pathlib import Path
import hashlib
import struct
from zipfile import ZipFile

def corrected(archive):
    base='Rkkdev/texdb/txd/txd'
    names=[l.split(b'"')[1] for l in archive.read(base+'.txt').splitlines() if l.startswith(b'"')]
    data=archive.read(base+'.dxt.dat')
    toc=archive.read(base+'.dxt.toc')
    offsets=list(struct.unpack('<%dI'%(len(toc)//4),toc))
    assert offsets[0]==len(data) and len(offsets)==len(names)+1
    pos=offsets[names.index(b'cloud1')+1]
    tag,dim,length=struct.unpack_from('<III',data,pos)
    raw=data[pos+12:pos+12+length]
    assert (tag>>16,dim,length)==(0x1401,0x80800200,2056)
    assert raw==b'\x01\0\0\0'+bytes.fromhex('01ff00000000')*342
    pixels=sum(max(1,512>>i)*max(1,128>>i) for i in range(10))
    # Preserve every existing zero RGBA pixel and supply the transparent end of the mip chain.
    rgba=bytes(4+pixels*4)
    rec=struct.pack('<III',tag,dim,len(rgba))+rgba
    tail=pos+12+length
    shift=len(rec)-12-length
    new=data[:pos]+rec+data[tail:]
    offsets=[v+shift if v>=tail and v!=0xffffffff else v for v in offsets]
    return new,struct.pack('<%dI'%len(offsets),*offsets)
if __name__=='__main__':
    import sys
    with ZipFile(sys.argv[1]) as archive: data,toc=corrected(archive)
    dest=Path(sys.argv[2]);dest.mkdir(parents=True,exist_ok=True)
    (dest/'txd.dxt.dat').write_bytes(data);(dest/'txd.dxt.toc').write_bytes(toc)
