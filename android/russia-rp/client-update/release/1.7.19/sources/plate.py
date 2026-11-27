"""Create static plate lettering with the character advances used by the client."""
from pathlib import Path
from fontTools.fontBuilder import FontBuilder
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen

def build(source, current, target):
    font = instantiateVariableFont(TTFont(source), {"wght": 650}, inplace=False)
    glyphs = font.getGlyphSet()
    lookup = font.getBestCmap()
    letters = 'ABEKMHOPCTYX'
    equivalents = dict(zip('АВЕКМНОРСТУХ', letters))
    originals = TTFont(current).getBestCmap()
    chars = sorted(set(originals) | set(range(32, 127)) | set(range(0x410, 0x450)) | {0x401, 0x451})
    names, outlines, metrics = {}, {}, {}
    cap = font['OS/2'].sCapHeight
    for value in [None] + chars:
        ch = chr(value) if value is not None else None
        canonical = equivalents.get(ch.upper(), ch.upper()) if ch and (ch.upper() in equivalents or ch.upper() in letters) else ch
        key = '.notdef' if canonical is None else 'uni%04X' % ord(canonical)
        if value is not None:
            names[value] = key
        if key in outlines:
            continue
        source_key = '.notdef' if canonical is None else lookup[ord('У' if canonical == 'Y' else canonical)]
        glyph = glyphs[source_key]
        bounds = BoundsPen(glyphs)
        glyph.draw(bounds)
        pen = TTGlyphPen(None)
        advance = 425 if canonical != ' ' else 210
        left = 0
        if bounds.bounds:
            xmin, _, xmax, _ = bounds.bounds
            sy = (780 if canonical is None or not canonical.isalpha() else 735) / cap
            ideal = (xmax - xmin) * sy
            width = min(369, ideal)
            # Keep the narrow native opening of 1 instead of widening it to fit its cell.
            if canonical == '1':
                width = min(width, 226)
            left = round((advance - width) / 2)
            scale = width / (xmax - xmin)
            recording = DecomposingRecordingPen(glyphs)
            glyph.draw(recording)
            recording.replay(TransformPen(pen, (scale, 0, 0, sy, left - xmin * scale, 0)))
        outlines[key] = pen.glyph()
        metrics[key] = advance, left
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(list(outlines))
    fb.setupCharacterMap(names)
    fb.setupGlyf(outlines)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=1000, descent=0)
    license_text = Path(source).with_name('Roboto-OFL.txt').read_text()
    fb.setupNameTable({'familyName':'Russia RP Plate', 'styleName':'Semibold',
        'psName':'RussiaRPPlate-Semibold', 'fullName':'Russia RP Plate Semibold',
        'uniqueFontIdentifier':'RussiaRPPlate-Semibold-1.019', 'version':'Version 1.019',
        'copyright': license_text.splitlines()[0], 'licenseDescription': license_text,
        'licenseInfoURL':'https://openfontlicense.org/'})
    fb.setupOS2(sTypoAscender=1000, sTypoDescender=0, usWinAscent=1000, usWinDescent=250,
                sCapHeight=735, usWeightClass=650)
    fb.setupPost(isFixedPitch=0)
    fb.setupMaxp()
    fb.save(target)
    new = TTFont(target)
    assert set(originals).issubset(new.getBestCmap())
    assert all(new.getBestCmap()[ord(a)] == new.getBestCmap()[ord(b)] for a,b in equivalents.items())

if __name__ == '__main__':
    import sys
    build(*sys.argv[1:])
