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

def edit_dex(project,meta,manifest,preview,preview_id):
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
    s=once(once(conf.read_text(),'VERSION_CODE:I = 0x2e','VERSION_CODE:I = 0x32'),'VERSION_NAME:Ljava/lang/String; = "1.7.22"','VERSION_NAME:Ljava/lang/String; = "1.7.26"')
    if preview:s=s.replace('com.russiarp.hudx',preview_id)
    conf.write_text(s)
    if preview:
        smali=project/'smali/blackrussia/online'
        path=smali/'Settings.smali';s=path.read_text()
        anchor='    sput-object v0, Lblackrussia/online/Settings;->GAME_PATH:Ljava/lang/String;'
        path.write_text(once(s,anchor,anchor+"""
    new-instance v1, Ljava/io/File;
    invoke-direct {v1, v0}, Ljava/io/File;-><init>(Ljava/lang/String;)V
    invoke-static {v1}, Lblackrussia/online/SharedCache;->adopt(Ljava/io/File;)V"""))
        path=smali/'WeikCache.smali';s=path.read_text()
        anchor='    iput-object p1, p0, Lblackrussia/online/WeikCache;->root:Ljava/io/File;'
        s=once(s,anchor,anchor+'\n    invoke-static {p1}, Lblackrussia/online/SharedCache;->adopt(Ljava/io/File;)V')
        anchor='    invoke-static {v0, v2}, Lblackrussia/online/CacheUpdates;->worker('
        s=once(s,anchor,"""    iget-object v3, v0, Lblackrussia/online/WeikCache;->root:Ljava/io/File;
    invoke-direct {v0, v1}, Lblackrussia/online/WeikCache;->destination(Ljava/lang/String;)Ljava/io/File;
    move-result-object v4
    move-object v5, v1
    iget-wide v6, v2, Lblackrussia/online/WeikCache$Entry;->size:J
    iget-object v8, v2, Lblackrussia/online/WeikCache$Entry;->hash:Ljava/lang/String;
    invoke-static/range {v3 .. v8}, Lblackrussia/online/SharedCache;->reuse(Ljava/io/File;Ljava/io/File;Ljava/lang/String;JLjava/lang/String;)Z
    move-result v3
    if-eqz v3, :shared_cache_continue
    return-void
    :shared_cache_continue
"""+anchor)
        path.write_text(s)

def headlight_renderer(data, library, abi):
    # Both renderers use five vertices per headlamp. Keep the fully transparent
    # far edge, the model transform and the original vehicle colour. A 14-unit
    # reach with half-width 2.125 preserves the opening angle of the older beam.
    # Peak alpha is 248 - 64 * abs(view dot forward), so the front three-quarter
    # view still has a bright core. Source-over retains detail on white snow.
    tweaks = {
        ("libGame.so", "arm64-v8a"): [
            (0x6b48a4, "e1031f32", "c1008052"),
            (0x6b48e8, "0856a852", "0850a852"),
            (0x6b4970, "0b502e1e", "0b30201e"),
            (0x6b49a4, "29590011", "29e10211"),
            (0x6b49e8, "15d0231e", "1590251e"),
        ],
        ("libGame.so", "armeabi-v7a"): [
            (0x59088a, "0221", "0621"),
            (0x5908b8, "b7ee02ea", "b0ee01ea"),
            (0x59097c, "b7ee045a", "b0ee0f5a"),
            (0x5909a0, "b1ee0e6a", "b2ee0c6a"),
            (0x590b64, "0000b042", "00008042"),
        ],
        ("libmultiplayer.so", "arm64-v8a"): [
            (0x1b24e4, "01902e1e", "01f0211e"),
            (0x1b24e8, "0856a852", "0850a852"),
            (0x1b2630, "11d0231e", "1190251e"),
            (0x1b264c, "16502e1e", "1630201e"),
        ],
        ("libmultiplayer.so", "armeabi-v7a"): [
            (0x123bcc, "b7ee023a", "b0ee013a"),
            (0x123bd0, "b7ee044a", "b0ee0f4a"),
            (0x123bd4, "b1ee0e5a", "b2ee0c5a"),
            (0x123df4, "0000b042", "00008042"),
        ],
    }
    result = bytearray(data)
    for offset, original, adjusted in tweaks[library, abi]:
        before = bytes.fromhex(original)
        if result[offset:offset + len(before)] != before:
            raise ValueError(f'Unexpected headlamp code in {abi}/{library} at {offset:x}')
        result[offset:offset + len(before)] = bytes.fromhex(adjusted)
    return bytes(result)

def package(base,assets,apktool,out,preview,r8=None,standalone=False):
    preview = preview or standalone
    preview_id = 'com.russiarp.winter27.lights' if standalone else 'com.russiarp.snow'
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
        edit_dex(project,meta,json.loads(z.read('assets/json/weik-cache.json'))['files'],preview,preview_id)
        run('b','-j','2',project,'-o',built)
        doc=Doc(z.read('AndroidManifest.xml'));root=doc.elements()[0]
        assert root.get('versionCode')==46
        root.set('versionCode',16,50);root.set('versionName',3,doc.pool.add('1.7.26'))
        if preview:
            doc.pool.values=[s.replace('com.russiarp.hudx',preview_id) for s in doc.pool.values]
            app=next(e for e in doc.elements() if e.tag=='application')
            label = 'RUSSIA RP · Зима 2027 · Фары' if standalone else 'RUSSIA RP · Зима'
            app.set('label',3,doc.pool.add(label))
        files={p.relative_to(assets).as_posix():p for p in (assets/'assets').rglob('*') if p.is_file()}
        if preview:
            if r8 is None or hashlib.sha256(r8.read_bytes()).hexdigest()!='900dfbc649519969fc5a4c7520d6b7355338e565fa1249874e0190b8d61b1199':
                raise ValueError('Preview requires the pinned R8 8.3.37 jar')
            classes=tmp/'shared-cache';classes.mkdir()
            helper=Path(__file__).resolve().with_name('SharedCache.java')
            subprocess.run(['javac','--release','8','-d',str(classes),str(helper)],check=True)
            subprocess.run(['java','-cp',str(r8.resolve()),'com.android.tools.r8.D8','--min-api','26','--output',str(classes),str(classes/'blackrussia/online/SharedCache.class')],check=True)
            assert 'classes9.dex' not in z.namelist()
            files['classes9.dex']=classes/'classes.dex'
        with ZipFile(built) as compiled,ZipFile(out,'w',allowZip64=False) as result:
            edits={'AndroidManifest.xml':doc.encode(),**{n:compiled.read(n) for n in dexfiles}}
            for abi in ('arm64-v8a', 'armeabi-v7a'):
                for library in ('libGame.so', 'libmultiplayer.so'):
                    path = f'lib/{abi}/{library}'
                    renderer = headlight_renderer(z.read(path), library, abi)
                    if library == 'libmultiplayer.so':
                        renderer = once(renderer, b'RUSSIA RP 1.7.22%.0s', b'RUSSIA RP 1.7.26%.0s')
                    edits[path] = renderer
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
    parser.add_argument('--r8',type=Path)
    parser.add_argument('--preview',action='store_true')
    parser.add_argument('--standalone', action='store_true', help='Build the independently signed winter client alongside either earlier package.')
    package(**vars(parser.parse_args()))
