"""Procedurally drawn animals and body parts.

Each creature is stylised but anatomically honest enough for a science class:
the camel gets a fat hump (not a water tank), the kangaroo rat gets the long
tufted tail and oversized hind legs that make it a desert survivor.
"""

import math

from draw import bone, circle, limb, xform


def _ellipse_pts(cx, cy, rx, ry, n=26):
    return [(cx + rx * math.cos(a), cy + ry * math.sin(a))
            for a in (i * math.tau / n for i in range(n))]


def _place(points, x, y, s, rot=0.0, flip=False):
    return xform(points, x, y, s, rot, flip)


# ------------------------------------------------------- kangaroo rat ------
def kangaroo_rat(d, x, y, s=1.0, phase=0.0, fur=(228, 190, 138),
                 shade=(150, 112, 70), dark=(38, 30, 26), flip=False):
    """Side view, mid-hop. `phase` drives the hop cycle."""
    hop = abs(math.sin(phase))
    y -= 78 * s * hop
    tilt = -0.22 * math.cos(phase)

    def P(pts):
        return _place(pts, x, y, s, tilt, flip)

    # tail: long, thin, with a tuft — the balance organ the lesson talks about
    tail = [(48, -6), (96, -26 - 16 * hop), (140, -56 - 26 * hop), (168, -92 - 30 * hop)]
    tp = P(tail)
    for i in range(len(tp) - 1):
        bone(d, tp[i], tp[i + 1], 9 * s, (*shade, 255))
    tuft = P(_ellipse_pts(176, -104 - 32 * hop, 22, 14))
    d.polygon(tuft, fill=(*fur, 255))

    # hind leg — folded when airborne, extended on push-off
    ext = 0.45 + 0.55 * (1 - hop)
    knee = P([(26, 30)])[0]
    ankle = P([(46 * ext + 10, 62)])[0]
    toe = P([(6, 78)])[0]
    bone(d, knee, ankle, 15 * s, (*shade, 255))
    bone(d, ankle, toe, 11 * s, (*shade, 255))

    d.polygon(P(_ellipse_pts(0, 0, 62, 45)), fill=(*fur, 255))          # body
    d.polygon(P(_ellipse_pts(16, 16, 40, 26)), fill=(*shade, 70))        # belly shade

    fore = P([(-34, 20)])[0]
    paw = P([(-52, 40 - 8 * hop)])[0]
    bone(d, fore, paw, 8 * s, (*shade, 255))

    # ears — oversized, a desert-heat adaptation worth seeing
    for ear_y, ear_ang in ((-54, -0.55), (-46, -0.18)):
        cx, cy = P([(-46, ear_y)])[0]
        d.polygon(_place(_ellipse_pts(0, 0, 13, 27), cx, cy, s, ear_ang, flip),
                  fill=(*fur, 255))

    d.polygon(P(_ellipse_pts(-58, -16, 33, 29)), fill=(*fur, 255))       # head
    d.polygon(P(_ellipse_pts(-84, -6, 15, 12)), fill=(*fur, 255))        # snout
    eye = P([(-70, -22)])[0]
    circle(d, eye, 6.5 * s, fill=(*dark, 255))
    circle(d, (eye[0] - 2 * s, eye[1] - 2 * s), 2.2 * s, fill=(255, 255, 255, 235))
    nose = P([(-96, -2)])[0]
    circle(d, nose, 3.4 * s, fill=(*dark, 255))
    for k in (-1, 0, 1):                                                  # whiskers
        tip = P([(-140, -6 + k * 14)])[0]
        d.line([nose, tip], fill=(255, 255, 255, 90), width=max(1, int(1.6 * s)))


# ----------------------------------------------------------- polar bear ----
def polar_bear(d, x, y, s=1.0, phase=0.0, coat=(243, 248, 255),
               shade=(196, 216, 236), dark=(30, 44, 62), flip=False):
    def P(pts):
        return _place(pts, x, y, s, 0.0, flip)

    swing = math.sin(phase)
    for i, (hx, sgn, depth) in enumerate(((-52, 1, 0), (-40, -1, 1), (48, -1, 0), (60, 1, 1))):
        col = shade if depth else coat
        hip = P([(hx, 34)])[0]
        knee = limb(hip, 42 * s, math.pi / 2 + 0.42 * swing * sgn)
        paw = limb(knee, 40 * s, math.pi / 2 - 0.3 * swing * sgn)
        bone(d, hip, knee, 24 * s, (*col, 255))
        bone(d, knee, paw, 20 * s, (*col, 255))
        d.polygon(_place(_ellipse_pts(0, 0, 18, 11), *paw, s, 0, flip), fill=(*col, 255))

    d.polygon(P(_ellipse_pts(0, 0, 96, 52)), fill=(*coat, 255))           # body
    d.polygon(P(_ellipse_pts(24, 26, 62, 22)), fill=(*shade, 55))
    d.polygon(P(_ellipse_pts(-70, -14, 40, 33)), fill=(*coat, 255))       # shoulder/neck
    d.polygon(P(_ellipse_pts(-108, -22, 34, 27)), fill=(*coat, 255))      # head
    d.polygon(P(_ellipse_pts(-136, -14, 20, 15)), fill=(*coat, 255))      # muzzle
    d.polygon(P(_ellipse_pts(-98, -46, 11, 10)), fill=(*coat, 255))       # ear
    eye = P([(-120, -28)])[0]
    circle(d, eye, 4.6 * s, fill=(*dark, 255))
    circle(d, P([(-152, -12)])[0], 5.0 * s, fill=(*dark, 255))            # nose


# ---------------------------------------------------------------- camel ----
def camel(d, x, y, s=1.0, phase=0.0, coat=(212, 160, 98),
          shade=(168, 118, 66), dark=(48, 32, 20), flip=False):
    def P(pts):
        return _place(pts, x, y, s, 0.0, flip)

    swing = math.sin(phase)
    for hx, sgn in ((-46, 1), (-34, -1), (54, -1), (66, 1)):
        col = coat if sgn > 0 else shade
        hip = P([(hx, 28)])[0]
        knee = limb(hip, 62 * s, math.pi / 2 + 0.36 * swing * sgn)
        hoof = limb(knee, 58 * s, math.pi / 2 - 0.24 * swing * sgn)
        bone(d, hip, knee, 17 * s, (*col, 255))
        bone(d, knee, hoof, 13 * s, (*col, 255))

    d.polygon(P(_ellipse_pts(0, 0, 92, 44)), fill=(*coat, 255))           # barrel
    d.polygon(P(_ellipse_pts(4, -40, 46, 34)), fill=(*coat, 255))         # hump (fat!)
    neck_base = P([(-70, -18)])[0]
    head_base = P([(-116, -96)])[0]
    bone(d, neck_base, head_base, 30 * s, (*coat, 255))
    d.polygon(_place(_ellipse_pts(0, 0, 30, 20), *head_base, s, -0.35, flip),
              fill=(*coat, 255))
    muzzle = P([(-146, -104)])[0]
    d.polygon(_place(_ellipse_pts(0, 0, 18, 13), *muzzle, s, -0.25, flip),
              fill=(*coat, 255))
    d.polygon(_place(_ellipse_pts(0, 0, 8, 12), *P([(-104, -118)])[0], s, -0.2, flip),
              fill=(*shade, 255))                                          # ear
    circle(d, P([(-126, -108)])[0], 4.6 * s, fill=(*dark, 255))            # eye
    tail_a = P([(88, -8)])[0]
    tail_b = P([(120, 34 + 8 * swing)])[0]
    bone(d, tail_a, tail_b, 7 * s, (*shade, 255))


# ------------------------------------------------------------- goldfish ----
def goldfish(d, x, y, s=1.0, phase=0.0, body=(244, 148, 52),
             fin=(250, 190, 110), dark=(40, 26, 16), flip=False):
    wag = math.sin(phase)

    def P(pts, rot=0.0):
        return _place(pts, x, y, s, rot, flip)

    tail_root = P([(52, 0)])[0]
    for spread, alpha in ((0.55, 210), (0.28, 150)):
        tip_up = P([(112, -46 * spread + 30 * wag)])[0]
        tip_dn = P([(112, 46 * spread + 30 * wag)])[0]
        d.polygon([tail_root, tip_up, P([(92, 0 + 18 * wag)])[0], tip_dn],
                  fill=(*fin, alpha))
    d.polygon(P(_ellipse_pts(0, 0, 58, 34)), fill=(*body, 255))            # body
    d.polygon(P(_ellipse_pts(-6, 14, 38, 18)), fill=(250, 186, 112, 255))
    d.polygon([P([(6, -32)])[0], P([(46, -60 - 8 * wag)])[0], P([(40, -26)])[0]],
              fill=(*fin, 215))                                            # dorsal
    d.polygon([P([(-4, 26)])[0], P([(28, 58 + 8 * wag)])[0], P([(34, 22)])[0]],
              fill=(*fin, 190))                                            # pelvic
    d.polygon(_place(_ellipse_pts(0, 0, 20, 12), *P([(-16, 12)])[0], s, 0.5 + 0.3 * wag,
                     flip), fill=(*fin, 200))                              # pectoral
    eye = P([(-40, -8)])[0]
    circle(d, eye, 8 * s, fill=(255, 255, 255, 240))
    circle(d, eye, 4.4 * s, fill=(*dark, 255))
    gill = P([(-24, -4)])[0]
    d.arc([gill[0] - 12 * s, gill[1] - 20 * s, gill[0] + 12 * s, gill[1] + 20 * s],
          250, 110, fill=(206, 112, 34, 255), width=max(2, int(3 * s)))


# ------------------------------------------------------- running skeleton --
def skeleton_runner(d, x, y, s=1.0, phase=0.0, col=(207, 233, 255), alpha=255):
    """X-ray style run cycle: skull, ribs, spine, pelvis, four limbs."""
    c = (*col, alpha)
    bob = 6 * s * math.sin(phase * 2)
    hip = (x, y + bob)
    neck = (x - 4 * s, y - 86 * s + bob)
    skull = (x - 8 * s, y - 118 * s + bob)

    bone(d, hip, neck, 11 * s, c)                                          # spine
    for i in range(5):                                                     # ribs
        ry = y - (30 + i * 13) * s + bob
        rw = (44 - i * 4) * s
        d.arc([x - rw, ry - 13 * s, x + rw, ry + 13 * s], 200, 340,
              fill=c, width=max(2, int(4 * s)))
    d.ellipse([skull[0] - 21 * s, skull[1] - 23 * s, skull[0] + 21 * s, skull[1] + 21 * s],
              outline=c, width=max(2, int(5 * s)))
    d.line([hip[0] - 26 * s, hip[1], hip[0] + 26 * s, hip[1]], fill=c,
           width=max(3, int(9 * s)))                                       # pelvis

    for side, ph in ((1, 0.0), (-1, math.pi)):
        a = phase + ph
        # legs
        thigh_ang = math.pi / 2 + 0.85 * math.sin(a)
        knee = limb(hip, 60 * s, thigh_ang)
        shin_ang = thigh_ang + 0.75 * (1 + math.sin(a - 1.1))
        foot = limb(knee, 58 * s, min(shin_ang, math.pi / 2 + 1.15))
        toe = (foot[0] + 20 * s, foot[1] + 6 * s)
        w = 9 * s if side > 0 else 7 * s
        bone(d, hip, knee, w, c)
        bone(d, knee, foot, w * 0.85, c)
        bone(d, foot, toe, w * 0.6, c)
        # arms
        sh = (neck[0], neck[1] + 12 * s)
        up_ang = math.pi / 2 - 0.95 * math.sin(a)
        elbow = limb(sh, 46 * s, up_ang)
        hand = limb(elbow, 44 * s, up_ang - 0.9)
        bone(d, sh, elbow, w * 0.72, c)
        bone(d, elbow, hand, w * 0.62, c)
