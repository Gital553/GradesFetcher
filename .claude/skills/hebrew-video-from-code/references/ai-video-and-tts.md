# Adding AI footage (Sora / Veo) and real narration (Gemini TTS)

The code-rendered pipeline is deterministic, free, offline and gives pixel-exact
Hebrew. AI generation gives photoreal footage and a human-sounding voice. You do
not have to choose — but you do have to divide the work along the right seam.

**The seam: generated pixels underneath, typography and timing from code on top.**

Video models still garble Hebrew text inside the frame, and a curriculum trailer
needs exact wording (`הדבשת אוגרת שומן — לא מים` cannot come out as decorative
squiggles). So never ask the model for on-screen text. Ask it for the plate;
composite the words yourself.

```
shot list ──┬─► Sora/Veo per shot ──► plate.mp4 ──┐
            │                                     ├─► ffmpeg overlay ──► final.mp4
            └─► code-rendered RGBA overlay ───────┘        ▲
                (Hebrew titles, captions, diagrams)        │
   narration text ──► TTS ──► per-line wav + real durations┘
```

## Contents

- [Part 1 — Sora as a footage source](#part-1--sora-as-a-footage-source)
- [Part 2 — Narration with Gemini / Google Cloud TTS](#part-2--narration-with-gemini--google-cloud-tts)
- [Part 3 — Timing-first: let audio drive the timeline](#part-3--timing-first-let-audio-drive-the-timeline)
- [Part 4 — Mixing and final assembly](#part-4--mixing-and-final-assembly)
- [Cost, latency and failure planning](#cost-latency-and-failure-planning)

---

## Part 1 — Sora as a footage source

### Why it slots in cleanly

The shot list is already the right unit of work. Sora generates short clips
(seconds, not minutes), which is exactly one shot. A per-shot architecture — one
encode per shot, concatenated with `-c copy` — means a generated plate and a
code-rendered shot are interchangeable at the same seam. You can convert the film
one shot at a time and always have something that plays.

### Prompting per shot, not per film

A single "make me a 3-minute trailer" prompt is unusable. Derive one prompt per
shot from the shot list, and keep four things stable across all of them so the
cuts belong to the same film: lens/format, palette, lighting direction, and
grade. Then vary only the subject.

```python
STYLE = ("cinematic 35mm, shallow depth of field, warm natural light from the "
         "left, muted earth palette, no text, no captions, no logos, no watermark")

SHOTS = [
    {"id": 2,  "seconds": 9,
     "prompt": f"A kangaroo rat foraging on moonlit desert dunes at night, "
               f"low camera close to the sand, slow dolly right to left. {STYLE}"},
    {"id": 9,  "seconds": 8,
     "prompt": f"A camel walking across glowing dunes in late afternoon haze, "
               f"backlit silhouette, wide shot, slow pan. {STYLE}"},
]
```

Always include the negative constraints (`no text, no captions, no logos`) —
generated pseudo-text under your real captions looks like a rendering bug.

### API shape

Video generation is asynchronous everywhere: create a job, poll, download.

```python
from openai import OpenAI

client = OpenAI()

def generate_plate(prompt, seconds, out_path, size="1920x1080", model="sora-2"):
    job = client.videos.create(model=model, prompt=prompt,
                               seconds=str(seconds), size=size)
    while job.status in ("queued", "in_progress"):
        time.sleep(5)
        job = client.videos.retrieve(job.id)
    if job.status != "completed":
        raise RuntimeError(f"generation failed: {job.status} {getattr(job, 'error', '')}")
    content = client.videos.download_content(job.id, variant="video")
    content.write_to_file(out_path)
    return out_path
```

Verify model names, duration limits and the exact download call against the
current API docs before running a batch — this surface moves quickly. Cache by a
hash of `(model, prompt, seconds, size)` so a re-run never regenerates a clip you
already paid for.

### Compositing the overlay

Render the shot's typography and diagrams as an RGBA PNG sequence with the same
code you use today (transparent background instead of the painted one), then let
ffmpeg do the composite:

```bash
# plate → exact duration, fps and frame size, then overlay the RGBA sequence
ffmpeg -y -i plate.mp4 -framerate 30 -i overlay/f%05d.png \
  -filter_complex "[0:v]scale=1920:1080:force_original_aspect_ratio=increase,\
crop=1920:1080,fps=30,trim=duration=9,setpts=PTS-STARTPTS[bg];\
[bg][1:v]overlay=0:0:format=auto[v]" \
  -map "[v]" -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p shot_02.mp4
```

Two things keep text readable over live footage: a gradient scrim behind the
caption band (draw it into the overlay, not the plate), and a slight darkening of
the plate itself under the text region. Generated footage has far more local
contrast than flat vector art — captions that read perfectly over a painted
gradient can disappear over real sand.

### Keep the deterministic path alive

Keep every scene function. Make the plate optional per shot:

```python
TIMELINE = [
    (scenes.s02_desert, 9.0, {"plate": "plates/shot_02.mp4"}),  # AI footage
    (scenes.s05_board,  10.0, {}),                              # code-rendered
]
```

Diagram shots — the table, the gears, the water cycle, the joints — should stay
code-rendered forever. They are information graphics; a video model will produce
something that *looks* like a water cycle but is not the one you are teaching.

---

## Part 2 — Narration with Gemini / Google Cloud TTS

### Fixing the snippet first

The client setup needs one import that is easy to miss, and the region must match
the model's availability:

```python
import os
from google.api_core.client_options import ClientOptions   # <- missing in the snippet
from google.cloud import texttospeech

PROJECT_ID = os.environ["GOOGLE_CLOUD_PROJECT"]
TTS_LOCATION = os.environ.get("GOOGLE_CLOUD_REGION", "global")
API_ENDPOINT = (f"{TTS_LOCATION}-texttospeech.googleapis.com"
                if TTS_LOCATION != "global" else "texttospeech.googleapis.com")

client = texttospeech.TextToSpeechClient(
    client_options=ClientOptions(api_endpoint=API_ENDPOINT))
```

### Which API, and the free path

There are two different Google products here and they take different credentials:

| | Gemini Developer API | Cloud Text-to-Speech |
|---|---|---|
| Host | `generativelanguage.googleapis.com` | `texttospeech.googleapis.com` |
| Auth | API key from AI Studio | API key or service-account ADC on a billing-enabled project |
| Cost | free tier, rate-limited | free monthly quota, then paid |
| Style steering | natural language in the prompt | `input.prompt` on TTS models |
| Returns | **headerless PCM**, base64 | base64 WAV/MP3 per `audioEncoding` |

For a classroom film — a few thousand characters — the free tier is enough. Start
there; move to Cloud TTS when you need SSML, long-form chunking, or a specific
`he-IL` voice that only exists there.

**The Gemini response is raw PCM, not a WAV.** `inlineData.mimeType` looks like
`audio/L16;codec=pcm;rate=24000`; write a RIFF header around the bytes yourself or
every downstream tool will reject the file. Parse the rate out of the mime type
rather than assuming 24 kHz.

```python
part = resp["candidates"][0]["content"]["parts"][0]["inlineData"]
rate = int(dict(p.split("=") for p in part["mimeType"].split(";")[1:]
                if "=" in p).get("rate", 24000))
with wave.open(out, "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
    w.writeframes(base64.b64decode(part["data"]))
```

**Prove the chain before you spend anything.** `apt-get install espeak-ng` gives
real (robotic) Hebrew speech offline: `espeak-ng -v he -s 145 -w out.wav "טקסט"`.
Run the whole pipeline on it first — durations, fit report, ducking, subtitles,
mux — so that switching to the real engine is one flag and the only variable left
is voice quality. Do keep in mind that pacing differs between engines, so leave
headroom rather than tuning line lengths against the stand-in.

### Synthesising a Hebrew line

```python
def say(text, out_path, voice_name="he-IL-Chirp3-HD-Achernar",
        model_name=None, style_prompt=None, rate=1.0):
    """Render one narration line to a 24 kHz mono WAV."""
    synth_input = texttospeech.SynthesisInput(text=text)
    if style_prompt:                      # Gemini TTS models accept steering
        synth_input.prompt = style_prompt

    voice = texttospeech.VoiceSelectionParams(language_code="he-IL", name=voice_name)
    if model_name:                        # e.g. "gemini-2.5-flash-tts"
        voice.model_name = model_name

    resp = client.synthesize_speech(
        input=synth_input, voice=voice,
        audio_config=texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            sample_rate_hertz=24000, speaking_rate=rate))
    with open(out_path, "wb") as fh:
        fh.write(resp.audio_content)
    return out_path
```

Notes that matter for Hebrew specifically:

- **Voice availability is the constraint, not the code.** Confirm which Hebrew
  (`he-IL`) voices exist for the model tier you want before designing around it;
  the newest model families reach Hebrew later than English. List them once with
  `client.list_voices(language_code="he-IL")` and pick from what comes back.
- **Write for the ear.** Send plain text, not the on-screen caption. `שער ג׳`
  should be narrated as `שער גימל`; digits and abbreviations should be spelled
  out. Keep a separate `narration` field per shot — never reuse the caption
  string.
- **Style steering** (`prompt=`, on the Gemini TTS models) is where warmth comes
  from: *"Read like a curious teacher talking to nine-year-olds — unhurried,
  slightly amused."* This does more for the film than any voice-name choice.
- **Nikud only where a word is genuinely ambiguous.** Sprinkling it everywhere
  tends to make the model over-articulate.
- Cache by a hash of `(text, voice, model, rate, prompt)`. Narration gets
  re-rendered constantly during script edits and it is the slowest step.

---

## Part 3 — Timing-first: let audio drive the timeline

This is the part that actually changes the architecture, and it is worth getting
right before you generate anything.

With captions only, you pick shot durations and the words fit. With narration,
the words have a fixed, unknown length — so **generate the audio first, measure
it, and derive the timeline from the measurements.** Guessing durations and
trimming afterwards produces clipped sentences and dead air, and re-guessing after
every script edit is where the time goes.

```python
import wave

def wav_seconds(path):
    with wave.open(path) as w:
        return w.getnframes() / w.getframerate()

SCRIPT = [
    {"shot": "desert",  "text": "איך שורדים במדבר בלי לשתות?", "pad": 1.2},
    {"shot": "dew",     "text": "היא אינה שותה כלל. את המים היא מפיקה מן הזרעים.",
     "pad": 1.0},
]

def build_timeline(script, voice_dir="build/vo"):
    timeline, cursor, srt = [], 0.0, []
    for i, line in enumerate(script):
        wav = say(line["text"], f"{voice_dir}/{i:03d}.wav",
                  style_prompt="Warm, curious teacher, unhurried.")
        speech = wav_seconds(wav)
        duration = speech + line["pad"]        # breathing room after the line
        timeline.append({"shot": line["shot"], "duration": duration,
                         "vo": wav, "vo_at": cursor})
        srt.append((cursor, cursor + speech, line["text"]))
        cursor += duration
    return timeline, srt, cursor
```

Then print a **fit report** before mixing anything: for each line, does
`at + measured_seconds` land inside its shot? Overruns are the only real failure
mode, and they cluster on the short shots — a 3-second gate card cannot hold a
3.5-second sentence. Shorten the *spoken* line (the caption can stay long) or
grow the shot.

Consequences worth planning for:

- **Total runtime becomes an output, not an input.** If it must be exactly 3:00,
  absorb the difference in shots that have no narration (gate cards, the finale
  hold) rather than by speeding up speech.
- **Captions become subtitles.** Once there is a voice, on-screen text should be
  short reinforcement of key terms, not the full sentence — and you get an SRT
  for free from the same measurements, which is also your accessibility story.
- **Music must follow the new timeline**, not the old one. Keep the score's
  section boundaries as variables derived from the timeline, not literals.

---

## Part 4 — Mixing and final assembly

Narration sits on top; music ducks under it. A static −9 dB dip during speech is
usually enough, and it is easy to reason about:

```python
def duck(music, vo_spans, sr, depth_db=-9.0, ramp=0.35):
    """Attenuate the music where narration plays, with short ramps."""
    import numpy as np
    gain = np.ones_like(music)
    g = 10 ** (depth_db / 20)
    for start, end in vo_spans:
        a, b = int(start * sr), int(end * sr)
        r = int(ramp * sr)
        gain[a:b] = g
        gain[max(0, a - r):a] = np.linspace(1, g, min(r, a))
        gain[b:b + r] = np.linspace(g, 1, len(gain[b:b + r]))
    return music * gain
```

**Ducking by level alone is not enough**, and this is the mistake that produces
"I can't hear the narration" even when the meters look right. Music and speech
share the 300 Hz–3.5 kHz band where intelligibility lives, so also carve the
music in that band while someone is talking — lows and highs stay, so the score
still reads as music rather than just going quiet. Two details:

- **Carve the ducked signal, not the original.** Subtracting a band of the
  full-level music from an already-quiet signal *adds* energy back. Getting this
  backwards cost 9 dB of intelligibility and was invisible on a level meter.
- **Shape the voice too**: high-pass below ~90 Hz, lift 1.6–4.5 kHz, and
  compress. Synthetic speech has a wide dynamic range and the quiet syllables are
  exactly the ones that disappear.

Measure the thing you actually care about: **voice versus music, band-limited to
300–3.5 kHz, during speech only**. Comparing whole-mix RMS in speech windows
against music-only windows tells you nothing — those should be similar, because
consistent program level is the goal. Target ~12–15 dB of voice advantage in the
speech band.

Then assemble: narration laid onto a silent bed at `vo_at`, mixed with the ducked
music, and muxed onto the picture.

```bash
ffmpeg -y -i silent.mp4 -i mix.wav \
  -c:v copy -c:a aac -b:a 192k -movflags +faststart -shortest final.mp4
```

Burning subtitles is a separate pass, so you can ship a clean master and a
subtitled copy from the same render:

```bash
ffmpeg -y -i final.mp4 -vf "subtitles=narration.srt:force_style='Alignment=2'" \
  -c:a copy final_subs.mp4
```

Check with `ffprobe` that the audio stream exists and the duration still matches.

---

## Cost, latency and failure planning

| | Code-rendered | + Sora plates | + TTS narration |
|---|---|---|---|
| Marginal cost | none | per second of generated video | per character |
| Wall clock | minutes, local | minutes per clip, remote queue | seconds per line |
| Determinism | exact | re-runs differ | near-exact per input |
| Offline | yes | no | no |
| Hebrew text in frame | exact | unusable — overlay instead | n/a |

Practical rules:

1. **Cache every remote artifact** keyed by a hash of its inputs, and commit the
   cache manifest. A script tweak should regenerate one line, not the film.
2. **Keep the offline path working.** The code-rendered version is the fallback
   when a key is missing, a region is unavailable, or a generation is rejected —
   the film still plays.
3. **Review generated plates before compositing.** Extract a few frames per clip
   and look at them; a plate with a sixth finger or invented text is cheaper to
   regenerate than to discover in the final cut.
4. **Say what is synthetic.** For classroom material, note in the description
   that footage and voice are AI-generated. It is both honest and a teaching
   opportunity.
