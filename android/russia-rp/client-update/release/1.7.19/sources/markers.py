"""Draw radar sprites and matching transparent world marker artwork."""
from pathlib import Path
from PIL import Image, ImageDraw
import subprocess, json, tempfile
from concurrent.futures import ThreadPoolExecutor

# key, title, source pictogram, category colour, existing texture (if confirmed)
PLACES = [
    ('hospital','Больница','hospital','#B93F4E','radar_hostpital'),
    ('police','Полиция','police','#2C60A4','radar_police'),
    ('repair','Автосервис','car-repair','#B45028','radar_modGarage'),
    ('clothes','Одежда','clothing-store','#805689','radar_tshirt'),
    ('food','Закусочная','fast-food','#9C5120','radar_burgerShot'),
    ('dining','Ресторан','restaurant','#9C5120','radar_dateFood'),
    ('pizza','Пиццерия','restaurant-pizza','#9C5120','radar_pizza'),
    ('bar','Бар','bar','#92536E','radar_dateDrink'),
    ('cash','Деньги','bank','#28755A','radar_cash'),
    ('house-green','Дом · зелёная метка','home','#29754C','radar_propertyG'),
    ('house-red','Дом · красная метка','home','#AC4146','radar_propertyR'),
    ('barber','Парикмахерская','hairdresser','#805689','radar_barbers'),
    ('gym','Спортзал','fitness-centre','#28757B','radar_gym'),
    ('airfield','Аэродром','airfield','#496781','radar_airYard'),
    ('hotel','Отель','lodging','#316F89','radar_BIGSMOKE'),
    ('dealer','Автосалон','car','#A44725','radar_CESARVIAPANDO'),
    ('fuel','АЗС','fuel','#946316',None),
    ('entry','Вход','entrance','#286B69',None),
    ('parking','Парковка','parking','#34698B',None),
    ('station','Вокзал','rail','#436597',None),
]
DARK='#19212A'
def make_one(record, source, out):
    key,title,icon,color,texture = record
    with tempfile.TemporaryDirectory() as tmp:
        f=Path(tmp)/'symbol.png'
        subprocess.run(['inkscape',str(source/'icons'/(icon+'.svg')),'--export-filename='+str(f),'--export-width=160','--export-height=160'],capture_output=True,check=True)
        alpha=Image.open(f).convert('RGBA').getchannel('A')
    glyph=Image.new('RGBA',alpha.size,'#FFF9EF');glyph.putalpha(alpha)
    face=Image.new('RGBA',(256,256))
    draw=ImageDraw.Draw(face)
    draw.rounded_rectangle((8,8,247,247),radius=40,fill=DARK)
    draw.rounded_rectangle((24,24,231,231),radius=24,fill=color)
    face.alpha_composite(glyph,(48,48))
    face.resize((64,64),Image.Resampling.BOX).save(out/'radar'/(key+'.png'))
    pin=Image.new('RGBA',(256,256))
    d=ImageDraw.Draw(pin)
    d.polygon([(79,156),(177,156),(128,243)],fill=DARK)
    d.polygon([(91,158),(165,158),(128,220)],fill=color)
    pin.alpha_composite(face.resize((202,202),Image.Resampling.LANCZOS),(27,5))
    pin.save(out/'pickups'/(key+'.png'))
    return dict(id=key,title=title,pictogram=icon,texture=texture)
def build(source, out):
    for name in ('radar','pickups'): (out/name).mkdir(parents=True,exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        result=list(pool.map(lambda row:make_one(row,source,out),PLACES))
    (out/'markers.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':
    import sys
    build(Path(sys.argv[1]), Path(sys.argv[2]))
