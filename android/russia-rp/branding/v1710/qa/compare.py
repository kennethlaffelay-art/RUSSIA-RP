"""Compare visible artwork drawn by Android from the two installed APKs."""
from pathlib import Path
import sys

from PIL import Image


def measure(path):
    with Image.open(path) as image:
        alpha = image.convert("RGBA").getchannel("A").point(lambda a: 255 if a >= 12 else 0)
    alpha = alpha.crop(alpha.getbbox())
    gutter = alpha.getprojection()[0].index(0)
    emblem = alpha.crop((0, 0, gutter, alpha.height)).getbbox()
    letters = alpha.crop((gutter, 0, alpha.width, alpha.height)).getbbox()
    return emblem[3] - emblem[1], letters[2] - letters[0], letters[3] - letters[1]


if __name__ == "__main__":
    root = Path(sys.argv[1])
    for width in (1280, 1600):
        name = f"mark-{width}.png"
        old = measure(root / "before" / name)
        new = measure(root / "after" / name)
        print(f"{width}x720: (emblem height, city width, city height) {old} -> {new}")
        if not (1.9 <= new[0] / old[0] <= 2.3 and
                .89 <= new[1] / old[1] <= .95 and new[2] < old[2]):
            raise ValueError("HUD must enlarge the cathedral and shrink the city slightly")
