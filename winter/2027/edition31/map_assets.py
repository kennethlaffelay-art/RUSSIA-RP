"""Encode all radar sprites and world markers against the actual winter client."""
import argparse
import hashlib
import io
import json
import sys
from pathlib import Path
from zipfile import ZipFile

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from resources import Textures, img_index, serialise_patch, Texture
from symbols import NAMES, radar
from world_marks import design_names, model

PREVIOUS_SHA = 'ac2b0163930ffc700f9f98c73425a7f98377babb4f51fae172298b3f2525141c'
PREFIX = 'assets/weik-defaults/'

def encode_symbol(record, name):
    image = radar(name)
    for size in (64,60,56,52,48,44,40,36,32):
        canvas = Image.new('RGBA',(64,64))
        canvas.paste(image.resize((size,size),Image.Resampling.NEAREST),((64-size)//2,)*2)
        try:
            packed = record.encode(canvas)
        except ValueError:
            continue
        decoded = Texture(packed,*record.size,record.block,record.marker).image()
        return packed,decoded
    raise ValueError(f'Cannot fit {name} in its native slot')

def edits(root, previous):
    db = Textures(root,'txd')
    found = {n[6:] for n in db.ids if n.startswith('radar_')}
    if found != NAMES:
        raise ValueError(f'Missing or obsolete map symbols: {found ^ NAMES}')
    prefix = 'texdb/txd/txd.dxt.'
    thumbnail = (root/(prefix+'tmb')).read_bytes()
    import struct
    offset = 0
    thumbs = []
    while offset < len(thumbnail):
        thumbs.append(offset)
        offset += 12+struct.unpack_from('<I',thumbnail,offset+8)[0]
    if offset != len(thumbnail):
        raise ValueError('Invalid thumbnail catalog')
    bank = {prefix+'dat':[],prefix+'tmb':[]}
    examples = {}
    try:
        for name in sorted(found):
            key = 'radar_'+name
            pos, record = db.record(key)
            data, displayed = encode_symbol(record,name)
            bank[prefix+'dat'].append((pos,data))
            i = thumbs[db.thumbs[key]]
            tag,w,h,length,marker = struct.unpack_from('<IHHII',thumbnail,i)
            if (tag&65535,w,h,length,marker) != (int.from_bytes(record.source[:2],'little'),1,1,8,0):
                raise ValueError('Unexpected thumbnail for '+name)
            bank[prefix+'tmb'].append((i+16,displayed.resize((1,1),Image.Resampling.BOX).tobytes()))
            examples[name] = displayed
    finally:
        db.file.close()
    required = design_names(root)
    seen = set()
    for basename in ('gta3.img','samp.img','gta_int.img'):
        name='texdb/'+basename
        # The winter fair adds sectors in samp.img. Read the directory shipped in the APK.
        with (io.BytesIO(previous.read(PREFIX+name)) if PREFIX+name in previous.namelist() else (root/name).open('rb')) as f:
            ranges=[]
            for entry,(offset,capacity) in img_index(f).items():
                key=entry.removesuffix('.dff')
                if not entry.endswith('.dff') or key not in required:
                    continue
                f.seek(offset)
                raw=f.read(capacity)
                updated=model(key,raw,capacity)
                if raw==updated:
                    raise ValueError('Unmodified world model: '+key)
                ranges.append((offset,updated))
                seen.add(key)
            bank[name]=ranges
    if seen != required:
        raise ValueError(f'World models missing: {required-seen}')
    return bank,examples

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root',type=Path)
    parser.add_argument('previous',type=Path)
    parser.add_argument('out',type=Path)
    args=parser.parse_args()
    with args.previous.open('rb') as stream:
        if hashlib.file_digest(stream,'sha256').hexdigest()!=PREVIOUS_SHA:
            raise ValueError('Requires the published 1.7.30 client')
    args.out.mkdir(parents=True,exist_ok=True)
    with ZipFile(args.previous) as previous:
        files,icons=edits(args.root,previous)
        manifest=json.loads(previous.read('assets/json/weik-cache.json'))['files']
    for name,changes in files.items():
        out=args.out/(name+'.patch')
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_bytes(serialise_patch(manifest[name][1],sorted(changes)))
    sheet=Image.new('RGB',(8*114,8*98),(32,42,47))
    draw=ImageDraw.Draw(sheet)
    for i,(name,im) in enumerate(icons.items()):
        x,y=i%8*114,i//8*98
        sheet.paste(im,(x+25,y+6),im)
        draw.text((x+57,y+77),name,anchor='mm',fill='#eadcc9',font=ImageFont.load_default(size=12))
    sheet.save(args.out/'radar.png')
    print(f'{len(icons)} radar sprites, {sum(len(v) for k,v in files.items() if k.endswith(".img"))} world model records')
if __name__=='__main__':
    main()
