"""Route the two confirmed maintenance actions back to the existing menu until Play is pressed."""
import struct

def defer_download(dex):
    data=bytearray(dex)
    def word(pos): return struct.unpack_from('<I',data,pos)[0]
    def uleb(pos):
        result=shift=0
        while True:
            v=data[pos];pos+=1;result|=(v&127)<<shift
            if v<128:return result,pos
            shift+=7
    strings=[]
    for i in range(word(56)):
        _,p=uleb(word(word(60)+4*i))
        strings.append(data[p:data.index(0,p)].decode('utf8','replace'))
    types=[strings[word(word(68)+4*i)] for i in range(word(64))]
    methods=[]
    for i in range(word(88)):
        owner,proto,name=struct.unpack_from('<HHI',data,word(92)+8*i)
        methods.append((types[owner],strings[name]))
    main='Lblackrussia/online/activities/MainActivity;'
    menu=methods.index((main,'onClickMonitoring'))
    downloader=types.index('Lblackrussia/online/Downloader;')
    required={'Lblackrussia/online/fragments/SettingsFragment$13;','Lblackrussia/online/fragments/SettingsFragment$15;'}
    done=set()
    for i in range(word(96)):
        pos=word(100)+i*32
        name=types[word(pos)]
        if name not in required:continue
        p=word(pos+24);sizes=[]
        for _ in range(4):
            n,p=uleb(p);sizes.append(n)
        for _ in range(sum(sizes[:2])):
            _,p=uleb(p);_,p=uleb(p)
        for count in sizes[2:]:
            method=0
            for _ in range(count):
                diff,p=uleb(p);method+=diff;_,p=uleb(p);code,p=uleb(p)
                if methods[method]!=(name,'onClick'):continue
                ins=code+16
                assert struct.unpack_from('<HH',data,ins+14)==(0x22,types.index('Landroid/content/Intent;'))
                assert struct.unpack_from('<HH',data,ins+30)==(0x021c,downloader)
                assert data[ins+34]==0x70 and data[ins+40]==0x6e
                # Keep dialog dismissal, getActivity(), and the stock preference reset.
                # No Intent construction: use the same main tab as the menu's monitoring button.
                data[ins+14:ins+18]=b'\0'*4
                data[ins+30:ins+46]=struct.pack('<8H',0x011f,types.index(main),0x106e,menu,1,0,0,0)
                done.add(name)
    if done!=required:raise ValueError('Unexpected settings callbacks')
    return data
