"""Render winter cloud domes in the disk UV projection of the shipped sky meshes."""
from io import BytesIO
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter
from gtaLib import dff

# Phase, mesh suffix, seed, zenith, horizon, dark cloud, illuminated cloud.
SKIES = (
    ('Rasv','Rasv',31,(58,87,146),(241,184,154),(119,127,158),(253,211,178)),
    ('Day','Day',32,(42,94,162),(182,208,224),(124,153,181),(247,247,238)),
    ('Zakat','Zak',33,(61,75,130),(235,145,106),(107,94,133),(255,186,138)),
    ('Nght','Night',34,(12,21,45),(55,68,91),(33,43,64),(84,94,113)),
)


def cloud_field(rng, size):
    field = np.zeros((size,size),np.float32)
    for grid, amplitude in ((7,.44),(15,.26),(32,.16),(65,.09),(132,.05)):
        tile = Image.fromarray(rng.random((grid,grid+grid//2),dtype=np.float32))
        field += amplitude*np.asarray(tile.resize((size,size),Image.Resampling.BICUBIC))
    return field


def sky_images(root):
    size = 2048
    axis = (np.arange(size,dtype=np.float32)+.5)/size*2-1
    x,y = axis[None,:],axis[:,None]
    radius = np.sqrt(x*x+y*y)
    altitude = np.sqrt(np.maximum(0,1-radius**2))
    edge = np.clip((1-radius)*8,0,1)
    for phase,mesh,seed,zenith,horizon,shade,light in SKIES:
        rng = np.random.default_rng(seed)
        field = cloud_field(rng,size)
        cloud = np.clip((field-.435)*4.5,0,1)*edge
        glow = np.clip((field-.38)*2.6,0,1)
        elevation = altitude**.80
        sun_side = (x*.5+.5) if phase=='Rasv' else (.5-x*.5)
        rgba = np.empty((size,size,3),np.uint8)
        for c in range(3):
            sky = horizon[c]+(zenith[c]-horizon[c])*elevation
            lit = shade[c]+(light[c]-shade[c])*glow
            if phase in ('Rasv','Zakat'):
                sky += (24,7,-7)[c]*sun_side*(1-elevation)
            rgba[:,:,c] = np.clip(sky*(1-cloud)+lit*cloud,0,255).round()
        if phase=='Nght':
            stars = (rng.random((size,size),dtype=np.float32)>.99955)&(cloud<.14)&(altitude>.22)
            rgba[stars] = rng.integers(115,205,size=(stars.sum(),1),dtype=np.uint8)
        image = Image.fromarray(rgba)
        for suffix,texture_suffix in (('',''),('_bl','_blur')):
            model = dff.dff()
            model.load_memory((root/f'loader/BR_Sky_{mesh}{suffix}.dff').read_bytes())
            texture = f'BR_Nebo_{phase}{texture_suffix}'
            names = {t.name for cl in model.clumps for g in cl.geometry_list for m in g.materials for t in m.textures}
            if names!={texture}:
                raise ValueError(f'Sky mesh expects {names}, generated {texture}')
            stream = BytesIO()
            (image.filter(ImageFilter.GaussianBlur(12)) if suffix else image).save(stream,'PNG')
            yield 'loader/'+texture+'.png', stream.getvalue()
