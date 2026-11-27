"""Read the mobile IMG and texture records used by client 1.7.22."""
from collections import defaultdict
from itertools import groupby
from io import BytesIO
from pathlib import Path
import struct
from PIL import Image

def img_index(stream):
    stream.seek(0)
    tag, count = struct.unpack('<4sI', stream.read(8))
    if tag != b'VER2':
        raise ValueError('Expected IMG v2')
    return {name.split(b'\0')[0].decode('ascii').lower(): (sector*2048, (size & 65535)*2048)
            for sector, size, name in struct.iter_unpack('<II24s', stream.read(count*32))}

def img_archive(entries):
    start = (8 + 32*len(entries) + 2047)//2048
    directory = bytearray(struct.pack('<4sI', b'VER2', len(entries)))
    payload = bytearray()
    for name, data in entries.items():
        sectors = (len(data)+2047)//2048
        directory.extend(struct.pack('<II24s', start+len(payload)//2048, sectors, name.encode('ascii')))
        payload.extend(data.ljust(sectors*2048, b'\0'))
    return directory.ljust(start*2048, b'\0') + payload

def patch_ranges(data):
    magic, size, count = struct.unpack_from('>IQI', data)
    assert magic == 0x57533134
    cursor = 16
    edits = []
    for _ in range(count):
        off, n = struct.unpack_from('>QI', data, cursor)
        cursor += 12
        edits.append((off, data[cursor:cursor+n]))
        cursor += n
    assert cursor == len(data)
    return size, edits

def merge_ranges(size, earlier, latest):
    merged = list(earlier)
    for off, data in sorted(latest):
        end = off + len(data)
        if not (0 <= off < end <= size):
            raise ValueError('Cache range outside file')
        keep = []
        for pos, old in merged:
            if pos+len(old) <= off or pos >= end:
                keep.append((pos, old))
                continue
            if pos < off:
                keep.append((pos, old[:off-pos]))
            if pos+len(old) > end:
                keep.append((end, old[end-pos:]))
        keep.append((off,data))
        merged = keep
    return sorted(merged)

def serialise_patch(size, edits):
    return struct.pack('>IQI',0x57533134,size,len(edits))+b''.join(
        struct.pack('>QI',pos,len(data))+data for pos,data in edits)

class Textures:
    def __init__(self, root, name):
        base = Path(root)/'texdb'/name
        lines = (base/(name+'.txt')).read_text('latin1').splitlines()
        self.ids = {line.split('"')[1].lower(): i for i,line in
                    enumerate((l for l in lines if l.startswith('"')),1) if 'affiliate=' not in line}
        names=[line.split('"')[1].lower() for line in lines if line.startswith('"') and 'affiliate=' not in line]
        self.thumbs={n:i for i,n in enumerate(names)}
        self.table = (base/(name+'.dxt.toc')).read_bytes()
        self.file = (base/(name+'.dxt.dat')).open('rb')
        self.name = name

    def record(self, name):
        start, end = struct.unpack_from('<II', self.table, 4*self.ids[name.lower()])
        self.file.seek(start)
        data = self.file.read(end-start)
        kind,w,h,length,marker = struct.unpack_from('<IHHII',data)
        assert length+12 == len(data), name
        width, height = w & 32767, h & 32767
        block = {0:8,3:16}[(kind>>16)&15]
        return start, Texture(data,width,height,block,marker)

class Texture:
    def __init__(self, source, w, h, block, marker):
        self.source, self.size, self.block, self.marker = source,(w,h),block,marker
        blocks=[]
        pos=16
        while pos < len(source):
            n=1
            if marker and source[pos]==marker:
                n=source[pos+1]
                pos+=2
            blocks.append(source[pos:pos+block]*n)
            pos+=block
        assert pos==len(source)
        self.raw=b''.join(blocks)

    def image(self):
        return Image.frombytes('RGBA', self.size, self.raw,'bcn',(1 if self.block==8 else 3,))

    def encode(self, image, keep_runs=False):
        image=image.convert('RGBA')
        w,h=self.size
        raw=bytearray()
        while len(raw)<len(self.raw):
            im=image.resize((w,h),Image.Resampling.LANCZOS)
            s=BytesIO()
            im.save(s,format='DDS',pixel_format='DXT1' if self.block==8 else 'DXT5')
            raw.extend(s.getvalue()[128:])
            w,h=max(1,w//2),max(1,h//2)
        assert len(raw)==len(self.raw)
        target=len(self.source)-16
        bs=self.block
        if not self.marker:
            assert len(raw)==target
            return self.source[:16]+raw
        # Tagged singleton runs are valid. The decoder stops at the original record boundary.
        if keep_runs:
            # Preserve the original transparent spans. Sample the most frequent block in
            # each shared run so empty winter sky is never filled from a single branch.
            from collections import Counter
            result=bytearray(self.source[:16]);pos=16;block_at=0
            while pos<len(self.source):
                tagged=self.source[pos]==self.marker
                count=self.source[pos+1] if tagged else 1
                span=raw[block_at:block_at+count*bs]
                best=Counter(bytes(span[i:i+bs]) for i in range(0,len(span),bs)).most_common(1)[0][0]
                if tagged:result.extend((self.marker,count));pos+=2
                elif best[0]==self.marker:best=bytes((best[0]^1,))+best[1:]
                result.extend(best);pos+=bs;block_at+=count*bs
            assert len(result)==len(self.source) and block_at==len(raw)
            return bytes(result)
        groups=[]
        for data,items in groupby(bytes(raw[i:i+bs]) for i in range(0,len(raw),bs)):
            count=sum(1 for _ in items)
            while count:
                n=min(count,255)
                groups.append([n,data])
                count-=n
        def cost(n,b):
            return bs+2 if n>1 or b[0]==self.marker else bs
        left=target-sum(cost(n,b) for n,b in groups)
        if left<0:
            raise ValueError(f'Artwork exceeds record by {-left} bytes')
        output=[]
        for n,b in groups:
            while n>1:
                increase=cost(1,b)+cost(n-1,b)-cost(n,b)
                if increase>left:break
                left-=increase
                output.append([1,b])
                n-=1
            output.append([n,b])
        result=bytearray(self.source[:16])
        for n,b in output:
            if n>1 or b[0]==self.marker:
                result.extend((self.marker,n))
            elif left>=2:
                result.extend((self.marker,1));left-=2
            result.extend(b)
        if left:raise ValueError(f'Cannot fill original record, {left} bytes left')
        assert len(result)==len(self.source)
        return bytes(result)
