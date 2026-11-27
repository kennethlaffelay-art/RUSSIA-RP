"""Integrate the season into the release cache loader and build a normal or side-by-side APK."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED, ZIP_STORED

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'android/russia-rp/branding'))
from android_xml import Doc

def once(source,old,new):
    if source.count(old)!=1:raise ValueError('Unexpected integration point '+old[:70])
    return source.replace(old,new)

def edit_dex(project,meta,manifest,preview):
    pkg='Lblackrussia/online/'
    cat=pkg+'WinterCatalog;'
    root=project/'smali_classes6/blackrussia/online'
    path=root/'WinterCatalog.smali';s=path.read_text()
    # Route each cumulative patch back to the stock archive member. The legacy
    # verified installer then reapplies every range and checks the final SHA-256.
    target='.method static original(Ljava/lang/String;)Lblackrussia/online/WeikCache$Entry;\n    .locals 19'
    route=[]
    for i,(name,row) in enumerate(meta['delta'].items()):
        route.extend([f'    const-string v0, "{row["hash"]}"','    move-object/from16 v1, p0',
                      '    invoke-virtual {v0, v1}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z',
                      '    move-result v0',f'    if-eqz v0, :winter_base_{i}',
                      f'    new-instance v0, {pkg}WeikCache$Entry;',f'    const-string v1, "{row["source"][0]}"',
                      f'    const-wide v2, {row["source"][1]}',f'    const-wide v4, {row["source"][2]}',
                      f'    const-wide v6, {row["source"][3]}',f'    const/16 v8, {row["source"][4]}',
                      f'    invoke-direct/range {{v0 .. v8}}, {pkg}WeikCache$Entry;-><init>(Ljava/lang/String;JJJI)V',
                      '    return-object v0',f'    :winter_base_{i}' ])
    s=once(s,target,target+'\n'+'\n'.join(route)+'\n    :winter_base_done')
    target='    :cond_0\n    invoke-virtual {p1}, Ljava/lang/String;->hashCode()I'
    samples=[]
    for i,(name,row) in enumerate({**meta['bundled'],**meta['delta']}.items()):
        size=row['size'] if 'size' in row else row['source'][1]
        samples.extend([f'    const-string v0, "{name}"',
                        '    invoke-virtual {v0, p1}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z',
                        '    move-result v0',f'    if-eqz v0, :winter_sample_{i}',
                        '    invoke-virtual {p0}, Ljava/io/File;->length()J','    move-result-wide v1',
                        f'    const-wide v3, {size}','    cmp-long v0, v1, v3','    if-nez v0, :winter_bad_size',
                        f'    const-wide v1, {row.get("at",0)}',f'    const-string v3, "{row["sample"]}"',
                        f'    invoke-static {{p0, v1, v2, v3}}, {cat}->matches(Ljava/io/File;JLjava/lang/String;)Z',
                        '    move-result v0','    return v0',f'    :winter_sample_{i}'])
    s=once(s,target,'    :cond_0\n'+'\n'.join(samples)+'\n    goto :winter_stock\n    :winter_bad_size\n    const/4 v0, 0\n    return v0\n    :winter_stock\n'+target.split('\n')[1])
    # Also repair interrupted installs when the original, shorter readiness list passes.
    start=s.index('.method public static ready(');end=s.index('.end method',start)
    ready=s[start:end]
    anchor='    :cond_0\n'
    extra=[]
    for i,name in enumerate({**meta['bundled'],**meta['delta']}):
        if f'"{name}"' in ready:continue
        extra.extend(['    new-instance v1, Ljava/io/File;',f'    const-string v2, "{name}"',
                      '    invoke-direct {v1, p0, v2}, Ljava/io/File;-><init>(Ljava/lang/String;Ljava/lang/String;)V',
                      f'    invoke-static {{v1, v2}}, {cat}->sample(Ljava/io/File;Ljava/lang/String;)Z',
                      '    move-result v1',f'    if-nez v1, :winter_ready_{i}','    return v0',f'    :winter_ready_{i}'])
    s=s[:start]+once(ready,anchor,anchor+'\n'.join(extra)+'\n')+s[end:]
    path.write_text(s)
    path=root/'CacheUpdates.smali';s=path.read_text()
    target='    iget-object p2, v1, Lblackrussia/online/CacheUpdates;->members:Ljava/util/Map;\n\n    invoke-interface {p1, p2}, Ljava/util/Map;->putAll(Ljava/util/Map;)V'
    # This APK embeds all of channel 20. An authentic newer channel can supersede it.
    s=once(s,target,'''    iget v2, v1, Lblackrussia/online/CacheUpdates;->generation:I
    const/16 v3, 20
    if-gt v2, v3, :winter_new_channel
    invoke-static {}, Ljava/util/Collections;->emptyMap()Ljava/util/Map;
    move-result-object p1
    sput-object p1, Lblackrussia/online/CacheUpdates;->active:Ljava/util/Map;
    return-object p0
    :winter_new_channel
'''+target)
    path.write_text(s)
    conf=project/'smali_classes3/com/wn/blackrussia/BuildConfig.smali'
    s=once(once(conf.read_text(),'VERSION_CODE:I = 0x2e','VERSION_CODE:I = 0x2f'),'VERSION_NAME:Ljava/lang/String; = "1.7.22"','VERSION_NAME:Ljava/lang/String; = "1.7.23"')
    if preview:s=s.replace('com.russiarp.hudx','com.russiarp.snow')
    conf.write_text(s)
    if preview:
        p=project/'smali/com/joom/paranoid/Deobfuscator$wn$Debug.smali'
        s=p.read_text()
        target='    move-result-object p0\n\n    return-object p0'
        # Scope path changes to local game directories, retaining archive member names and URLs.
        s=once(s,target,'''    move-result-object p0
    const-string v0, "/Weik"
    invoke-virtual {p0, v0}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result p1
    if-eqz p1, :winter_path_prefix
    const-string p0, "/RWin"
    return-object p0
    :winter_path_prefix
    const-string v0, "/Weik/"
    invoke-virtual {p0, v0}, Ljava/lang/String;->startsWith(Ljava/lang/String;)Z
    move-result p1
    if-eqz p1, :winter_path_done
    const-string p1, "/RWin/"
    invoke-virtual {p0, v0, p1}, Ljava/lang/String;->replace(Ljava/lang/CharSequence;Ljava/lang/CharSequence;)Ljava/lang/String;
    move-result-object p0
    :winter_path_done
    return-object p0''')
        p.write_text(s)

def package(base,assets,apktool,out,preview):
    if hashlib.sha256(base.read_bytes()).hexdigest()!='a6bbb1a9aafdd0358e57c8938179fc0ec346ab5d5b9eb656a41ca2fc62c226a1':raise ValueError('Requires 1.7.22')
    meta=json.loads((assets/'integration.json').read_bytes())
    with tempfile.TemporaryDirectory(dir=out.parent) as tmp,ZipFile(base) as z:
        tmp=Path(tmp).resolve();mini=tmp/'input.apk';project=tmp/'decoded';built=tmp/'rebuilt.apk'
        dexfiles=['classes3.dex','classes6.dex']+(['classes.dex'] if preview else [])
        with ZipFile(mini,'w') as seed:
            for n in ['AndroidManifest.xml','resources.arsc',*dexfiles]:seed.writestr(n,z.read(n))
        def run(*args):
            subprocess.run(['java','-Xmx2g','-Djava.io.tmpdir='+str(tmp),'-jar',str(apktool.resolve()),*map(str,args)],check=True)
        run('d','-r','-j','2',mini,'-o',project)
        edit_dex(project,meta,json.loads(z.read('assets/json/weik-cache.json'))['files'],preview)
        run('b','-j','2',project,'-o',built)
        doc=Doc(z.read('AndroidManifest.xml'));root=doc.elements()[0]
        assert root.get('versionCode')==46
        root.set('versionCode',16,47);root.set('versionName',3,doc.pool.add('1.7.23'))
        if preview:
            doc.pool.values=[s.replace('com.russiarp.hudx','com.russiarp.snow') for s in doc.pool.values]
            app=next(e for e in doc.elements() if e.tag=='application');app.set('label',3,doc.pool.add('RUSSIA RP · Зима'))
        files={p.relative_to(assets).as_posix():p for p in (assets/'assets').rglob('*') if p.is_file()}
        with ZipFile(built) as compiled,ZipFile(out,'w',allowZip64=False) as result:
            edits={'AndroidManifest.xml':doc.encode(),**{n:compiled.read(n) for n in dexfiles}}
            # Constants belong to DoHeadLightBeam only. Increase the minimum angular
            # visibility of each existing beam. The vehicle keeps its dummy, switch and tint.
            for abi,edits_at in {
                'arm64-v8a':[(0x1b24e4,'01902e1e','01502f1e'),(0x1b24e8,'0856a852','0846a852'),
                             (0x1b2670,'f5e30039','ffe30039'),(0x1b269c,'f5e70039','ffe70039')],
                'armeabi-v7a':[(0x123bd0,'b7ee044a','b7ee0a4a'),(0x123df4,'0000b042','00003042'),
                               (0x123cf8,'8df84420','8df84460'),(0x123cfc,'8df84320','8df84360')]
            }.items():
                n=f'lib/{abi}/libmultiplayer.so';raw=bytearray(z.read(n))
                for at,old,new in edits_at:
                    before=bytes.fromhex(old)
                    if raw[at:at+len(before)]!=before:raise ValueError('Unknown headlamp renderer '+abi)
                    raw[at:at+len(before)]=bytes.fromhex(new)
                if preview:
                    old=b'/storage/emulated/0/Weik/\0'
                    if raw.count(old)!=1:raise ValueError('Unknown native game path')
                    raw=raw.replace(old,b'/storage/emulated/0/RWin/\0')
                edits[n]=raw
            def put(name,raw,method):
                info=ZipInfo(name,(2026,1,1,0,0,0));info.compress_type=method
                if method==ZIP_STORED:
                    align=16384 if name.endswith('.so') else 4
                    pad=(-(result.fp.tell()+30+len(name.encode())+4))%align
                    info.extra=struct.pack('<HH',0xbeef,pad)+bytes(pad)
                result.writestr(info,raw)
            for ent in z.infolist():
                n=ent.filename
                if re.fullmatch(r'META-INF/(MANIFEST\.MF|[^/]+\.(SF|RSA|EC|DSA))',n,re.I):continue
                if n.startswith('assets/weik-defaults/') and n.endswith('.patch'):
                    if n.removeprefix('assets/weik-defaults/').removesuffix('.patch') in meta['bundled']:
                        continue
                if n in files:raw=files.pop(n).read_bytes()
                elif n in edits:raw=edits.pop(n)
                else:raw=z.read(n)
                put(n,raw,ent.compress_type)
            for n,p in sorted(files.items()):put(n,p.read_bytes(),ZIP_DEFLATED)
            assert not edits
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('base','assets','apktool','out'):parser.add_argument(name,type=Path)
    parser.add_argument('--preview',action='store_true')
    package(**vars(parser.parse_args()))
