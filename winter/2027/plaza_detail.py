"""Textured geometry for mobile world objects with native texture database materials."""
import math
import random
import numpy as np
from gtaLib import dff as rw

BARK=(78,62,43)
FIR=(55,83,58)
STEEL=(104,118,130)
WHITE_METAL=(170,175,181)

def surface(color,glow):
    return {
        (106,65,44):'CJ_LIGHTWOOD', (68,47,39):'ab_panel_woodgrime',
        (211,164,78):'ab_goldpipe', (196,205,211):'new_ryazan_lesdirt_rd',
        (159,52,47):'ab_redwall', (255,213,148):'ab_metal_brass',
        (53,65,60):'steel256128', (144,173,187):'E_KvPr_Ice',
        (161,185,196):'new_ryazan_lesdirt_rd', BARK:'ab_panel_woodgrime',
        FIR:'pinebranch1', STEEL:'steel256128', WHITE_METAL:'cj_chrome',
    }.get(tuple(color),'ab_metal_brass' if glow else 'CJ_LIGHTWOOD')

def material(mesh,color,glow,name=None):
    name=name or surface(color,glow)
    key=(name,tuple(color),glow)
    if key not in mesh.slots:
        t=rw.Texture();t.name=name;t.filters=6;t.uv_addressing=0x11
        m=rw.Material();m.textures=[t]
        # Albedo comes from the actual texture, including on mobile shaders that skip prelight.
        m.color=rw.RGBA(*(tuple(min(238,int(95+c*.64)) for c in color)),255)
        m.surface_properties=rw.GeomSurfPro(.92 if glow else .72,0.,.34 if glow else .65)
        mesh.slots[key]=len(mesh.geo.materials);mesh.geo.materials.append(m)
    return mesh.slots[key]

def branch_crown(mesh):
    rng=random.Random(81722)
    mesh.bar((0,0,.03),(0,0,12.25),.23,BARK,sides=8)
    for j in range(22):
        t=j/22;z=.89+11.4*t;radius=3.26*(1-t)**.81+.09
        count=max(7,round(24*(1-t*.66)))
        for i in range(count):
            a=i*math.tau/count+j*1.28+rng.uniform(-.10,.10)
            radial=np.array([math.cos(a),math.sin(a),0.]);tangent=np.array([-radial[1],radial[0],0.])
            r=radius*rng.uniform(.86,1.08);width=r*.27+.09
            start=radial*r*.15+[0,0,z+.28]
            end=radial*r+[0,0,z-.30-rng.uniform(0,.18)]
            for tilt in (-1,1):
                sideways=width*(tangent*.68+np.array([0,0,.79*tilt]))
                pts=[start-sideways*.38,end-sideways,end+sideways,start+sideways*.38]
                mesh.face(pts,FIR,tex='pinebranch1',uv=[(0,0),(1,0),(1,1),(0,1)])
                mesh.face(pts[::-1],FIR,tex='pinebranch1',uv=[(0,1),(1,1),(1,0),(0,0)])
    # Textured parcels and ribbons belong to the same static asset.
    for i,(x,y,s) in enumerate([(-2,-1,.85),(1.7,-.8,.69),(-.9,-2.5,.72),(1.9,1,.57),(.3,-2.1,.52)]):
        red=(159,52,47);gold=(211,164,78)
        mesh.box((x-s/2,y-s/2,0),(x+s/2,y+s/2,s),red if i%2==0 else gold)
        mesh.box((x-.08,y-s/2-.005,-.003),(x+.08,y+s/2+.005,s+.008),gold if i%2==0 else red)

def wheel_structure(m):
    radius=11.72
    gold=(211,164,78);red=(159,52,47)
    for i in range(48):
        a=math.tau*i/48;b=math.tau*(i+1)/48
        for y in (-1.44,1.44):
            p=(radius*math.cos(a),y,radius*math.sin(a));q=(radius*math.cos(b),y,radius*math.sin(b))
            m.bar(p,q,.11,WHITE_METAL,sides=5)
            if i%4==0:
                m.bar((0,y,0),p,.063,STEEL,sides=4)
                m.bar(p,(p[0],-y,p[2]),.071,WHITE_METAL,sides=4)
    m.bar((0,-2.75,0),(0,2.75,0),.34,STEEL,sides=8)
    for y in (-2.7,2.7):
        for sign in (-1,1):
            x=8.8*sign
            m.bar((0,y,0),(x,y*1.52,-16.2),.24,STEEL,sides=6)
            m.box((x-.62,y*1.52-.62,-16.23),(x+.62,y*1.52+.62,-15.9),WHITE_METAL)
    for i in range(10):
        a=math.tau*i/10;x=radius*math.cos(a);z=radius*math.sin(a)
        for y in (-1.0,1.0):
            m.bar((x,y,z),(x,y,z-1.29),.054,STEEL,sides=4)
        m.box((x-.74,-1.13,z-2.17),(x+.74,1.13,z-1.37),red if i%3 else gold)
        m.box((x-.84,-1.21,z-.99),(x+.84,1.21,z-.87),WHITE_METAL)
