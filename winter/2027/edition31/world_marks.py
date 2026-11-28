"""Build the 3D navigation marks used by the engine and streamed object dictionaries."""
import math
import re
import struct
import numpy as np
from gtaLib import dff as rw

ENGINE = {'arrow', 'cylinder', 'hoop', 'diamond_3'}
PALETTE = {
    'property_locked': (231,104,87), 'property_fsale': (97,214,160),
    'health': (233,95,108), 'adrenaline': (240,181,92), 'bribe': (102,175,223),
    'bigdollar': (101,201,144), 'bodyarmour': (113,165,209), 'info': (241,188,107),
    'killfrenzy': (227,120,98), 'clothesp': (173,148,221),
}
def design_names(root):
    catalog = set(ENGINE)
    for name in ('generic','SAMP'):
        text = (root / ('data/maps/'+name+'.ide')).read_text('latin1')
        catalog.update(match.lower() for match in re.findall(
            r'^\s*\d+,\s*([\w-]+),\s*(?:icons\d*|enexmarkers|matarrows)\s*,',text,re.M|re.I))
    return catalog | {'areaboundary1m','enexmarker4'}

class Mark:
    def __init__(self, old):
        self.geo = rw.Geometry()
        self.geo.export_flags['light'] = False
        self.geo.bounding_sphere = old.bounding_sphere
        mat = rw.Material()
        mat.color = rw.RGBA(255,255,255,255)
        mat.surface_properties = rw.GeomSurfPro(1.,0.,.6)
        self.geo.materials = [mat]
        pos = np.asarray(old.vertices)
        self.low = pos.min(axis=0)
        self.span = pos.max(axis=0)-self.low
        self.indices = {}

    def vertex(self, point, color):
        key = (*point,*color)
        if key not in self.indices:
            self.indices[key] = len(self.geo.vertices)
            self.geo.vertices.append(rw.Vector(*(self.low+self.span*np.asarray(point))))
            self.geo.prelit_colors.append(rw.RGBA(*color))
        return self.indices[key]

    def face(self, points, colors):
        ids = [self.vertex(p,c) for p,c in zip(points,colors)]
        for i in range(1,len(ids)-1):
            self.geo.triangles.append(rw.Triangle(ids[i],ids[0],0,ids[i+1]))

    def band(self, rows, sides):
        for (z,r,c),(Z,R,C) in zip(rows,rows[1:]):
            for i in range(sides):
                a,b = i*math.tau/sides, ((i+1)%sides)*math.tau/sides
                def point(angle, radius, h):
                    return (.5+radius*math.cos(angle),.5+radius*math.sin(angle),h)
                self.face([point(a,r,z),point(b,r,z),point(b,R,Z),point(a,R,Z)],[c,c,C,C])

    def chevron(self, low, high, color):
        # Convex panels form a double-sided extruded downward chevron along the stock YZ plane.
        mid=(high+low)/2
        outline=[(.04, high),(.5,mid),(.96,high),(.96,mid),(.5,low),(.04,mid)]
        # Each wing is a convex quad. Keep the central cutout hollow.
        for x,order in ((0.,(3,2,1,0)),(1.,(0,1,2,3))):
            for wing in ((0,1,4,5),(1,2,3,4)):
                pts=[(x,*outline[wing[i]]) for i in order]
                self.face(pts,[color]*4)
        edge=(118,88,62,255)
        for i,(y,z) in enumerate(outline):
            Y,Z=outline[(i+1)%len(outline)]
            self.face([(0.,y,z),(1.,y,z),(1.,Y,Z),(0.,Y,Z)],[edge]*4)

def model(name, raw, budget):
    d=rw.dff()
    d.load_memory(raw)
    if not d.clumps: raise ValueError(name)
    ivory=(255,239,207,255)
    copper=(214,137,87,255)
    for clump in d.clumps:
        for i,old in enumerate(clump.geometry_list):
            mark=Mark(old)
            if name.startswith('arrow'):
                mark.chevron(.03,.64,ivory)
                mark.chevron(.62,.99,copper)
            elif name=='hoop':
                mark.band([(.02,.40,copper),(.46,.49,ivory),(.99,.40,copper),(.46,.37,ivory),(.02,.40,copper)],16)
            elif name in {'diamond_3','enexmarker1','enexmarker2','enexmarker3'}:
                # An open, faceted locator floats above the exact interaction point.
                mark.band([(.01,.015,copper),(.44,.39,ivory),(.65,.47,copper),(.69,.35,ivory)],6)
                mark.band([(.78,.35,copper),(.90,.39,ivory),(.99,.18,copper)],6)
            elif name=='cylinder' or name.startswith(('cpsize','enexmarker4')):
                tint=next((v for k,v in [('red',(246,102,87)),('green',(107,212,151)),
                    ('blue',(113,186,242)),('-2',(246,102,87)),('-3',(107,212,151)),
                    ('-4',(113,186,242))] if k in name),(247,188,121))
                mark.band([(0,.49,(*tint,220)),(.055,.49,(*tint,198)),(.18,.48,(*tint,68)),
                           (.96,.47,(*tint,8)),(1,.47,(*tint,40))],12)
            elif name.startswith('areaboundary'):
                for lo,hi,alpha in [(0.,.025,185),(.025,.17,75),(.17,1.,12)]:
                    mark.face([(0,0,lo),(1,0,lo),(1,0,hi),(0,0,hi)],[(231,146,99,alpha)]*4)
                    mark.face([(0,0,hi),(1,0,hi),(1,0,lo),(0,0,lo)],[(231,146,99,alpha)]*4)
            else:
                return refinish_pickup(name, raw, clump.geometry_list)
            clump.geometry_list[i]=mark.geo
    data=bytes(d.write_memory(d.rw_version))
    if len(data)>budget: raise ValueError(f'{name}: {len(data)} bytes in a {budget}-byte slot')
    return data.ljust(budget,b'\0')

def refinish_pickup(name, raw, geometries):
    # Preserve opaque extensions, animation data and indices in their original slots.
    data = bytearray(raw)
    tint = np.array(PALETTE.get(name,(222,172,117)))
    for geo in geometries:
        xyz = np.asarray(geo.vertices, dtype='<f4')
        if not len(xyz):
            continue
        original = xyz.tobytes()
        offset = raw.find(original)
        if offset < 0 or raw.find(original,offset+1)>=0:
            raise ValueError(f'Ambiguous vertex stream in {name}')
        lo, hi = xyz.min(axis=0), xyz.max(axis=0)
        height = (xyz[:,2]-lo[2])/max(hi[2]-lo[2],1e-6)
        center = (lo[:2]+hi[:2])*.5
        xyz[:,:2] = center + (xyz[:,:2]-center)*(.84+.16*np.sin(math.pi*height))[:,None]
        data[offset:offset+len(original)] = xyz.tobytes()
        if geo.prelit_colors:
            rgba = np.asarray(geo.prelit_colors,dtype=np.uint8)
            old = rgba.tobytes()
            # The prelight array precedes UVs, triangles, and the 24-byte morph target header.
            at = offset-24-8*len(geo.triangles)-8*len(xyz)*len(geo.uv_layers)-len(old)
            if raw[at:at+len(old)] != old:
                raise ValueError(f'Unexpected prelight layout in {name}')
            rgba[:,:3] = np.rint((.70+.30*height[:,None])*tint)
            data[at:at+len(old)] = rgba.tobytes()
    if data == raw:
        raise ValueError(f'No visible pickup change in {name}')
    return bytes(data)
