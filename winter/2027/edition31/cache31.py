"""Assemble bundled files and cumulative WS14 patches against published 1.7.30."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from zipfile import ZipFile

from map_assets import PREFIX, PREVIOUS_SHA, edits
from resources import merge_ranges, patch_ranges, serialise_patch
from surfaces import MATERIALS, lamp_edits, texture_edits
from skins import garment_edits


def sha(data):
    return hashlib.sha256(data).hexdigest()


def apply(data, ranges):
    for at, raw in ranges:
        if not (0 <= at < at+len(raw) <= len(data)):
            raise ValueError('Invalid patch extent')
        data[at:at+len(raw)] = raw


def build(root, apk, out):
    if sha(apk.read_bytes()) != PREVIOUS_SHA:
        raise ValueError('Expected the published 1.7.30 APK')
    assets = out/'assets'
    stock = json.loads((Path(__file__).resolve().parents[3]/'weik-cache.json').read_bytes())['files']
    meta = {'delta':{}, 'bundled':{}}
    with ZipFile(apk) as z:
        manifest = json.loads(z.read('assets/json/weik-cache.json'))
        changes,_ = edits(root,z)
        changes["loader/img/loader_skin.img"] = list(garment_edits(root))
        banks = {f'texdb/{db}/{db}.dxt.dat' for db in MATERIALS}
        for name in sorted(set(changes) | banks | {'models/particle.txd'}):
            path = PREFIX+name
            bundled = path in z.namelist()
            data = bytearray(z.read(path) if bundled else (root/name).read_bytes())
            prior = []
            if not bundled and sha(data) != stock[name][0]:
                raise ValueError('Wrong archive member '+name)
            if path+'.patch' in z.namelist():
                size,prior = patch_ranges(z.read(path+'.patch'))
                assert size == len(data)
                apply(data,prior)
            row = manifest['files'][name]
            if sha(data)!=row[0]:
                raise ValueError('Wrong installed baseline '+name)
            new = list(changes.get(name,[]))
            if name in banks:
                new.extend(texture_edits(root,name,data))
            if name == 'models/particle.txd':
                new.extend(lamp_edits(data))
            at = next(offset+i for offset,raw in new for i,b in enumerate(raw)
                      if data[offset+i]!=b)
            at = min(at,len(data)-24)
            apply(data,new)
            row[0] = sha(data)
            fields = dict(at=at,sample=data[at:at+24].hex())
            if bundled:
                meta['bundled'][name] = dict(size=len(data),**fields)
                content = data
            else:
                meta['delta'][name] = dict(hash=row[0],source=stock[name],**fields)
                content = serialise_patch(len(data),merge_ranges(len(data),prior,new))
                replay = bytearray((root/name).read_bytes())
                apply(replay,patch_ranges(content)[1])
                assert sha(replay)==row[0]
                path += '.patch'
            dest = out/path
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(content)
    (assets/'json').mkdir(parents=True,exist_ok=True)
    (assets/'json/weik-cache.json').write_text(json.dumps(manifest,separators=(',',':')))
    (out/'integration.json').write_text(json.dumps(meta,indent=2)+'\n')


if __name__=='__main__':
    build(*map(Path,sys.argv[1:]))
