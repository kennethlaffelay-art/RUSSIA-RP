"""Generate winter lighting tables and wheel spray from the installed cache format."""
from pathlib import Path
from zipfile import ZipFile
import collections, math, re, sys, json, hashlib, shutil

# Ambient world, ambient objects, zenith, horizon, sunlight, clouds and horizontal visibility.
LIGHT = [
 ((25,32,45),(117,132,155),(13,23,43),(33,46,65),(150,171,201),(53,65,86),.30),
 ((30,37,51),(132,143,163),(28,39,68),(82,77,93),(205,169,148),(91,85,103),.35),
 ((47,50,61),(162,159,167),(66,89,128),(191,161,150),(247,183,135),(159,145,149),.52),
 ((60,65,75),(178,181,186),(96,132,174),(207,210,216),(255,225,190),(186,191,198),.64),
 ((66,73,84),(184,190,197),(87,133,184),(202,219,232),(251,243,221),(201,212,225),.72),
 ((52,53,63),(163,157,164),(75,90,129),(208,160,144),(249,177,124),(172,146,146),.60),
 ((36,41,58),(144,145,166),(44,56,94),(113,100,125),(205,158,141),(116,105,134),.43),
 ((26,33,47),(122,134,156),(20,31,56),(46,56,78),(155,167,194),(70,77,99),.33),
]
def lighting(source):
    output=[]; sky=None; row=0; changed=collections.Counter()
    for line in source.decode('ascii').splitlines(keepends=True):
        name=re.match(r'^/{4,}\s*(\w+)',line)
        if name: sky=name[1];row=0
        if not re.match(r'^\s*-?\d',line): output.append(line);continue
        slot=row;row+=1
        if sky=='UNDERWATER' or sky.startswith('EXTRACOLOURS'): output.append(line);continue
        words=line.split()
        assert len(words) in (51,52) and 0<=slot<8
        amb,obj,zen,hor,sun,cloud,visibility=LIGHT[slot]
        overcast=.58 if any(k in sky for k in ['FOGGY','RAINY','SANDSTORM']) else .38 if 'CLOUDY' in sky else .08 if 'SUNNY' in sky and 'EXTRA' not in sky else .02
        def blend(a,b,f): return [round(x*(1-f)+y*f) for x,y in zip(a,b)]
        def color(i,values): words[i:i+3]=map(str,values)
        gray=round(sum(hor)/3)
        color(0,amb); color(3,obj)
        color(9,blend(zen,(gray,gray,gray+4),overcast))
        color(12,blend(hor,(gray,gray,gray+3),overcast*.75))
        color(15,blend(sun,hor,overcast*.5));color(18,blend(sun,hor,.23+overcast*.4))
        words[21]=str(round(min(float(words[21]),2.0 if slot in (2,5) else 1.35),2))
        # Retain the current draw distance. Haze starts farther out on clear winter days.
        far=float(words[27]); words[28]=str(round(max(1,far*visibility*(1-overcast*.83)),2))
        color(30,blend(cloud,zen,.28));color(33,cloud)
        # RGB filter values follow their corresponding alpha in both stock layouts.
        color(41,blend(tuple(int(float(x)) for x in words[41:44]),hor,.22))
        color(45,blend(tuple(int(float(x)) for x in words[45:48]),zen,.18))
        original=re.findall(r'\S+',line); idx=iter(words)
        output.append(re.sub(r'\S+',lambda _:next(idx),line))
        assert len(original)==len(words)
        changed[(sky,slot)]+=1
    assert sum(changed.values())==160 and row==8
    return ''.join(output).encode('ascii')

def spray(raw):
    text=raw.decode('ascii').replace('\r\n','\n')
    blocks=text.split('FX_SYSTEM_DATA:\n'); found=0
    for i,system in enumerate(blocks):
        if '\nNAME: prt_wheeldirt\n' not in system: continue
        found+=1
        curves={'LIFE':[1.15], 'FORCEZ':[-1.9], 'RED':[224,212,197], 'GREEN':[235,226,216],
                'BLUE':[246,238,232], 'ALPHA':[158,57,0], 'SIZEX':[.68], 'SIZEY':[.48]}
        for key,values in curves.items():
            pattern=r'(?m)^'+key+r':\n(FX_INTERP_DATA:\nLOOPED: \d+\nNUM_KEYS: \d+\n(?:FX_KEYFLOAT_DATA:\nTIME: [^\n]+\nVAL: [^\n]+\n)+)'
            matches=list(re.finditer(pattern,system));assert len(matches)==1,key
            match=matches[0]; curve=match[0]
            assert curve.count('VAL: ')==len(values)
            nums=iter(values);new=re.sub(r'(?m)^VAL: [^\n]+',lambda _:'VAL: %.3f'%next(nums),curve)
            system=system[:match.start()]+new+system[match.end():]
        blocks[i]=system
    assert found==1
    return 'FX_SYSTEM_DATA:\n'.join(blocks).replace('\n','\r\n').encode('ascii')

if __name__=='__main__':
    warehouse,old_channel,output=map(Path,sys.argv[1:4])
    shutil.copytree(old_channel,output,dirs_exist_ok=True)
    with ZipFile(warehouse) as z:
        for name in ('data/timecyc.dat','data/ctimecy.dat','models/effects.fxp'):
            raw=z.read('Weik/'+name)
            result=spray(raw) if name.endswith('fxp') else lighting(raw)
            dest=output/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(result)
            print(name,len(raw),len(result))
        # Both spellings are opened by the Android file resolver.
        dest=output/'SAMP/TIMECYC.DAT';dest.parent.mkdir(exist_ok=True);dest.write_bytes((output/'data/timecyc.dat').read_bytes())
