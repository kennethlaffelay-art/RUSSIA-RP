"""Replace verified DXT5 radar records without moving any texture in the database."""
import hashlib, io, json, struct
from pathlib import Path
from PIL import Image
from itertools import accumulate

def decode(packed):
    off=0; blocks=[]
    while off<len(packed):
        count=1
        if packed[off]==1:
            count=packed[off+1];off+=2
        block=packed[off:off+16]
        assert len(block)==16 and count>0
        blocks.extend([block]*count);off+=16
    return b''.join(blocks)

def pack_to_length(pixels,length):
    blocks=[pixels[i:i+16] for i in range(0,len(pixels),16)]
    assert len(blocks)==256
    # The first byte 1 is reserved by the game's block run encoder.
    blocks=[b if b[0]!=1 else bytes([2])+b[1:] for b in blocks]
    size=len(blocks)
    runs=[1]*size
    for i in range(size-2,-1,-1):
        if blocks[i]==blocks[i+1]:runs[i]=min(255,runs[i+1]+1)
    lengths=[0]*(size+1)
    lengths[size]=1
    mask=(1<<(length+1))-1
    for i in range(size-1,-1,-1):
        candidates=lengths[i+1]<<16
        for n in range(2,runs[i]+1):
            candidates|=lengths[i+n]<<18
        lengths[i]=candidates&mask
    if not (lengths[0]>>length)&1:raise ValueError(f'Cannot fit sprite into original {length} bytes')
    left=length;i=0;result=bytearray()
    while i<size:
        for n in range(runs[i],0,-1):
            cost=16 if n==1 else 18
            if left>=cost and (lengths[i+n]>>(left-cost))&1:
                if n>1:result.extend(bytes([1,n]))
                result.extend(blocks[i]);left-=cost;i+=n;break
        else:raise AssertionError(i)
    assert left==0 and decode(result)==b''.join(blocks)
    return bytes(result)
def emit(path, original, edits, out):
    modified=bytearray(original)
    delta=bytearray(struct.pack('>IQI',0x57533134,len(original),len(edits)))
    for offset,value in sorted(edits):
        delta.extend(struct.pack('>QI',offset,len(value)))
        delta.extend(value);modified[offset:offset+len(value)]=value
    (out/(path.split('/')[-1]+'.patch')).write_bytes(delta)
    # Store a validation sample that also changes when upgrading an existing install.
    for offset,value in sorted(edits):
        for j in range(0,len(value)):
            sample=value[j:j+min(20,len(value))]
            if sample and original[offset+j:offset+j+len(sample)]!=sample:
                return dict(path=path,size=len(original),old=hashlib.sha256(original).hexdigest(),
                            updated=hashlib.sha256(modified).hexdigest(),offset=offset+j,sample=sample.hex())
    raise ValueError('No changed bytes')
def build(database,assets,out):
    out.mkdir(parents=True,exist_ok=True)
    rows=(database/'txd.txt').read_text().splitlines()
    ids={r.split('"')[1]:i for i,r in enumerate(rows) if r.startswith('"')}
    table=(database/'txd.dxt.toc').read_bytes()
    data=(database/'txd.dxt.dat').read_bytes()
    thumbs=(database/'txd.dxt.tmb').read_bytes()
    cursor=0;thumb_offsets={}
    for i in range(1,len(rows)):
        # Only actual records have offsets in the table. Text aliases do not have thumbnails.
        if i>max(ids[k] for k in ids if k.startswith('radar_')):break
        thumb_offsets[i]=cursor
        sz=struct.unpack_from('<I',thumbs,cursor+8)[0];cursor+=12+sz
    dat_edits=[]; tiny_edits=[]
    for row in json.loads((assets/'markers.json').read_text()):
        if not row['texture']:continue
        idx=ids[row['texture']]
        start,end=struct.unpack_from('<II',table,idx*4)
        tag,width,height,length,flag=struct.unpack_from('<IHHII',data,start)
        assert width==height==64 and length+12==end-start and flag==1
        assert len(decode(data[start+16:end]))==4096
        icon=Image.open(assets/'radar'/(row['id']+'.png')).convert('RGBA')
        buffer=io.BytesIO();icon.save(buffer,format='DDS',pixel_format='DXT5')
        raw=buffer.getvalue()[128:]
        encoded=pack_to_length(raw,end-start-16)
        dat_edits.append((start+16,encoded))
        displayed=Image.frombytes('RGBA',(64,64),decode(encoded),'bcn',(3,))
        (out/'decoded').mkdir(exist_ok=True)
        displayed.save(out/'decoded'/(row['id']+'.png'))
        offset=thumb_offsets[idx]
        tag_t,w,h,bytes_t,mode=struct.unpack_from('<IHHII',thumbs,offset)
        assert (tag_t&65535)==(tag&65535) and (w,h,bytes_t,mode)==(1,1,8,0)
        tiny_edits.append((offset+16,icon.resize((1,1),Image.Resampling.BOX).tobytes()))
    output=[emit('texdb/txd/txd.dxt.dat',data,dat_edits,out),emit('texdb/txd/txd.dxt.tmb',thumbs,tiny_edits,out)]
    (out/'records.json').write_text(json.dumps(output,indent=2)+'\n')
    print(len(dat_edits),'updated radar records',[(p['path'],p['size']) for p in output])
if __name__=='__main__':
    import sys
    build(*map(Path,sys.argv[1:]))
