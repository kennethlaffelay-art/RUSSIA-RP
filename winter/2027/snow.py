import math
import random
import numpy as np
from gtaLib import dff as rw
from plaza import Mesh

def flurries():
    mesh=Mesh('FakeSnow1')
    rng=random.Random(69017)
    for j in range(37):
        x,y,z=rng.uniform(-5,5),rng.uniform(-5,5),rng.uniform(-1.8,3.9)
        radius=rng.uniform(.022,.054) if j>2 else rng.uniform(.060,.077)
        opacity=rng.randint(80,143) if j>2 else rng.randint(160,188)
        for plane in (0,math.pi/2):
            a=plane+j*.73
            ux=radius*math.cos(a);uy=radius*math.sin(a)
            g=mesh.geo;start=len(g.vertices)
            for dx,dy,dz,alpha in [(0,0,0,opacity),(ux,uy,0,0),(0,0,radius*1.4,0),(-ux,-uy,0,0),(0,0,-radius*1.4,0)]:
                g.vertices.append(rw.Vector(x+dx,y+dy,z+dz))
                g.normals.append(rw.Vector(-math.sin(a),math.cos(a),0))
                g.prelit_colors.append(rw.RGBA(214,222,231,alpha))
                mesh.night.append(rw.RGBA(145,160,180,alpha))
            for k in range(4):
                g.triangles.append(rw.Triangle(start+1+k,start,0,start+1+(k+1)%4))
    return mesh.store()
