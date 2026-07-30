# Bug catalogue — symptom → cause → fix

Everything here was hit in production on a real 3-minute Hebrew film. Ordered by
how much time each one costs before you notice it.

## Contents

- [Text](#text)
- [Rendering and compositing](#rendering-and-compositing)
- [Encoding and file size](#encoding-and-file-size)
- [Composition and motion](#composition-and-motion)
- [Delivery](#delivery)
- [Pre-render checklist](#pre-render-checklist)

---

## Text

### Hebrew renders mirrored, but "looks about right"

**Symptom.** Captions look like Hebrew and you can *almost* read them. Reviewing
frames by eye, you keep concluding it is fine.

**Cause.** Pillow wheels ship with Raqm, which applies the BiDi algorithm during
layout. Passing the string through `python-bidi.get_display()` first reverses it
a second time, producing logical order on screen.

**Fix.** Pick exactly one owner of ordering:

```python
# option A — Pillow owns it (no font fallback available)
draw.text(xy, logical_string, font=f, direction="rtl")

# option B — you own it (needed for font fallback)
font = ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.BASIC)
draw.text(xy, get_display(logical_string), font=font)
```

**Detection.** `scripts/rtl_check.py`. Do not trust visual inspection — a fluent
reader re-orders mirrored text unconsciously. This is the single highest-value
check in the whole pipeline; a mirrored film is a total loss.

### Punctuation and digits render as empty boxes

**Symptom.** `?`, `—`, `·`, `,`, `.`, `5` appear as tofu rectangles.

**Cause.** Hebrew-only faces. `NotoSansHebrew-Bold.ttf` covers the Hebrew block,
geresh and gershayim, and the space — nothing else. Culmus faces are similar.

**Fix.** Per-run font fallback: read each font's cmap once with `fontTools`,
split the visual-order line into runs by coverage, draw each run with a font that
has the glyph, and advance x by `font.getlength(run)`. `scripts/hebrew_text.py`
implements this, including per-line widths so centring and shadows still work.

### Multi-line strings come out in the wrong line order

**Cause.** BiDi is a per-paragraph algorithm. Feeding it a string with embedded
newlines can reorder the lines themselves.

**Fix.** Split on `\n` first, reorder each line independently, then stack them
using the font's ascent/descent for line height.

### Right-to-left applies to layout, not only to glyphs

The first icon in a row, the first column of a table, the "before" state in a
before→after diagram, and the primary column of a two-column comparison all
belong on the **right**. Build index → x-position as `x0 + (n - 1 - i) * step`.

---

## Rendering and compositing

### Translucent shapes cut holes in solid artwork

**Symptom.** A dark fan behind a swinging limb. Grey speckles on a white animal
during snowfall. A "dirty" patch on a solid-coloured body.

**Cause.** `ImageDraw` writes pixels; it does not blend them. Drawing
`fill=(r, g, b, 70)` over an area already at alpha 255 *replaces* it with alpha
70, so the background shows through the object.

**Fix.** One layer per transparency level, composited in order with
`Image.alpha_composite`. Opaque artwork on its own layer; particles, glows,
motion trails and range-of-motion wedges on separate layers above or below it.
Make internal highlights and shading opaque colours rather than low-alpha
overlays of the same hue.

### A loop variable shadows a module import

**Symptom.** `AttributeError: 'int' object has no attribute 'kangaroo_rat'`.

**Cause.** `for cx, cy, cr in craters:` inside a function that also uses
`import creatures as cr`. Python treats `cr` as local for the whole function.

**Fix.** Rename the loop variable. Worth a quick AST scan across the project:
collect module-level import names, then flag any function whose assigned names
intersect them.

### Everything is slow

Cache anything static — gradients, star fields, vignette masks, glow sprites —
with `functools.lru_cache`, returning an image you `.copy()` per frame. Build
gradients with numpy broadcasting, never per-pixel Python. Prefer Pillow's C
primitives (`alpha_composite`, `polygon`, `line(joint="curve")`) over anything
you write yourself. Gaussian blur on a full 1080p frame costs ~50 ms — use it
sparingly, not every frame.

---

## Encoding and file size

### The finished file is enormous

**Symptom.** 3 minutes of 1080p at CRF 20 → 148 MB.

**Cause.** Film grain. Per-frame random noise is uncorrelated between frames and
destroys inter-frame prediction; the encoder spends its whole budget on it.

**Fix.** Lower the grain amplitude first (alpha 9 → 4 took the same film to
43 MB and looks identical at playback speed), then raise CRF. Rendering with a
handful of pre-baked grain tiles cycled per frame is cheaper than fresh noise and
compresses slightly better.

### The pipeline runs out of disk

5,400 raw 1080p frames is ~33 GB. Stream `img.tobytes()` into
`ffmpeg -f rawvideo -pix_fmt rgb24 -i pipe:0` and never touch disk.

### Iterating takes minutes per change

Encode one ffmpeg per shot in a process pool, then concatenate with `-c copy`.
Fixing one scene becomes: re-encode that shot, reassemble. 60 seconds instead of
6 minutes. Keep encoder settings byte-identical across shots or concat fails, and
refuse to assemble if any shot's part file is missing.

---

## Composition and motion

| Symptom | Cause | Fix |
|---|---|---|
| Subject invisible | White subject on white background | Draw a slightly larger pass in a contrasting colour underneath, plus a contact shadow |
| Caption sits on top of the action | Fixed lower-third caption + subject crossing the lower third | Move the caption to the upper third for that shot |
| Animal moonwalks | Local coordinates face one way, motion goes the other | Face the subject one way in local coords, flip via the transform, and tie the flip to the direction of travel |
| Shot ends on an empty frame | `ease_out` over a crossing covers most distance early | Constant speed across the full shot duration, entering and exiting just off-frame |
| Particles turn grey or green mid-transition | RGB interpolation blue→orange passes through grey | Route the ramp through a light neutral or a deliberate mid-hue |
| Icon overlaps the title | Elements animating into a shared band | Lay out titles, icons and tables in explicit non-overlapping bands and check the arithmetic |
| Grid has a stray empty row | Row/column counts drawn from different expressions | Derive both from the same count |

---

## Delivery

- Verify the **finished MP4**, not the renderer: `ffprobe` for exact duration,
  resolution, fps, and the presence of both a video and an **audio** stream.
- Extract frames from that file at a dozen timestamps and look at them. Bugs fixed
  in code but never re-encoded are invisible until you do this.
- Chat/upload limits are typically ~30 MB. Keep the master and send a transcode
  (`-crf 27 -preset slow`) as the viewing copy.
- On private repos, `raw.githubusercontent.com` links fail without a token — give
  the `github.com/.../blob/...` page link instead.

---

## Pre-render checklist

Before committing to thousands of frames:

1. `scripts/rtl_check.py` passes.
2. Every string with punctuation or digits has been rendered once and inspected.
3. One frame from every shot has been rendered and viewed.
4. The timeline's durations sum to the target runtime (assert it).
5. Grain amplitude is low; a 10-second test encode extrapolates to an acceptable
   file size.
6. The soundtrack has no dead air and its section levels are within ~2×.
