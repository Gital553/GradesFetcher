"""The 23 shots of the trailer.

Every scene is a pure function ``f(t, p, fi) -> RGBA image`` where ``t`` is the
time in seconds since the shot started, ``p`` the normalised progress and ``fi``
the global frame index. Content is grounded in the four source documents:
the three lesson plans (תצפית/פרשנות, מאפייני חיים, צרכי קיום) and the yearly
plan's four gates (שערים א'–ד').
"""

import math

from PIL import Image, ImageDraw

import creatures as cr
from draw import (AMBER, BONE, BRASS, CORAL, CYAN, DESERT_BOT, DESERT_TOP, H,
                  ICE_BOT, ICE_TOP, MOON, NIGHT_BOT, NIGHT_TOP, SAND,
                  SLATE_BOT, SLATE_TOP, TEAL, W, WATER_BOT, WATER_TOP,
                  WHITE, XRAY_BOT, XRAY_TOP, bone, circle, clamp, cue, dim,
                  draw_stars, dunes, ease_in, ease_out, lerp, lerp_color,
                  limb, overlay, paste_glow, rise, scrim, smoothstep,
                  vgrad, waves)
from hebrew import draw_text

# --------------------------------------------------------------- helpers ---
CX = W / 2


def caption(img, t, start, dur, text, size=58, y=H - 150, color=WHITE,
            sub=None, sub_size=36, band=170, fade=0.45):
    """Lower-third caption with a soft scrim so it stays legible."""
    a, dy = rise(t, start, dur, distance=30, fade=fade)
    if a <= 0.004:
        return
    if band:
        scrim(img, y - 120, y + 150, int(band * a))
    draw_text(img, (CX, y + dy), text, size=size, fill=color, alpha=a)
    if sub:
        draw_text(img, (CX, y + dy + size * 0.92), sub, size=sub_size,
                  weight="regular", fill=(226, 232, 240), alpha=a * 0.92)


def label(img, t, start, dur, text, xy, size=40, color=WHITE, weight="bold",
          anchor="mm", fade=0.4):
    a = cue(t, start, dur, fade)
    if a > 0.004:
        draw_text(img, xy, text, size=size, weight=weight, fill=color,
                  alpha=a, anchor=anchor)


def rule(d, x0, x1, y, k, color=AMBER, width=5):
    """A horizontal rule that draws itself outward from the centre."""
    k = clamp(k)
    if k <= 0:
        return
    half = (x1 - x0) / 2 * ease_out(k)
    mid = (x0 + x1) / 2
    d.line([mid - half, y, mid + half, y], fill=(*color, 235), width=width)


def blueprint_grid(d, spacing=96, color=(90, 150, 190), alpha=46, offset=0.0):
    off = offset % spacing
    for x in range(-int(spacing), W + spacing, spacing):
        d.line([x + off, 0, x + off, H], fill=(*color, alpha), width=2)
    for y in range(-int(spacing), H + spacing, spacing):
        d.line([0, y + off, W, y + off], fill=(*color, alpha), width=2)


def gate_card(t, p, fi, letter, title, subtitle, top, bottom, accent):
    img = vgrad(top, bottom).copy()
    ov, d = overlay()
    a = min(smoothstep(p / 0.22), smoothstep((1 - p) / 0.22))
    draw_text(ov, (CX, H / 2 + 120), letter, size=620, fill=accent,
              alpha=0.13 * a, shadow=None)
    draw_text(ov, (CX, H / 2 - 90), title, size=92, fill=WHITE, alpha=a)
    rule(d, CX - 300, CX + 300, H / 2 + 10, (t - 0.25) / 0.7, accent)
    draw_text(ov, (CX, H / 2 + 92), subtitle, size=46, weight="regular",
              fill=(226, 232, 240), alpha=a * 0.95)
    img.alpha_composite(ov)
    return img


# ================================================================= ACT 1 ===
def s01_open(t, p, fi):
    """Starfield, then the title of the year."""
    img = vgrad(NIGHT_TOP, NIGHT_BOT).copy()
    ov, d = overlay()
    star_a = smoothstep((t - 0.4) / 2.2)
    draw_stars(d, t, star_a * 0.95, count=320)
    img.alpha_composite(ov)

    paste_glow(img, (CX, H * 0.62), 620, (60, 92, 190), 0.30 * star_a, 2.6)

    ov2, d2 = overlay()
    a1, dy1 = rise(t, 1.1, 5.0, distance=44, fade=0.9)
    draw_text(ov2, (CX, 400 + dy1), "מדע וטכנולוגיה", size=64,
              weight="regular", fill=(198, 216, 255), alpha=a1)
    a2, dy2 = rise(t, 1.6, 4.5, distance=60, fade=1.0)
    draw_text(ov2, (CX, 540 + dy2), "כיתה ד׳", size=200, fill=WHITE, alpha=a2)
    rule(d2, CX - 260, CX + 260, 690, (t - 2.6) / 1.0, AMBER)
    a3, dy3 = rise(t, 3.1, 2.9, distance=26)
    draw_text(ov2, (CX, 790 + dy3), "המסע השנתי מתחיל", size=52,
              weight="regular", fill=SAND, alpha=a3)
    img.alpha_composite(ov2)
    dim(img, ease_in((t - 5.4) / 0.6) if t > 5.4 else 0)
    return img


def s02_desert_night(t, p, fi):
    """A kangaroo rat crossing moonlit dunes — the opening image of lesson 1."""
    img = vgrad(NIGHT_TOP, (52, 44, 78)).copy()
    ov, d = overlay()
    draw_stars(d, t, 0.85, count=280, band=int(H * 0.62), seed=11)
    img.alpha_composite(ov)

    moon = (W * 0.76, H * 0.20)
    paste_glow(img, moon, 300, MOON, 0.34, 2.4)
    ov, d = overlay()
    circle(d, moon, 74, fill=(*MOON, 250))
    for cxm, cym, crad in ((26, -16, 9), (-18, 22, 12), (4, -34, 6), (-34, -6, 7),
                           (30, 26, 5)):
        circle(d, (moon[0] + cxm, moon[1] + cym), crad, fill=(232, 220, 190, 60))

    drift = t * 12
    dunes(d, H * 0.70, (36, 34, 66, 255), amp=54, freq=1.4, phase=0.6 - drift / 900)
    dunes(d, H * 0.80, (26, 24, 50, 255), amp=64, freq=1.9, phase=2.1 - drift / 500)
    img.alpha_composite(ov)

    ov, d = overlay()
    dunes(d, H * 0.93, (14, 13, 30, 255), amp=44, freq=2.4, phase=4.0 - drift / 260)
    # the rat crosses right to left, hopping
    x = lerp(W + 220, -260, clamp(t / 9.0))
    ground = H * 0.905
    for k in range(7):                                   # dust puffs behind it
        pa = 0.55 - k * 0.07
        px = x + 120 + k * 46 + 18 * math.sin(t * 4 + k)
        circle(d, (px, ground + 30 + 6 * math.sin(t * 3 + k)), 10 + k * 2.5,
               fill=(120, 116, 150, int(60 * pa)))
    cr.kangaroo_rat(d, x, ground, s=1.15, phase=t * 5.4)
    img.alpha_composite(ov)

    ov, _ = overlay()
    # kept high in frame: the rat crosses the lower third
    caption(ov, t, 1.4, 6.4, "כיצד שורדים במדבר בלי לשתות?", size=66, y=330,
            band=110)
    img.alpha_composite(ov)
    return img


def s03_dew(t, p, fi):
    """The reveal: dew on seeds — water that arrives without rain."""
    img = vgrad((22, 20, 46), (58, 46, 52)).copy()
    paste_glow(img, (CX, H * 0.78), 520, (120, 150, 220), 0.34, 2.2)
    ov, d = overlay()

    # a scatter of seeds on the desert floor, dew beading on top of them
    seeds = [(CX - 430, 902, 62, 34, -0.25), (CX - 300, 862, 54, 30, 0.18),
             (CX - 170, 918, 66, 36, 0.05), (CX - 40, 872, 58, 32, -0.32),
             (CX + 90, 916, 62, 34, 0.22), (CX + 220, 868, 55, 30, -0.12),
             (CX + 350, 910, 64, 35, 0.30), (CX + 470, 866, 52, 29, -0.20),
             (CX - 360, 962, 60, 32, 0.12), (CX - 100, 968, 66, 34, -0.16),
             (CX + 160, 964, 58, 31, 0.26), (CX + 410, 960, 62, 33, -0.08)]
    for sx, sy, rx, ry, rot in seeds:
        pts = [(sx + rx * math.cos(a) * math.cos(rot) - ry * math.sin(a) * math.sin(rot),
                sy + rx * math.cos(a) * math.sin(rot) + ry * math.sin(a) * math.cos(rot))
               for a in (i * math.tau / 26 for i in range(26))]
        d.polygon(pts, fill=(146, 112, 70, 255))
        d.polygon([(px, py - 9) for px, py in pts], fill=(184, 146, 96, 255))
        d.line([sx - rx * 0.55, sy - 12, sx + rx * 0.55, sy - 12],
               fill=(126, 94, 58, 255), width=3)          # crease

    # drops swell one after another and catch the moonlight
    for i, (sx, sy, rx, ry, _r) in enumerate(seeds[:6]):
        grow = smoothstep(clamp((t - 0.5 - i * 0.34) / 1.3))
        r = 30 * grow
        if r < 2:
            continue
        cxx, cyy = sx + 6, sy - ry - r * 0.5
        d.polygon([(cxx, cyy - r * 1.55), (cxx + r * 0.92, cyy + r * 0.25),
                   (cxx - r * 0.92, cyy + r * 0.25)], fill=(168, 218, 252, 235))
        circle(d, (cxx, cyy + r * 0.18), r * 0.92, fill=(168, 218, 252, 235))
        circle(d, (cxx - r * 0.34, cyy - r * 0.1), r * 0.26,
               fill=(255, 255, 255, 240))
    img.alpha_composite(ov)

    ov, _ = overlay()
    a, dy = rise(t, 0.5, 2.6, distance=34)
    draw_text(ov, (CX, 300 + dy), "טל", size=150, fill=(180, 226, 255), alpha=a)
    draw_text(ov, (CX, 430 + dy), "מים שמגיעים בלי גשם", size=54,
              weight="regular", fill=WHITE, alpha=a)
    caption(ov, t, 3.2, 2.7, "היא אינה שותה כלל —",
            sub="את כל המים היא מפיקה מן הזרעים שהיא אוכלת", size=58)
    img.alpha_composite(ov)
    return img


def s04_boundary(t, p, fi):
    """Fire, cloud, robot — the boundary cards of lesson 2."""
    img = vgrad((14, 16, 30), (30, 34, 56)).copy()
    pw, ph = 500, 560
    gap = 60
    total = pw * 3 + gap * 2
    x_start = (W - total) / 2
    y0 = 250

    for i, kind in enumerate(("fire", "cloud", "robot")):
        # right-to-left entrance order: fire (right), cloud, robot
        idx = 2 - i
        appear = clamp((t - 0.3 - i * 0.55) / 0.8)
        if appear <= 0:
            continue
        a = ease_out(appear)
        x0 = x_start + idx * (pw + gap)
        yy = y0 + (1 - a) * 60
        panel = vgrad((26, 30, 52), (16, 18, 34), height=ph, width=pw)
        mask = Image.new("L", (pw, ph), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, pw - 1, ph - 1], 30, fill=int(235 * a))
        img.paste(panel, (int(x0), int(yy)), mask)

        ov, d = overlay()
        cxp = x0 + pw / 2
        if kind == "fire":
            base = yy + ph - 120
            for layer, (col, scale) in enumerate((((214, 74, 32), 1.0),
                                                  ((242, 148, 44), 0.68),
                                                  ((255, 214, 120), 0.36))):
                half = 128 * scale
                pts = [(cxp - half, base)]
                for k in range(15):
                    u = k / 14
                    flick = math.sin(t * 9 + k * 1.3 + layer) * 14 * scale
                    # teardrop profile: wide at the base, tapering to a tip
                    spread = math.sin(u * math.pi) ** 0.45
                    pts.append((cxp - half * (1 - u * 2) + flick * 0.6,
                                base - (330 * scale) * spread * (0.35 + 0.65 * u) + flick))
                pts.append((cxp + half, base))
                d.polygon(pts, fill=(*col, int(235 * a)))
            d.ellipse([cxp - 132, base - 26, cxp + 132, base + 26],
                      fill=(214, 74, 32, int(150 * a)))
            for k in range(6):                              # embers
                ey = base - 180 - ((t * 90 + k * 70) % 320)
                d.ellipse([cxp - 60 + k * 24 - 3, ey - 3, cxp - 60 + k * 24 + 3, ey + 3],
                          fill=(255, 196, 110, int(180 * a)))
        elif kind == "cloud":
            for k, (ox, oy, r) in enumerate(((-110, 20, 76), (-20, -30, 96),
                                             (80, 10, 82), (10, 40, 70))):
                drift2 = 14 * math.sin(t * 1.1 + k)
                circle(d, (cxp + ox + drift2, yy + 300 + oy), r,
                       fill=(226, 234, 248, int(230 * a)))
            for k in range(4):
                rx = cxp - 90 + k * 60
                ry = yy + 400 + ((t * 70 + k * 40) % 110)
                d.line([rx, ry, rx - 6, ry + 26], fill=(150, 200, 240, int(200 * a)), width=5)
        else:
            bx, by = cxp, yy + 300
            d.rounded_rectangle([bx - 100, by - 90, bx + 100, by + 120], 22,
                                fill=(120, 132, 156, int(240 * a)))
            d.rounded_rectangle([bx - 74, by - 60, bx + 74, by + 10], 14,
                                fill=(24, 32, 48, int(240 * a)))
            blink = 0.35 + 0.65 * (math.sin(t * 4.2) > -0.2)
            for ex in (-36, 36):
                circle(d, (bx + ex, by - 26), 15,
                       fill=(90, 240, 200, int(240 * a * blink)))
            d.line([bx, by - 90, bx, by - 150], fill=(160, 172, 196, int(240 * a)), width=8)
            circle(d, (bx, by - 160), 15, fill=(240, 96, 80, int(240 * a * blink)))
            for sx in (-100, 100):
                d.line([bx + sx, by - 40, bx + sx * 1.5, by + 40],
                       fill=(120, 132, 156, int(240 * a)), width=16)
        img.alpha_composite(ov)

        ov, _ = overlay()
        label(img, t, 0.3 + i * 0.55, 20, {"fire": "אש", "cloud": "ענן",
                                           "robot": "רובוט"}[kind],
              (cxp, yy + ph - 46), size=54, color=SAND)

    ov, _ = overlay()
    a, dy = rise(t, 0.6, 3.4, distance=26)
    draw_text(ov, (CX, 150 + dy), "האם זה יצור חי?", size=76, fill=WHITE, alpha=a)
    caption(ov, t, 4.4, 3.2, "האש גדלה, נעה וצריכה אוויר — שלושה מתוך שבעה",
            size=54)
    caption(ov, t, 7.9, 3.0, "יצור חי מקיים את כל המאפיינים", size=62,
            color=AMBER)
    img.alpha_composite(ov)
    return img


def s05_observation(t, p, fi):
    """The two columns the teacher writes on the board."""
    img = vgrad((16, 26, 32), (30, 44, 52)).copy()
    ov, d = overlay()
    d.rounded_rectangle([70, 70, W - 70, H - 70], 26, outline=(96, 122, 132, 190),
                        width=4, fill=(20, 32, 38, 210))
    k = clamp((t - 0.2) / 1.0)
    if k > 0:
        d.line([CX, 150, CX, 150 + (H - 300) * ease_out(k)],
               fill=(120, 150, 160, 200), width=4)
    img.alpha_composite(ov)

    ov, _ = overlay()
    # right column: observation (read first in Hebrew)
    label(img, t, 0.4, 20, "תצפית", (W * 0.74, 270), size=86, color=AMBER)
    label(img, t, 0.9, 20, "מה שהעיניים ראו", (W * 0.74, 355), size=38,
          color=(200, 214, 220), weight="regular")
    label(img, t, 1.7, 20, "פרשנות", (W * 0.26, 270), size=86, color=CYAN)
    label(img, t, 2.2, 20, "מה שאני חושב שזה אומר", (W * 0.26, 355), size=38,
          color=(200, 214, 220), weight="regular")

    ov2, d2 = overlay()
    for x_c, txt, start, col in ((W * 0.74, "יש לה זנב ארוך", 3.1, AMBER),
                                 (W * 0.26, "הזנב עוזר לה לאזן", 4.3, CYAN)):
        a = cue(t, start, 20, 0.5)
        if a <= 0.004:
            continue
        d2.rounded_rectangle([x_c - 340, 500, x_c + 340, 640], 18,
                             fill=(255, 255, 255, int(18 * a)),
                             outline=(*col, int(150 * a)), width=3)
        draw_text(ov2, (x_c, 570), txt, size=52, fill=WHITE, alpha=a)
    img.alpha_composite(ov2)

    ov3, _ = overlay()
    caption(ov3, t, 5.8, 3.9, "שתיהן חשובות — אבל הן לא אותו דבר",
            sub="ובמדע לא מבלבלים ביניהן", size=58, y=H - 190)
    img.alpha_composite(ov3)
    return img


def s06_question_wall(t, p, fi):
    """Sticky notes flying onto the question wall."""
    img = vgrad((28, 34, 60), (48, 56, 92)).copy()
    ov, d = overlay()
    notes = [(-380, -190, -0.16, (250, 214, 96)), (-90, -230, 0.10, (150, 226, 200)),
             (220, -180, -0.08, (246, 168, 150)), (-300, 60, 0.13, (168, 206, 250)),
             (40, 40, -0.05, (250, 214, 96)), (330, 70, 0.09, (198, 190, 250)),
             (-140, 250, 0.06, (150, 226, 200)), (210, 260, -0.12, (246, 168, 150))]
    for i, (ox, oy, rot, col) in enumerate(notes):
        a = ease_out(clamp((t - i * 0.11) / 0.5))
        if a <= 0:
            continue
        cxp, cyp = CX + ox, H / 2 + oy + (1 - a) * 260
        s = 74
        pts = [(-s, -s), (s, -s), (s, s), (-s, s)]
        c, sn = math.cos(rot), math.sin(rot)
        d.polygon([(cxp + px * c - py * sn, cyp + px * sn + py * c) for px, py in pts],
                  fill=(*col, int(245 * a)))
        draw_text(ov, (cxp, cyp), "?", size=64, fill=(40, 40, 60), alpha=a * 0.75,
                  weight="latin_bold", shadow=None)
    img.alpha_composite(ov)

    ov, _ = overlay()
    a, dy = rise(t, 0.9, 2.6, distance=24)
    draw_text(ov, (CX, 170 + dy), "קיר השאלות", size=88, fill=WHITE, alpha=a)
    draw_text(ov, (CX, H - 170), "כל שאלה שנשארה — עולה לקיר", size=46,
              weight="regular", fill=SAND, alpha=cue(t, 1.5, 2.0, 0.4))
    img.alpha_composite(ov)
    dim(img, ease_in((t - 2.6) / 0.4) if t > 2.6 else 0)
    return img


# ================================================================= ACT 2 ===
def s07_gate_a(t, p, fi):
    return gate_card(t, p, fi, "א", "מפגשים עם בעלי חיים",
                     "שער א׳ · עולמם של בעלי החיים · שפע של מינים",
                     (16, 44, 40), (28, 74, 64), TEAL)


def s08_polar_bear(t, p, fi):
    img = vgrad(ICE_TOP, ICE_BOT).copy()
    ov, d = overlay()
    for k in range(3):                                   # aurora ribbons
        pts = []
        for i in range(0, W + 1, 24):
            u = i / W
            pts.append((i, 150 + k * 70 + 60 * math.sin(u * 5 + t * 0.7 + k)))
        for i in range(W, -1, -24):
            u = i / W
            pts.append((i, 210 + k * 70 + 60 * math.sin(u * 5 + t * 0.7 + k)))
        d.polygon(pts, fill=(120, 240, 200, 38))
    img.alpha_composite(ov)

    ov, d = overlay()
    d.polygon([(0, H * 0.62), (W, H * 0.58), (W, H), (0, H)],
              fill=(168, 202, 228, 255))
    d.polygon([(0, H * 0.66), (W, H * 0.63), (W, H), (0, H)],
              fill=(198, 224, 242, 255))
    for k in range(5):                                   # ice cracks
        x0 = 120 + k * 380
        d.line([x0, H * 0.72 + k * 12, x0 + 200, H * 0.86 + k * 8],
               fill=(150, 186, 214, 200), width=4)
    bear_x = lerp(W + 300, -300, clamp(t / 8.0))
    d.ellipse([bear_x - 250, H * 0.815, bear_x + 190, H * 0.865],
              fill=(120, 158, 192, 120))                 # contact shadow
    # a slightly larger dark pass first gives the white coat a readable edge
    cr.polar_bear(d, bear_x, H * 0.74, s=1.58, phase=t * 3.2,
                  coat=(118, 156, 192), shade=(118, 156, 192))
    cr.polar_bear(d, bear_x, H * 0.74, s=1.52, phase=t * 3.2)
    img.alpha_composite(ov)

    ov, d = overlay()
    for k in range(60):                                  # snowfall
        sx = (k * 137 + t * (40 + k % 5 * 22)) % W
        sy = (k * 211 + t * (70 + k % 7 * 26)) % H
        circle(d, (sx, sy), 2 + k % 3, fill=(255, 255, 255, 140))
    img.alpha_composite(ov)

    ov, _ = overlay()
    label(img, t, 0.5, 6.6, "דוב קוטב", (W - 220, 130), size=64, color=(226, 244, 255))
    caption(ov, t, 1.2, 5.8, "אותם צרכים — סביבה אחרת",
            sub="שכבת שומן ופרווה כפולה שומרות על חום הגוף", size=56)
    img.alpha_composite(ov)
    return img


def s09_camel(t, p, fi):
    img = vgrad(DESERT_TOP, DESERT_BOT).copy()
    sun = (W * 0.22, H * 0.30)
    paste_glow(img, sun, 420, (255, 220, 150), 0.55, 2.0)
    ov, d = overlay()
    circle(d, sun, 92, fill=(255, 238, 190, 240))
    dunes(d, H * 0.66, (198, 118, 48, 255), amp=48, freq=1.3, phase=0.4)
    dunes(d, H * 0.76, (168, 92, 38, 255), amp=58, freq=1.8, phase=2.3)
    img.alpha_composite(ov)

    ov, d = overlay()
    dunes(d, H * 0.92, (120, 62, 28, 255), amp=40, freq=2.2, phase=4.1)
    # backlit by the desert sun: the camel reads as a warm silhouette
    cr.camel(d, lerp(W + 420, -420, clamp(t / 8.0)), H * 0.83,
             s=1.75, phase=t * 2.6, coat=(96, 50, 22), shade=(70, 34, 14),
             dark=(24, 12, 4))
    img.alpha_composite(ov)

    ov, d = overlay()
    for k in range(40):                                  # blown sand
        sx = (k * 173 - t * (120 + k % 6 * 40)) % (W + 200) - 100
        sy = H * 0.72 + (k * 37) % 220 + 8 * math.sin(t * 3 + k)
        d.line([sx, sy, sx + 22, sy + 2], fill=(255, 226, 178, 70), width=2)
    img.alpha_composite(ov)

    ov, _ = overlay()
    label(img, t, 0.5, 6.6, "גמל", (W - 200, 130), size=64, color=(255, 238, 208))
    caption(ov, t, 1.2, 2.9, "הדבשת אוגרת שומן — לא מים", size=60, color=(255, 232, 190),
            band=215)
    caption(ov, t, 4.4, 3.2, "והשומן עוזר לו לשרוד ימים בלי אוכל", size=54, band=215)
    img.alpha_composite(ov)
    return img


def s10_goldfish(t, p, fi):
    img = vgrad(WATER_TOP, WATER_BOT).copy()
    ov, d = overlay()
    for k in range(6):                                   # light shafts
        x0 = 140 + k * 300 + 40 * math.sin(t * 0.5 + k)
        d.polygon([(x0, 0), (x0 + 110, 0), (x0 + 250, H), (x0 + 40, H)],
                  fill=(180, 240, 255, 26))
    img.alpha_composite(ov)

    ov, d = overlay()
    for k in range(9):                                   # water plants
        bx = 70 + k * 230
        for b in range(3):
            sway = 26 * math.sin(t * 1.3 + k + b)
            pts = [(bx + b * 26, H), (bx + b * 26 + sway * 0.4, H - 140),
                   (bx + b * 26 + sway, H - 300)]
            for i in range(len(pts) - 1):
                bone(d, pts[i], pts[i + 1], 16 - b * 3, (28, 110, 96, 220))
    cr.goldfish(d, lerp(W + 300, -300, clamp(t / 7.0)),
                H * 0.52 + 60 * math.sin(t * 1.4), s=2.0, phase=t * 6.0)
    img.alpha_composite(ov)

    ov, d = overlay()
    for k in range(34):                                  # bubbles
        bx = (k * 251) % W
        by = H - ((t * (70 + k % 5 * 30) + k * 90) % (H + 120))
        r = 4 + k % 4 * 3
        circle(d, (bx + 12 * math.sin(by / 70 + k), by), r,
               fill=(210, 245, 255, 90))
        circle(d, (bx + 12 * math.sin(by / 70 + k) - r * 0.3, by - r * 0.3), r * 0.3,
               fill=(255, 255, 255, 120))
    img.alpha_composite(ov)

    ov, _ = overlay()
    label(img, t, 0.5, 5.8, "דג זהב", (W - 220, 130), size=64, color=(220, 250, 255))
    caption(ov, t, 1.2, 5.0, "נושם חמצן מומס במים",
            sub="הצורך זהה — הדרך שונה", size=58)
    img.alpha_composite(ov)
    return img


def _icon_water(d, cx, cy, r, col, a):
    d.polygon([(cx, cy - r), (cx + r * 0.78, cy + r * 0.32),
               (cx, cy + r * 0.86), (cx - r * 0.78, cy + r * 0.32)],
              fill=(*col, a))


def _icon_food(d, cx, cy, r, col, a):
    leaf = [(cx, cy - r), (cx + r * 0.72, cy - r * 0.1), (cx, cy + r * 0.86),
            (cx - r * 0.72, cy - r * 0.1)]
    d.polygon(leaf, fill=(*col, a))
    d.line([cx, cy - r * 0.8, cx, cy + r * 1.05], fill=(20, 40, 30, a), width=5)
    for k in (-1, 1):
        for j in range(1, 4):
            yy = cy - r * 0.55 + j * r * 0.36
            d.line([cx, yy, cx + k * r * 0.42, yy - r * 0.2],
                   fill=(20, 40, 30, int(a * 0.75)), width=4)


def _icon_air(d, cx, cy, r, col, a, t=0.0):
    for k in range(3):
        rr = r * (0.45 + k * 0.26)
        start = 20 + k * 40 + t * 40
        d.arc([cx - rr, cy - rr, cx + rr, cy + rr], start, start + 260,
              fill=(*col, a), width=8)


def _icon_temp(d, cx, cy, r, col, a, level=0.6):
    d.rounded_rectangle([cx - r * 0.24, cy - r, cx + r * 0.24, cy + r * 0.42],
                        r * 0.24, fill=(*col, int(a * 0.35)), outline=(*col, a), width=6)
    circle(d, (cx, cy + r * 0.6), r * 0.42, fill=(*col, a))
    top = cy + r * 0.3 - (r * 1.15) * level
    d.rounded_rectangle([cx - r * 0.1, top, cx + r * 0.1, cy + r * 0.5],
                        r * 0.1, fill=(*col, a))


def _icon_shield(d, cx, cy, r, col, a):
    d.polygon([(cx, cy - r), (cx + r * 0.82, cy - r * 0.5),
               (cx + r * 0.62, cy + r * 0.55), (cx, cy + r),
               (cx - r * 0.62, cy + r * 0.55), (cx - r * 0.82, cy - r * 0.5)],
              fill=(*col, a))


NEEDS = (("מים", _icon_water, (110, 200, 255)),
         ("מזון", _icon_food, (150, 226, 140)),
         ("אוויר", _icon_air, (200, 220, 255)),
         ("טמפרטורה", _icon_temp, (250, 170, 110)),
         ("הגנה", _icon_shield, (200, 176, 250)))


def s11_five_needs(t, p, fi):
    """Five icons, then the table that turns them into a pattern."""
    img = vgrad((12, 32, 46), (24, 62, 76)).copy()
    ov, d = overlay()
    blueprint_grid(d, 120, (90, 170, 200), 26)
    img.alpha_composite(ov)

    lift = ease_out(clamp((t - 5.6) / 1.2)) * 190
    icon_y = 430 - lift
    ov, d = overlay()
    for i, (name, icon, col) in enumerate(NEEDS):
        # right-to-left: first need on the right
        slot = 4 - i
        cxp = 260 + slot * 350
        appear = clamp((t - 0.5 - i * 0.62) / 0.7)
        if appear <= 0:
            continue
        a = ease_out(appear)
        aa = int(240 * a)
        scale = lerp(0.6, 1.0, ease_out(appear)) * (1 - lift / 900)
        circle(d, (cxp, icon_y), 96 * scale, fill=(255, 255, 255, int(16 * a)))
        circle(d, (cxp, icon_y), 96 * scale, outline=(*col, int(150 * a)), width=4)
        if icon is _icon_air:
            icon(d, cxp, icon_y, 56 * scale, col, aa, t)
        else:
            icon(d, cxp, icon_y, 56 * scale, col, aa)
        draw_text(img, (cxp, icon_y + 140 * scale), name, size=int(42 * scale),
                  fill=WHITE, alpha=a)
    img.alpha_composite(ov)

    # the wall table: rows = needs, columns = the four animals of lesson 3
    ta = ease_out(clamp((t - 6.4) / 1.1))
    if ta > 0.01:
        ov, d = overlay()
        animals = ("חולדת קנגורו", "דוב קוטב", "גמל", "דג זהב")
        x0, y0, cw, rh = 250, 480, 340, 92
        for c in range(5):
            x = x0 + c * cw
            d.line([x, y0, x, y0 + rh * 5 * ta], fill=(150, 200, 220, int(120 * ta)),
                   width=3)
        for r in range(6):
            y = y0 + r * rh
            if y > y0 + rh * 5 * ta + 2:
                break
            d.line([x0, y, x0 + cw * 4, y], fill=(150, 200, 220, int(120 * ta)), width=3)
        img.alpha_composite(ov)
        for i, name in enumerate(animals):
            # rightmost column = first animal
            xc = x0 + (3 - i) * cw + cw / 2
            label(img, t, 6.8 + i * 0.12, 20, name, (xc, y0 - 42), size=34,
                  color=(190, 230, 245))
        for r, (name, _icon, col) in enumerate(NEEDS):
            yc = y0 + r * rh + rh / 2
            label(img, t, 7.0 + r * 0.1, 20, name, (W - 180, yc), size=36, color=col)
            for c in range(4):
                ca = cue(t, 7.6 + (r * 4 + c) * 0.11, 20, 0.35)
                if ca <= 0.01:
                    continue
                xc = x0 + (3 - c) * cw + cw / 2
                ov2, d2 = overlay()
                d2.line([xc - 18, yc, xc - 4, yc + 15], fill=(*col, int(235 * ca)), width=7)
                d2.line([xc - 4, yc + 15, xc + 22, yc - 18], fill=(*col, int(235 * ca)),
                        width=7)
                img.alpha_composite(ov2)

    ov, _ = overlay()
    a, dy = rise(t, 0.2, 5.6, distance=22)
    draw_text(ov, (CX, 128 + dy), "חמשת צרכי הקיום", size=78, fill=WHITE, alpha=a)
    label(img, t, 6.6, 6.4, "טבלה — כלי לגילוי דפוס", (CX, 128), size=62,
          color=AMBER)
    img.alpha_composite(ov)
    return img


def s12_big_idea(t, p, fi):
    img = vgrad((10, 28, 40), (16, 48, 58)).copy()
    paste_glow(img, (CX, H / 2), 700, (40, 150, 170), 0.34, 2.4)
    ov, d = overlay()
    a1, dy1 = rise(t, 0.3, 5.4, distance=36, fade=0.7)
    draw_text(ov, (CX, 430 + dy1), "כולם צריכים אותו דבר.", size=88,
              fill=WHITE, alpha=a1)
    a2, dy2 = rise(t, 1.9, 3.8, distance=36, fade=0.7)
    draw_text(ov, (CX, 590 + dy2), "כל אחד משיג אותו אחרת.", size=88,
              fill=AMBER, alpha=a2)
    rule(d, CX - 240, CX + 240, 700, (t - 3.0) / 0.9, TEAL)
    label(img, t, 3.4, 2.4, "הרעיון של היחידה — בניסוח של תלמידה",
          (CX, 790), size=40, color=(190, 216, 226), weight="regular")
    img.alpha_composite(ov)
    dim(img, ease_in((t - 5.4) / 0.6) if t > 5.4 else 0)
    return img


# ================================================================= ACT 3 ===
def s13_gate_b(t, p, fi):
    return gate_card(t, p, fi, "ב", "טכנולוגיה במחשבה תחילה",
                     "שער ב׳ · מהי טכנולוגיה? · בואו נתכן! · מערכות בפעולה",
                     (26, 20, 46), (60, 44, 88), (196, 160, 255))


def s14_design(t, p, fi):
    """מצב מצוי → מצב רצוי: the engineering-design move of gate ב."""
    img = vgrad(SLATE_TOP, SLATE_BOT).copy()
    ov, d = overlay()
    blueprint_grid(d, 96, (90, 150, 190), 40, offset=t * 6)
    img.alpha_composite(ov)

    ov, d = overlay()
    # right: the problem — a wobbly, broken structure
    rx, ry = W * 0.74, H * 0.52
    a1 = ease_out(clamp((t - 0.4) / 0.8))
    if a1 > 0:
        wob = 6 * math.sin(t * 7)
        for i, (x0, y0, x1, y1) in enumerate(((-190, 130, 190, 130), (-145, 130, -95, -95),
                                              (145, 130, 64, -80), (-95, -95, 64, -80))):
            d.line([rx + x0 + wob * (i % 2), ry + y0, rx + x1 - wob * (i % 2), ry + y1],
                   fill=(230, 120, 100, int(235 * a1)), width=18)
        for k in range(3):
            circle(d, (rx - 110 + k * 110, ry - 180 + 10 * math.sin(t * 5 + k)), 10,
                   fill=(230, 120, 100, int(200 * a1)))
    # left: the designed solution — braced and stable
    lx, ly = W * 0.26, H * 0.52
    a2 = ease_out(clamp((t - 2.6) / 0.9))
    if a2 > 0:
        for x0, y0, x1, y1 in ((-190, 130, 190, 130), (-145, 130, -112, -112),
                               (145, 130, 112, -112), (-112, -112, 112, -112),
                               (-145, 130, 112, -112), (145, 130, -112, -112)):
            d.line([lx + x0, ly + y0, lx + x1, ly + y1],
                   fill=(120, 226, 190, int(235 * a2)), width=18)
    # arrow from the problem towards the solution (right → left)
    a3 = ease_out(clamp((t - 1.9) / 0.7))
    if a3 > 0:
        ax0, ax1 = rx - 270, rx - 270 - 300 * a3
        d.line([ax0, ry, ax1, ry], fill=(*CYAN, 230), width=11)
        d.polygon([(ax1 - 44, ry), (ax1 + 8, ry - 28), (ax1 + 8, ry + 28)],
                  fill=(*CYAN, 235))
    img.alpha_composite(ov)

    ov, _ = overlay()
    label(img, t, 0.8, 6.6, "מצב מצוי", (rx, ry + 250), size=58, color=(240, 150, 130))
    label(img, t, 3.0, 4.4, "מצב רצוי", (lx, ly + 250), size=58, color=(130, 236, 200))
    a, dy = rise(t, 0.2, 7.4, distance=20)
    draw_text(ov, (CX, 150 + dy), "לזהות בעיה — ולתכנן פתרון", size=72,
              fill=WHITE, alpha=a)
    caption(ov, t, 4.8, 3.0, "דרישות · אילוצים · דגם", size=58, color=CYAN)
    img.alpha_composite(ov)
    return img


def _gear(d, cx, cy, r, teeth, ang, fill, hub=(24, 34, 44)):
    pts = []
    n = teeth * 4
    tooth = r * 0.18
    for i in range(n):
        a = ang + i * math.tau / n
        rr = r + tooth if i % 4 in (1, 2) else r
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=fill)
    circle(d, (cx, cy), r * 0.30, fill=(*hub, 255))
    for k in range(5):
        a = ang * 0.5 + k * math.tau / 5
        d.line([cx + r * 0.34 * math.cos(a), cy + r * 0.34 * math.sin(a),
                cx + r * 0.74 * math.cos(a), cy + r * 0.74 * math.sin(a)],
               fill=(*hub, 200), width=max(3, int(r * 0.07)))


def s15_gears(t, p, fi):
    """Meshed gears at honest relative speeds — תמסורת."""
    img = vgrad(SLATE_TOP, SLATE_BOT).copy()
    ov, d = overlay()
    blueprint_grid(d, 96, (90, 150, 190), 34, offset=-t * 5)
    img.alpha_composite(ov)

    ov, d = overlay()
    base = t * 1.05
    g1 = (W * 0.60, H * 0.50, 210, 22)
    g2 = (g1[0] - 330, g1[1] - 120, 128, 13)
    g3 = (g1[0] + 300, g1[1] + 150, 118, 12)
    spin = ease_out(clamp(t / 1.2))
    _gear(d, g1[0], g1[1], g1[2], g1[3], base * spin, (*BRASS, 245))
    _gear(d, g2[0], g2[1], g2[2], g2[3],
          -base * spin * g1[3] / g2[3] + 0.14, (216, 226, 236, 245))
    _gear(d, g3[0], g3[1], g3[2], g3[3],
          -base * spin * g1[3] / g3[3] + 0.31, (*CYAN, 235))
    # belt drive to a small pulley
    px, py, pr = W * 0.20, H * 0.30, 70
    circle(d, (px, py), pr, fill=(216, 226, 236, 240))
    circle(d, (px, py), pr * 0.3, fill=(24, 34, 44, 255))
    d.line([px, py - pr, g2[0], g2[1] - g2[2]], fill=(40, 48, 60, 235), width=12)
    d.line([px, py + pr, g2[0], g2[1] + g2[2]], fill=(40, 48, 60, 235), width=12)
    img.alpha_composite(ov)

    ov, _ = overlay()
    a, dy = rise(t, 0.3, 9.0, distance=20)
    draw_text(ov, (CX, 140 + dy), "מערכת טכנולוגית בפעולה", size=76,
              fill=WHITE, alpha=a)
    caption(ov, t, 2.2, 3.2, "מבנה · פעולה · תמסורת", size=60, color=BRASS)
    caption(ov, t, 5.8, 3.6, "גלגל גדול מסובב גלגל קטן — מהר יותר", size=54)
    img.alpha_composite(ov)
    return img


def s16_gate_c(t, p, fi):
    return gate_card(t, p, fi, "ג", "אוויר ומים בארץ ובשמים",
                     "שער ג׳ · מזג אוויר · מצבי צבירה · מחזור המים",
                     (10, 34, 54), (22, 76, 104), CYAN)


def _particle_layout(n, mode, t):
    """Positions for the states-of-matter particle system."""
    pts = []
    cols = 8
    for i in range(n):
        col, row = i % cols, i // cols
        if mode == "solid":
            x = CX - 300 + col * 86 + 5 * math.sin(t * 9 + i)
            y = 470 + row * 86 + 5 * math.cos(t * 8 + i * 1.7)
        elif mode == "liquid":
            x = CX - 330 + col * 92 + 34 * math.sin(t * 1.9 + i * 0.6)
            y = 560 + row * 62 + 26 * math.sin(t * 2.6 + i)
        else:
            x = CX + 520 * math.sin(t * 0.9 + i * 2.399)
            y = 560 + 330 * math.sin(t * 1.15 + i * 1.77)
        pts.append((x, y))
    return pts


def s17_states(t, p, fi):
    img = vgrad((8, 30, 48), (18, 62, 84)).copy()
    ov, d = overlay()
    blueprint_grid(d, 120, (90, 170, 200), 22)
    img.alpha_composite(ov)

    # blend between the three states over the shot
    if t < 3.4:
        mode_a, mode_b, k = "solid", "solid", 0.0
    elif t < 4.4:
        mode_a, mode_b, k = "solid", "liquid", smoothstep((t - 3.4) / 1.0)
    elif t < 6.6:
        mode_a, mode_b, k = "liquid", "liquid", 0.0
    elif t < 7.6:
        mode_a, mode_b, k = "liquid", "gas", smoothstep((t - 6.6) / 1.0)
    else:
        mode_a, mode_b, k = "gas", "gas", 0.0
    pa = _particle_layout(32, mode_a, t)
    pb = _particle_layout(32, mode_b, t)

    ov, d = overlay()
    heat = clamp((t - 1.0) / 8.0)
    col = (lerp_color((104, 184, 255), (206, 224, 255), heat * 2) if heat < 0.5
           else lerp_color((206, 224, 255), (255, 148, 72), (heat - 0.5) * 2))
    for (xa, ya), (xb, yb) in zip(pa, pb):
        x, y = lerp(xa, xb, k), lerp(ya, yb, k)
        circle(d, (x, y), 22, fill=(*col, 235))
        circle(d, (x - 6, y - 7), 7, fill=(255, 255, 255, 255))
    # thermometer on the left edge
    tx, ty0, ty1 = 180, 300, 820
    d.rounded_rectangle([tx - 26, ty0, tx + 26, ty1], 26, outline=(200, 224, 240, 200),
                        width=5)
    circle(d, (tx, ty1 + 42), 46, fill=(*CORAL, 235))
    fill_y = lerp(ty1, ty0 + 30, heat)
    d.rounded_rectangle([tx - 14, fill_y, tx + 14, ty1 + 20], 14, fill=(*CORAL, 235))
    img.alpha_composite(ov)

    ov, _ = overlay()
    a, dy = rise(t, 0.2, 9.4, distance=20)
    draw_text(ov, (CX, 140 + dy), "אותו חומר — שלושה מצבים", size=74,
              fill=WHITE, alpha=a)
    label(img, t, 0.9, 2.9, "מוצק", (CX, 300), size=72, color=(150, 210, 255))
    label(img, t, 4.2, 2.5, "נוזל", (CX, 300), size=72, color=(120, 220, 230))
    label(img, t, 7.4, 2.4, "גז", (CX, 300), size=72, color=(255, 190, 140))
    img.alpha_composite(ov)
    return img


def s18_water_cycle(t, p, fi):
    img = vgrad((46, 118, 178), (156, 208, 232)).copy()
    sun = (W * 0.16, H * 0.20)
    paste_glow(img, sun, 340, (255, 236, 170), 0.70, 1.8)
    ov, d = overlay()
    circle(d, sun, 82, fill=(255, 246, 208, 255))

    # mountains on the right, sea on the left
    d.polygon([(W * 0.55, H * 0.86), (W * 0.78, H * 0.34), (W, H * 0.86)],
              fill=(74, 106, 118, 255))
    d.polygon([(W * 0.72, H * 0.86), (W * 0.90, H * 0.46), (W * 1.05, H * 0.86)],
              fill=(96, 128, 138, 255))
    d.polygon([(W * 0.755, H * 0.44), (W * 0.78, H * 0.34), (W * 0.805, H * 0.44)],
              fill=(232, 244, 252, 255))
    waves(d, H * 0.86, (26, 96, 130), 12, 3.0, t * 1.4, 255)
    waves(d, H * 0.89, (36, 126, 160), 10, 4.2, -t * 1.8, 220)

    # evaporation: droplets lifting off the sea with a fading trail
    for k in range(16):
        ph = (t * 0.5 + k * 0.17) % 1.0
        x = 110 + k * 58
        y = H * 0.86 - 420 * ph
        a = int(235 * math.sin(ph * math.pi))
        wob = 18 * math.sin(ph * 8 + k)
        r = 9 + 5 * (1 - ph)
        d.ellipse([x + wob - r, y - r * 1.5, x + wob + r, y + r * 1.5],
                  fill=(238, 250, 255, a))
    # cloud
    ca = ease_out(clamp((t - 1.6) / 1.8))
    if ca > 0:
        for ox, oy, r in ((-150, 0, 78), (-40, -42, 100), (70, -6, 86), (0, 30, 74)):
            circle(d, (CX - 60 + ox + 12 * math.sin(t * 0.7 + ox), H * 0.30 + oy),
                   r * ca, fill=(240, 246, 255, int(240 * ca)))
    # rain onto the mountain
    ra = clamp((t - 4.2) / 1.2)
    for k in range(26):
        if ra <= 0:
            break
        rx = CX - 200 + k * 34
        ry = H * 0.36 + ((t * 420 + k * 63) % (H * 0.44))
        d.line([rx, ry, rx - 5, ry + 26], fill=(180, 224, 250, int(220 * ra)), width=4)
    # runoff river back to the sea
    ka = clamp((t - 6.2) / 1.4)
    if ka > 0:
        pts = [(W * 0.80, H * 0.60), (W * 0.66, H * 0.72), (W * 0.50, H * 0.80),
               (W * 0.30, H * 0.855)]
        cut = 1 + int((len(pts) - 1) * ease_out(ka))
        d.line(pts[:cut], fill=(150, 214, 245, 235), width=14, joint="curve")
    img.alpha_composite(ov)

    ov, _ = overlay()
    a, dy = rise(t, 0.2, 10.4, distance=20)
    draw_text(ov, (CX, 130 + dy), "מחזור המים בטבע", size=76, fill=WHITE, alpha=a)
    label(img, t, 1.0, 3.0, "אידוי", (300, H * 0.60), size=50, color=(200, 236, 252))
    label(img, t, 2.6, 3.0, "התעבות", (CX - 60, H * 0.16), size=50, color=(230, 244, 255))
    label(img, t, 4.6, 3.0, "משקעים", (CX + 250, H * 0.56), size=50, color=(190, 226, 250))
    label(img, t, 6.6, 3.2, "נגר", (W * 0.60, H * 0.70), size=50, color=(170, 220, 248))
    img.alpha_composite(ov)
    dim(img, ease_in((t - 10.6) / 0.4) if t > 10.6 else 0)
    return img


# ================================================================= ACT 4 ===
def s19_gate_d(t, p, fi):
    return gate_card(t, p, fi, "ד", "מבט אל תוך הגוף",
                     "שער ד׳ · זהו גופנו · עטופים בעור · גוף בתנועה",
                     (40, 16, 32), (86, 34, 56), (255, 150, 160))


def s20_skin(t, p, fi):
    """Cross-section of skin, slowly pushing in."""
    img = vgrad((36, 18, 28), (70, 34, 44)).copy()
    zoom = lerp(1.0, 1.16, ease_out(clamp(t / 8.6), 1.6))
    ov, d = overlay()

    def Y(y):
        return H / 2 + (y - H / 2) * zoom

    bands = ((300, 430, (246, 214, 186), "אפידרמיס"),
             (430, 700, (226, 160, 140), "דרמיס"),
             (700, 900, (246, 214, 140), "רקמת שומן"))
    for y0, y1, col, _name in bands:
        d.rectangle([0, Y(y0), W, Y(y1)], fill=(*col, 255))
    for k in range(60):                                   # epidermis texture
        x = k * 34
        d.line([x, Y(300), x + 18, Y(330)], fill=(255, 240, 220, 120), width=3)

    # hair + follicle
    hx = W * 0.30
    d.line([hx, Y(80), hx - 26, Y(300)], fill=(60, 40, 34, 255), width=9)
    d.line([hx - 26, Y(300), hx - 4, Y(560)], fill=(60, 40, 34, 255), width=11)
    circle(d, (hx - 4, Y(575)), 26, fill=(90, 60, 48, 255))
    # sweat gland: coil in the fat layer with a duct to the surface
    gx = W * 0.62
    duct = [(gx, Y(300)), (gx + 24, Y(420)), (gx - 10, Y(540)), (gx + 18, Y(640))]
    for i in range(len(duct) - 1):
        bone(d, duct[i], duct[i + 1], 12, (150, 200, 230, 255))
    for k in range(9):
        a = k * 0.9 + t * 0.8
        circle(d, (gx + 18 + 46 * math.cos(a), Y(700) + 30 * math.sin(a)), 13,
               fill=(150, 200, 230, 255))
    # blood vessel
    vpts = [(0, Y(640))]
    for i in range(0, W + 1, 40):
        vpts.append((i, Y(640) + 22 * math.sin(i / 130 + t * 0.9)))
    d.line(vpts, fill=(206, 70, 70, 255), width=12, joint="curve")
    # a sweat droplet rising to the surface
    ph = (t * 0.42) % 1.0
    circle(d, (gx + 18, lerp(Y(660), Y(280), ph)), 10,
           fill=(200, 236, 255, int(230 * math.sin(ph * math.pi))))
    img.alpha_composite(ov)

    ov, _ = overlay()
    for i, (y0, y1, col, name) in enumerate(bands):
        label(img, t, 1.0 + i * 0.6, 20, name, (W - 260, Y((y0 + y1) / 2)),
              size=44, color=(60, 30, 30))
    a, dy = rise(t, 0.2, 8.4, distance=20)
    draw_text(ov, (CX, 140 + dy), "עטופים בעור", size=80, fill=WHITE, alpha=a)
    caption(ov, t, 4.6, 3.8, "מבנה שמתאים לתפקוד", size=58, y=H - 120)
    img.alpha_composite(ov)
    return img


def s21_joints(t, p, fi):
    """Hinge and ball-and-socket, side by side and moving."""
    img = vgrad((26, 14, 30), (58, 30, 52)).copy()
    ov, d = overlay()
    blueprint_grid(d, 120, (200, 150, 190), 24)
    img.alpha_composite(ov)

    ov, d = overlay()
    # right: hinge (elbow)
    hx, hy = W * 0.72, H * 0.52
    swing = math.radians(lerp(15, 135, (math.sin(t * 1.7) + 1) / 2))
    upper_end = (hx - 190, hy - 40)
    bone(d, (hx + 30, hy - 150), upper_end, 40, (*BONE, 245))
    fore = limb(upper_end, 230, math.pi - swing)
    bone(d, upper_end, fore, 34, (*BONE, 245))
    circle(d, upper_end, 34, fill=(*CORAL, 235))
    d.arc([upper_end[0] - 120, upper_end[1] - 120, upper_end[0] + 120, upper_end[1] + 120],
          180, 180 + math.degrees(swing), fill=(255, 210, 120, 200), width=6)

    # left: ball and socket (shoulder)
    bx, by = W * 0.28, H * 0.50
    ang = math.sin(t * 1.25) * 1.05
    img.alpha_composite(ov)

    # range-of-motion arc, drawn under the bone on its own layer so the
    # translucent wedge cannot overwrite the opaque arm
    ov, d = overlay()
    d.pieslice([bx - 258, by - 258, bx + 258, by + 258],
               math.degrees(math.pi / 2 - 1.05), math.degrees(math.pi / 2 + 1.05),
               fill=(206, 226, 255, 34))
    d.arc([bx - 250, by - 250, bx + 250, by + 250],
          math.degrees(math.pi / 2 - 1.05), math.degrees(math.pi / 2 + 1.05),
          fill=(255, 210, 120, 200), width=6)
    img.alpha_composite(ov)

    ov, d = overlay()
    d.arc([bx - 108, by - 108, bx + 108, by + 108], 196, 344, fill=(*BONE, 245),
          width=30)                                      # socket (scapula cup)
    circle(d, (bx, by), 58, fill=(*CORAL, 235))          # head of the humerus
    arm = limb((bx, by), 250, math.pi / 2 + ang)
    bone(d, (bx, by), arm, 36, (*BONE, 245))
    img.alpha_composite(ov)

    ov, _ = overlay()
    label(img, t, 0.8, 8.4, "מפרק ציר — מרפק", (hx, H * 0.80), size=52, color=WHITE)
    label(img, t, 2.0, 7.2, "מפרק כדור־שקע — כתף", (bx, H * 0.80), size=52, color=WHITE)
    a, dy = rise(t, 0.2, 9.4, distance=20)
    draw_text(ov, (CX, 140 + dy), "מפרקים בתנועה", size=78, fill=WHITE, alpha=a)
    caption(ov, t, 5.6, 3.6, "אותו שלד — פתרונות תנועה שונים", size=54,
            y=H - 110)
    img.alpha_composite(ov)
    return img


def s22_xray_run(t, p, fi):
    img = vgrad(XRAY_TOP, XRAY_BOT).copy()
    paste_glow(img, (CX, H * 0.62), 620, (40, 110, 200), 0.40, 2.4)
    ov, d = overlay()
    for k in range(30):                                   # speed streaks
        y = 120 + k * 32
        x0 = (W + 400) - ((t * 900 + k * 250) % (W + 900))
        d.line([x0, y, x0 + 260, y], fill=(120, 190, 255, 40), width=3)
    img.alpha_composite(ov)

    ov, d = overlay()
    x = lerp(-260, W + 260, ease_out(clamp((t - 0.2) / 9.4), 1.05))
    for k in range(4):                                    # after-images
        cr.skeleton_runner(d, x - 130 * (k + 1), H * 0.62, s=1.5, phase=t * 7.2 - 0.34 * (k + 1),
                           alpha=max(0, 60 - k * 15))
    cr.skeleton_runner(d, x, H * 0.62, s=1.5, phase=t * 7.2, alpha=255)
    img.alpha_composite(ov)
    paste_glow(img, (x, H * 0.55), 240, (150, 210, 255), 0.28, 2.4)

    ov, _ = overlay()
    a, dy = rise(t, 0.3, 10.0, distance=20)
    draw_text(ov, (CX, 150 + dy), "גוף בתנועה", size=84, fill=WHITE, alpha=a)
    caption(ov, t, 2.0, 3.4, "שלד · מפרקים · שרירים", size=60, color=BONE)
    caption(ov, t, 6.2, 3.6, "כל תנועה שאתם עושים — היא מערכת", size=54)
    img.alpha_composite(ov)
    return img


def s23_finale(t, p, fi):
    img = vgrad((10, 14, 40), (28, 34, 74)).copy()
    ov, d = overlay()
    draw_stars(d, t, 0.7, count=240, seed=21)
    img.alpha_composite(ov)
    paste_glow(img, (CX, H * 0.52), 700, (70, 100, 200), 0.34, 2.6)

    ov, d = overlay()
    a1, dy1 = rise(t, 0.4, 11.0, distance=40, fade=0.9)
    draw_text(ov, (CX, 330 + dy1), "מדעים · כיתה ד׳", size=140, fill=WHITE, alpha=a1)
    rule(d, CX - 340, CX + 340, 440, (t - 1.4) / 1.0, AMBER)
    a2, dy2 = rise(t, 1.8, 9.4, distance=30, fade=0.9)
    draw_text(ov, (CX, 530 + dy2), "לצפות · לנמק · לגלות", size=76,
              fill=SAND, alpha=a2)

    a3 = cue(t, 3.6, 7.6, 0.9)
    if a3 > 0.004:
        d.rounded_rectangle([CX - 700, 660, CX + 700, 850], 26,
                            fill=(255, 255, 255, int(16 * a3)),
                            outline=(*AMBER, int(150 * a3)), width=3)
        draw_text(ov, (CX, 755), "במדע, נימוק טוב שווה יותר מניחוש מוצלח",
                  size=62, fill=WHITE, alpha=a3)
    a4 = cue(t, 6.6, 4.6, 0.8)
    draw_text(ov, (CX, 950), "שנה טובה — נתחיל לחקור", size=48, weight="regular",
              fill=(200, 216, 255), alpha=a4)
    img.alpha_composite(ov)
    dim(img, ease_in((t - 10.4) / 1.6) if t > 10.4 else 0)
    return img
