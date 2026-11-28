"""RUSSIA RP map artwork. Keys are the engine's texture names without radar_."""
from PIL import Image, ImageDraw, ImageFont

INK = "#182329"
IVORY = "#fff4dc"
COPPER = "#d58754"
GROUPS = {
    "airyard boatyard impound truck bulldozer runway modgarage cesarviapando": "#368093",
    "girlfriend fire enemyattack propertyr": "#bd5345",
    "hospital hostpital police crash1": "#466fa2",
    "propertyg cash gangg": "#338863",
    "barbers tshirt tattoo datedisco datedrink spray": "#7a6192",
    "race flag gym school": "#527f75",
    "gangb": "#367798", "gangn": "#508da9", "gangy": "#ba8534", "gangp": "#865593",
}
COLORS = {name: color for keys, color in GROUPS.items() for name in keys.split()}
MONOGRAMS = dict(catalinapink="C", cj="CJ", crash1="C", maddog="MD",
                 mcstrap="MC", ogloc="OG", ryder="R", school="S", sweet="S",
                 thetruth="TT", toreno="T", torenoranch="TR", woozie="W", zero="Z")
SYMBOLS = {
    'plane':'airyard', 'sidearm':'ammugun emmetgun', 'scissors':'barbers', 'bed':'bigsmoke',
    'anchor':'boatyard', 'forklift':'bulldozer', 'burger':'burgershot', 'coin':'cash',
    'car':'cesarviapando', 'cloche':'chicken', 'disc':'datedisco', 'glass':'datedrink',
    'cutlery':'datefood', 'cup':'diner', 'pennant':'enemyattack', 'beacon':'fire',
    'flag':'flag', 'jersey':'gangb gangg gangn gangp gangy', 'heart':'girlfriend',
    'weight':'gym', 'medical':'hostpital', 'parking':'impound', 'sun':'light',
    'skull':'locosyndicate', 'dice':'mafiacasino', 'wrench':'modgarage', 'pizza':'pizza',
    'shield':'police', 'house':'propertyg propertyr', 'help':'qmark', 'cupwin':'race',
    'strip':'runway', 'disk':'savegame', 'can':'spray', 'needle':'tattoo',
    'crest':'triads triadscasino', 'lorry':'truck', 'shirt':'tshirt',
}
KINDS = {name: kind for kind, names in SYMBOLS.items() for name in names.split()}
NAMES = set(KINDS) | set(MONOGRAMS) | {'north','centre','waypoint'}

def radar(name, size=64):
    """Draw at native pixel grid so the silhouette survives DXT and small HUD sizes."""
    if name not in NAMES:
        raise ValueError(f"Map sprite needs its own design: {name}")
    im = Image.new("RGBA", (64,64))
    d = ImageDraw.Draw(im)
    def poly(points, color=IVORY): d.polygon(points, fill=color)
    def line(points, color=IVORY, w=4): d.line(points, fill=color, width=w, joint="curve")
    def oval(box, color=IVORY): d.ellipse(box, fill=color)
    def box(rect, color=IVORY): d.rectangle(rect, fill=color)
    def label(text, height=22):
        font = ImageFont.load_default(size=height)
        d.text((32,31), text, font=font, fill=IVORY, stroke_width=1, stroke_fill=IVORY, anchor="mm")
    tone = COLORS.get(name, "#ae653d")
    if name == 'centre':
        poly([(32,2),(54,55),(32,47),(10,55)], INK)
        poly([(32,9),(47,48),(32,41),(17,48)])
        poly([(32,17),(32,39),(21,44)], COPPER)
    elif name == 'waypoint':
        poly([(32,2),(55,21),(52,37),(32,62),(12,37),(9,21)],INK)
        poly([(32,8),(49,22),(47,35),(32,54),(17,35),(15,22)],COPPER)
        oval((23,17,41,35)); oval((28,22,36,30),INK)
    elif name == 'north':
        poly([(32,2),(55,17),(55,52),(32,60),(9,52),(9,17)],INK)
        poly([(32,6),(40,17),(24,17)],COPPER)
        label('N',26)
    else:
        # Chamfered plate, raised rim and two colour cues remain legible on snow and asphalt.
        poly([(12,3),(50,3),(60,13),(60,50),(50,60),(12,60),(3,51),(3,13)],INK)
        poly([(13,7),(49,7),(55,13),(55,47),(48,54),(14,54),(8,48),(8,14)],tone)
        poly([(15,12),(47,12),(51,16),(51,44),(45,49),(17,49),(12,44),(12,17)],INK)
        line([(20,55),(43,55)],COPPER,3)
        kind = KINDS.get(name)
        if name in MONOGRAMS: label(MONOGRAMS[name],22 if len(MONOGRAMS[name])==1 else 16)
        elif kind=='plane':
            poly([(30,16),(34,16),(35,27),(47,33),(47,36),(35,33),(35,40),(39,43),(39,45),(32,43),(25,45),(25,43),(29,40),(29,33),(17,36),(17,33),(29,27)])
        elif kind=='sidearm':
            poly([(16,21),(46,21),(46,29),(32,29),(29,34),(25,34),(23,43),(16,41),(20,28),(16,28)])
            line([(34,24),(43,24)],tone,2)
        elif kind=='scissors':
            for x in (18,33): oval((x,33,x+11,44));oval((x+3,36,x+8,41),INK)
            line([(23,35),(42,18)]);line([(38,35),(22,18)])
        elif kind=='bed':
            line([(17,20),(17,43)]);line([(18,36),(47,36),(47,43)])
            box((21,28,26,33));poly([(28,25),(40,25),(46,29),(46,33),(28,33)])
        elif kind=='anchor':
            oval((27,16,36,25));oval((30,19,33,22),INK)
            line([(32,24),(32,43)]);line([(23,28),(41,28)])
            line([(18,33),(21,39),(32,44),(43,39),(46,33)])
        elif kind in ('forklift','lorry'):
            box((17,23,33,35));poly([(34,26),(40,26),(45,32),(45,36),(34,36)])
            if kind=='forklift':line([(43,19),(43,34),(48,34)],COPPER,3)
            for x in (21,35):oval((x,34,x+7,41))
        elif kind=='burger':
            d.pieslice((18,18,46,40),180,360, fill=IVORY);box((17,31,47,34),COPPER)
            poly([(19,37),(45,37),(41,42),(23,42)])
        elif kind=='coin':
            line([(26,43),(26,19),(36,19),(40,22),(40,27),(36,31),(23,31)],w=4)
            line([(22,36),(36,36)],COPPER,3)
        elif kind=='help': label('?',25)
        elif kind in ('car','parking'):
            poly([(17,32),(21,22),(40,22),(46,32),(46,41),(42,41),(41,38),(23,38),(22,41),(17,41)])
            poly([(22,29),(25,25),(38,25),(41,29)],INK)
            for x in (20,38):box((x,33,x+5,35),tone)
            if kind=='parking':line([(26,18),(38,18)],COPPER,2)
        elif kind=='cloche':
            d.pieslice((18,22,46,46),180,360,fill=IVORY);box((16,36,48,39));oval((30,18,34,23),COPPER)
        elif kind=='disc':
            oval((18,17,46,45));oval((24,23,40,39),tone);oval((28,27,36,35),INK);oval((31,30,33,32))
        elif kind=='glass':
            poly([(17,19),(47,19),(34,34),(34,40),(41,42),(41,44),(23,44),(23,42),(30,40),(30,34)])
            poly([(23,22),(40,22),(36,26),(27,26)],tone)
        elif kind=='cutlery':
            for x in (20,24,28):line([(x,18),(x,29)],w=2)
            box((20,28,29,31));box((23,30,26,44));poly([(40,18),(41,44),(37,44),(37,33),(33,32),(35,22)])
        elif kind=='cup':
            poly([(21,25),(43,25),(40,43),(24,43)]);line([(18,22),(45,22)]);line([(33,22),(36,16),(42,16)],COPPER,2)
        elif kind in ('pennant','flag'):
            line([(20,17),(20,45)]);poly([(23,19),(45,19),(41,25),(45,31),(23,31)],tone if kind=='pennant' else IVORY)
            if kind=='flag':
                for x,y in ((23,19),(31,19),(27,23),(35,23),(23,27),(31,27)):box((x,y,x+3,y+3),INK)
        elif kind=='beacon':
            d.rounded_rectangle((22,24,42,39),radius=7,fill=IVORY);box((18,39,46,43))
            for seg in [[(32,15),(32,20)],[(16,21),(20,24)],[(48,21),(44,24)]]:line(seg,COPPER,2)
        elif kind in ('shirt','jersey'):
            poly([(26,18),(31,21),(34,21),(38,18),(47,24),(43,32),(39,30),(39,43),(25,43),(25,30),(21,32),(17,24)])
            if kind=='jersey':box((28,27,36,31),tone);box((31,32,34,38),tone)
        elif kind=='heart':
            oval((18,20,32,34));oval((31,20,45,34));poly([(19,30),(44,30),(32,44)])
        elif kind=='weight':
            box((17,26,20,36));box((22,21,27,41));box((27,29,37,33));box((37,21,42,41));box((44,26,47,36))
        elif kind=='medical':box((28,18,36,44));box((19,27,45,35))
        elif kind=='sun':
            oval((25,24,39,38))
            for a,b in [((32,16),(32,21)),((32,41),(32,46)),((17,31),(22,31)),((42,31),(47,31))]:line([a,b],COPPER,3)
        elif kind=='skull':
            oval((19,18,45,39));box((25,32,39,42))
            for x in (24,34):oval((x,27,x+5,32),INK)
            line([(30,38),(30,43)],INK,2)
        elif kind=='dice':
            poly([(31,16),(46,26),(42,40),(32,45),(18,36),(18,24)])
            for x,y in ((26,23),(34,26),(25,32),(36,36)):oval((x,y,x+3,y+3),INK)
        elif kind=='wrench':
            poly([(18,39),(32,26),(32,21),(38,17),(43,18),(37,24),(41,28),(47,22),(47,28),(42,34),(36,34),(23,44)])
            oval((21,38,24,41),INK)
        elif kind=='pizza':
            poly([(17,22),(31,17),(46,22),(32,44)])
            for x,y in ((23,23),(34,23),(29,31)):oval((x,y,x+4,y+4),tone)
        elif kind in ('shield','crest'):
            poly([(32,16),(45,21),(43,34),(37,41),(32,45),(26,41),(21,34),(19,21)])
            if kind=='shield':poly([(32,22),(35,28),(40,29),(36,33),(37,38),(32,35),(27,38),(28,32),(24,29),(29,28)],tone)
            else:line([(25,34),(36,23),(38,28),(29,37)],tone,4)
        elif kind=='house':
            poly([(16,30),(32,17),(48,30),(44,33),(41,31),(41,43),(23,43),(23,31),(20,33)])
            box((29,33,35,43),tone)
        elif kind=='cupwin':
            poly([(23,18),(41,18),(39,30),(34,35),(34,40),(40,40),(40,43),(24,43),(24,40),(30,40),(30,35),(25,30)])
            for seg in [[(23,21),(17,21),(18,27),(24,30)],[(40,21),(47,21),(45,27),(40,30)]]:line(seg,w=2)
        elif kind=='strip':
            poly([(28,17),(36,17),(44,44),(20,44)])
            for y in (20,27,35):box((31,y,33,y+3),INK)
        elif kind=='disk':
            poly([(19,18),(40,18),(45,23),(45,43),(19,43)]);box((24,18,36,26),tone);box((24,32,40,41),INK);box((27,35,37,37))
        elif kind=='can':
            box((24,26,40,43));box((27,21,37,25));box((29,17,34,20))
            line([(39,20),(46,17)],COPPER,2);box((26,32,38,35),tone)
        elif kind=='needle':
            poly([(37,17),(44,23),(33,35),(28,31)]);line([(29,32),(19,43)],w=3);line([(35,18),(43,26)],COPPER,2)
        else: raise ValueError(name)
    return im.resize((size,size), Image.Resampling.LANCZOS) if size!=64 else im
