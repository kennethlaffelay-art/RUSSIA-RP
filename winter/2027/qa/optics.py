"""Check the illuminated near lens in the fixed dusk camera frames."""
from pathlib import Path
import sys
from PIL import Image, ImageChops, ImageFilter


def check_lens(off, on):
    width, height = on.size
    rect = tuple(round(unit * dimension) for unit, dimension in zip(
        (0.494, 0.401, 0.558, 0.454), (width, height, width, height)))
    lens = on.crop(rect).convert('RGB')
    gain = ImageChops.subtract(lens, off.crop(rect).convert('RGB')).convert('L')
    if gain.getextrema()[1] < 76:
        raise ValueError('The near lens does not light up')
    # A saturated square in 1.7.26 occupied ~18x18 screen pixels at 1280x720.
    # An exposed centre is expected; a broad white plateau with square corners is not.
    mask = Image.new('L', lens.size)
    mask.putdata([255 if r > 232 and g > 220 and b > 210 and delta > 100 else 0
                  for (r, g, b), delta in zip(lens.getdata(), gain.getdata())])
    radius = max(2, round(width * 7 / 1280))
    coverage = mask.filter(ImageFilter.BoxBlur(radius)).getextrema()[1] / 255
    print(f'Highest bright-pixel coverage in a lens window: {coverage:.1%}')
    if coverage > 0.84:
        raise ValueError('The lit lens still has a flat white square')


def check_road(off, on, bounds, label):
    width, height = off.size
    region = tuple(round(value * scale) for value, scale in zip(bounds, (width,height,width,height)))
    before = off.crop(region).convert('RGB')
    after = on.crop(region).convert('RGB')
    gain = ImageChops.subtract(after, before).convert('L')
    changed = sum(gain.histogram()[14:])
    clipped = sum(delta >= 14 and min(rgb) >= 246
                  for delta, rgb in zip(gain.getdata(), after.getdata()))
    if changed < .003 * gain.width * gain.height:
        raise ValueError(f'{label}: missing illuminated road')
    if clipped > .20 * changed:
        raise ValueError(f'{label}: {clipped/changed:.1%} of illuminated road clips to white')
    print(f'{label}: {changed} lit pixels, {clipped/changed:.1%} near white')


if __name__ == '__main__':
    directory = Path(sys.argv[1])
    for first, bounds, label in [
        (21, (.15,.60,.39,.77), 'dusk asphalt'),
        (26, (.18,.30,.82,.60), 'night snow from behind'),
        (28, (.12,.39,.88,.64), 'night snow from the side'),
        (30, (.16,.48,.84,.83), 'night snow head-on'),
    ]:
        with Image.open(directory/f'world-{first}.png') as off, Image.open(directory/f'world-{first+1}.png') as on:
            if first == 21:
                check_lens(off, on)
            check_road(off, on, bounds, label)
    # Daylight snow can have little measurable gain. Keep both frames for direct comparison.
    for frame in (32,33):
        with Image.open(directory/f'world-{frame}.png') as image:
            image.verify()
