"""Original reflection probes and specular masks for the mobile vehicle materials."""
import hashlib
import mmap
import struct

import numpy as np
from PIL import Image

from resources import Texture, Textures, merge_ranges, patch_ranges, serialise_patch


MAPS = {
    'txd': ('vehicleenvmap128', 'xvehicleenv128', 'vehiclespecdot64'),
    'gta_int': ('vehicleenvmap128', 'chrome', 'vehiclespecdot64'),
    'loader_car': ('envmap', 'chrome'),
}


def surface_map(name, size):
    w, h = size
    v, u = np.mgrid[:h, :w]
    u, v = (u + .5) / w, (v + .5) / h
    if name == 'vehiclespecdot64':
        # A concentrated light source with a broader, dim clear-coat shoulder.
        radius = ((u - .5) * 2)**2 + ((v - .5) * 2)**2
        value = 245 * (.68*np.exp(-19*radius) + .32*np.exp(-7*radius))
        value *= np.maximum(0, 1-radius)**2
        rgb = np.repeat(value[..., None], 3, axis=2)
    else:
        # Periodic azimuth, so sampling across the texture seam stays continuous.
        angle = 2*np.pi*u
        chrome = name == 'chrome'
        height = .50 + .024*np.cos(2*angle) + .014*np.sin(3*angle)
        above = height - v
        sky = np.clip(.5 + above/.075, 0, 1)
        sky = sky*sky*(3 - 2*sky)
        horizon = np.exp(-((above - .055)/.095)**2)
        bank = np.exp(-((above + .19)/.105)**2)
        side_light = (.5+.5*np.cos(angle-.8))**4
        value = (43 + 19*bank + sky*(59 + 18*side_light) +
                 horizon*(54 + 20*side_light))
        if chrome:
            value = 26 + (value-26)*1.14 + 31*bank*side_light
        if name == 'xvehicleenv128':
            # This small RLE map is a repeating horizon band, with little angular detail.
            value = np.broadcast_to(value.mean(axis=1, keepdims=True), value.shape)
            sky = np.broadcast_to(sky.mean(axis=1, keepdims=True), sky.shape)
        rgb = np.stack((value - 5*sky, value + 2*sky, value + 11*sky), axis=-1)
    return Image.fromarray(np.rint(np.clip(rgb, 0, 255)).astype('uint8')).convert('RGBA')


def texture_records(root, db):
    cat = Textures(root, db)
    prefix = 'texdb/' + db + '/' + db + '.dxt.'
    thumb = (root / (prefix + 'tmb')).read_bytes()
    thumbnails = []
    offset = 0
    while offset < len(thumb):
        length = struct.unpack_from('<I', thumb, offset+8)[0] + 12
        thumbnails.append((offset, thumb[offset:offset+length]))
        offset += length
    assert offset == len(thumb)
    changes = {prefix+'dat': [], prefix+'tmb': []}
    try:
        for name in MAPS[db]:
            offset, record = cat.record(name)
            image = surface_map(name, record.size)
            # Smooth horizons can share adjacent BC blocks in the small RLE records.
            for span in (1, 2, 4, 8, 16):
                try:
                    encoded = record.encode(image, block_span=span)
                    break
                except ValueError:
                    if span == 16:
                        raise
            changes[prefix+'dat'].append((offset, encoded))
            offset, tiny = thumbnails[cat.thumbs[name]]
            tag,w,h,_,marker = struct.unpack_from('<IHHII', tiny)
            if tag & 65535 != int.from_bytes(record.source[:2], 'little'):
                raise ValueError('Thumbnail identity mismatch: ' + name)
            kind = (tag >> 16) & 15
            if kind == 1:
                encoded = tiny[:16] + image.resize((w,h),Image.Resampling.BOX).tobytes()
            else:
                encoded = Texture(tiny,w,h,{0:8,3:16}[kind],marker).encode(image)
            if len(encoded) != len(tiny):
                raise ValueError('Thumbnail length changed: ' + name)
            changes[prefix+'tmb'].append((offset, encoded))
    finally:
        cat.file.close()
    return changes


def apply_vehicle_maps(root, out, files, metadata):
    for db in MAPS:
        for name, additions in texture_records(root, db).items():
            patch = out / ('assets/weik-defaults/' + name + '.patch')
            size, prior = patch_ranges(patch.read_bytes())
            row = metadata['delta'][name]
            with (root/name).open('rb') as f, mmap.mmap(f.fileno(),0,access=mmap.ACCESS_COPY) as data:
                if len(data) != size:
                    raise ValueError('Unexpected texture bank: ' + name)
                for offset, raw in prior:
                    data[offset:offset+len(raw)] = raw
                if hashlib.sha256(data).hexdigest() != files[name][0]:
                    raise ValueError('Unexpected previous texture bank: ' + name)
                sample = None
                for offset, raw in additions:
                    if sample is None:
                        changed = next((i for i in range(16,len(raw)-23)
                                        if data[offset+i] != raw[i]),None)
                        if changed is not None:
                            sample = offset+changed
                    data[offset:offset+len(raw)] = raw
                if sample is None:
                    raise ValueError('Missing changed sample in ' + name)
                digest = hashlib.sha256(data).hexdigest()
                files[name][0] = digest
                row.update(hash=digest, at=sample, sample=data[sample:sample+24].hex())
            patch.write_bytes(serialise_patch(size, merge_ranges(size,prior,additions)))
