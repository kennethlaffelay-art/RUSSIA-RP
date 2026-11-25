"""Rebuild the signed RUSSIA RP 1.7.3 APK from the public 1.7.2 release.
Usage: python rebuild_173.py BASE_APK APKTOOL_JAR ANDROID_BUILD_TOOLS OUTPUT_APK
Use Apktool 2.11.1 and the release signing variables used by rebuild_171.py.
"""
import hashlib
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import zipfile

INPUT_SHA256 = "2ad0f0921a4243c2c4ccf5b8a240313b475a66ece1af3e8dc3d21ca9214d47b6"

def replace_utf16(data, old, new, count):
    source, target = (value.encode("utf-16le") for value in (old, new))
    if len(source) != len(target) or data.count(source) != count:
        raise ValueError("Unexpected binary resource or manifest")
    return data.replace(source, target)

def manifest(raw):
    data = bytearray(replace_utf16(raw, "1.7.2", "1.7.3", 1))
    pos, edits, resources = 8, 0, ()
    while pos < len(data):
        kind, header, size = struct.unpack_from("<HHI", data, pos)
        if not 8 <= header <= size <= len(data) - pos:
            raise ValueError("Invalid binary XML chunk")
        if kind == 0x180:
            resources = struct.unpack_from("<" + "I" * ((size-header)//4), data, pos+header)
        elif kind == 0x102:
            offset, stride, count = struct.unpack_from("<HHH", data, pos+24)
            for index in range(count):
                attr = pos+16+offset+index*stride
                name = struct.unpack_from("<I", data, attr+4)[0]
                if name < len(resources) and resources[name] == 0x0101021B:
                    if struct.unpack_from("<I", data, attr+16)[0] != 26:
                        raise ValueError("Unexpected version code")
                    struct.pack_into("<I", data, attr+16, 27)
                    edits += 1
        pos += size
    if edits != 1:
        raise ValueError("Missing or duplicate version code")
    return data

def main():
    src, apktool, tools, out = map(lambda p: Path(p).resolve(), sys.argv[1:])
    with src.open("rb") as file:
        if hashlib.file_digest(file, "sha256").hexdigest() != INPUT_SHA256:
            raise ValueError("Unexpected input APK")
    key, password = (os.environ[k] for k in ("RUSSIA_RP_KEYSTORE", "RUSSIA_RP_KEYPASS_FILE"))
    run = lambda *args, **kwargs: subprocess.run(args, check=True, **kwargs)
    with tempfile.TemporaryDirectory() as temp:
        work = Path(temp)
        decoded = work/"decoded"
        run("java", "-jar", apktool, "d", "-r", "-f", src, "-o", decoded)
        activity = decoded/"smali_classes3/com/wn/blackrussia/game/Multiplayer.smali"
        target = "    invoke-super {p0, p1}, Lcom/wn/blackrussia/game/Game;->onCreate(Landroid/os/Bundle;)V"
        source = activity.read_text()
        if source.count(target) != 1:
            raise ValueError("Unexpected game activity initialization")
        prepare_fonts = (
            "    sget-object v0, Lblackrussia/online/Settings;->GAME_PATH:Ljava/lang/String;\n\n"
            "    invoke-static {p0, v0}, Lcom/russiarp/launcher/PlateAssets;->install(Landroid/content/Context;Ljava/lang/String;)V\n\n"
        )
        activity.write_text(source.replace(target, prepare_fonts + target))
        run("java", "-jar", apktool, "b", "--no-apk", decoded)
        with zipfile.ZipFile(src) as old, zipfile.ZipFile(work/"unsigned.apk", "w") as new:
            for info in old.infolist():
                name = info.filename
                if re.fullmatch(r"META-INF/[^/]+\.(?:RSA|DSA|EC|SF|MF)", name, re.I):
                    continue
                data = old.read(info)
                if name == "AndroidManifest.xml":
                    data = manifest(data)
                elif name == "lib/arm64-v8a/libmultiplayer.so":
                    # CTimer::Update computes the same uint32_t twice, once in a scalar
                    # SIMD lane and once in a general register. Use the general
                    # conversion and copy its bits to the lane for Android NDK translation.
                    old_code = bytes.fromhex("44b8a17e5100391e")
                    new_code = bytes.fromhex("5100391e2402271e")
                    if data.count(old_code) != 1 or data[0x1ce22c:0x1ce234] != old_code:
                        raise ValueError("Unexpected timer implementation")
                    data = data.replace(old_code, new_code)
                elif name == "classes3.dex":
                    data = (decoded/"build/apk"/name).read_bytes()
                if re.fullmatch(r"classes\d*\.dex", name):
                    dex = work/name
                    dex.write_bytes(data)
                    run(tools/"dexdump", "-f", dex, stdout=subprocess.DEVNULL)
                new.writestr(info, data)
        run(tools/"zipalign", "-f", "-P", "16", "4", work/"unsigned.apk", work/"aligned.apk")
        run(tools/"apksigner", "sign", "--ks", key, "--ks-key-alias", "russia-rp", "--ks-pass", "file:"+password, "--out", out, work/"aligned.apk")
        run(tools/"apksigner", "verify", "--verbose", out)
        run(tools/"zipalign", "-c", "-P", "16", "4", out)

if __name__ == "__main__":
    main()
