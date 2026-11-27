"""Vehicle material response, shadow masks and wet-road highlights for the winter client."""
import re

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter


def shadow_mask(image):
    pixels = np.array(image.convert('RGBA'))
    height, width = pixels.shape[:2]
    y, x = np.mgrid[:height, :width]
    x = 2*(x+.5)/width - 1
    y = 2*(y+.5)/height - 1
    coverage = pixels[:, :, 3].astype(float) / 255
    near = gaussian_filter(coverage, sigma=(height*.021, width*.028), mode='constant')
    soft = gaussian_filter(coverage, sigma=(height*.065, width*.077), mode='constant')
    rim = np.clip((1-np.maximum(abs(x),abs(y))-.034)/.12, 0, 1)
    contact = .70 + .30*np.exp(-1.6*x*x-1.15*y*y)
    pixels[:, :, 3] = (255*contact*(.58*near+.42*soft)*rim*rim*(3-2*rim)).round()
    return Image.fromarray(pixels)


def wet_highlight(size):
    width, height = size
    y, x = np.mgrid[:height, :width]
    x = 2*(x+.5)/width-1
    y = 2*(y+.5)/height-1
    radius = x*x + y*y
    edge = np.maximum(0, 1-radius)**2
    core = .70*np.exp(-12*x*x-3.2*y*y)
    spread = .30*np.exp(-4.4*x*x-1.3*y*y)
    surface = .90 + .07*np.cos(19*y) + .03*np.cos(34*y + 2*x)
    light = edge*(core+spread)*surface
    rgb = light[:,:,None]*[216,215,211]
    # The renderer uses additive RGB. Both mobile and XRGB particle rasters
    # must have a black border even when alpha is ignored.
    return Image.fromarray(np.dstack((rgb, np.full_like(light,255))).round().astype('uint8'))


def weather_lighting(raw):
    # The engine interpolates eight time slots per weather. Preserve the server's
    # clock, draw distances, headlight projection strength and all interior rows.
    result = []
    weather = b''
    for line in raw.splitlines(keepends=True):
        header = re.match(rb'^/{4,}\s*(\w+)', line)
        if header:
            weather = header[1]
            slot = 0
        if not re.match(rb'^\s*-?\d',line) or weather.startswith((b'UNDERWATER', b'EXTRACOLOURS')):
            result.append(line)
            continue
        fields = line.split()
        if len(fields) not in (51,52) or not 0 <= slot < 8:
            raise ValueError('Unexpected exterior timecycle format')
        cover = next((factor for key,factor in ((b'FOG',.96),(b'RAIN',.86),(b'SANDSTORM',.85),
                      (b'CLOUD',.68),(b'SMOG',.42)) if key in weather),0.)
        sun = (.06,.18,.59,.93,1.,.66,.23,.06)[slot]
        warmth = (0.,.28,.72,.12,.06,.80,.38,0.)[slot]*(1-cover)
        def scale(index, factor):
            fields[index] = str(round(np.clip(float(fields[index])*factor,0,255))).encode()
        for i,tint in enumerate((.065,.010,-.055)):
            scale(6+i,(.96+.06*sun-.17*cover)*(1+tint*warmth))
            scale(3+i,1.0+.045*cover)
        scale(24,.76+.31*sun-.30*cover)
        scale(26,.70+.33*sun-.36*cover)
        vals=iter(fields)
        result.append(re.sub(rb'\S+',lambda _:next(vals),line))
        slot+=1
    return b''.join(result)
