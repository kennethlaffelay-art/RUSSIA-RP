"""Calculate the Android v2 content digest or assemble an offline-signed APK."""
import hashlib
from pathlib import Path
import struct
import sys

def sections(data):
    off = data.rfind(b'PK\x05\x06', max(0, len(data)-65557))
    assert off >= 0 and off+22+struct.unpack_from('<H',data,off+20)[0]==len(data)
    cd, = struct.unpack_from('<I', data, off+16)
    assert data[cd:cd+4] == b'PK\x01\x02'
    assert cd+struct.unpack_from('<I',data,off+12)[0] == off
    return cd, off

def digest(data, cd, off):
    hashes=[]
    for begin,end in ((0,cd),(cd,off),(off,len(data))):
        for p in range(begin,end,1024*1024):
            block=data[p:min(p+1024*1024,end)]
            hashes.append(hashlib.sha256(b'\xa5'+struct.pack('<I',len(block))+block).digest())
    return hashlib.sha256(b'\x5a'+struct.pack('<I',len(hashes))+b''.join(hashes)).hexdigest()

if __name__ == '__main__':
    command,apk=sys.argv[1:3]
    data=Path(apk).read_bytes()
    cd,off=sections(data)
    ident=digest(data,cd,off)
    if command=='digest':
        print('APK_V2_DIGEST',ident)
        print('UNSIGNED_SHA256',hashlib.sha256(data).hexdigest())
    elif command=='apply':
        import base64,json
        record=json.loads(Path(sys.argv[3]).read_text())
        assert ident==record['content_digest'] and hashlib.sha256(data).hexdigest()==record['unsigned_sha256']
        block=base64.b64decode(record['signing_block'],validate=True)
        assert block[-16:]==b'APK Sig Block 42'
        eocd=bytearray(data[off:])
        struct.pack_into('<I',eocd,16,cd+len(block))
        Path(sys.argv[4]).write_bytes(data[:cd]+block+data[cd:off]+eocd)
    else:
        raise ValueError(command)
