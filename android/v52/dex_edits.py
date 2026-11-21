import hashlib
import struct
import zlib

def finish(b):
    b[12:32]=hashlib.sha1(b[32:]).digest()
    struct.pack_into('<I',b,8,zlib.adler32(b[12:])&0xffffffff)
    return b

class Dex:
    def __init__(self,data):
        self.b=bytearray(data)
        self.strings=[]
        for i in range(self.u32(56)):
            _,p=self.leb(self.u32(self.u32(60)+i*4))
            self.strings.append(self.b[p:self.b.index(0,p)].decode('utf8','replace'))
        self.types=[self.strings[self.u32(self.u32(68)+4*i)] for i in range(self.u32(64))]
    def u32(self,p):return struct.unpack_from('<I',self.b,p)[0]
    def leb(self,p):
        v=shift=0
        while True:
            c=self.b[p];p+=1;v|=(c&127)<<shift
            if c<128:return v,p
            shift+=7
    def methods(self):
        for i in range(self.u32(88)):
            t,proto,name=struct.unpack_from('<HHI',self.b,self.u32(92)+8*i)
            pos=self.u32(76)+12*proto
            lst=self.u32(pos+8)
            args=[] if not lst else [self.types[a] for a in struct.unpack_from('<%dH'%self.u32(lst),self.b,lst+4)]
            yield self.types[t],self.strings[name],''.join(args),self.types[self.u32(pos+4)]
    def cls(self,name):
        return next(p for p in range(self.u32(100),self.u32(100)+32*self.u32(96),32) if self.types[self.u32(p)]==name)
    def code(self,name,method):
        p=self.u32(self.cls(name)+24);counts=[]
        for _ in range(4):n,p=self.leb(p);counts.append(n)
        for _ in range(sum(counts[:2])):_,p=self.leb(p);_,p=self.leb(p)
        methods=list(self.methods())
        for count in counts[2:]:
            mid=0
            for _ in range(count):
                x,p=self.leb(p);mid+=x;_,p=self.leb(p);c,p=self.leb(p)
                if methods[mid][1:]==method:return c+16
        raise KeyError(method)

def fix_game(data):
    d=Dex(data);code=d.code('Lcom/wn/blackrussia/game/Multiplayer;',('onCreate','Landroid/os/Bundle;','V'))
    # The catch still logs the full native-link exception. Supply its tag and message locally.
    start=code+2*0x12a
    original=struct.unpack_from('<7H',d.b,start)
    assert original[0]==0x106e and original[3]==0x090c and original[4]==0x2071
    methods=list(d.methods())
    assert methods[original[5]]==('Landroid/util/Log;','e','Ljava/lang/String;Ljava/lang/String;','I')
    dest=methods.index(('Landroid/util/Log;','e','Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;','I'))
    msg=d.strings.index('initializeClient')
    tag=d.strings.index('Multiplayer')
    struct.pack_into('<7H',d.b,start,0x001a,tag,0x021a,msg,0x3071,dest,0x0920)
    return finish(d.b)

def move_worker(data):
    d=Dex(data);p=d.cls('Lblackrussia/online/Downloader$DownloadFilesTask;')
    n=d.u32(96);end=d.u32(100)+32*n
    d.b[p:end]=d.b[p+32:end]+bytes(32)
    struct.pack_into('<I',d.b,96,n-1)
    m=d.u32(52)
    offsets={struct.unpack_from('<H',d.b,m+4+12*i)[0]:m+4+12*i for i in range(d.u32(m))}
    assert 0xf000 not in offsets and d.u32(offsets[6]+4)==n
    struct.pack_into('<I',d.b,offsets[6]+4,n-1)
    return finish(d.b)
