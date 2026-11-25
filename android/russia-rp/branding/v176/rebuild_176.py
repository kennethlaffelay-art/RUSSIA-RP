"""Finish the visual patch from the signed 1.7.5 APK. Requires Pillow and Android build tools."""
import argparse
import hashlib
from io import BytesIO
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import numpy as np
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from android_xml import Doc

# Gameplay-state indicators use their own colors. These entries are interface artwork.
CONTROL_ART = """
bpclose checkbox_red close_round donate_transfer_family exit menu_exchange menu_lic menu_med
menu_paper menu_passport people peoples_aples radial_bg_control_suspension_and_submenu
radial_bg_door_light_and_submenu radial_bg_turbo_engine_and_submenu radial_close
tuning_button_back_details_info tuning_button_close_submenu_apply tuning_button_info
summer_banner_close tuning_bg_box_card_invisible tuning_bg_box_view tuning_ellipse_53 tuning_view_car_res
""".split()


def finish_icon(data):
    pixels=np.array(Image.open(BytesIO(data)).convert("RGBA"))
    rgb=pixels[:,:,:3].astype(float)
    red,green,blue=rgb.transpose(2,0,1)
    distance=red-blue
    # Isolate saturated reds by their hue. Neutral detail, shadows and source alpha stay intact.
    mask=(distance>18)&(green-blue<.20*distance)&(red>green+15)
    peak=(red/255)**.88
    rgb[mask]=np.stack((213*peak,127*peak,81*peak),axis=-1)[mask]
    pixels[:,:,:3]=np.rint(rgb).astype(np.uint8)
    buf=BytesIO()
    Image.fromarray(pixels).save(buf,"WEBP",lossless=True)
    return buf.getvalue()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for flag in ("base","apktool","build-tools","output"):
        parser.add_argument("--"+flag,type=Path,required=True)
    a=parser.parse_args()
    if hashlib.sha256(a.base.read_bytes()).hexdigest()!="97caf7cd3f892fa6239b306749e87838574fed40e438a6b218ee0895f594a7dc":
        parser.error("Expected the signed 1.7.5 APK")
    def run(*cmd):
        subprocess.run(list(map(str,cmd)),check=True)
    with TemporaryDirectory(dir=a.output.resolve().parent) as tmp:
        root=Path(tmp)
        dump=subprocess.check_output([a.build_tools/"aapt","dump","--values","resources",a.base]).decode()
        paths=dict(re.findall(r'resource 0x[\da-f]+ com.russiarp.game:drawable/([^:]+): t=[^\n]+\n +\(string8\) "(res/[^"]+)"',dump))
        run("java","-jar",a.apktool,"d","-r","-f",a.base,"-o",root/"decoded")
        build=root/"decoded/smali_classes3/com/wn/blackrussia/BuildConfig.smali"
        cfg=build.read_text()
        assert 'VERSION_CODE:I = 0x1d' in cfg and '"1.7.5"' in cfg
        build.write_text(cfg.replace("VERSION_CODE:I = 0x1d","VERSION_CODE:I = 0x1e").replace('"1.7.5"','"1.7.6"'))
        run("java","-jar",a.apktool,"b","--no-apk",root/"decoded")
        with ZipFile(a.base) as src, ZipFile(root/"unsigned.apk","w") as dest:
            edits={paths[k]:finish_icon(src.read(paths[k])) for k in CONTROL_ART}
            doc=Doc(src.read("AndroidManifest.xml"))
            m=doc.elements()[0]
            m.set("versionCode",16,30)
            m.set("versionName",3,doc.pool.add("1.7.6"))
            edits["AndroidManifest.xml"]=doc.encode()
            edits["classes3.dex"]=(root/"decoded/build/apk/classes3.dex").read_bytes()
            for info in src.infolist():
                if re.fullmatch(r'META-INF/[^/]+\.(RSA|DSA|EC|SF|MF)',info.filename,re.I):continue
                dest.writestr(info,edits[info.filename] if info.filename in edits else src.read(info))
        run(a.build_tools/"zipalign","-f","-P","16","4",root/"unsigned.apk",root/"aligned.apk")
        run(a.build_tools/"apksigner","sign","--ks",os.environ["RUSSIA_RP_KEYSTORE"],"--ks-key-alias","russia-rp","--ks-pass","file:"+os.environ["RUSSIA_RP_KEYPASS_FILE"],"--out",a.output,root/"aligned.apk")
        run(a.build_tools/"apksigner","verify","--verbose",a.output)
        run(a.build_tools/"zipalign","-c","-P","16","4",a.output)


if __name__=="__main__":
    main()
