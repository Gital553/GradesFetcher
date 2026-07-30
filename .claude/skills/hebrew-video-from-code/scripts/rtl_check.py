"""Prove Hebrew is rendering in the right direction — by pixels, not by eye.

Reading Hebrew off a rendered image is unreliable: a fluent reader silently
re-orders mirrored text while reading it, so mirrored captions pass casual
review and ship. This check is objective.

The test: in `אבג`, the *last* logical letter (ג) must end up **leftmost** on
screen. Render `אבג`, render `ג` and `א` alone, and compare the leftmost glyph's
pixels against both. If it matches ג, ordering is correct; if it matches א, the
text is mirrored — almost always because Pillow's Raqm layout engine ran BiDi
and something else reversed the string as well.

    python3 rtl_check.py [path/to/hebrew_text.py's directory]
"""

import sys

import numpy as np
from PIL import Image

sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else ".")

from hebrew_text import draw_text  # noqa: E402

SAMPLES = [
    "כיצד שורדים במדבר בלי לשתות?",   # question mark
    "מדעים · כיתה ד׳",                 # middle dot + geresh
    "3 מתוך 7",                        # digits inside Hebrew
    "שתיהן חשובות — אבל לא אותו דבר",  # em dash
]


def _render(text, size=90, width=1400):
    img = Image.new("RGBA", (width, 220), (0, 0, 0, 255))
    draw_text(img, (40, 110), text, size=size, anchor="lm", shadow=None)
    return np.array(img.convert("L"))


def _ink(arr):
    cols = np.where(arr.max(axis=0) > 40)[0]
    return (int(cols.min()), int(cols.max())) if len(cols) else (None, None)


def _diff(a, b):
    n = min(a.shape[1], b.shape[1])
    return float(np.abs(a[:, :n].astype(int) - b[:, :n].astype(int)).mean())


def check_direction():
    full, gimel, alef = _render("אבג"), _render("ג"), _render("א")
    g0, g1 = _ink(gimel)
    width = g1 - g0
    f0, _ = _ink(full)
    a0, _ = _ink(alef)
    crop = lambda arr, x: arr[:, x:x + width + 6]  # noqa: E731

    d_gimel = _diff(crop(full, f0), crop(gimel, g0))
    d_alef = _diff(crop(full, f0), crop(alef, a0))
    ok = d_gimel < d_alef
    print(f"leftmost glyph vs ג (last letter)  = {d_gimel:6.2f}")
    print(f"leftmost glyph vs א (first letter) = {d_alef:6.2f}")
    print("RTL ordering:", "OK" if ok else "BROKEN — text is mirrored")
    return ok


def check_glyphs():
    """Every sample must draw ink and must not fall back to tofu boxes.

    A .notdef box is a tall rectangle of near-constant width; a missing glyph
    usually shows up first as a *wider* line than the same text without it, so
    this reports spans for eyeballing alongside the direction check.
    """
    ok = True
    for s in SAMPLES:
        arr = _render(s, 56)
        lo, hi = _ink(arr)
        if lo is None:
            print(f"  NO INK: {s!r}")
            ok = False
        else:
            print(f"  ink {lo:4d}..{hi:4d}   {s}")
    return ok


if __name__ == "__main__":
    direction_ok = check_direction()
    print("\nmixed-content samples (check these visually once):")
    glyphs_ok = check_glyphs()
    sys.exit(0 if (direction_ok and glyphs_ok) else 1)
