"""Build the RUSSIA RP 1.7.4 visual update on top of the signed 1.7.3 client.

Pass the exact cathedral logo, banner without text, and banner with the slogan.
The signing key and its password file use the same environment variables as
rebuild_173.py. The build uses Android API 35, Apktool 2.11.1, and Eclipse ECJ.
"""

import argparse, hashlib, json, os, re, struct, subprocess, tempfile
from pathlib import Path
from zipfile import ZipFile, ZipInfo
from struct import pack, unpack
from android_xml import ANDROID, NIL, Doc, Element, H, U, chunks, p32
from artwork import artwork


def fp(f):
    return unpack("<I", pack("<f", f))[0]


def replace_tag(e, t):
    name = e.doc.pool.add(t)
    old = U(e.head, 20)
    nest = 0
    for i in range(e.doc.parts.index(e) + 1, len(e.doc.parts)):
        item = e.doc.parts[i]
        if isinstance(item, Element):
            nest += 1
        if isinstance(item, bytes) and H(item, 0) == 0x103:
            if not nest:
                assert U(item, 20) == old
                e.doc.parts[i] = item[:20] + p32(name) + item[24:]
                break
            nest -= 1
    struct.pack_into("<I", e.head, 20, name)


def rescolor(data, targets):
    data = bytearray(data)
    found = set()
    for pkg in chunks(data):
        if H(pkg, 0) != 0x200:
            continue
        off = H(pkg, 2)
        base = data.index(pkg)
        package = U(pkg, 8)
        while off < len(pkg):
            ty, h, size = struct.unpack_from("<HHI", pkg, off)
            if ty == 0x201:
                typ, flags = pkg[off + 8 : off + 10]
                n, voff = struct.unpack_from("<II", pkg, off + 12)
                for rid, col in targets.items():
                    if (rid >> 24, rid >> 16 & 255) != (package, typ):
                        continue
                    idx = rid & 65535
                    if flags & 1:
                        v = next(
                            (
                                a * 4
                                for i, a in struct.iter_unpack(
                                    "<HH", pkg[off + h : off + h + 4 * n]
                                )
                                if i == idx
                            ),
                            None,
                        )
                    elif idx >= n:
                        continue
                    elif flags & 2:
                        a = H(pkg, off + h + idx * 2)
                        v = None if a == 65535 else a * 4
                    else:
                        a = U(pkg, off + h + idx * 4)
                        v = None if a == NIL else a
                    if v is None:
                        continue
                    entry = off + voff + v
                    if (
                        H(pkg, entry + 2) & 8
                    ):  # Compact entry stores type in flags and the datum as key.
                        assert pkg[entry + 3] in (28, 29, 30, 31)
                        val = entry + 4
                    else:
                        val = entry + H(pkg, entry) + 4
                        assert pkg[val - 1] in (28, 29, 30, 31)
                    struct.pack_into("<I", data, base + val, col)
                    found.add(rid)
            off += size
    assert set(targets) == found
    return data


def assemble(z, resource_dump, art_files, hud_dex, version_dex, unsigned):
    names = {
        int(n, 16): k
        for n, k in re.findall(
            r"spec resource (0x[0-9a-f]+) com.russiarp.game:([^:]+):", resource_dump
        )
    }
    ids = {v: k for k, v in names.items()}
    entries = re.findall(
        r'resource (0x[0-9a-f]+) com.russiarp.game:([^:]+): t=[^\n]+\n +\(string8\) "(res/[^"]+)"',
        resource_dump,
    )
    paths = {k: p for i, k, p in entries}
    overrides = artwork(z, paths, entries, *art_files)

    def xml(key):
        p = paths.get(key, key)
        return p, Doc(z.read(p))

    def by_id(doc, k):
        return next(e for e in doc.elements() if e.get("id") == ids["id/" + k])

    p, d = xml("AndroidManifest.xml")
    for e in d.elements():
        if e.tag == "manifest":
            e.set("versionCode", 16, 28)
            e.set("versionName", 3, d.pool.add("1.7.4"))
        if e.tag == "application":
            e.set("label", 3, d.pool.add("РОССИЯ РП"))
    overrides[p] = d.encode()
    cols = {
        "gradient1": 0xFF984720,
        "gradient2": 0xFFBC5D33,
        "menuTextEnable": 0xFFDF966C,
    }
    overrides["resources.arsc"] = rescolor(
        z.read("resources.arsc"), {ids["color/" + k]: v for k, v in cols.items()}
    )
    for n in (
        "br_serverselect",
        "br_serverselect_server",
        "item_server",
        "wn_loadingscreen",
        "activity_splash",
        "registration_view",
        "br_hud",
    ):
        p, d = xml("layout/" + n)
        root = d.elements()[0]
        if n in ("br_serverselect", "wn_loadingscreen", "activity_splash"):
            bg = {
                "br_serverselect": "server_select_background",
                "wn_loadingscreen": "mylogo_vesnaold",
                "activity_splash": "server_select_background",
            }[n]
            root.drop("background")
            if n == "activity_splash":
                root.set("background", 28, 0xFF191715, 0x10100D4)
                image = d.image(root, ids["drawable/logo_splash"])
                image.set("layout_width", 5, 0x9001)
                image.set("layout_height", 5, 0xAC01)
                image.set("layout_gravity", 17, 17, 0x10100B3)
                image.set("scaleType", 16, 3)
            else:
                d.image(root, ids["drawable/" + bg])
            if n == "br_serverselect":
                for k in ("choose_server_root_loading", "choose_server_root_choose"):
                    by_id(d, k).drop("background")
        if n in ("br_serverselect", "br_serverselect_server"):
            by_id(d, "server_list_back_color").set("alpha", 4, fp(0.96))
            by_id(d, "br_server_x2").set("text", 3, d.pool.add("x4"))
        if n == "item_server":
            for e in d.elements():
                if e.get("background") == ids["drawable/server_rectangle"]:
                    value = 0.12 if e.get("id") == ids["id/backColor"] else 0.96
                    e.set("alpha", 4, fp(value))
        if n == "registration_view":
            person = by_id(d, "reg_person")
            person.set("scaleType", 16, 4, 0x101011D)
            person.drop("layout_constraintTop_toTopOf")
            person.drop("layout_constraintVertical_bias")
        if n == "br_hud":
            mark = by_id(d, "brHudLogo")
            replace_tag(mark, "com.russiarp.ui.SafeMark")
            mark.set("src", 1, ids["drawable/logobrgreen"], 0x1010119)
            mark.drop("srcCompat")
            mark.set("layout_width", 1, ids["dimen/_68sdp"])
            mark.set("layout_height", 1, ids["dimen/_19sdp"])
            mark.set("layout_marginStart", 5, 0x301, 0x10103B5)
            mark.set("layout_marginBottom", 5, 0x301, 0x10100FA)
            mark.set("scaleType", 16, 3, 0x101011D)
            badge = by_id(d, "brHudDoubleLogo")
            badge.drop("background")
            badge.drop("layout_constraintEnd_toEndOf")
            badge.drop("layout_marginTop")
            badge.set("src", 1, ids["drawable/logobrx2"], 0x1010119)
            badge.set("scaleType", 16, 3, 0x101011D)
            badge.set(
                "layout_constraintBottom_toBottomOf",
                1,
                ids["id/brHudLogo"],
                ids["attr/layout_constraintBottom_toBottomOf"],
            )
            # constraint attrs already mapped to the app namespace in this document
            attr = next(
                a
                for a in badge.attrs
                if badge.name(a) == "layout_constraintBottom_toBottomOf"
            )
            source = next(
                a
                for a in mark.attrs
                if mark.name(a) == "layout_constraintBottom_toBottomOf"
            )
            attr[:4] = source[:4]
            badge.set("layout_marginStart", 5, 0x201, 0x10103B5)
        overrides[p] = d.encode()
    color_map = {
        0xFFFF6317: 0xFFDA8C5B,
        0xFFCE0E03: 0xFF984720,
        0xFFF75514: 0xFFBC5D33,
        0xFFE2310C: 0xFFAE512B,
    }
    for k, p in paths.items():
        if not k.startswith("drawable/") or not p.endswith(".xml"):
            continue
        n = k.split("/")[1]
        if not (
            re.search(
                r"(button|_btn|reg_but|divider_br_red_s_corn|server_rectangle_gradient|donate_tile_button)",
                n,
            )
        ):
            continue
        d = Doc(z.read(p))
        changed = False
        for e in d.elements():
            for a in e.attrs:
                col = U(a, 16)
                key = e.name(a)
                if a[15] in (28, 29, 30, 31) and col in color_map:
                    e.set(key, 28, color_map[col])
                    changed = True
                if (
                    n == "server_rectangle_gradient"
                    and e.tag == "gradient"
                    and key in ("startColor", "centerColor", "endColor")
                ):
                    e.set(
                        key,
                        28,
                        {
                            "startColor": 0xF4211B18,
                            "centerColor": 0xEB2B211C,
                            "endColor": 0xEB382820,
                        }[key],
                    )
                    changed = True
        if changed:
            overrides[p] = d.encode()
    p = "assets/json/servers.json"
    import json

    servers = json.loads(z.read(p))
    servers[0]["color"] = "BC5D33"
    overrides[p] = json.dumps(servers, ensure_ascii=False, indent=2).encode()
    # Use a new multidex entry so all previously working native and Java behavior survives.
    overrides["classes5.dex"] = hud_dex.read_bytes()
    overrides["classes3.dex"] = version_dex.read_bytes()
    with ZipFile(unsigned, "w") as out:
        for ent in z.infolist():
            name = ent.filename
            if re.fullmatch(r"META-INF/[^/]+\.(RSA|DSA|EC|SF|MF)", name, re.I):
                continue
            out.writestr(
                ent, overrides.get(name) if name in overrides else z.read(name)
            )
        entry = ZipInfo("classes5.dex", (2026, 11, 25, 8, 5, 22))
        out.writestr(entry, overrides["classes5.dex"], compress_type=8)
    print("Updated", len(overrides), "entries")


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in (
        "base",
        "logo",
        "banner",
        "poster",
        "android-jar",
        "apktool",
        "ecj",
        "build-tools",
        "output",
    ):
        cli.add_argument("--" + name, required=True, type=Path)
    a = cli.parse_args()
    if (
        hashlib.sha256(a.base.read_bytes()).hexdigest()
        != "970658af58e84a537b38e20269a1fd1e22a0b97ef7c83e2358beba739d012321"
    ):
        cli.error("The baseline must be the signed 1.7.3 build from rebuild_173.py")

    def run(*cmd):
        subprocess.run(list(map(str, cmd)), check=True)

    with tempfile.TemporaryDirectory(dir=a.output.resolve().parent) as tmp:
        work = Path(tmp)
        decoded = work / "decoded"
        classes = work / "classes"
        dex = work / "dex"
        classes.mkdir()
        dex.mkdir()
        run("java", "-jar", a.apktool, "d", "-r", "-f", a.base, "-o", decoded)
        cfg = decoded / "smali_classes3/com/wn/blackrussia/BuildConfig.smali"
        original = cfg.read_text()
        assert (
            "VERSION_CODE:I = 0x1a" in original
            and 'VERSION_NAME:Ljava/lang/String; = "1.7.2"' in original
        )
        cfg.write_text(
            original.replace("VERSION_CODE:I = 0x1a", "VERSION_CODE:I = 0x1c").replace(
                'VERSION_NAME:Ljava/lang/String; = "1.7.2"',
                'VERSION_NAME:Ljava/lang/String; = "1.7.4"',
            )
        )
        run("java", "-jar", a.apktool, "b", "--no-apk", decoded)
        run(
            "java",
            "-jar",
            a.ecj,
            "-source",
            "1.8",
            "-target",
            "1.8",
            "-proc:none",
            "-nowarn",
            "-bootclasspath",
            a.android_jar,
            "-d",
            classes,
            Path(__file__).with_name("SafeMark.java"),
        )
        run(
            a.build_tools / "d8",
            "--min-api",
            "23",
            "--lib",
            a.android_jar,
            "--output",
            dex,
            *sorted(classes.rglob("*.class"))
        )
        dump = subprocess.check_output(
            [a.build_tools / "aapt", "dump", "--values", "resources", a.base]
        ).decode("utf-8")
        with ZipFile(a.base) as z:
            assemble(
                z,
                dump,
                (a.logo, a.banner, a.poster),
                dex / "classes.dex",
                decoded / "build/apk/classes3.dex",
                work / "unsigned.apk",
            )
        run(
            a.build_tools / "zipalign",
            "-f",
            "-P",
            "16",
            "4",
            work / "unsigned.apk",
            work / "aligned.apk",
        )
        run(
            a.build_tools / "apksigner",
            "sign",
            "--ks",
            os.environ["RUSSIA_RP_KEYSTORE"],
            "--ks-key-alias",
            "russia-rp",
            "--ks-pass",
            "file:" + os.environ["RUSSIA_RP_KEYPASS_FILE"],
            "--out",
            a.output,
            work / "aligned.apk",
        )
        run(a.build_tools / "apksigner", "verify", "--verbose", a.output)
        run(a.build_tools / "zipalign", "-c", "-P", "16", "4", a.output)


if __name__ == "__main__":
    main()
