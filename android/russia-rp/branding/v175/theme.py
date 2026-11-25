"""Apply the copper palette and the single-column server picker to the signed 1.7.4 client."""
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
import re, sys
import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFont
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from android_xml import Doc, U
from rebuild_174 import rescolor
L=Image.Resampling.LANCZOS
def image_bytes(im, fmt='WEBP', **options):
    buf=BytesIO()
    im.save(buf, fmt, **options)
    return buf.getvalue()
def copper_image(im):
    """Change the chroma of red UI highlights without tinting text or neutral surfaces."""
    a=np.array(im.convert('RGBA'))
    rgb=a[:,:,:3].astype('float32')/255
    r,g,b=rgb.transpose(2,0,1)
    chroma=np.maximum(r-np.minimum(g,b),0)
    warmth=np.clip((r-g-.012)*12,0,1)*np.clip((r-b-.01)*12,0,1)
    strength=warmth*np.clip(chroma*9,0,1)
    # Lift the midtones of an emissive accent while preserving the existing shading.
    peak=r**.87
    warm=np.stack([peak*.865,peak*(.415+.065*g),peak*(.225+.035*g)],axis=2)
    rgb=rgb+(warm-rgb)*strength[:,:,None]
    a[:,:,:3]=(np.clip(rgb,0,1)*255+.5).astype('uint8')
    return Image.fromarray(a)
def build(base,compiled,resource_dump,logo_file,banner_file,dex,out):
    assert __import__('hashlib').sha256(base.read_bytes()).hexdigest()=='1406c4d026d56ee62a997cac58cb7176983a588086233553a310a769cd1f5dd1'
    dump=resource_dump.read_text()
    ids={k:int(i,16) for i,k in re.findall(r'spec resource (0x[0-9a-f]+) com.russiarp.game:([^:]+):',dump)}
    paths={k:p for k,p in re.findall(r'resource 0x[\da-f]+ com.russiarp.game:([^:]+): t=[^\n]+\n +\(string8\) "(res/[^"]+)"',dump)}
    with ZipFile(base) as z:
        edits={}
        with ZipFile(compiled) as design:
            for name in design.namelist():
                if name.startswith(('res/drawable/','res/layout/')) and name.endswith('.xml'):
                    key=name[4:-4]
                    edits[paths[key]]=design.read(name)
        doc=Doc(z.read('AndroidManifest.xml'));manifest=doc.elements()[0]
        manifest.set('versionCode',16,29);manifest.set('versionName',3,doc.pool.add('1.7.5'));edits['AndroidManifest.xml']=doc.encode()
        def source(name):return Image.open(BytesIO(z.read(paths['drawable/'+name]))).convert('RGBA')
        def save(name,im):edits[paths['drawable/'+name]]=image_bytes(im,lossless=True)
        # Global theme shades used by spawn selection, dialog chrome, and focus states.
        old=(0xe2310c,0xac0000,0xce0e03,0xf75514,0xde2a09,0xff6317,0xf60000)
        palette={0xe2310c:0xbc5d33,0xac0000:0x914525,0xce0e03:0x984720,0xf75514:0xc57444,0xde2a09:0xd88b60,0xff6317:0xd88b60,0xf60000:0xbc5d33}
        scalars={}
        for k,col in re.findall(r'resource 0x[\da-f]+ com.russiarp.game:(color/[^:]+): t=0x1[c-f] d=(0x[0-9a-f]+)',dump):
            rgba=int(col,16)
            if (rgba&0xffffff) in old and not re.search('error|danger|diagnostic',k,re.I):
                scalars[ids[k]]=(rgba&0xff000000)|palette[rgba&0xffffff]
        edits['resources.arsc']=rescolor(z.read('resources.arsc'),scalars)
        # Direct literals in the app's drawables bypass the color resource table.
        chrome=re.compile(r'(?:^hud_|^progressbar_hud|^spawn_location|^br_|^bp_|^button_|_button|^background_window|^dialog_|^donate_|^reg_|^registration_|^divider|^fractions_|^toggle_|^indicator_|^menu_|^keyboard|^play_|^checkbox|^switch_|^speedo_|^slider)',re.I)
        extra={0xff2d2d:0xcd7b4b,0xbb2a2a:0x9a4929,0xff3c14:0xe29865,0xff0000:0xbc5d33,0xd62d03:0xae542d,0xff3300:0xcf7a46}
        for key,p in paths.items():
            if not key.startswith('drawable/') or not chrome.search(key[9:]) or p in edits:continue
            if not p.endswith('.xml'):continue
            d=Doc(z.read(p));changed=False
            for e in d.elements():
                for a in e.attrs:
                    value=U(a,16);rgb=value&0xffffff;t=a[15]
                    if t in (28,29,30,31) and (rgb in palette or rgb in extra):
                        e.set(e.name(a),28,(value&0xff000000)|(palette.get(rgb) or extra[rgb]));changed=True
            if changed:edits[p]=d.encode()
        # Spawn selection previously stretched a red band over the main image.
        # The new vector border in the design bundle occupies the entire selected card.
        def get(d, name):return next(e for e in d.elements() if e.get('id')==ids['id/'+name])
        p=paths['layout/spawn_location_item'];d=Doc(z.read(p));sel=get(d,'view_selection');sel.drop('layout_marginTop');sel.drop('layout_marginBottom');edits[p]=d.encode()
        # Regrade only interface illustrations. The map, items and vehicles are artwork.
        names='back hud_back hud_up hud_center hud_down hud_menu hud_star hud_heart_old hud_gps menu_back'.split()
        for k in paths:
            if k.startswith(('drawable/br_menu_','drawable/ic_hud_btn_')):names.append(k[9:])
        for name in names:
            im=source(name);tone=copper_image(im)
            if name=='back':
                # Restore warmth in the original right-hand glow, including its very dark falloff.
                a=np.asarray(tone).copy();h,w=a.shape[:2];y,x=np.ogrid[0:h,0:w]
                glow=np.exp(-((x/w-1.04)/.63)**2-((y/h-.74)/.43)**2)
                a[:,:,:3]=np.minimum(255,a[:,:,:3].astype(float)+glow[:,:,None]*np.array([22,13,6])).astype('uint8')
                tone=Image.fromarray(a)
            # Encode dark photos with high-quality lossy WebP. Flat UI shapes keep exact alpha.
            if name=='back':edits[paths['drawable/back']]=image_bytes(tone,quality=92,method=5)
            else:save(name,tone)
        banner=Image.open(banner_file).convert('RGB')
        a=np.asarray(banner).astype('float32');h,w=a.shape[:2]
        y,x=np.mgrid[0:h,0:w];u=x/(w-1)
        t=np.clip((u-.10)/.66,0,1);t=t*t*(3-2*t)
        shade=.91-.80*t+.05*np.abs(y/(h-1)-.48)
        a=a*(1-shade[:,:,None])+np.array([23,21,21])*shade[:,:,None]
        edits[paths['drawable/server_select_background']]=image_bytes(Image.fromarray(a.astype('uint8')),'JPEG',quality=91,optimize=True)
        logo=Image.open(logo_file).convert('RGBA');logo=logo.crop(logo.getbbox())
        # Fill the monitor badge with the complete mark, and keep a narrow breathing space inside its progress ring.
        monitor=Image.new('RGBA',(400,400));glyph=ImageOps.contain(logo,(354,354),L);monitor.alpha_composite(glyph,((400-glyph.width)//2,(400-glyph.height)//2));save('bear_paw',monitor)
        save('br_peaw_servers',ImageOps.contain(logo,(240,300),L))
        p=paths['layout/item_server'];d=Doc(z.read(p));els=d.elements()
        mark=get(d,'bearPaw');ring=get(d,'progressBar');frame=next(e for e in els if e.tag=='FrameLayout' and e.get('layout_width')==ids['dimen/_50sdp'])
        for e in (mark,ring,frame):
            for attr in ('layout_width','layout_height'):e.set(attr,1,ids['dimen/_62sdp'])
        ring.set('cpb_progressbar_color',28,0xffbc5d33);ring.set('cpb_progressbar_width',5,0x201)
        edits[p]=d.encode()
        # Rasterize the exact source mark and optically center it on the capital letters.
        font=ImageFont.truetype(BytesIO(z.read(paths['font/montserrat_bold'])),112)
        letters=Image.new('RGBA',(900,190));draw=ImageDraw.Draw(letters)
        draw.text((4,0),'МОСКВА',font=font,fill='#FFFAF4',stroke_width=3,stroke_fill='#493328');letters=letters.crop(letters.getbbox())
        glyph=ImageOps.contain(logo,(150,round(letters.height*1.12)),L)
        row=Image.new('RGBA',(glyph.width+16+letters.width,max(glyph.height,letters.height)))
        row.alpha_composite(glyph,(0,(row.height-glyph.height)//2));row.alpha_composite(letters,(glyph.width+16,(row.height-letters.height)//2))
        word=image_bytes(row,lossless=True)
        for k,p in paths.items():
            if k.startswith('drawable/logobr') and k!='drawable/logobrx2':edits[p]=word
        p=paths['layout/br_hud'];d=Doc(z.read(p));hud_logo=get(d,'brHudLogo')
        hud_logo.set('layout_width',1,ids['dimen/_66sdp']);hud_logo.set('layout_height',1,ids['dimen/_12sdp'])
        hud_logo.set('layout_marginStart',5,0x101);hud_logo.set('layout_marginBottom',5,0x101)
        edits[p]=d.encode()
        edits['classes3.dex']=(dex/'ui.dex').read_bytes();edits['classes5.dex']=(dex/'classes.dex').read_bytes()
        with ZipFile(out,'w') as dest:
            for i in z.infolist():
                if re.fullmatch(r'META-INF/[^/]+\.(RSA|DSA|EC|SF|MF)',i.filename,re.I):continue
                dest.writestr(i,edits[i.filename] if i.filename in edits else z.read(i))
        print('Changed',len(edits),'entries,',len(scalars),'theme colors; HUD symbol/text height ratio',round(glyph.height/letters.height,2))
if __name__=='__main__':build(*(Path(v) for v in sys.argv[1:]))
