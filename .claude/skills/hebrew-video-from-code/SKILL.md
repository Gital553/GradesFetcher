---
name: hebrew-video-from-code
description: Build a real MP4 video — trailer, explainer, lesson intro, animated title sequence — by rendering frames from code with Pillow/numpy and encoding with ffmpeg, with correct Hebrew (RTL) typography. Use this whenever the user asks for a סרטון, קדימון, טריילר, אנימציה, סרטון הסבר, כתוביות בעברית, or any video/animation containing Hebrew or Arabic text, and also whenever they hand you a video prompt written for Sora/Veo/Runway but no such generator is available in the environment — this skill is the way to actually deliver a playable file instead of a script. Also use it when Hebrew text renders mirrored, reversed, or as empty boxes in generated images or video frames, and when planning a hybrid pipeline where AI-generated footage needs Hebrew titles composited on top.
---

# Hebrew video, rendered from code

You can produce a genuinely good 1080p video with nothing but Pillow, numpy and
ffmpeg. A 3-minute film is ~5,400 frames; on 4 cores that is a handful of
minutes. The output looks like motion graphics — flat vector shapes, kinetic
typography, procedural illustration — which is exactly the right register for
classroom material, explainers and title sequences.

The hard parts are never the animation. They are (1) Hebrew coming out mirrored,
(2) transparency silently punching holes in your artwork, and (3) discovering at
the end that the file is 150 MB. All three are solved below.

## Start here

1. **Write the timeline first**, as data: a list of `(scene_function, duration,
   fade_in, fade_out)`. Everything else derives from it — total runtime, frame
   indices, which shot to re-render. Assert the total equals the target runtime.
2. **Each shot is a pure function** `f(t, p, frame_index) -> RGBA image`, where
   `t` is seconds since the shot started and `p` is progress 0→1. Pure functions
   mean you can render any single frame instantly for inspection, which is the
   whole QA loop.
3. **Copy `scripts/hebrew_text.py` into the project** and route every string
   through it. Do not hand-roll RTL — see the bug below.
4. **Copy `scripts/render_pipeline.py`** as the encoder skeleton. It encodes
   shots in parallel, one ffmpeg per shot, streaming raw frames over a pipe, then
   concatenates without re-encoding and muxes audio.
5. **Look at your frames.** Render single timestamps to PNG and actually view
   them. Then, at the end, extract frames from the *finished MP4* and view those
   too — the deliverable is the file, not the renderer.

## The Hebrew bug that will get you

Pillow built with Raqm (`PIL.features.check('raqm')` → `True`, which is the norm
for modern wheels) **runs the BiDi algorithm itself**. If you also pass text
through `python-bidi`'s `get_display()`, the string is reversed twice and every
line renders mirrored. It still *looks* like plausible Hebrew at a glance, which
is why this survives casual review.

Two consistent ways out:

- **Let Pillow do it**: pass the logical string with `direction="rtl"`. Simplest,
  but you get no font fallback (see below).
- **Do it yourself** (what `scripts/hebrew_text.py` does): load fonts with
  `layout_engine=ImageFont.Layout.BASIC` to switch Raqm off, reorder once with
  `get_display()`, and then you own the layout — which is what makes per-run font
  fallback possible. Hebrew needs no glyph shaping, so BASIC costs nothing.

Never mix the two.

**Verify by pixels, not by eye.** Reading Hebrew off a rendered image is
unreliable — you will "auto-correct" mirrored text while reading it. Run
`scripts/rtl_check.py`, which renders `אבג`, renders `ג` alone, and asserts the
leftmost glyph matches gimel (the *last* logical letter must sit leftmost). Run
it once per project before rendering thousands of frames.

## Hebrew fonts have no punctuation

`NotoSansHebrew-*.ttf` is a Hebrew-only face: no comma, no period, no question
mark, no digits, no `·`, no `—`. Any of those render as tofu boxes. Culmus fonts
have the same gap.

`hebrew_text.py` handles this by splitting each visual-order line into runs by
glyph coverage (read from the font's cmap with `fontTools`) and drawing each run
with a font that actually has the glyph — Hebrew runs in Noto, punctuation and
digits in DejaVu. Widths are summed per run so centring still works.

Getting fonts: `apt-get install -y fonts-noto-core culmus`. Google Fonts over
raw.githubusercontent is often blocked by network policy; don't count on it.

## Transparency punches holes

`ImageDraw` **overwrites** the pixels it touches — it does not alpha-blend. Draw
a shape at alpha 70 over an opaque shape on the same layer and you cut a
translucent hole through it. Symptoms: dark fans behind moving limbs, speckles on
white subjects, "dirty" patches on solid bodies.

The rule: **one layer per transparency level, composited in order.**

```python
img = background.copy()                       # RGBA
ov = Image.new("RGBA", SIZE, (0, 0, 0, 0))    # opaque artwork
d = ImageDraw.Draw(ov); draw_the_subject(d)
img.alpha_composite(ov)

ov = Image.new("RGBA", SIZE, (0, 0, 0, 0))    # translucent pass: snow, dust,
d = ImageDraw.Draw(ov); draw_the_particles(d) # bubbles, glows, motion trails
img.alpha_composite(ov)
```

Highlights and shading *inside* an opaque object should be opaque colours, not
low-alpha overlays of the same colour.

## Size and speed

- **Film grain is the single biggest cost.** Per-frame noise defeats inter-frame
  prediction. At a grain alpha of ~9 a 3-minute 1080p cut came out at 148 MB; at
  alpha 4 with CRF 21 the same film was 43 MB and looks the same. Tune grain
  before you tune CRF.
- **Never write frames to disk.** 5,400 raw 1080p frames is ~33 GB. Stream
  `img.tobytes()` into `ffmpeg -f rawvideo -pix_fmt rgb24 -i pipe:0`.
- **Parallelise by shot, not by frame.** One ffmpeg per shot avoids shipping raw
  frames between processes, and gives you free incremental re-rendering: fix one
  scene, re-encode that shot, concatenate all shots with `-c copy`. Keep encoder
  settings identical across shots or concat will fail.
- Cache anything static (gradients, star fields, vignette, glow sprites) with
  `functools.lru_cache` and `.copy()` per frame. Build gradients in numpy, never
  per-pixel Python.

## Composition mistakes that only show up on screen

These cost real re-renders; check for them while reviewing frames.

- **Subject vs background contrast.** A white polar bear on white ice is
  invisible. Fix by drawing the subject twice — a slightly larger pass in a
  contrasting colour, then the real one on top — plus a contact shadow.
- **Captions collide with the action.** If the subject crosses the lower third,
  move the caption to the upper third rather than fighting it with a scrim.
- **Facing direction.** Define creatures in local coordinates facing one way and
  flip via the transform. If it moves right-to-left, it must face left, or it
  moonwalks.
- **Ease-out empties the frame.** An object crossing with `ease_out` covers most
  of the distance early and leaves ~1.5 s of empty shot before the cut. For a
  crossing that should last the whole shot, use constant speed over the full
  duration.
- **Colour ramps through grey.** Interpolating blue→orange in RGB passes through
  grey. Route through a light neutral or a deliberate mid-hue instead.
- **Right-to-left ordering applies to layout, not just text.** The first item in
  a row, the first table column, the "before" side of a before→after arrow all
  belong on the **right**.

## Audio

Synthesise it; don't hunt for music files. The `video-soundtrack` skill has a
small numpy synth (`Track`, `bowed`, `pluck`, `room`, `melody`) that is plenty for
a four-movement score. Build one movement per act, keep section RMS within ~2× of
each other, check for dead air in 5-second windows, then mux:

```bash
ffmpeg -i silent.mp4 -i track.wav -c:v copy -c:a aac -b:a 192k \
       -movflags +faststart -shortest out.mp4
```

Verify the result with `ffprobe`: exact duration, resolution, fps, **and that an
audio stream exists** — a silent "finished" film is an easy miss.

## Delivering

Chat upload limits are small (~30 MB). Keep the master in the repo and send a
transcoded viewing copy (`-crf 27 -preset slow` keeps 1080p and roughly quarters
the size). If the file is pushed to git, give a browsable link, not only a raw
URL — raw links fail on private repos.

## Going further

- `references/pitfalls.md` — the full bug catalogue with symptoms, causes and
  fixes, including a pre-render checklist. Read it when something looks wrong on
  screen and you want the diagnosis fast.
- `references/ai-video-and-tts.md` — how to slot in AI-generated footage (Sora,
  Veo) and real narration (Gemini / Google Cloud TTS) without giving up correct
  Hebrew typography, and why the audio must be generated *before* the timeline is
  locked. Read it when the user asks for photoreal footage or a spoken voiceover.
