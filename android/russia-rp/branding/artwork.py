from PIL import Image, ImageOps, ImageDraw, ImageFont
from io import BytesIO
import numpy as np

L = Image.Resampling.LANCZOS


def encode(im, fmt="WEBP", **options):
    out = BytesIO()
    im.save(out, fmt, **options)
    return out.getvalue()


def center(layer, art):
    layer.alpha_composite(
        art, ((layer.width - art.width) // 2, (layer.height - art.height) // 2)
    )


def artwork(z, paths, entries, logo_file, banner_file, poster_file):
    logo = Image.open(logo_file).convert("RGBA")
    logo = logo.crop(logo.getbbox())
    banner = Image.open(banner_file).convert("RGB")
    poster = Image.open(poster_file).convert("RGB")
    overrides = {}

    def save(name, data):
        overrides[paths["drawable/" + name]] = data

    # These photos are already at the author's aspect ratio; Android crops them at draw time.
    sky = encode(banner, "JPEG", quality=92, optimize=True, subsampling=0)
    full = encode(poster, "JPEG", quality=92, optimize=True, subsampling=0)
    for n in ("mylogo", "mylogo_mai", "mylogo_vesnaold"):
        save(n, full)
    for n in ("server_select_background", "loading_screenbg"):
        save(n, sky)
    # Show a wider crop of the supplied scene. Android masks only the center 72 of 108 units.
    photo = np.asarray(banner.crop((400, 0, 1520, 768)))
    # Extend only sky and foreground snow; reflecting the whole image repeats the sign.
    top = Image.fromarray(photo[:38][::-1]).resize((1120, 144), L)
    bottom = Image.fromarray(photo[-32:][::-1]).resize((1120, 208), L)
    square = Image.new("RGB", (1120, 1120))
    square.paste(top, (0, 0))
    square.paste(Image.fromarray(photo), (0, 144))
    square.paste(bottom, (0, 912))
    adaptive = Image.fromarray(
        np.pad(np.array(square), ((280, 280), (280, 280), (0, 0)), mode="edge")
    )
    for _, k, p in entries:
        if k.startswith("mipmap/ic_launcher") and not p.endswith(".xml"):
            with Image.open(BytesIO(z.read(p))) as old:
                size = old.size
            art = (
                (adaptive if "foreground" in k else square)
                .resize(size, L)
                .convert("RGBA")
            )
            if k.endswith("_round"):
                mask = Image.new("L", (size[0] * 3, size[1] * 3))
                ImageDraw.Draw(mask).ellipse(
                    (0, 0, mask.width - 1, mask.height - 1), fill=255
                )
                art.putalpha(mask.resize(size, L))
            overrides[p] = encode(art, quality=93, method=5)
    # Use a fully opaque, sharp mark inside the existing progress ring and card.
    for n, pad in [("bear_paw", 0.20), ("br_peaw_servers", 0.15)]:
        size = 300
        layer = Image.new("RGBA", (size, size))
        center(
            layer,
            ImageOps.contain(logo, (int(size * (1 - pad)), int(size * (1 - pad))), L),
        )
        save(n, encode(layer, lossless=True))
    font_path = next(p for k, p in paths.items() if k == "font/montserrat_bold")
    font = ImageFont.truetype(BytesIO(z.read(font_path)), 105)
    # Crop to the visible bounds of the exact mark and lettering, then align optical centers.
    w, h = 900, 300
    row = Image.new("RGBA", (w, h))
    mark = ImageOps.contain(logo, (185, 209), L)
    row.alpha_composite(mark, (3, (h - mark.height) // 2))
    letters = Image.new("RGBA", (730, 180))
    draw = ImageDraw.Draw(letters)
    draw.text(
        (4, 0), "МОСКВА", font=font, fill="white", stroke_width=2, stroke_fill="#422A21"
    )
    letters = letters.crop(letters.getbbox())
    row.alpha_composite(letters, (mark.width + 22, (h - letters.height) // 2))
    row = row.crop(row.getbbox())
    word = encode(row, lossless=True)
    for k in paths:
        if k.startswith("drawable/logobr") and k != "drawable/logobrx2":
            overrides[paths[k]] = word
    badge = Image.new("RGBA", (200, 94))
    d = ImageDraw.Draw(badge)
    d.rounded_rectangle(
        (1, 2, 198, 91), radius=19, fill="#964621", outline="#DE8954", width=3
    )
    ft = ImageFont.truetype(BytesIO(z.read(font_path)), 73)
    d.text((100, 46), "x4", font=ft, anchor="mm", fill="white", stroke_width=0)
    for n in ("logobrx2", "x2"):
        save(n, encode(badge, lossless=True))
    # Preserve the original antialiasing, highlights, icon shape, and touch bounds.
    for n in ("play_btn", "br_highlight_button_play", "gradient_select_server"):
        key = paths["drawable/" + n]
        im = Image.open(BytesIO(z.read(key))).convert("RGBA")
        arr = np.array(im)
        r, g, b = [arr[:, :, i].astype(float) for i in range(3)]
        mask = (r > g + 12) & (r > b + 15) & (arr[:, :, 3] > 0)
        strength = np.clip((r - b) / 210, 0, 1)
        mix = np.clip((g + 15) / 170, 0, 1)
        for i, (low, high) in enumerate([(155, 207), (66, 113), (34, 65)]):
            val = low + (high - low) * mix
            arr[:, :, i] = np.where(
                mask, arr[:, :, i] * (1 - strength) + val * strength, arr[:, :, i]
            ).astype("uint8")
        overrides[key] = encode(Image.fromarray(arr), lossless=True)
    return overrides
