"""Measure the two parts of the wordmark as actually rendered by Android."""
from pathlib import Path
import sys

from PIL import Image


def measure(path, gutter_center):
    with Image.open(path) as mark:
        alpha = mark.convert("RGBA").getchannel("A").point(lambda a: 255 if a >= 12 else 0)
        left, top, right, bottom = alpha.getbbox()
        split = round(left + (right - left) * gutter_center)
        if alpha.crop((split, top, split + 1, bottom)).getbbox():
            raise ValueError(f"No transparent gutter at {split} in {path}")
        emblem = alpha.crop((left, top, split, bottom)).getbbox()
        word = alpha.crop((split, top, right, bottom)).getbbox()
        return emblem[3] - emblem[1], word[3] - word[1], word[2] - word[0]


root = Path(sys.argv[1])
version = sys.argv[2] if len(sys.argv) > 2 else "1.7.8"
if version not in ("1.7.8", "1.7.9"):
    raise ValueError(f"Unknown HUD version {version}")
large_emblem = version == "1.7.9"
gutter = (194 + 7) / 698 if large_emblem else (69 + 7) / 616
for screen in (1280, 1600):
    old = measure(root / "before" / f"mark-{screen}.png", (118 + 7) / 665)
    new = measure(root / "after" / f"mark-{screen}.png", gutter)
    ratio = new[2] / old[2]
    print(f"{screen}x720: emblem and letters {new[0]} and {new[1]} px, word width {old[2]} -> {new[2]} px ({ratio:.1%})")
    if large_emblem:
        print(f"{screen}x720: cathedral height {old[0]} -> {new[0]} px")
        if not (1.58 <= new[0] / old[0] <= 1.72 and 0.89 <= ratio <= 0.95):
            raise ValueError("Cathedral must grow and the server name must shrink relative to 1.7.7")
    elif abs(new[0] - new[1]) > 2 or not 0.88 <= ratio <= 0.92:
        raise ValueError("Rendered proportions are outside the expected range")
