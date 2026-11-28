"""Match animated ANP3 tracks to the HAnim hierarchy and skinned vertex weights."""
import struct
import numpy as np


def animation_tracks(path):
    raw = path.read_bytes()
    magic,length = struct.unpack_from('<4sI',raw)
    assert magic==b'ANP3' and length==len(raw)-8
    count, = struct.unpack_from('<I',raw,32)
    pos = 36
    clips = {}
    for _ in range(count):
        name = raw[pos:pos+24].split(b'\0')[0].lower()
        bones, = struct.unpack_from('<I',raw,pos+24)
        pos += 36
        tracks = {}
        for _ in range(bones):
            fmt,frames,bone = struct.unpack_from('<III',raw,pos+24)
            stride = {3:10,4:16}[fmt]
            pos += 36
            if name in (b'handsup',b'walk_civi'):
                tracks[bone] = frames
            pos += frames*stride
        if tracks:
            clips[name] = tracks
    assert pos==len(raw) and set(clips)=={b'handsup',b'walk_civi'}
    return clips


def check_rig(clump,clips):
    skin = clump.geometry_list[0].extensions['skin']
    root, = [f.bone_data for f in clump.frame_list if f.bone_data and f.bone_data.bones]
    mapping = {b.id:b.index for b in root.bones}
    frames = {f.bone_data.header.id for f in clump.frame_list if f.bone_data}
    assert set(mapping)==frames and set(mapping.values())==set(range(skin.num_bones))
    assert len(skin.bone_matrices)==skin.num_bones and np.isfinite(skin.bone_matrices).all()
    weights = np.asarray(skin.vertex_bone_weights)
    indices = np.asarray(skin.vertex_bone_indices)
    assert len(weights)==len(clump.geometry_list[0].vertices) and indices.shape==weights.shape
    assert (weights>=0).all() and np.allclose(weights.sum(axis=1),1,atol=.001)
    used = set(indices[weights>0])
    assert used <= set(mapping.values())
    for clip,tracks in clips.items():
        if not set(tracks)<=frames or max(tracks.values())<2:
            raise ValueError(f'Animation track mismatch for {clip!r}: {set(tracks)-frames}')
