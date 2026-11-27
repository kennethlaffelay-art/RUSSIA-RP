"""Build a cumulative bundle against the released APK, signed cache 20 and base warehouse."""
import hashlib
import json
import math
import re
import struct
import sys
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
from PIL import Image
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
from resources import *
from artwork import plate,woodlands,pine,headlamp,halo,snow_surface,ground_snow
from lighting import timecycle,colorcycle,winter_sky
from plaza import layout
from snow import flurries
from gtaLib import col

APK_SHA='a6bbb1a9aafdd0358e57c8938179fc0ec346ab5d5b9eb656a41ca2fc62c226a1'
CACHE_SHA='aec496b553b3528483d9dea231440bc861a9c910588d99de20c67b0b5afbbe5c'
def digest(data):
    return hashlib.sha256(data).hexdigest()

def change_font(data):
    font=TTFont(BytesIO(data));cmap=font.getBestCmap()
    for glyphname in set(cmap[ord(c)] for c in 'АВЕКМНОРСТУХ0123456789'):
        glyph=font['glyf'][glyphname]
        if glyph.isComposite():raise ValueError('Unexpected composite plate glyph')
        # Keep the native baseline and cell advance. Expand the outline uniformly around its centre.
        adv,lsb=font['hmtx'][glyphname];mid=adv/2
        glyph.coordinates[:]=[(round(mid+(x-mid)*1.07),round(y*1.07)) for x,y in glyph.coordinates]
        glyph.recalcBounds(font['glyf']);font['hmtx'][glyphname]=(adv,glyph.xMin)
    out=BytesIO();font.save(out);return out.getvalue()

def insert_rows(data,section,rows):
    match=re.search(rb'(?mi)^'+section+rb'\r?\n.*?^end\s*$',data,re.S)
    if not match:raise ValueError('Missing map section')
    at=data.rfind(b'end',match.start(),match.end());eol=b'\r\n' if b'\r\n' in data else b'\n'
    return data[:at]+eol.join(r.encode() for r in rows)+eol+data[at:]

def compiled_models(root,apk,year):
    meshes,ids,places=layout(year)
    definitions=(root/'data/maps/trees_map.ide').read_bytes()
    used={int(m[1]) for p in (root/'data/maps').rglob('*.ide') for m in re.finditer(rb'(?m)^\s*(\d+)\s*,',p.read_bytes())}
    if used.intersection(ids.values()):raise ValueError('Map object ID collision')
    ide=insert_rows(definitions,b'objs',[f'{ids[m.name]}, {m.name}, 1, {180 if m.name in ("rrp_wheelight","rrp_firtop") else 125}, 0' for m in meshes])
    lines=[f'{mid}, {name}, 0, {x:.5f}, {y:.5f}, {z:.5f}, 0, 0, {math.sin(math.radians(angle)/2):.7f}, {math.cos(math.radians(angle)/2):.7f}, -1' for mid,name,x,y,z,angle in places]
    ipl=insert_rows((root/'data/maps/map7.ipl').read_bytes(),b'inst',lines)
    path='texdb/samp.img';img=bytearray((root/path).read_bytes())
    _,prior=patch_ranges(apk.read('assets/weik-defaults/'+path+'.patch'))
    for off,value in prior:img[off:off+len(value)]=value
    index=img_index(BytesIO(img))
    snow=flurries();pos,capacity=index['fakesnow1.dff'];assert len(snow)<=capacity
    img[pos:pos+capacity]=snow.ljust(capacity,b'\0')
    count=struct.unpack_from('<I',img,4)[0]
    if 8+32*(count+len(meshes))>min(s for s,n in index.values()):raise ValueError('IMG directory has insufficient space')
    for i,m in enumerate(meshes,count):
        data=m.store();sectors=(len(data)+2047)//2048
        struct.pack_into('<II24s',img,8+32*i,len(img)//2048,sectors,(m.name+'.dff').encode())
        img.extend(data.ljust(sectors*2048,b'\0'))
    struct.pack_into('<I',img,4,count+len(meshes))
    colpath='texdb/SAMPCOL.img';source=(root/colpath).read_bytes();entries={n:source[p:p+s] for n,(p,s) in img_index(BytesIO(source)).items()}
    data=entries['allsampcols.col'];end=0
    while data[end:end+3]==b'COL':end+=8+struct.unpack_from('<I',data,end+4)[0]
    assert end>0 and not any(data[end:])
    entries['allsampcols.col']=data[:end]+b''.join(m.collision(ids[m.name]) for m in meshes)
    return {path:img,colpath:img_archive(entries),'data/maps/trees_map.ide':ide,'data/maps/map7.ipl':ipl},snow

def thumbnail(record,image):
    tag,w,h,size,flag=struct.unpack_from('<IHHII',record)
    kind=(tag>>16)&15
    if kind==1:
        raw=image.convert('RGBA').resize((w,h),Image.Resampling.BOX).tobytes()
        if len(raw)!=len(record)-16:raise ValueError('Unknown RGBA thumbnail')
        return record[:16]+raw
    return Texture(record,w,h,{0:8,3:16}[kind],flag).encode(image)

def dust_needles(record):
    tag,w,h,size,marker=struct.unpack_from('<IHHII',record)
    if tag>>16 != 0x8033:raise ValueError('Unexpected pine texture encoding')
    out=bytearray(record);pos=16
    while pos<len(out):
        run=marker and out[pos]==marker
        if run:pos+=2
        for offset in (pos,pos+2):
            v=struct.unpack_from('<H',out,offset)[0]
            r,g,b,a=v>>12,(v>>8)&15,(v>>4)&15,v&15
            if a and g>=r and g>b:
                amount=max(0,min(.74,(g-3)*.105))
                r,g,b=(round(c+(snow-c)*amount) for c,snow in zip((r,g,b),(12,13,14)))
            new=(r<<12)|(g<<8)|(b<<4)|a
            if offset==pos and not run and marker and new&255==marker:new^=16
            struct.pack_into('<H',out,offset,new)
        pos+=4
    assert pos==len(out)
    return out

def texture_updates(root,apk,fontfile):
    changes={}
    deciduous={'buktree1','buktree2','r_dub1','r_berez1_b','r_berez1_t','r_listv1','vyhl_listv1','vyhl_listv2','newtreeleavesb128','treecron9716','treecron9716_2','auctreecrone8712'}
    surfaces={'new_ryazan_lesdirt_rd','brusch_3','ind_road_crossing','road_blank256hv','pzu_road_03','dt_road','antey_roof1','antey_roof2','bat_bank_krysha','bazar01krish','izbaroof1','otb_rooftile1','otb_rooftile2','rooftar01_e','sad_krysha','sjm_metalroof1','ruscount_grass'}
    open_ground={'new_ryazan_les','oldgrs2_bld_citygrass','grass_128hv','ruscount_grass'}
    for db in ('gta_int','loader_car','txd','samp'):
        cat=Textures(root,db);path='texdb/'+db+'/'+db+'.dxt.'
        thumbs=(root/(path+'tmb')).read_bytes();lookup=[];pos=0
        while pos<len(thumbs):
            code,_,_,length=struct.unpack_from('<IHHI',thumbs,pos)
            lookup.append((pos,thumbs[pos:pos+12+length]));pos+=12+length
        assert pos==len(thumbs)
        names=['plate_ru','nomer'] if db!='txd' else ['headlight','headlight1','coronaheadlightline']
        if db=='samp':names=['pinelo128']
        previous=[]
        if db=='gta_int':
            _,previous=patch_ranges(apk.read('assets/weik-defaults/'+path+'dat.patch'))
            names+=sorted((surfaces|open_ground).intersection(cat.ids))
            names+=sorted(n for n in cat.ids if n in deciduous or re.fullmatch(r'lodbuktree\d+_a889|pinebranch1',n))
        for n in names:
            if db=='samp':
                at,end=struct.unpack_from('<II',cat.table,4*cat.ids[n])
                cat.file.seek(at);rec=cat.file.read(end-at)
                changes.setdefault(path+'dat',[]).append((at,dust_needles(rec)))
                off,tiny=lookup[cat.thumbs[n]]
                if struct.unpack_from('<H',tiny,2)[0]==0x8033:
                    changes.setdefault(path+'tmb',[]).append((off,dust_needles(tiny)))
                continue
            start,t=cat.record(n)
            if n in ('plate_ru','nomer'):img=plate(t.size,fontfile)
            elif n in ('headlight','headlight1'):img=headlamp(t.image(),n)
            elif n=='coronaheadlightline':img=halo(t.image())
            elif n in ('pinebranch1','pinelo128'):img=pine(t.image())
            elif n in open_ground:img=ground_snow(t.image())
            elif n in surfaces:
                current=bytearray(t.source);touched=False
                for pos,data in previous:
                    a=max(pos,start);b=min(pos+len(data),start+len(current))
                    if b>a:
                        current[a-start:b-start]=data[a-pos:b-pos];touched=True
                if not touched:continue
                t=Texture(current,*t.size,t.block,t.marker)
                img=snow_surface(t.image())
            else:img=woodlands(t.image(),n)
            try:encoded=t.encode(img)
            except ValueError:
                if n in ('headlight','headlight1'):
                    encoded=t.encode(img,block_span=2)
                else:
                    encoded=t.encode(img,keep_runs=True)
            changes.setdefault(path+'dat',[]).append((start,encoded))
            tag=int.from_bytes(t.source[:4],'little')
            off,rec=lookup[cat.thumbs[n]]
            if int.from_bytes(rec[:2],'little') != (tag&65535):raise ValueError('Thumbnail identity '+n)
            changes.setdefault(path+'tmb',[]).append((off,thumbnail(rec,img)))
            print(db,n,t.size,flush=True)
    return changes

def plaza_ground(stream,idx):
    start,capacity=idx['rip8.col']
    stream.seek(start);raw=stream.read(capacity)
    offset=0;chunks=[];found=False
    while raw[offset:offset+3]==b'COL':
        size=8+struct.unpack_from('<I',raw,offset+4)[0]
        chunk=raw[offset:offset+size]
        if chunk[8:30].split(b'\0')[0].lower()==b'hln_ter2':
            c=col.coll();c.load_memory(chunk);m=c.models[0]
            # This stock mesh is flat here but its collision triangles stop outside the fair.
            # Coordinates come from the actual map7_stream instance and rendered triangles.
            pos=(745.5414428710938,-2383.38623046875,34.962520599365234)
            a=tuple(v-o for v,o in zip((691.,-2353.,36.10),pos))
            b=tuple(v-o for v,o in zip((744.,-2248.,36.37),pos))
            m.boxes.append(col.TBox(col.TVector(*a),col.TVector(*b),col.TSurface(0,0,0,0x76)))
            chunk=c.write_memory();found=True
        chunks.append(chunk);offset+=size
    out=b''.join(chunks)
    if not found or any(raw[offset:]) or len(out)>capacity:raise ValueError('Unexpected map7 collision bank')
    return start,out.ljust(capacity,b'\0')

def build(apkfile,channel,root,out,fontfile):
    if digest(apkfile.read_bytes())!=APK_SHA or digest(channel.read_bytes())!=CACHE_SHA:raise ValueError('Version mismatch')
    out.mkdir(parents=True,exist_ok=True)
    config=json.loads(Path(__file__).with_name('season.json').read_text())
    with ZipFile(apkfile) as apk,ZipFile(channel) as winter:
        manifest=json.loads(apk.read('assets/json/weik-cache.json'));files=manifest['files']
        source_manifest=json.loads((Path(__file__).resolve().parents[2]/'weik-cache.json').read_bytes())['files']
        locals_,snow=compiled_models(root,apk,config['year'])
        for phase in ('Rasv','Day','Zakat'):
            for suffix in ('','_blur'):
                name=f'loader/BR_Nebo_{phase}{suffix}.png'
                locals_[name]=winter_sky((root/name).read_bytes(),phase)
        for n in winter.namelist():
            raw=winter.read(n)
            if n.lower().endswith(('timecyc.dat','ctimecy.dat')):raw=timecycle(raw)
            if n=='data/colorcycle.dat':raw=colorcycle(raw)
            locals_[n]=raw
        patches=texture_updates(root,apk,fontfile)
        with (root/'texdb/gta_int.img').open('rb') as f:
            idx=img_index(f);floor=plaza_ground(f,idx)
        pos,size=idx['fakesnow1.dff']
        patches['texdb/gta_int.img']=[(pos,snow.ljust(size,b'\0')),floor]
        metadata={'bundled':{},'delta':{}}
        def save(n,data):
            p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        for n,raw in locals_.items():
            h=digest(raw);files[n]=[h,len(raw),0,len(raw),0]
            save('assets/weik-defaults/'+n,raw)
            metadata['bundled'][n]={'size':len(raw),'sample':bytes(raw[:24]).hex()}
        for n,new in patches.items():
            original=root/n;source=source_manifest[n]
            with original.open('rb') as stream:
                if hashlib.file_digest(stream,'sha256').hexdigest()!=source[0]:raise ValueError('Wrong base '+n)
            try:sz,old=patch_ranges(apk.read('assets/weik-defaults/'+n+'.patch'))
            except KeyError:sz=source[1];old=[]
            total=merge_ranges(sz,old,new)
            expected=hashlib.sha256();cursor=0
            with original.open('rb') as stream:
                for offset,data in total:
                    while cursor<offset:
                        buf=stream.read(min(1048576,offset-cursor));expected.update(buf);cursor+=len(buf)
                    expected.update(data);cursor+=len(data);stream.seek(cursor)
                while buf:=stream.read(1048576):expected.update(buf)
            finalhash=expected.hexdigest();files[n]=[finalhash,*source[1:]]
            sample_off,sample_data=new[0]
            metadata['delta'][n]={'hash':finalhash,'source':source,'at':sample_off+16,'sample':sample_data[16:40].hex()}
            save('assets/weik-defaults/'+n+'.patch',serialise_patch(sz,total))
        save('assets/json/weik-cache.json',json.dumps(manifest,separators=(',',':')).encode())
        save('assets/russia/plate.ttf',change_font(apk.read('assets/russia/plate.ttf')))
        save('integration.json',json.dumps(metadata,indent=2).encode())
if __name__=='__main__':build(*map(Path,sys.argv[1:]))
