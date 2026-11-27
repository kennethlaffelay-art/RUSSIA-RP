"""Author textures in the native plate, vegetation and projected-light UV spaces."""
import hashlib
import math
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFont

def plate(size, font):
    w,h=size
    scale=4
    image=Image.new('RGB',(256*scale,64*scale),(40,43,46))
    canvas=ImageDraw.Draw(image)
    def rounded(rect,r,fill):
        canvas.rounded_rectangle(tuple(round(v*scale) for v in rect),radius=r*scale,fill=fill)
    rounded((1,1,254.9,62.9),4,(26,29,32))
    rounded((3,3,253,61),3,(211,215,217))
    canvas.rectangle((192*scale,3*scale,193*scale,61*scale),fill=(32,35,37))
    canvas.text((197*scale,37*scale),'RUS',font=ImageFont.truetype(font,13*scale),fill=(28,31,33),stroke_width=0)
    canvas.rectangle((228*scale,39*scale,248*scale,51*scale),fill=(56,60,64))
    for i,c in enumerate([(234,235,234),(32,74,151),(183,54,61)]):
        canvas.rectangle((229*scale,(40+i*3.5)*scale,247*scale,(43.5+i*3.5)*scale),fill=c)
    return image.resize((w,h),Image.Resampling.LANCZOS)

def woodlands(original,name):
    # Far LOD atlases contain several different trees. Keep their original UV islands.
    px=np.asarray(original)
    from scipy.ndimage import gaussian_filter, label, find_objects
    mask=px[:,:,3]>45
    h,w=mask.shape
    if name.lower().startswith('lod'):
        grouped=gaussian_filter(mask.astype(float),2.2)>.08
        ids,count=label(grouped)
        slots=[(s[1].start,s[0].start,s[1].stop,s[0].stop) for s in find_objects(ids)
               if s and (s[0].stop-s[0].start)*(s[1].stop-s[1].start)>w*h*.022]
    else:
        ys,xs=np.where(mask)
        slots=[(xs.min(),ys.min(),xs.max()+1,ys.max()+1)]
    rng=random.Random(int.from_bytes(hashlib.sha256(name.lower().encode()).digest()[:8],'big'))
    ss=3
    im=Image.new('RGBA',(ss*w,ss*h));draw=ImageDraw.Draw(im)
    for x0,y0,x1,y1 in slots:
        width=x1-x0;height=y1-y0
        cx=x0+width*rng.uniform(.42,.57);foot=y1-.6
        def branch(x,y,angle,length,weight,depth):
            bent=angle+rng.uniform(-.13,.13)
            mx=x+math.cos(angle)*length*.48;my=y+math.sin(angle)*length*.48
            tx=mx+math.cos(bent)*length*.52;ty=my+math.sin(bent)*length*.52
            shade=rng.randrange(61,94)
            draw.line([(ss*x,ss*y),(ss*mx,ss*my),(ss*tx,ss*ty)],fill=(shade+9,shade+4,shade,244),width=max(1,round(weight*ss)))
            if abs(math.cos(angle))>.25 and weight>1 and rng.random()<.72:
                draw.line([(ss*x,ss*(y-weight*.28)),(ss*mx,ss*(my-weight*.28))],fill=(175,185,192,226),width=max(1,round(weight*.24*ss)))
            if depth:
                branch(tx,ty,bent+rng.uniform(-.22,.18),length*.74,weight*.65,depth-1)
                branch(mx,my,bent+rng.choice((-1,1))*rng.uniform(.34,.84),length*.70,weight*.52,depth-1)
        for side in (-1,1):
            for j in range(7):
                q=j/7
                branch(cx,foot-height*(.18+.64*q),-math.pi/2+side*(1.06-.4*q),min(width*.25,height*(.23-.09*q)),max(.65,width*.017*(1-.6*q)),4)
        branch(cx,foot,-math.pi/2,height*.30,max(1.3,width*.036),5)
    rgba=np.asarray(im.resize((w,h),Image.Resampling.LANCZOS)).copy()
    rgba[rgba[:,:,3]<24]=0
    return Image.fromarray(rgba)

def pine(original):
    p=np.asarray(original).copy()
    yy,xx=np.indices(p.shape[:2])
    brightness=p[:,:,:3].astype(float).mean(2)
    frost=np.clip(.18+(brightness-51)/116 + .17*np.cos(yy*.16+np.sin(xx*.07)),.08,.65)
    for i, channel in enumerate([185,197,204]):
        p[:,:,i]=p[:,:,i]*(1-frost)+channel*frost
    return Image.fromarray(p)

def headlamp(original, name):
    width, height = original.size
    rows, columns = np.mgrid[:height, :width]
    x = 2 * (columns + 0.5) / width - 1
    distance = 1 - (rows + 0.5) / height

    # The renderer projects either one lamp or a pair across the vehicle width.
    # Both masks use the bottom edge as the bumper and widen towards the road.
    paired = name == 'headlight'
    half_width = (0.036 + 0.35 * distance) if paired else (0.055 + 0.77 * distance)
    centres = (-0.43, 0.43) if paired else (0.0,)
    profile = np.zeros_like(x)
    for centre in centres:
        cross_section = np.abs(x - centre * (1 + 0.09 * distance)) / half_width
        edge = np.clip((1 - cross_section) / 0.27, 0, 1)
        feather = edge * edge * (3 - 2 * edge)
        core = 1 - 0.24 * np.minimum(cross_section, 1) ** 2
        profile = np.maximum(profile, feather * core)

    # Keep pavement visible close to the bumper and roll off the far edge.
    fade = np.clip((1 - distance) / 0.26, 0, 1)
    light = profile * (0.86 - 0.23 * distance) * fade * fade * (3 - 2 * fade)
    tint = np.array([255, 244, 216])
    if paired:
        # Split energy across RGB and alpha for a smooth edge in either blend mode.
        rgb = np.sqrt(light)[:, :, None] * tint
        alpha = np.sqrt(light) * 225
    else:
        # This texture uses DXT1. Its black background is the additive neutral value.
        rgb = light[:, :, None] * tint
        alpha = np.full_like(light, 255)
    pixels = np.dstack((rgb, alpha)).round().astype(np.uint8)
    return Image.fromarray(pixels)

def halo(original):
    h,w=original.height,original.width
    y,x=np.mgrid[:h,:w];r=((x+.5-w/2)/(w/2))**2+((y+.5-h/2)/(h/2))**2
    a=np.uint8(240*np.exp(-r*5.5)*np.clip(1-r,0,1))
    out=Image.new('RGBA',(w,h),(245,245,240));out.putalpha(Image.fromarray(a));return out

def snow_surface(original):
    p=np.array(original)
    rgb=p[:,:,:3].astype(float)
    y=rgb.mean(axis=2)
    high=np.clip((y-105)/118,0,1)
    # Compress the white point while retaining the source markings and ruts in the midtones.
    adjusted=rgb*(1-.085*high[:,:,None]) + np.dstack((-1.4*high,0*high,1.7*high))
    p[:,:,:3]=np.clip(adjusted,0,255).astype(np.uint8)
    return Image.fromarray(p)

def ground_snow(original):
    p=np.asarray(original).copy()
    rgb=p[:,:,:3].astype(float);luma=rgb@np.array([.28,.52,.20])
    detail=luma-np.mean(luma)
    surface=np.clip(177+detail*.31,128,204)
    p[:,:,:3]=np.stack([surface*.967,surface*.989,surface*1.01],axis=2).astype(np.uint8)
    return Image.fromarray(p)
