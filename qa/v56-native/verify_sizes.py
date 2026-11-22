"""Check memory, bookkeeping, cursor and loop coverage independently in the signed APK."""
import struct
import sys
from zipfile import ZipFile

def instruction(data,address):
    return struct.unpack_from('<I',data,address)[0]

def wide(data,address):
    value=instruction(data,address)
    return (value>>5&65535) << ((value>>21&3)*16)

def pair(data,first,second):
    return wide(data,first)|wide(data,second)

with ZipFile(sys.argv[1]) as apk:
    multi=apk.read('lib/arm64-v8a/libmultiplayer.so')
    game=apk.read('lib/arm64-v8a/libGame.so')
    cap, cursor=struct.unpack_from('<ii',multi,0x6a0c8)
    assert cap==1000000 and cursor==-1
    assert pair(multi,0xec00c,0xec010)==16*cap
    assert pair(multi,0xec01c,0xec020)==cap
    assert pair(multi,0xec028,0xec030)==cap
    stop=pair(multi,0xec040,0xec04c)
    # Initialization proceeds in chunks of 40; each flag must be written once.
    assert len(range(39,stop,40))*40==cap and range(39,stop,40)[-1]==cap-1
    assert pair(game,0x4f137c,0x4f1380)==16*cap
    assert pair(game,0x4f138c,0x4f1390)==pair(game,0x4f1394,0x4f1398)==cap
    field=(~wide(game,0x4f13a4)&0xffffffffffffffff)&~(65535<<16)|wide(game,0x4f13a8)
    assert struct.unpack('<Ii',struct.pack('<Q',field))==(cap,-1)
    print('Verified both signed ARM64 initializers, all backing storage, cursor and flag coverage.')
