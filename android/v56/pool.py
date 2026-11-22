"""Resize the ARM64 world-sector list pool coherently in the two shipped initializers."""
from hashlib import sha256
from struct import pack_into, unpack_from

CAPACITY = 1_000_000
DIGESTS = {
    'libGame.so': 'babb5ac55aa151ac54fcd10e41612186af7ed88211c8306ba960190013328d8f',
    'libmultiplayer.so': 'd1f2ccd71d34425d808244531450e6beacceaf4c96d43d610be416bf08df247a',
}

def replace_size(data, low, high, before, after, negative=False):
    """Change only the immediate value, retaining the destination, width, and operation."""
    for pos, shift in ((low, 0), (high, 16)):
        ins, = unpack_from('<I', data, pos)
        old = (before >> shift) & 0xffff
        new = (after >> shift) & 0xffff
        if negative and not shift:
            old ^= 0xffff
            new ^= 0xffff
        assert (ins >> 5) & 0xffff == old
        pack_into('<I', data, pos, (ins & ~(0xffff << 5)) | (new << 5))

def resize(name, payload):
    assert sha256(payload).hexdigest() == DIGESTS[name]
    data=bytearray(payload)
    if name=='libGame.so':
        count=75_000
        replace_size(data,0x4f137c,0x4f1380,count*16,CAPACITY*16)
        replace_size(data,0x4f138c,0x4f1390,count,CAPACITY)
        replace_size(data,0x4f1394,0x4f1398,count,CAPACITY)
        replace_size(data,0x4f13a4,0x4f13a8,count,CAPACITY,negative=True)
    else:
        count=100_000
        assert CAPACITY % 40 == count % 40 == 0
        replace_size(data,0xec00c,0xec010,count*16,CAPACITY*16)
        replace_size(data,0xec01c,0xec020,count,CAPACITY)
        replace_size(data,0xec028,0xec030,count,CAPACITY)
        replace_size(data,0xec040,0xec04c,count+39,CAPACITY+39)
        assert unpack_from('<ii',data,0x6a0c8)==(count,-1)
        pack_into('<I',data,0x6a0c8,CAPACITY)
    return data
