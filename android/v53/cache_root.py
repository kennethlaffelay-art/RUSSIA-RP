"""Initialize the game client's existing cache-directory variable before the renderer starts."""
from pathlib import Path
import hashlib,struct,sys

# In these two shipped builds the storage callback assigns this variable after font
# initialization on some devices. Give it the same built-in default at load time.
LAYOUT={
    'arm64-v8a': ('f52c861d2edcaba58fd6a41917b76dce9003396fc7db1101ca316af5a10b2b40',0x6a4c50,0x7417b,1027),
    'armeabi-v7a': ('4bb17e73750799dc0262b11da6e33c3e87c01daebed9d9a0bb2bf75999cd69e3',0x4c2248,0x62b38,23),
}
def initialize_root(source,abi):
    digest,variable,literal,kind=LAYOUT[abi]
    assert hashlib.sha256(source).hexdigest()==digest
    a64=abi=='arm64-v8a'
    hdr=struct.Struct('<16sHHIQQQIHHHHHH' if a64 else '<16sHHIIIIIHHHHHH')
    ph=struct.Struct('<IIQQQQQQ' if a64 else '<IIIIIIII')
    sh=struct.Struct('<IIQQQQIIQQ' if a64 else '<IIIIIIIIII')
    rel=struct.Struct('<QQq' if a64 else '<II')
    dyn=struct.Struct('<QQ' if a64 else '<II')
    h=list(hdr.unpack_from(source)); po,so=h[5:7]
    assert h[9]==ph.size and h[11]==sh.size
    progs=[list(ph.unpack_from(source,po+i*ph.size)) for i in range(h[10])]
    sections=[list(sh.unpack_from(source,so+i*sh.size)) for i in range(h[12])]
    names=sections[h[13]]
    byname={source[names[4]+s[0]:].split(b'\0',1)[0].decode():s for s in sections}
    # Program header field order differs between ELF32 and ELF64.
    off,va,fs,ms=(2,3,5,6) if a64 else (1,2,4,5)
    seg=max((p for p in progs if p[0]==1),key=lambda p:p[va])
    assert (seg[1] if a64 else seg[6])==6
    assert source[literal:literal+26]==b'/storage/emulated/0/Weik/\x00'
    bss=byname['.bss']
    assert bss[1]==8 and bss[3]<=variable< bss[3]+bss[5] <= seg[va]+seg[ms]
    table=byname['.rela.dyn' if a64 else '.rel.dyn']
    assert table[9]==rel.size
    old=source[table[4]:table[4]+table[5]]
    assert all(record[0]!=variable for record in rel.iter_unpack(old))
    idx_addr,idx_size,idx_count=(7,8,0x6ffffff9) if a64 else (17,18,0x6ffffffa)
    dynamic=byname['.dynamic']
    tags={}
    for p in range(dynamic[4],dynamic[4]+dynamic[5],dyn.size):
        tag,value=dyn.unpack_from(source,p)
        if tag:tags[tag]=(value,p)
    assert tags[idx_addr][0]==table[3] and tags[idx_size][0]==len(old)
    count=tags[idx_count][0]
    assert all(record[1]==kind for record in rel.iter_unpack(old[:count*rel.size]))
    entry=rel.pack(variable,kind,literal) if a64 else rel.pack(variable,kind)
    # Keep relative relocations first, as prescribed by DT_REL(A)COUNT.
    added=old[:count*rel.size]+entry+old[count*rel.size:]
    end=seg[off]+seg[fs]
    assert so>=end
    dest=(seg[off]+seg[ms]+15)&~15
    result=bytearray(source[:end])+bytes(dest-end)+added+source[end:]
    shift=dest+len(added)-end
    for s in sections:
        if s[1]!=8 and s[4]>=end and s[4]:s[4]+=shift
    bss[1],bss[4]=1,seg[off]+bss[3]-seg[va]
    if not a64:
        struct.pack_into('<I',result,seg[off]+variable-seg[va],literal)
    table[3]=seg[va]+dest-seg[off];table[4]=dest;table[5]=len(added)
    for tag,value in [(idx_addr,table[3]),(idx_size,len(added)),(idx_count,count+1)]:
        dyn.pack_into(result,tags[tag][1],tag,value)
    seg[fs]=dest+len(added)-seg[off];seg[ms]=seg[fs]
    h[6]=so+shift
    hdr.pack_into(result,0,*h)
    for i,p in enumerate(progs):ph.pack_into(result,po+i*ph.size,*p)
    for i,s in enumerate(sections):sh.pack_into(result,h[6]+i*sh.size,*s)
    text=byname['.text']; assert result[text[4]:text[4]+text[5]]==source[text[4]:text[4]+text[5]]
    return result
if __name__=='__main__':
    src,out,abi=sys.argv[1:]
    Path(out).write_bytes(initialize_root(Path(src).read_bytes(),abi))
