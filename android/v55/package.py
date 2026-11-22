"""Add the report control to the stock settings layout. Keep every existing resource index."""
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

def chunks(data):
    pos = 8
    while pos < len(data):
        kind, header, size = struct.unpack_from('<HHI', data, pos)
        yield kind, data[pos:pos+size]
        pos += size
    assert pos == len(data)

def u32(data, offset):
    return struct.unpack_from('<I',data,offset)[0]

def setsize(chunk):
    struct.pack_into('<I',chunk,4,len(chunk))
    return chunk

def append_strings(pool, values):
    count, styles, flags, start, style_offset = struct.unpack_from('<5I',pool,8)
    assert styles == style_offset == 0 and flags == 0x100
    offsets = list(struct.unpack_from('<%dI'%count,pool,28))
    body = bytearray(pool[start:])
    for value in values:
        encoded=value.encode('utf-8')
        assert len(value)<128 and len(encoded)<128
        offsets.append(len(body))
        body.extend(bytes([len(value),len(encoded)])+encoded+b'\0')
    while len(body)%4: body.append(0)
    header=bytearray(pool[:28])
    struct.pack_into('<I',header,8,len(offsets))
    struct.pack_into('<I',header,20,28+4*len(offsets))
    return setsize(header+struct.pack('<%dI'%len(offsets),*offsets)+body),count

def settings(xml):
    rows=list(chunks(xml))
    assert rows[0][0]==1
    pool, widget=append_strings(rows[0][1], ['ru.russiarp.report.ReportButton', 'Отправить крашлог'])
    result=bytearray(xml[:8])+pool
    template = [chunk for kind,chunk in rows if kind in (258,259) and u32(chunk,8)==135]
    assert len(template)==2
    node,end=map(bytearray,template)
    struct.pack_into('<I',node,20,widget)
    struct.pack_into('<I',end,20,widget)
    off, stride, total=struct.unpack_from('<HHH',node,24)
    attrs=16+off
    # The style is copied from the existing settings row; the new element needs its own label only.
    ids=[]
    for i in range(total):
        p=attrs+i*stride
        if u32(node,p+16)==0x7f090291: ids.append(p)
        if node[p+15]==3 and u32(node,p+8)!=0xffffffff:
            struct.pack_into('<I',node,p+8,widget+1)
            struct.pack_into('<I',node,p+16,widget+1)
    assert len(ids)==1
    del node[ids[0]:ids[0]+stride]
    struct.pack_into('<HH',node,28,total-1,0)
    setsize(node)
    inserted=0
    for kind,chunk in rows[1:]:
        result.extend(chunk)
        if kind==259 and u32(chunk,8)==41:
            result+=node+end
            inserted+=1
    assert inserted==1
    return setsize(result)

def manifest(xml):
    previous='1.6.6'.encode('utf-16le')
    assert xml.count(previous)==1
    result=bytearray(xml[:8])
    changed=0
    for kind,chunk in chunks(xml.replace(previous,'1.6.7'.encode('utf-16le'))):
        if kind==1:
            count=u32(chunk,8); start=u32(chunk,20); names=[]
            for ofs in struct.unpack_from('<%dI'%count,chunk,28):
                p=start+ofs
                length=2*struct.unpack_from('<H',chunk,p)[0]
                names.append(chunk[p+2:p+2+length].decode('utf-16le'))
        if kind==258 and names[u32(chunk,20)]=='manifest':
            chunk=bytearray(chunk)
            start,stride,count=struct.unpack_from('<HHH',chunk,24)
            for i in range(count):
                p=16+start+i*stride
                if names[u32(chunk,p+4)]=='versionCode':
                    assert u32(chunk,p+16)==22
                    struct.pack_into('<I',chunk,p+16,23);changed+=1
        result+=chunk
    assert changed==1
    return result

if __name__=='__main__':
    base,work=map(Path,sys.argv[1:])
    work=work.resolve()
    with ZipFile(base) as z:
        (work/'res').mkdir(exist_ok=True)
        (work/'res/qb.xml').write_bytes(settings(z.read('res/qb.xml')))
        (work/'AndroidManifest.xml').write_bytes(manifest(z.read('AndroidManifest.xml')))
    names=['res/qb.xml','AndroidManifest.xml','classes6.dex']
    unsigned=work/'unsigned.apk'
    shutil.copyfile(base,unsigned)
    subprocess.run(['zip','-qd',str(unsigned),*names],check=True)
    names.append('classes9.dex')
    for n in names: os.utime(work/n,(946684800,946684800))
    subprocess.run(['zip','-0','-q','-X',str(unsigned),*names],cwd=work,check=True,env=dict(os.environ,TZ='UTC'))
