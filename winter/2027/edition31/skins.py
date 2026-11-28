"""Add winter garment thickness in the existing rigged models' vertex slots."""
import re
import numpy as np
from gtaLib import dff
from resources import img_index
from rig import animation_tracks, check_rig

MODELS = {54: ('ofost', {'fsbagent_shirt','fsbagent_armor'}),
          291: ('paul', {'350bomber7','350hood7'})}


def garment_edits(root):
    clips = animation_tracks(root/'anim/ped.ifp')
    catalog = (root/'SAMP/peds.ide').read_text('latin1')
    with (root/'loader/img/loader_skin.img').open('rb') as stream:
        entries = img_index(stream)
        for game_id,(name,materials) in MODELS.items():
            if not re.search(rf'^\s*{game_id},\s*{name}\s*,',catalog,re.M|re.I):
                raise ValueError('Missing skin ID '+str(game_id))
            start,size = entries[name+'.dff']
            stream.seek(start)
            raw = stream.read(size)
            model = dff.dff()
            model.load_memory(raw)
            geo, = model.clumps[0].geometry_list
            xyz = np.array(geo.vertices,dtype='<f4')
            normals = np.array(geo.normals,dtype='<f4')
            assert 'skin' in geo.extensions and xyz.shape == normals.shape
            target = {i for i,m in enumerate(geo.materials)
                      if any(t.name.lower() in materials for t in m.textures)}
            keep, puff = set(),set()
            for tri in geo.extensions['mat_split']:
                (puff if tri.material in target else keep).update((tri.a,tri.b,tri.c))
            # Keep garment seams attached to unmodified surfaces. Collapse seam
            # duplicates onto a single displacement even across separate UV islands.
            fixed = {tuple(xyz[i]) for i in keep}
            groups = {}
            for i in sorted(puff):
                point = tuple(xyz[i])
                if point not in fixed:
                    groups.setdefault(point,[]).append(i)
            original = xyz.tobytes()
            if raw.count(original)!=1 or not groups:
                raise ValueError('Unexpected vertex layout for '+name)
            for indices in groups.values():
                normal = normals[indices].mean(axis=0)
                xyz[indices] += normal*(.007/max(np.linalg.norm(normal),1e-6))
            at = raw.index(original)
            replacement = xyz.tobytes()
            changed = dff.dff()
            changed.load_memory(raw[:at]+replacement+raw[at+len(original):])
            check_rig(changed.clumps[0],clips)
            yield start+at,replacement
