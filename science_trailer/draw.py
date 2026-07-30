"""Drawing primitives shared by every scene.

Design notes
------------
* Everything expensive that does not change over time (gradients, star fields,
  vignette, grain) is built once and cached, then composited with Pillow's C
  routines. At 5,400 frames a per-pixel Python loop is not an option.
* Scenes draw into a transparent RGBA overlay and alpha-composite it onto a
  cached background copy, which keeps translucency (glows, fades) correct.
"""

import math
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 1920, 1080
SIZE = (W, H)

# ---------------------------------------------------------------- palette ---
INK = (8, 12, 24)
WHITE = (255, 255, 255)
SAND = (232, 197, 138)
AMBER = (242, 166, 59)
MOON = (255, 243, 214)
NIGHT_TOP = (9, 13, 38)
NIGHT_BOT = (38, 40, 86)
ICE_TOP = (10, 40, 74)
ICE_BOT = (126, 196, 232)
DESERT_TOP = (58, 26, 12)
DESERT_BOT = (232, 148, 56)
WATER_TOP = (5, 46, 66)
WATER_BOT = (22, 132, 148)
SLATE_TOP = (14, 24, 34)
SLATE_BOT = (32, 54, 70)
BRASS = (214, 169, 74)
CYAN = (79, 195, 247)
XRAY_TOP = (4, 12, 30)
XRAY_BOT = (12, 40, 74)
BONE = (207, 233, 255)
SKIN = (233, 180, 140)
TEAL = (63, 214, 192)
CORAL = (240, 110, 96)


# ------------------------------------------------------------- easing ------
def clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(a, b, t):
    t = clamp(t)
    return tuple(int(round(lerp(a[i], b[i], t))) for i in range(3))


def smoothstep(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def ease_out(t, power=3):
    return 1 - (1 - clamp(t)) ** power


def ease_in(t, power=3):
    return clamp(t) ** power


def fade_band(p, fade_in=0.12, fade_out=0.12):
    """Alpha envelope over a normalised 0..1 progress."""
    return min(smoothstep(p / fade_in) if fade_in else 1.0,
               smoothstep((1 - p) / fade_out) if fade_out else 1.0)


def cue(t, start, dur, fade=0.45):
    """Alpha for a caption that appears at `start` and lives `dur` seconds."""
    if t < start or t > start + dur:
        return 0.0
    return min(clamp((t - start) / fade), clamp((start + dur - t) / fade))


def rise(t, start, dur, distance=34, fade=0.45):
    """(alpha, y-offset) for a caption that fades in while sliding up."""
    a = cue(t, start, dur, fade)
    k = clamp((t - start) / fade) if fade else 1.0
    return a, distance * (1 - ease_out(k))


# --------------------------------------------------------- backgrounds -----
@lru_cache(maxsize=64)
def vgrad(top, bottom, height=H, width=W, curve=1.0):
    """Cached vertical gradient as an RGBA image."""
    t = np.linspace(0.0, 1.0, height, dtype=np.float32) ** curve
    ramp = (np.array(top, np.float32)[None, :] * (1 - t)[:, None]
            + np.array(bottom, np.float32)[None, :] * t[:, None])
    arr = np.repeat(ramp[:, None, :], width, axis=1).astype(np.uint8)
    rgba = np.dstack([arr, np.full((height, width), 255, np.uint8)])
    return Image.fromarray(rgba, "RGBA")


@lru_cache(maxsize=32)
def glow(radius, color, strength=1.0, falloff=2.2):
    """Cached soft radial glow sprite (RGBA), centred in a 2R box."""
    r = int(radius)
    yy, xx = np.mgrid[-r:r, -r:r].astype(np.float32)
    d = np.sqrt(xx * xx + yy * yy) / r
    a = np.clip(1.0 - d, 0, 1) ** falloff * (255 * clamp(strength))
    rgb = np.zeros((2 * r, 2 * r, 3), np.uint8)
    rgb[:] = color
    return Image.fromarray(np.dstack([rgb, a.astype(np.uint8)]), "RGBA")


def paste_glow(img, xy, radius, color, strength=1.0, falloff=2.2):
    g = glow(int(radius), tuple(color), round(clamp(strength), 3), falloff)
    img.alpha_composite(g, (int(xy[0] - radius), int(xy[1] - radius)))


@lru_cache(maxsize=8)
def vignette(strength=0.55):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dx = (xx - W / 2) / (W / 2)
    dy = (yy - H / 2) / (H / 2)
    d = np.sqrt(dx * dx + dy * dy) / 1.42
    a = (np.clip(d - 0.35, 0, 1) ** 1.7) * (255 * strength)
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., 3] = a.astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


@lru_cache(maxsize=1)
def _grain_bank(n=6, amount=4):
    # Keep this low: per-frame noise is expensive for h264 to encode, and at
    # amount=9 a 3-minute 1080p cut ballooned to ~150 MB.
    rng = np.random.default_rng(7)
    bank = []
    for _ in range(n):
        g = rng.integers(0, 256, (H // 2, W // 2), dtype=np.uint8)
        rgba = np.zeros((H // 2, W // 2, 4), np.uint8)
        rgba[..., 0] = rgba[..., 1] = rgba[..., 2] = g
        rgba[..., 3] = amount
        bank.append(Image.fromarray(rgba, "RGBA").resize(SIZE, Image.BILINEAR))
    return bank


def finish(img, frame_index, grain=True, vig=0.5):
    """Common grade applied to every frame."""
    if vig:
        img.alpha_composite(vignette(round(vig, 2)))
    if grain:
        bank = _grain_bank()
        img.alpha_composite(bank[frame_index % len(bank)])
    return img


def dim(img, k, color=(0, 0, 0)):
    """Fade the frame towards `color` (k=0 no-op, k=1 fully covered)."""
    if k <= 0.001:
        return
    img.alpha_composite(Image.new("RGBA", SIZE, (*color, int(255 * clamp(k)))))


def overlay():
    ov = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    return ov, ImageDraw.Draw(ov)


def blurred(ov, radius):
    return ov.filter(ImageFilter.GaussianBlur(radius))


# ------------------------------------------------------------ geometry -----
def xform(points, x=0.0, y=0.0, s=1.0, rot=0.0, flip=False):
    """Scale/flip/rotate/translate a point list."""
    c, sn = math.cos(rot), math.sin(rot)
    out = []
    for px, py in points:
        px = -px if flip else px
        px, py = px * s, py * s
        out.append((x + px * c - py * sn, y + px * sn + py * c))
    return out


def circle(d, xy, r, **kw):
    d.ellipse([xy[0] - r, xy[1] - r, xy[0] + r, xy[1] + r], **kw)


def bone(d, p0, p1, width, fill):
    """A capsule — the building block of every limb in the film."""
    d.line([p0, p1], fill=fill, width=int(width), joint="curve")
    circle(d, p0, width / 2, fill=fill)
    circle(d, p1, width / 2, fill=fill)


def limb(origin, length, angle):
    return (origin[0] + length * math.cos(angle), origin[1] + length * math.sin(angle))


@lru_cache(maxsize=16)
def star_field(count=260, seed=3, band=H):
    rng = np.random.default_rng(seed)
    return [
        (float(rng.uniform(0, W)), float(rng.uniform(0, band)),
         float(rng.uniform(0.8, 2.6)), float(rng.uniform(0, math.tau)))
        for _ in range(count)
    ]


def draw_stars(d, t, alpha=1.0, count=260, seed=3, band=H, speed=2.4):
    for x, y, r, phase in star_field(count, seed, band):
        tw = 0.55 + 0.45 * math.sin(t * speed + phase)
        a = int(255 * clamp(alpha) * tw)
        if a > 4:
            circle(d, (x, y), r, fill=(255, 255, 235, a))


def dunes(d, base_y, color, amp=60, freq=1.6, phase=0.0, seed_shift=0.0):
    """A soft dune/hill silhouette across the full width."""
    pts = [(0, H)]
    for i in range(0, W + 1, 12):
        u = i / W
        y = (base_y
             + amp * math.sin(u * math.pi * freq + phase)
             + amp * 0.4 * math.sin(u * math.pi * freq * 2.7 + phase * 1.7 + seed_shift))
        pts.append((i, y))
    pts.append((W, H))
    d.polygon(pts, fill=color)


def waves(d, base_y, color, amp, freq, phase, alpha=255, step=12):
    pts = [(0, H)]
    for i in range(0, W + 1, step):
        u = i / W
        pts.append((i, base_y + amp * math.sin(u * math.tau * freq + phase)))
    pts.append((W, H))
    d.polygon(pts, fill=(*color, alpha))


def scrim(img, y0, y1, alpha=150):
    """Dark band behind captions so text stays readable over artwork."""
    band = Image.new("RGBA", (W, int(y1 - y0)), (0, 0, 0, 0))
    arr = np.zeros((int(y1 - y0), W, 4), np.uint8)
    prof = np.sin(np.linspace(0, math.pi, int(y1 - y0), dtype=np.float32))
    arr[..., 3] = (prof * alpha).astype(np.uint8)[:, None]
    band = Image.fromarray(arr, "RGBA")
    img.alpha_composite(band, (0, int(y0)))
