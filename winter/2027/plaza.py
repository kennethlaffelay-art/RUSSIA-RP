"""Static RenderWare assets for the cleared holiday ground on map7."""
import math
import random
import numpy as np
from gtaLib import dff as rw, col
from resources import img_index

WOOD=(106,65,44); TRIM=(68,47,39); GOLD=(211,164,78); SNOW=(196,205,211)
RED=(159,52,47); WARM=(255,213,148); WIRE=(53,65,60); ICE=(144,173,187)
class Mesh:
    def __init__(self,name):
        self.name=name
        self.geo=rw.Geometry()
        self.night=[]
        self.boxes=[]
        self.fx=[]
    def face(self,points,color,glow=False):
        p=np.array(points,dtype=float)
        normal=np.cross(p[1]-p[0],p[2]-p[0]);normal/=np.linalg.norm(normal)
        g=self.geo;start=len(g.vertices)
        g.vertices.extend(rw.Vector(*v) for v in p)
        g.normals.extend([rw.Vector(*normal)]*len(p))
        g.prelit_colors.extend([rw.RGBA(*color,255)]*len(p))
        tone=color if glow else tuple(round(c*f) for c,f in zip(color,(.42,.50,.66)))
        self.night.extend([rw.RGBA(*tone,255)]*len(p))
        for j in range(1,len(p)-1):
            g.triangles.append(rw.Triangle(start+j,start,0,start+j+1))
    def box(self,low,high,color,solid=False,glow=False):
        x,y,z=low;X,Y,Z=high
        if solid:self.boxes.append((low,high))
        points=[(x,y,z),(X,y,z),(X,Y,z),(x,Y,z),(x,y,Z),(X,y,Z),(X,Y,Z),(x,Y,Z)]
        for ids in ((3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)):
            self.face([points[i] for i in ids],color,glow)
    def bar(self,a,b,r,color,glow=False,sides=5):
        a,b=np.array(a),np.array(b);v=b-a;v=v/np.linalg.norm(v)
        u=np.cross(v,[0.,0.,1.] if abs(v[2])<.85 else [0.,1.,0.]);u=u/np.linalg.norm(u);w=np.cross(v,u)
        offsets=[r*(u*math.cos(i*math.tau/sides)+w*math.sin(i*math.tau/sides)) for i in range(sides)]
        for i in range(sides):
            c,d=offsets[i-1],offsets[i]
            self.face([a+c,a+d,b+d,b+c],color,glow)
    def jewel(self,point,r,color,glow=False):
        x,y,z=point
        ring=[(x+r,y,z),(x,y+r,z),(x-r,y,z),(x,y-r,z)]
        for i in range(4):
            self.face([ring[i-1],ring[i],(x,y,z+r)],color,glow)
            self.face([ring[i],ring[i-1],(x,y,z-r)],color,glow)
    def lamp(self,p,color,wash=0,r=.17):
        fx=rw.Light2dfx(rw.Vector(*p));fx.color=rw.RGBA(*color,255)
        fx.coronaFarClip=115;fx.pointlightRange=wash;fx.coronaSize=r;fx.coronaTexName='coronastar'
        fx._flags1=64
        self.fx.append(fx)
    def string(self,a,b,count,sag=.20):
        prev=np.array(a,dtype=float)
        for i in range(1,count+1):
            t=i/count;p=(1-t)*np.array(a)+t*np.array(b);p[2]-=4*sag*t*(1-t)
            self.bar(prev,p,.017,WIRE,sides=3)
            self.jewel(p-[0,0,.045],.075,WARM,True)
            prev=p
    def store(self):
        g=self.geo;arr=np.array(g.vertices)
        mid=(arr.max(0)+arr.min(0))*.5
        g.bounding_sphere=rw.Sphere(*mid,np.linalg.norm(arr-mid,axis=1).max()+.02)
        material=rw.Material();material.color=rw.RGBA(255,255,255,255);material.surface_properties=rw.GeomSurfPro(1.,0.,.72)
        g.materials=[material]
        g.extensions['extra_vert_color']=rw.ExtraVertColorExtension(self.night)
        f=rw.Frame();f.name=self.name;f.position=rw.Vector(0,0,0);f.rotation_matrix=rw.Matrix(*(rw.Vector(*v) for v in np.eye(3)))
        a=rw.Atomic();a.flags=5
        c=rw.Clump();c.frame_list=[f];c.geometry_list=[g];c.atomic_list=[a];c.ext_2dfx.entries=self.fx
        d=rw.dff();d.clumps.append(c)
        return bytes(d.write_memory(0x36003))
    def collision(self,model_id):
        col.Sections.init_sections(3)
        m=col.ColModel();m.version=3;m.model_id=model_id;m.model_name=self.name
        for a,b in self.boxes:
            m.boxes.append(col.TBox(col.TVector(*a),col.TVector(*b),col.TSurface(0,0,0,0x76)))
        lo=np.min(self.geo.vertices,0);hi=np.max(self.geo.vertices,0)
        m.bounds=col.TBounds(col.TVector(*lo),col.TVector(*hi),col.TVector(*((lo+hi)*.5)),np.linalg.norm(hi-lo)*.5+.01)
        return col.coll(m).write_memory()

def chalet():
    m=Mesh('rrp_chalet')
    m.box((-2.4,-1.64,-.05),(2.4,1.64,2.6),WOOD,True)
    for i in range(12):
        z=.10+i*.21
        m.box((-2.42,-1.66,z),(2.42,1.66,z+.035),TRIM)
    for x in (-2.32,2.18):
        m.box((x,-1.71,-.03),(x+.14,1.71,2.65),TRIM)
    m.box((-1.64,-1.72,1.04),(1.64,-1.67,2.25),WARM,glow=True)
    for x in (-1.65,-.62,.53,1.57):
        m.box((x,-1.76,1.02),(x+.08,-1.72,2.29),TRIM)
    m.box((-1.86,-1.98,.99),(1.86,-1.65,1.09),TRIM)
    for y in (-1.66,1.66):
        pts=[(-2.4,y,2.58),(2.4,y,2.58),(0,y,3.81)]
        m.face(pts if y<0 else pts[::-1],RED)
    for side in (-1,1):
        x=2.74*side
        roof=[(x,-1.99,2.51),(x,1.99,2.51),(0,1.99,3.93),(0,-1.99,3.93)]
        m.face(roof if side==1 else roof[::-1],SNOW)
        m.bar((x,-1.99,2.47),(0,-1.99,3.89),.09,TRIM)
        m.string((x,-2.,2.48),(0,-2.,3.90),8,.07)
    m.lamp((0,-1.97,2.05),WARM,3.8,.14)
    return m

def rink():
    m=Mesh('rrp_rink')
    m.box((-10,-7,-.05),(10,7,.12),ICE,True)
    rng=random.Random(884)
    for _ in range(57):
        x=rng.uniform(-9.1,8.2);y=rng.uniform(-6.2,6.2)
        end=(x+rng.uniform(.4,1.6),y+rng.uniform(-.32,.32),.127)
        m.face([(x,y,.127),end,(x+.04,y+.024,.127)],(161,185,196))
    def rail(a,b):
        a,b=np.array(a),np.array(b);length=np.linalg.norm(b-a)
        for z in (.44,.90):m.bar(a+[0,0,z],b+[0,0,z],.065,WOOD)
        for t in np.linspace(0,1,math.ceil(length/2.8)+1):
            p=(1-t)*a+t*b;m.box(p+[-.075,-.075,0],p+[.075,.075,1.12],TRIM)
        lo=np.minimum(a,b);hi=np.maximum(a,b);m.boxes.append((lo+[-.08,-.08,.12],hi+[.08,.08,.97]))
        m.string(a+[0,0,1.1],b+[0,0,1.1],max(3,math.ceil(length/.85)),.13)
    for a,b in [((-10,-7,0),(-1.7,-7,0)),((1.7,-7,0),(10,-7,0)),((10,-7,0),(10,7,0)),((10,7,0),(-10,7,0)),((-10,7,0),(-10,-7,0))]:
        rail(a,b)
    m.bar((0,0,.10),(0,0,5.6),.095,WOOD)
    m.boxes.append(((-.11,-.11,.12),(.11,.11,5.6)))
    for x,y in [(-10,-7),(10,-7),(10,7),(-10,7),(0,7)]:
        m.bar((x,y,.85),(x,y,3.15),.06,WOOD)
        m.string((0,0,5.6),(x,y,3.15),13,.52)
    m.lamp((0,0,4.95),WARM,6,.16)
    return m

def tree_trim():
    m=Mesh('rrp_firtop')
    for i in range(108):
        t=i/108;theta=math.tau*(4.7*t+.12);r=3.30*(1-t)**.87+.10
        p=(r*math.cos(theta),r*math.sin(theta),1.0+10.9*t)
        m.jewel(p,.078+.02*(1-t),WARM,True)
        if i%3==0:
            p2=(p[0]*.96,p[1]*.96,p[2]-.22)
            m.jewel(p2,.14 if t>.65 else .20,RED if i%2 else GOLD)
        if i in (5,37,72):m.lamp(p,WARM,3.5 if i==5 else 0,.18)
    for side in (-1,1):
        center=(0,side*.19,13.10)
        ring=[(math.cos(math.pi/2+j*math.pi/5)*(.87 if j%2==0 else .36),0,
               13.10+math.sin(math.pi/2+j*math.pi/5)*(.87 if j%2==0 else .36)) for j in range(10)]
        for j in range(10):
            pts=[ring[j-1],ring[j],center];m.face(pts if side<0 else pts[::-1],GOLD if j%2 else WARM,True)
    m.bar((0,0,12.15),(0,0,12.72),.055,GOLD)
    m.lamp((0,0,13.12),WARM,0,.25)
    return m

def wheel_trim():
    m=Mesh('rrp_wheelight')
    for i in range(80):
        a=math.tau*i/80
        for y in (-1.77,1.77):
            p=(11.75*math.cos(a),y,11.75*math.sin(a))
            m.jewel(p,.080,RED if i%5==0 else WARM,True)
        if i%10==0:
            for r in (2.5,4.5,6.5,8.5):
                m.jewel((r*math.cos(a),-1.77,r*math.sin(a)),.093,(226,190,179),True)
    for side in (-1,1):
        for t in np.linspace(.1,.9,13):
            m.jewel((side*9*t,-4.3*t,-15.1*t),.10,RED,True)
    return m

def year_sign(year):
    if not isinstance(year,int) or not 1000<=year<=9999:raise ValueError('The season needs a four-digit year')
    m=Mesh('rrp_season')
    segments=[((0,2.06),(1.03,2.06)),((1.03,2.06),(1.03,1.09)),((1.03,1.09),(1.03,.12)),
              ((0,.12),(1.03,.12)),((0,1.09),(0,.12)),((0,2.06),(0,1.09)),((0,1.09),(1.03,1.09))]
    masks=['abcdef','bc','abged','abgcd','fgbc','afgcd','afgecd','abc','abcdefg','abfgcd']
    for k,char in enumerate(str(year)):
        for letter in masks[int(char)]:
            a,b=segments[ord(letter)-97];x=k*1.46-2.7
            m.bar((x+a[0],0,a[1]+.17),(x+b[0],0,b[1]+.17),.126,GOLD,True,8)
    m.box((-2.99,-.28,-.03),(2.99,.28,.19),TRIM,True)
    m.lamp((0,-.33,1.1),WARM,2.5,.1)
    return m

def decorations():
    m=Mesh('rrp_snowbank')
    rng=random.Random(551)
    for cx,cy,r,h in [(-1.2,.1,1.95,.43),(.94,-.1,1.55,.34)]:
        rings=[]
        for j in range(3):
            t=(j+1)/3
            rings.append([(cx+math.cos(a)*r*t,cy+math.sin(a)*r*t*.57,h*(1-t*t)+rng.uniform(-.029,.029)-.03)
                          for a in [i*math.tau/12 for i in range(12)]])
        for i in range(12):
            m.face([(cx,cy,h),rings[0][i-1],rings[0][i]],SNOW)
            for inner,outer in zip(rings,rings[1:]):
                m.face([inner[i-1],outer[i-1],outer[i],inner[i]],SNOW)
    return m

def layout(year):
    meshes=[chalet(),rink(),tree_trim(),wheel_trim(),year_sign(year),decorations()]
    ids={mesh.name:13636+i for i,mesh in enumerate(meshes)}
    z=36.375
    places=[]
    def add(mid,name,x,y,dz=0,angle=0):
        places.append((mid,name,x,y,z+dz,angle))
    # East-west access on the original bridge alignment stays clear.
    add(19076,'XmasTree1',719,-2313);add(ids['rrp_firtop'],'rrp_firtop',719,-2313)
    add(ids['rrp_season'],'rrp_season',719,-2319)
    for i,(x,y) in enumerate([(716.5,-2314),(718,-2315.7),(721.2,-2314.2),(717,-2311)]):
        add(19054+i,'XmasBox'+str(i+1),x,y,.66,15+i*17)
    for x,y,angle in [(700,-2317,-90),(700,-2326,-90),(737,-2326,90),(737,-2317,90)]:
        add(ids['rrp_chalet'],'rrp_chalet',x,y,0,angle)
    add(ids['rrp_rink'],'rrp_rink',721,-2286)
    for x,y,ang in [(706,-2289,0),(736,-2289,180),(707,-2326,90),(730,-2328,90)]:
        add(1280,'parkbench1',x,y,.401,ang)
    for x,y in [(706,-2292),(736,-2292)]:
        add(1300,'bin1',x,y,.37)
    for x,y in [(707,-2296),(735,-2296),(708,-2332),(733,-2332)]:
        add(1223,'lampost_coast',x,y,-.012)
    wx,wy=721,-2263
    for mid,name in [(18877,'FerrisWheelBit'),(18878,'FerrisBaseBit'),(ids['rrp_wheelight'],'rrp_wheelight')]:
        add(mid,name,wx,wy,16.23)
    for i in range(10):
        a=i*math.tau/10
        add(18879,'FerrisCageBit',wx+11.72*math.cos(a),wy,16.23+11.72*math.sin(a))
    for x,y,a in [(696,-2330,10),(697,-2310,76),(740,-2327,113),(710,-2276,25),(734,-2281,60),(706,-2266,15)]:
        add(ids['rrp_snowbank'],'rrp_snowbank',x,y,0,a)
    return meshes,ids,places
