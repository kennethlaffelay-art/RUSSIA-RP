"""Rebuild the 1.7.1 launcher from the exact published 1.7.0 APK.

Usage: python rebuild_171.py INPUT.apk APKTOOL.jar ANDROID_BUILD_TOOLS OUTPUT.apk
Set RUSSIA_RP_KEYSTORE to the private PKCS12 file and RUSSIA_RP_KEYPASS_FILE
to its password file. The signing alias is russia-rp. Use Android Build Tools 35+
and Apktool 2.11.1. Signing files must stay outside the source repository.
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

OLD_ID = "com.mirage.repair"
NEW_ID = "com.russiarp.game"
INPUT_SHA256 = "a2eb7a4e524ebcfb24189a157c65e460ec94cff5f76459d61ec7478f6617a59e"

def replace_utf16(data, old, new, count):
    source, target = (value.encode("utf-16le") for value in (old, new))
    if len(source) != len(target) or data.count(source) != count:
        raise ValueError("Unexpected binary resource or manifest")
    return data.replace(source, target)

def manifest(raw):
    data = bytearray(replace_utf16(replace_utf16(raw, OLD_ID, NEW_ID, 4), "1.7.0", "1.7.1", 1))
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
                    if struct.unpack_from("<I", data, attr+16)[0] != 24:
                        raise ValueError("Unexpected version code")
                    struct.pack_into("<I", data, attr+16, 25)
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
        config = decoded/"smali_classes3/com/wn/blackrussia/BuildConfig.smali"
        smali = config.read_text()
        for old, new in [(OLD_ID, NEW_ID), ('"1.7.0"', '"1.7.1"'), ("VERSION_CODE:I = 0x15","VERSION_CODE:I = 0x19")]:
            if smali.count(old) != 1:
                raise ValueError("Unexpected BuildConfig")
            smali = smali.replace(old, new)
        config.write_text(smali)
        run("java", "-jar", apktool, "b", "--no-apk", decoded)
        with zipfile.ZipFile(src) as old, zipfile.ZipFile(work/"unsigned.apk", "w") as new:
            for info in old.infolist():
                name = info.filename
                if re.fullmatch(r"META-INF/[^/]+\.(?:RSA|DSA|EC|SF|MF)", name, re.I):
                    continue
                data = old.read(info)
                if name == "AndroidManifest.xml":
                    data = manifest(data)
                elif name == "resources.arsc":
                    data = replace_utf16(data, OLD_ID, NEW_ID, 1)
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
