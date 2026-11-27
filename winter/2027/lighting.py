"""Tune exterior time slots without changing the server clock or weather selection."""
import re
import numpy as np
SLOTS=8
def timecycle(raw):
    weather=None
    result=[]
    for line in raw.splitlines(keepends=True):
        match=re.match(rb'^/{4,}\s*(\w+)',line)
        if match:weather=match[1];slot=0
        if not re.match(rb'^\s*-?\d',line) or weather==b'UNDERWATER' or weather.startswith(b'EXTRACOLOURS'):
            result.append(line);continue
        fields=line.split()
        assert len(fields) in (51,52) and slot<SLOTS
        day=(0,.09,.54,.92,1,.60,.20,0)[slot]
        dusk=slot in (2,5,6)
        # Keep highlights below clipping, retain ambient fill on the underside of vehicles.
        for start,factor in [(0,1.03),(3,.91+.015*day),(6,.51+.27*day)]:
            for i in range(start,start+3):fields[i]=str(round(float(fields[i])*factor)).encode()
        for start in (9,12,30,33):
            r,g,b=map(float,fields[start:start+3])
            target=(r+day*5+(4 if dusk else 0),g-day*1.5,b-day*5)
            fields[start:start+3]=[str(round(np.clip(v,0,255))).encode() for v in target]
        for i in (24,26):
            fields[i]=str(round(min(float(fields[i]),110+50*day))).encode()
        # Reserve post-process headroom for emissive lights, particularly after dusk.
        for i in (40,44):
            fields[i]=str(round(float(fields[i])*.68)).encode()
        vals=iter(fields)
        result.append(re.sub(rb'\S+',lambda _:next(vals),line));slot+=1
    return b''.join(result)

def colorcycle(raw):
    rows=raw.splitlines(keepends=True);result=[]
    for i,row in enumerate(rows):
        coeff=np.fromstring(row.decode(),sep=' ')
        assert len(coeff)==12
        if i>=20*SLOTS:
            result.append(row);continue
        m=coeff.reshape(3,4)
        strength=(.13,.15,.22,.31,.34,.23,.17,.13)[i%8]
        neutral=np.eye(3,4)
        m=m*(1-strength)+neutral*strength
        # Limit channel gain in sunlit snow while preserving differences between weather presets.
        result.append((' '.join(f'{v:.6f}' for v in m.flat)+'\n').encode())
    return b''.join(result)
