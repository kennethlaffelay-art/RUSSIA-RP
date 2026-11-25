"""Rebuild the 1.7.5 APK from the official 1.7.4, logo and banner."""
from pathlib import Path
from tempfile import TemporaryDirectory
import argparse
import os
import subprocess

from edit_dex import update
from theme import build


def run(*args):
    subprocess.run(list(map(str,args)),check=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for option in ("base","logo","banner","android-jar","apktool","ecj","build-tools","output"):
        parser.add_argument("--"+option,type=Path,required=True)
    a=parser.parse_args()
    src=Path(__file__).resolve().parent
    with TemporaryDirectory(dir=a.output.resolve().parent) as tmp:
        root=Path(tmp)
        decoded=root/"decoded"
        dex=root/"dex"
        classes=root/"classes"
        dex.mkdir()
        classes.mkdir()
        run("java","-jar",a.apktool,"d","-r","-f",a.base,"-o",decoded)
        update(decoded)
        run("java","-jar",a.apktool,"b","--no-apk",decoded)
        (dex/"ui.dex").write_bytes((decoded/"build/apk/classes3.dex").read_bytes())
        run("java","-jar",a.ecj,"-source","1.8","-target","1.8","-proc:none","-nowarn","-bootclasspath",a.android_jar,"-d",classes,src/"SafeMark.java")
        run(a.build_tools/"d8","--min-api","23","--lib",a.android_jar,"--output",dex,*sorted(classes.rglob("*.class")))
        run(a.build_tools/"aapt2","compile","--dir",src/"res","-o",root/"res.zip")
        run(a.build_tools/"aapt2","link","--no-auto-version","--min-sdk-version","23","--allow-reserved-package-id","--package-id","0x79","-I",a.android_jar,"-I",a.base,"--manifest",src/"AndroidManifest.xml",root/"res.zip","-o",root/"layouts.apk")
        dump=root/"resources.txt"
        dump.write_bytes(subprocess.check_output([a.build_tools/"aapt","dump","--values","resources",a.base]))
        build(a.base,root/"layouts.apk",dump,a.logo,a.banner,dex,root/"unsigned.apk")
        run(a.build_tools/"zipalign","-f","-P","16","4",root/"unsigned.apk",root/"aligned.apk")
        run(a.build_tools/"apksigner","sign","--ks",os.environ["RUSSIA_RP_KEYSTORE"],"--ks-key-alias","russia-rp","--ks-pass","file:"+os.environ["RUSSIA_RP_KEYPASS_FILE"],"--out",a.output,root/"aligned.apk")
        run(a.build_tools/"apksigner","verify","--verbose",a.output)
        run(a.build_tools/"zipalign","-c","-P","16","4",a.output)


if __name__=="__main__":
    main()
