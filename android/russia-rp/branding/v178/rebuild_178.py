"""Build a zip-aligned HUD update from the published 1.7.7 preview APK."""
import argparse
from dataclasses import dataclass
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

BASE_SHA256 = "6ec2e254c7ca3e6eac703708095620f7ad4760e9865a31b2c8f33c0153325d7e"
OLD_VERSION = "1.7.7"
PREVIEW_ID = "com.russiarp.test"


@dataclass(frozen=True)
class HudRelease:
    version: str
    version_code: int
    package: str
    label: str
    width_sdp: int
    height_sdp: int


HUD_178 = HudRelease("1.7.8", 32, "com.russiarp.hudx", "RUSSIA RP HUD", 70, 10)
HUD_179 = HudRelease("1.7.9", 33, "com.russiarp.hud2", "RUSSIA RP 1.7.9", 88, 31)


def wordmark(source, emblem_source, release=HUD_178):
    old = Image.open(BytesIO(source)).convert("RGBA")
    columns = old.getchannel("A").getprojection()[0]
    gap_start = columns.index(0)
    letters_start = columns.index(1, gap_start)
    letters = old.crop((letters_start, 0, old.width, old.height))
    letters = letters.crop(letters.getbbox())

    emblem = Image.open(BytesIO(emblem_source)).convert("RGBA")
    emblem = emblem.crop(emblem.getbbox())
    height = letters.height
    if release == HUD_179:
        # Anchor both sizes to the visible parts of the 1.7.7 artwork independently.
        old_emblem = old.crop((0, 0, gap_start, old.height))
        _, top, _, bottom = old_emblem.getchannel("A").getbbox()
        height = round((bottom - top) * 1.65)
        letters = letters.resize((round(letters.width * 0.92), round(letters.height * 0.92)),
                                 Image.Resampling.LANCZOS)
    emblem = ImageOps.contain(emblem, (height, height), Image.Resampling.LANCZOS)
    gap = letters_start - gap_start
    combined = Image.new("RGBA", (emblem.width + gap + letters.width, height))
    combined.alpha_composite(emblem)
    combined.alpha_composite(letters, (emblem.width + gap, (height - letters.height) // 2))
    encoded = BytesIO()
    combined.save(encoded, format="WEBP", lossless=True)
    return encoded.getvalue()


def build(base, sdk, apktool, output, standalone, release=HUD_178):
    if sha256(base.read_bytes()).hexdigest() != BASE_SHA256:
        raise ValueError("Expected the signed, published 1.7.7 preview")
    dump = subprocess.check_output([sdk / "aapt", "dump", "--values", "resources", base], text=True)
    ids = {k: int(n, 16) for n, k in re.findall(r"spec resource (0x[\da-f]+) com\.russiarp\.test:([^:]+):", dump)}
    entries = re.findall(r'resource 0x[\da-f]+ com\.russiarp\.test:([^:]+): t=[^\n]+\n +\(string8\) "(res/[^"]+)"', dump)
    paths = dict(entries)

    with TemporaryDirectory(dir=output.resolve().parent) as tmp:
        root = Path(tmp)
        decoded = root / "decoded"
        cmd = ["java", "-Xmx768m", "-jar", apktool]
        subprocess.run([*cmd, "d", "-j", "2", "-r", base, "-o", decoded], check=True)
        cfg = decoded / "smali_classes3/com/wn/blackrussia/BuildConfig.smali"
        source = replace_once(cfg.read_text(), "VERSION_CODE:I = 0x1f", f"VERSION_CODE:I = {release.version_code:#x}")
        source = replace_once(source, f'"{OLD_VERSION}"', f'"{release.version}"')
        if standalone:
            source = replace_once(source, PREVIEW_ID, release.package)
        cfg.write_text(source)
        subprocess.run([*cmd, "b", "-j", "2", "--no-apk", decoded], check=True)

        raw = root / "unsigned.apk"
        with ZipFile(base) as z, ZipFile(raw, "w") as dest:
            art = wordmark(z.read(paths["drawable/logobrgreen"]), z.read(paths["drawable/br_peaw_servers"]), release)
            replacements = {p: art for k, p in entries if k.startswith("drawable/logobr") and k != "drawable/logobrx2"}
            for k, p in entries:
                if k != "layout/br_hud":
                    continue
                layout = Doc(z.read(p))
                mark = next(e for e in layout.elements() if e.get("id") == ids["id/brHudLogo"])
                mark.set("layout_width", 1, ids[f"dimen/_{release.width_sdp}sdp"])
                mark.set("layout_height", 1, ids[f"dimen/_{release.height_sdp}sdp"])
                replacements[p] = layout.encode()
            manifest = Doc(z.read("AndroidManifest.xml"))
            if standalone:
                manifest.pool.values = [v.replace(PREVIEW_ID, release.package) for v in manifest.pool.values]
                app = next(e for e in manifest.elements() if e.tag == "application")
                app.set("label", 3, manifest.pool.add(release.label))
                table = z.read("resources.arsc")
                replacements["resources.arsc"] = replace_once(table, PREVIEW_ID.encode("utf-16le"), release.package.encode("utf-16le"))
            m = manifest.elements()[0]
            m.set("versionCode", 16, release.version_code)
            m.set("versionName", 3, manifest.pool.add(release.version))
            replacements["AndroidManifest.xml"] = manifest.encode()
            replacements["classes3.dex"] = (decoded / "build/apk/classes3.dex").read_bytes()
            for abi in ("arm64-v8a", "armeabi-v7a"):
                lib = f"lib/{abi}/libmultiplayer.so"
                old = b"RUSSIA RP " + OLD_VERSION.encode() + b"%.0s"
                new = b"RUSSIA RP " + release.version.encode() + b"%.0s"
                replacements[lib] = replace_once(z.read(lib), old, new)
            for info in z.infolist():
                if re.fullmatch(r"META-INF/[^/]+\.(RSA|DSA|EC|SF|MF)", info.filename, re.I):
                    continue
                data = replacements.get(info.filename)
                if data is None:
                    data = z.read(info)
                if standalone and info.filename.startswith("res/") and info.filename.endswith(".xml"):
                    data = data.replace(PREVIEW_ID.encode(), release.package.encode())
                    data = data.replace(PREVIEW_ID.encode("utf-16le"), release.package.encode("utf-16le"))
                dest.writestr(info, data)
        subprocess.run([sdk / "zipalign", "-f", "-P", "16", "4", raw, output], check=True)
        subprocess.run([sdk / "zipalign", "-c", "-P", "16", "4", output], check=True)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("base", "build-tools", "apktool", "output"):
        cli.add_argument("--" + name, type=Path, required=True)
    cli.add_argument("--standalone", action="store_true", help="Install as RUSSIA RP HUD beside the previous client")
    cli.add_argument("--large-emblem", action="store_true", help="Build 1.7.9 with a larger cathedral and slightly smaller server name")
    args = cli.parse_args()
    build(args.base, args.build_tools, args.apktool, args.output, args.standalone,
          HUD_179 if args.large_emblem else HUD_178)
