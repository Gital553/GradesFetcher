"""Drop-in Hebrew (RTL) text renderer for Pillow.

Copy this file into the project and route every on-screen string through
`draw_text`. Requires: pillow, python-bidi, fonttools.

Two things have to happen before Pillow can draw a Hebrew caption correctly:

1. **Reordering.** Pillow draws glyphs in string order and does not run the
   BiDi algorithm, so text is converted to *visual* order first.
2. **Font fallback.** Noto Sans Hebrew is a Hebrew-only face — it has no comma,
   no question mark, no digits. Every line is therefore split into runs of
   characters the Hebrew face covers and runs it does not, and each run is drawn
   with the font that has the glyph. Without this, punctuation renders as tofu.
"""

from functools import lru_cache

from PIL import ImageDraw, ImageFont
from bidi import get_display
from fontTools.ttLib import TTFont

NOTO = "/usr/share/fonts/truetype/noto"
DEJAVU = "/usr/share/fonts/truetype/dejavu"
FONTS = {
    "bold": f"{NOTO}/NotoSansHebrew-Bold.ttf",
    "regular": f"{NOTO}/NotoSansHebrew-Regular.ttf",
    "latin_bold": f"{DEJAVU}/DejaVuSans-Bold.ttf",
    "latin_regular": f"{DEJAVU}/DejaVuSans.ttf",
}
FALLBACK = {"bold": "latin_bold", "regular": "latin_regular",
            "latin_bold": "latin_bold", "latin_regular": "latin_regular"}


@lru_cache(maxsize=256)
def font(size, weight="bold"):
    # BASIC layout: Pillow is built with Raqm here, and Raqm runs the BiDi
    # algorithm itself. Combined with the reordering below that would flip the
    # text twice and render it mirrored, so the smart layout engine is off and
    # ordering is done explicitly in one place.
    return ImageFont.truetype(FONTS[weight], size,
                              layout_engine=ImageFont.Layout.BASIC)


@lru_cache(maxsize=8)
def _coverage(weight):
    return set(TTFont(FONTS[weight], fontNumber=0)["cmap"].getBestCmap())


@lru_cache(maxsize=4096)
def _visual(text):
    return get_display(text)


@lru_cache(maxsize=4096)
def _runs(text, weight):
    """Split a visual-order line into (substring, weight) runs by coverage."""
    cover = _coverage(weight)
    fb = FALLBACK[weight]
    out = []
    for ch in text:
        w = weight if ord(ch) in cover else fb
        if out and out[-1][1] == w:
            out[-1][0] += ch
        else:
            out.append([ch, w])
    return tuple((s, w) for s, w in out)


def line_width(text, size, weight):
    return sum(font(size, w).getlength(s) for s, w in _runs(text, weight))


def text_size(text, size, weight="bold"):
    lines = [_visual(l) for l in text.split("\n")]
    asc, desc = font(size, weight).getmetrics()
    return max(line_width(l, size, weight) for l in lines), (asc + desc) * len(lines)


def _draw_line(d, x, baseline, visual, size, weight, fill):
    for run, w in _runs(visual, weight):
        f = font(size, w)
        d.text((x, baseline), run, font=f, fill=fill, anchor="ls")
        x += f.getlength(run)


def draw_text(img, xy, text, size=48, weight="bold", fill=(255, 255, 255),
              alpha=1.0, anchor="mm", shadow=(0, 0, 0), shadow_offset=3,
              shadow_alpha=0.55, spacing=12, align="center"):
    """Draw a Hebrew string in visual order with a soft shadow.

    ``img`` must be RGBA so partially transparent text composites correctly.
    ``anchor`` supports the horizontal (l/m/r) and vertical (a/m/s) codes the
    film actually uses.
    """
    if alpha <= 0.001:
        return
    d = ImageDraw.Draw(img)
    lines = [_visual(line) for line in text.split("\n")]
    asc, desc = font(size, weight).getmetrics()
    line_h = asc + desc + spacing
    widths = [line_width(l, size, weight) for l in lines]
    block_w, block_h = max(widths), line_h * len(lines) - spacing
    a = max(0, min(255, int(255 * alpha)))

    ax, ay = anchor[0], anchor[1]
    left = xy[0] - block_w / 2 if ax == "m" else xy[0] - block_w if ax == "r" else xy[0]
    if ay == "m":
        top = xy[1] - block_h / 2
    elif ay == "s":
        top = xy[1] - block_h
    else:
        top = xy[1]

    passes = []
    if shadow is not None and shadow_offset:
        passes.append(((*shadow, int(a * shadow_alpha)), shadow_offset))
    passes.append(((*fill, a), 0))

    for pass_fill, off in passes:
        for i, (line, w) in enumerate(zip(lines, widths)):
            if align == "center":
                x = left + (block_w - w) / 2
            elif align == "right":
                x = left + (block_w - w)
            else:
                x = left
            _draw_line(d, x + off, top + asc + i * line_h + off, line, size,
                       weight, pass_fill)
