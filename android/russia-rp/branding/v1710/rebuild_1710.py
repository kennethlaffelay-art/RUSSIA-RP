"""Build the 1.7.10 lower-left HUD update from the released 1.7.8 HUD APK."""
import argparse
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from PIL import Image, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from android_xml import Doc
from v177.rebuild_177 import replace_once


BASE_HASH = "0e51dc291af843f3e015a5265482ca63b4aba68e0060b72822934f218c9a6768"
PACKAGE = "com.russiarp.hudx"
# The artwork and its ImageView share the same design units. The city letters
# previously occupied about 9.8 sdp. The cathedral now uses the full row height.
CITY_HEIGHT = 9
EMBLEM_HEIGHT = 21
ROW_WIDTH = 75


def make_wordmark(previous, cathedral):
    old = Image.open(BytesIO(previous)).convert("RGBA")
    columns = old.getchannel("A").getprojection()[0]
    gap_start = columns.index(0)
    city_start = columns.index(1, gap_start)
    city = old.crop((city_start, 0, old.width, old.height))
    city = city.crop(city.getbbox())

    emblem = Image.open(BytesIO(cathedral)).convert("RGBA")
    emblem = emblem.crop(emblem.getbbox())
    height = round(city.height * EMBLEM_HEIGHT / CITY_HEIGHT)
    emblem = ImageOps.contain(emblem, (height, height), Image.Resampling.LANCZOS)
    left = emblem.width + city_start - gap_start
    row = Image.new("RGBA", (left + city.width, height))
    row.alpha_composite(emblem, (0, 0))
    row.alpha_composite(city, (left, (height - city.height) // 2))
    output = BytesIO()
    row.save(output, format="WEBP", lossless=True)
    return output.getvalue()


def version_dex(base, root, apktool):
    decoded = root / "decoded"
    tool = ["java", "-Xmx768m", "-jar", apktool]
    subprocess.run([*tool, "d", "-j", "2", "-r", base, "-o", decoded], check=True)
    config = decoded / "smali_classes3/com/wn/blackrussia/BuildConfig.smali"
    data = replace_once(config.read_text(), "VERSION_CODE:I = 0x20", "VERSION_CODE:I = 0x22")
    config.write_text(replace_once(data, '"1.7.8"', '"1.7.10"'))
    subprocess.run([*tool, "b", "-j", "2", "--no-apk", decoded], check=True)
    return (decoded / "build/apk/classes3.dex").read_bytes()


def build(base, sdk, apktool, output):
    if sha256(base.read_bytes()).hexdigest() != BASE_HASH:
        raise ValueError("Expected the released 1.7.8 HUD APK")
    dump = subprocess.check_output([sdk / "aapt", "dump", "--values", "resources", base], text=True)
    prefix = re.escape(PACKAGE) + ":"
    ids = {name: int(rid, 16) for rid, name in
           re.findall(r"spec resource (0x[\da-f]+) " + prefix + r"([^:]+):", dump)}
    entries = re.findall(r"resource 0x[\da-f]+ " + prefix +
                         r'([^:]+): t=[^\n]+\n +\(string8\) "(res/[^"]+)"', dump)
    paths = dict(entries)
    with TemporaryDirectory(dir=output.resolve().parent) as tmp, ZipFile(base) as source:
        root = Path(tmp)
        row = make_wordmark(source.read(paths["drawable/logobrgreen"]),
                            source.read(paths["drawable/br_peaw_servers"]))
        edits = {}
        for name, path in entries:
            if name.startswith("drawable/logobr") and name != "drawable/logobrx2":
                edits[path] = row
            elif name == "layout/br_hud":
                hud = Doc(source.read(path))
                mark = next(e for e in hud.elements() if e.get("id") == ids["id/brHudLogo"])
                mark.set("layout_width", 1, ids[f"dimen/_{ROW_WIDTH}sdp"])
                mark.set("layout_height", 1, ids[f"dimen/_{EMBLEM_HEIGHT}sdp"])
                edits[path] = hud.encode()

        manifest = Doc(source.read("AndroidManifest.xml"))
        manifest.elements()[0].set("versionCode", 16, 34)
        manifest.elements()[0].set("versionName", 3, manifest.pool.add("1.7.10"))
        edits["AndroidManifest.xml"] = manifest.encode()
        edits["classes3.dex"] = version_dex(base, root, apktool)
        for abi in ("arm64-v8a", "armeabi-v7a"):
            path = f"lib/{abi}/libmultiplayer.so"
            suffix = b"%.0s%.0s (%s) FPS: %.0f Stream: %d/%d MB"
            old = b"RUSSIA RP 1.7.8" + suffix + bytes(2)
            new = b"RUSSIA RP 1.7.10" + suffix + bytes(1)
            edits[path] = replace_once(source.read(path), old, new)

        unsigned = root / "unsigned.apk"
        with ZipFile(unsigned, "w") as dest:
            for info in source.infolist():
                if re.fullmatch(r"META-INF/[^/]+\.(RSA|DSA|EC|SF|MF)", info.filename, re.I):
                    continue
                data = edits[info.filename] if info.filename in edits else source.read(info)
                dest.writestr(info, data)
        subprocess.run([sdk / "zipalign", "-f", "-P", "16", "4", unsigned, output], check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("base", "build-tools", "apktool", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    build(args.base, args.build_tools, args.apktool, args.output)
