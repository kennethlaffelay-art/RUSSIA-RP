"""Grade existing compressed color endpoints, preserving UVs, mipmaps and alpha."""
import struct

from resources import Textures

MATERIALS = {
    'loader_skin': {'350bomber7': 'wool', 'fsbagent_shirt': 'wool',
                    'fsbagent_pants': 'cloth', 'fsbagent_shoes': 'leather',
                    'fsbagent_armor': 'cloth', 'fsbagent_kobura': 'leather'},
    'loader_car': {'envmap': 'reflection', 'chrome': 'reflection'},
    'gta_int': {'vehicleenvmap128': 'reflection', 'chrome': 'reflection'},
    'txd': {'vehicleenvmap128': 'reflection', 'xvehicleenv128': 'reflection',
            'headlight': 'lamp', 'headlight1': 'lamp'},
}


def grade(rgb, kind):
    # Retain black outside lamps and the diffuse detail painted into garments.
    r, g, b = rgb
    luma = .2126*r + .7152*g + .0722*b
    if kind == 'lamp':
        return [v**1.18 * tint for v, tint in zip(rgb, (1., .98, .94))]
    if kind == 'reflection':
        return [v*(.83+.14*luma) + .06*luma**3 for v in rgb]
    if kind == 'leather':
        return [r*.92+.08*luma**3, g*.87+.08*luma**3, b*.81+.08*luma**3]
    tint = (.85, .92, 1.) if kind == 'wool' else (.85, .88, .91)
    return [(.82*v+.18*luma)*t for v,t in zip(rgb,tint)]


def endpoint(value, material):
    rgb = ((value>>11)/31, ((value>>5)&63)/63, (value&31)/31)
    r,g,b = (round(max(0,min(1,x))*m) for x,m in zip(grade(rgb, material),(31,63,31)))
    return r<<11 | g<<5 | b


def finish(raw, record, material):
    out = bytearray(raw)
    offset = 16
    while offset < len(raw):
        tagged = record.marker and raw[offset] == record.marker
        if tagged:
            offset += 2
        pos = offset + record.block - 8
        a,b = struct.unpack_from('<HH',raw,pos)
        x,y = endpoint(a,material), endpoint(b,material)
        # Preserve the DXT1 palette mode and the compressed record framing.
        if (record.block == 16 or (x>y)==(a>b)) and not (
                record.block == 8 and record.marker and not tagged and x&255 == record.marker):
            struct.pack_into('<HH',out,pos,x,y)
        offset += record.block
    if offset != len(raw) or out == raw:
        raise ValueError('Invalid or unchanged record')
    return bytes(out)


def texture_edits(root, name, previous):
    db = name.split('/')[1]
    bank = Textures(root,db)
    try:
        for key, material in MATERIALS[db].items():
            offset, record = bank.record(key)
            yield offset, finish(previous[offset:offset+len(record.source)], record, material)
    finally:
        bank.file.close()


def lamp_edits(raw):
    cursor = 12
    found = set()
    while cursor < len(raw):
        kind,size,_ = struct.unpack_from('<III',raw,cursor)
        header = cursor + 24
        cursor += size + 12
        if kind != 0x15:
            continue
        name = bytes(raw[header+8:header+40]).split(b'\0')[0]
        if name not in (b'headlight',b'headlight1',b'coronaheadlightline'):
            continue
        fmt,w,h,depth,mips,_,_,length = struct.unpack_from('<IHH4BI',raw,header+76)
        if (fmt,depth,mips,length) != (22,32,1,w*h*4):
            raise ValueError('Unexpected headlight raster')
        pos = header+92
        data = bytearray(raw[pos:pos+length])
        for channel, tint in enumerate((.94,.98,1.)):
            lut = bytes(round(255*tint*(i/255)**1.18) for i in range(256))
            data[channel::4] = data[channel::4].translate(lut)
        found.add(name)
        yield pos,bytes(data)
    if len(found)!=3:
        raise ValueError('Missing headlight sprites')
