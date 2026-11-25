"""Rebuild the Android 1.7.7 interface from the published 1.7.6 APK.

Output is zip-aligned and ready for signing. --preview changes the Android
application ID and provider authorities for installation alongside production.
"""
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
from android_xml import Doc, U

BASE_HASH = "369439b41206f51e205e7a7f728e59e22032fb1d3bdee613b2e3437c02ab5100"
APP_ID = "com.russiarp.game"
PREVIEW_ID = "com.russiarp.test"
VERSION = "1.7.7"
# Retain opacity, value types, resource references and gameplay status meanings.
PALETTE = {
    0x212121: 0x251F1C, 0x1A1A1A: 0x211C19, 0x20212A: 0x2C2420,
    0x38383D: 0x413733, 0x4D5877: 0x483931, 0x273047: 0x2C231F,
    0x6D7999: 0x675045, 0x959EB8: 0x80685B, 0x9DA7C1: 0x8D7465,
    0xFFBA08: 0xE4A780, 0x5DDD27: 0x87B77B, 0x7EFF47: 0xA4CC99,
    0x40B110: 0x5D955D, 0x0B131E: 0x211B18, 0x0D1522: 0x322720,
    0xFF6317: 0xD68B60, 0xC50000: 0xA45330, 0xFF5C00: 0xA45431,
    0xFF9900: 0xD68B60, 0xFF3434: 0xC16355, 0x861010: 0x743B34,
    0x36E40D: 0x7EAC75, 0x288014: 0x456A45, 0xF24C12: 0xAC6344,
    0xE2310C: 0xBC5D33,
}
SHARED_CHROME = {
    "drawable/oval_red", "drawable/background_window_red", "drawable/yellow_gradient",
    "drawable/button_yellow_gradient", "drawable/br_dialog_scroll_yellow_thumb",
    "drawable/br_dialog_scroll_yellow_thumb_rot", "layout/br_bp",
    "layout/black_pass_banner", "layout/br_notification",
}
NATIVE_TEXT = {
    "{FFFFFF}Клиент {FF0000}BLACK RUSSIA{FFFFFF} {FFFFFF}запущен":
        "{FFFFFF}Клиент {D68B60}RUSSIA RP{FFFFFF} запущен",
    "Соединение к BLACK RUSSIA...": "Подключение к RUSSIA RP...",
    # Consume the original date and time arguments. Keep the platform, FPS and stream usage.
    "WN Native Build %s %.5s (%s) FPS: %.0f Streaming: %d/%d MB":
        "RUSSIA RP 1.7.7%.0s%.0s (%s) FPS: %.0f Stream: %d/%d MB",
}


def replace_once(data, old, new):
    if data.count(old) != 1:
        raise ValueError(f"Expected one occurrence of {old!r}")
    return data.replace(old, new, 1)


def native_text(data):
    for original, replacement in NATIVE_TEXT.items():
        old = original.encode("cp1251")
        new = replacement.encode("cp1251")
        if len(new) > len(old):
            raise ValueError("Localized label does not fit")
        data = replace_once(data, b"\0" + old + b"\0", b"\0" + new.ljust(len(old), b"\0") + b"\0")
    return data


def pass_text(value):
    value = value.replace("BLACK PASS", "RUSSIA PASS").replace("Black Pass", "Russia Pass")
    return value.replace("black pass", "Russia Pass").replace("Купить BLACK COINS", "Купить BC")


def theme_xml(data):
    doc = Doc(data)
    changed = False
    for el in doc.elements():
        for attr in el.attrs:
            typ, val = attr[15], U(attr, 16)
            name = el.name(attr)
            if 28 <= typ <= 31 and (val & 0xFFFFFF) in PALETTE:
                el.set(name, 28, (val & 0xFF000000) | PALETTE[val & 0xFFFFFF])
                changed = True
            if typ == 3 and name in ("text", "contentDescription"):
                old = doc.pool.values[val]
                new = pass_text(old)
                if new != old:
                    el.set(name, 3, doc.pool.add(new))
                    changed = True
    return doc.encode() if changed else data


def hud_wordmark(z, paths):
    # Retain the original letterforms from 1.7.6. The fully transparent
    # gutter between the emblem and first letter marks the optical split.
    old = Image.open(BytesIO(z.read(paths["drawable/logobrgreen"]))).convert("RGBA")
    columns = old.getchannel("A").getprojection()[0]
    gap = next(x for x, occupied in enumerate(columns) if not occupied)
    text = old.crop((gap, 0, old.width, old.height))
    text = text.crop(text.getbbox())
    emblem = Image.open(BytesIO(z.read(paths["drawable/br_peaw_servers"]))).convert("RGBA")
    emblem = emblem.crop(emblem.getbbox())
    height = round(text.height * 1.7)
    emblem = ImageOps.contain(emblem, (height, height), Image.Resampling.LANCZOS)
    gutter = round(text.height * .16)
    row = Image.new("RGBA", (emblem.width + gutter + text.width, height))
    row.alpha_composite(emblem, (0, 0))
    row.alpha_composite(text, (emblem.width + gutter, (height - text.height) // 2))
    buf = BytesIO()
    row.save(buf, "WEBP", lossless=True)
    return buf.getvalue()


def edit_smali(decoded, preview):
    base = decoded / "smali_classes3/com/wn/blackrussia"
    config = base / "BuildConfig.smali"
    contents = replace_once(config.read_text(), "VERSION_CODE:I = 0x1e", "VERSION_CODE:I = 0x1f")
    contents = replace_once(contents, '"1.7.6"', f'"{VERSION}"')
    if preview:
        contents = replace_once(contents, APP_ID, PREVIEW_ID)
    config.write_text(contents)
    for relative in ("blackpass/BrBlackPass.smali", "donate/BrDonate.smali"):
        path = base / "game/ui" / relative
        path.write_text(pass_text(path.read_text()).replace("#FFBA08", "#E4A780"))
    service = decoded / "smali/blackrussia/online/DownloadService.smali"
    builder = "Landroidx/core/app/NotificationCompat$Builder;"
    icon_line = f"    invoke-virtual {{v3, v5}}, {builder}->setSmallIcon(I){builder}"
    new_lines = (
        icon_line + "\n\n    move-result-object v3\n\n    const v5, -0x43a2cd\n\n"
        f"    invoke-virtual {{v3, v5}}, {builder}->setColor(I){builder}"
    )
    service.write_text(replace_once(service.read_text(), icon_line, new_lines))


def build(base, sdk, apktool, output, preview):
    if sha256(base.read_bytes()).hexdigest() != BASE_HASH:
        raise ValueError("Expected published 1.7.6 APK")
    dump = subprocess.check_output([sdk / "aapt", "dump", "--values", "resources", base], text=True)
    ids = {k: int(i, 16) for i, k in re.findall(r"spec resource (0x[\da-f]+) com\.russiarp\.game:([^:]+):", dump)}
    entries = re.findall(r'resource 0x[\da-f]+ com\.russiarp\.game:([^:]+): t=[^\n]+\n +\(string8\) "(res/[^"]+)"', dump)
    paths = dict(entries)
    with TemporaryDirectory(dir=output.resolve().parent) as temp:
        root = Path(temp)
        decoded = root / "decoded"
        tool = ["java", "-Xmx768m", "-jar", apktool]
        subprocess.run([*tool, "d", "-j", "2", "-r", base, "-o", decoded], check=True)
        edit_smali(decoded, preview)
        subprocess.run([*tool, "b", "-j", "2", "--no-apk", decoded], check=True)
        unsigned = root / "unsigned.apk"
        with ZipFile(base) as z, ZipFile(unsigned, "w") as dest:
            edits = {}
            manifest = Doc(z.read("AndroidManifest.xml"))
            if preview:
                manifest.pool.values = [v.replace(APP_ID, PREVIEW_ID) for v in manifest.pool.values]
                app = next(el for el in manifest.elements() if el.tag == "application")
                app.set("label", 3, manifest.pool.add("RUSSIA RP Тест"))
                table = z.read("resources.arsc")
                edits["resources.arsc"] = replace_once(table, APP_ID.encode("utf-16le"), PREVIEW_ID.encode("utf-16le"))
            m = manifest.elements()[0]
            m.set("versionCode", 16, 31)
            m.set("versionName", 3, manifest.pool.add(VERSION))
            edits["AndroidManifest.xml"] = manifest.encode()
            wordmark = hud_wordmark(z, paths)
            for name, path in entries:
                if name.startswith("drawable/logobr") and name != "drawable/logobrx2":
                    edits[path] = wordmark
                elif name == "layout/br_hud":
                    hud = Doc(z.read(path))
                    mark = next(e for e in hud.elements() if e.get("id") == ids["id/brHudLogo"])
                    mark.set("layout_width", 1, ids["dimen/_84sdp"])
                    mark.set("layout_height", 1, ids["dimen/_20sdp"])
                    edits[path] = hud.encode()
                elif path.endswith(".xml") and (name in SHARED_CHROME or name.startswith((
                    "layout/bp_", "drawable/bp_", "drawable/donate_tile_", "drawable/background_br_notification_",
                ))):
                    original = z.read(path)
                    themed = theme_xml(original)
                    if original != themed:
                        edits[path] = themed
            for arch in ("arm64-v8a", "armeabi-v7a"):
                name = f"lib/{arch}/libmultiplayer.so"
                edits[name] = native_text(z.read(name))
            for name in ("classes.dex", "classes3.dex"):
                edits[name] = (decoded / "build/apk" / name).read_bytes()
            for info in z.infolist():
                if re.fullmatch(r"META-INF/[^/]+\.(?:RSA|DSA|EC|SF|MF)", info.filename, re.I):
                    continue
                data = edits.get(info.filename)
                if data is None:
                    data = z.read(info)
                if preview and info.filename.startswith("res/") and info.filename.endswith(".xml"):
                    data = data.replace(APP_ID.encode(), PREVIEW_ID.encode())
                dest.writestr(info, data)
        subprocess.run([sdk / "zipalign", "-f", "-P", "16", "4", unsigned, output], check=True)
        subprocess.run([sdk / "zipalign", "-c", "-P", "16", "4", output], check=True)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for arg in ("base", "build-tools", "apktool", "output"):
        cli.add_argument("--" + arg, required=True, type=Path)
    cli.add_argument("--preview", action="store_true")
    args = cli.parse_args()
    build(args.base, args.build_tools, args.apktool, args.output, args.preview)
