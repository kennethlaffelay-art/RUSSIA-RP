"""Apply the RUSSIA RP display palette while preserving Pawn source encoding."""
from pathlib import Path
import argparse
import re


def apply(source):
    for name, color in (
        (b"COR_SERVER", b"0xBC5D33FF"),
        (b"c_server", b'"{D68B60}"'),
        (b"c_s", b'"{D68B60}"'),
    ):
        pattern = rb"(?m)^(#define[ \t]+" + name + rb"[ \t]+)(0x[\dA-Fa-f]{8}|\"\{[\dA-Fa-f]{6}\}\")"
        source, count = re.subn(pattern, lambda m: m[1] + color, source)
        if count != 1:
            raise ValueError(f"Expected one definition of {name.decode()}")
    source = re.sub(rb"\{ff2400\}\|", b"{D68B60}|", source, flags=re.I)
    return source.replace(b"World revision 2026-11-25.2 loaded", b"World revision 2026-11-25.3 loaded")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    before = args.source.read_bytes()
    after = apply(before)
    if before != after:
        args.source.write_bytes(after)
