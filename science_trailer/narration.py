"""Hebrew narration for the trailer — Gemini TTS, with offline fallback.

Three engines behind one interface, so the pipeline is identical either way:

    gemini   Gemini Developer API (free tier, API key from aistudio.google.com).
             Best quality, supports natural-language style steering.
    cloud    Google Cloud Text-to-Speech (Chirp3-HD or the Gemini TTS models).
             Needs a billing-enabled project; also has a free monthly quota.
    espeak   Local espeak-ng. Robotic, but real Hebrew speech with no key —
             use it to prove timing, ducking, subtitles and muxing before
             spending anything.

Narration text is deliberately *not* the on-screen caption: it is written for
the ear ("שער ראשון", not "שער א׳"). Every line is cached by a hash of its
inputs, because a script edit should re-synthesise one line, not the film.

    export GEMINI_API_KEY=...            # free key from Google AI Studio
    python3 narration.py --list-voices   # what the key can actually use
    python3 narration.py --engine gemini # synthesise, mix, mux
    python3 narration.py --engine espeak --dry-run   # timing report, no network
"""

import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import imageio_ffmpeg

from render import FPS, TIMELINE, scene_start  # noqa: F401  (shot geometry)

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")
VO_DIR = os.path.join(BUILD, "vo")
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
SR = 44100                      # the soundtrack's rate; everything resamples to it

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta"
CLOUD_ENDPOINT = "https://texttospeech.googleapis.com/v1"

# How the voice should sound. Gemini TTS takes plain-language direction, and
# this does more for the result than the choice of voice name.
STYLE = ("קרא בקול חם וסקרן של מורה שמדברת אל ילדים בני תשע. "
         "לא ממהרת, עם חיוך קל בקול, והדגשה עדינה של מילות המפתח.")

# (shot index, seconds into that shot, text for the ear)
SCRIPT = [
    (0, 1.6, "השנה נצא למסע. מסע של שאלות."),
    (1, 1.8, "במדבר, בלילה, חיה קטנה אוספת זרעים. איך היא שורדת בלי לשתות?"),
    (2, 0.9, "התשובה היא טל: מים שמגיעים בלי גשם."),
    (2, 3.6, "היא אינה שותה כלל."),
    (3, 1.0, "אש גדלה, נעה, וצריכה אוויר. אז למה היא איננה יצור חי?"),
    (3, 6.0, "כי יצור חי מקיים את כל שבעת המאפיינים."),
    (4, 1.0, "מה שהעיניים ראו, זו תצפית."),
    (4, 4.6, "מה שאני חושב שזה אומר, זו פרשנות. ובמדע לא מבלבלים ביניהן."),
    (5, 0.3, "וכל שאלה שנשארת, עולה לקיר."),
    (6, 0.4, "שער ראשון: בעלי חיים."),
    (7, 1.6, "לדוב הקוטב יש שכבת שומן ופרווה כפולה."),
    (8, 1.6, "והדבשת של הגמל אוגרת שומן, לא מים."),
    (9, 1.3, "והדג נושם חמצן שמומס במים."),
    (10, 1.0, "חמישה צרכים: מים, מזון, אוויר, טמפרטורה, והגנה."),
    (10, 7.2, "טבלה עוזרת לנו לראות את הדפוס."),
    (11, 1.0, "כולם צריכים אותו דבר. כל אחד משיג אותו אחרת."),
    (12, 0.4, "שער שני: טכנולוגיה."),
    (13, 1.2, "מזהים בעיה, ומתכננים פתרון, עם דרישות ואילוצים."),
    (14, 1.6, "לכל מערכת יש מבנה, פעולה, ותמסורת שמעבירה תנועה."),
    (15, 0.4, "שער שלישי: אוויר ומים."),
    (16, 1.2, "אותו חומר, בשלושה מצבים: מוצק, נוזל, וגז."),
    (17, 1.2, "והמים נעים במעגל: אידוי, התעבות, משקעים, ונגר."),
    (18, 0.4, "שער רביעי: הגוף."),
    (19, 1.4, "העור עוטף אותנו, והמבנה שלו מתאים בדיוק לתפקיד."),
    (20, 1.4, "מפרק ציר מכופף. מפרק כדור־שקע מסובב."),
    (21, 1.4, "שלד, מפרקים ושרירים. כל תנועה היא מערכת."),
    (22, 1.6, "השנה נצפה, ננמק, ונגלה."),
    (22, 5.6, "כי במדע, נימוק טוב שווה יותר מניחוש מוצלח."),
]


# ------------------------------------------------------------- wav utils ---
def write_wav(path, pcm_bytes, rate, channels=1, sampwidth=2):
    with wave.open(path, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(sampwidth)
        w.setframerate(rate)
        w.writeframes(pcm_bytes)
    return path


def read_wav(path):
    """-> (float32 mono samples in [-1,1], sample rate)."""
    with wave.open(path) as w:
        rate, n, ch = w.getframerate(), w.getnframes(), w.getnchannels()
        raw = np.frombuffer(w.readframes(n), np.int16).astype(np.float32) / 32768
    if ch > 1:
        raw = raw.reshape(-1, ch).mean(axis=1)
    return raw, rate


def resample(sig, src_rate, dst_rate=SR):
    if src_rate == dst_rate:
        return sig
    n = int(len(sig) * dst_rate / src_rate)
    return np.interp(np.linspace(0, len(sig), n, endpoint=False),
                     np.arange(len(sig)), sig).astype(np.float32)


def duration(path):
    with wave.open(path) as w:
        return w.getnframes() / w.getframerate()


# --------------------------------------------------------------- engines ---
def _post(url, payload, headers=None):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"{exc.code} from {url.split('?')[0]}:\n"
                         f"{exc.read().decode()[:600]}")


def _pcm_rate_from_mime(mime, default=24000):
    """Gemini returns raw PCM, e.g. 'audio/L16;codec=pcm;rate=24000'."""
    for part in (mime or "").split(";"):
        if part.strip().startswith("rate="):
            return int(part.split("=")[1])
    return default


def say_gemini(text, out_path, voice="Kore", model="gemini-2.5-flash-preview-tts",
               style=STYLE):
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise SystemExit("set GEMINI_API_KEY (free key: https://aistudio.google.com/apikey)")
    data = _post(
        f"{GEMINI_ENDPOINT}/models/{model}:generateContent?key={key}",
        {"contents": [{"parts": [{"text": f"{style}\n\n{text}"}]}],
         "generationConfig": {
             "responseModalities": ["AUDIO"],
             "speechConfig": {"voiceConfig": {
                 "prebuiltVoiceConfig": {"voiceName": voice}}}}})
    part = data["candidates"][0]["content"]["parts"][0]["inlineData"]
    # the payload is headerless PCM — it needs a RIFF wrapper to be a .wav
    return write_wav(out_path, base64.b64decode(part["data"]),
                     _pcm_rate_from_mime(part.get("mimeType")))


def say_cloud(text, out_path, voice="he-IL-Chirp3-HD-Achernar", model=None,
              style=None, rate=1.0):
    key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    headers = {}
    url = f"{CLOUD_ENDPOINT}/text:synthesize"
    if key:
        url += f"?key={key}"
    else:                                   # fall back to ADC / service account
        import google.auth
        import google.auth.transport.requests
        creds, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"])
        creds.refresh(google.auth.transport.requests.Request())
        headers["Authorization"] = f"Bearer {creds.token}"

    voice_cfg = {"languageCode": "he-IL", "name": voice}
    if model:                               # e.g. "gemini-2.5-flash-tts"
        voice_cfg["modelName"] = model
    body = {"input": {"text": text},
            "voice": voice_cfg,
            "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": 24000,
                            "speakingRate": rate}}
    if style and model:                     # steering only applies to TTS models
        body["input"]["prompt"] = style
    data = _post(url, body, headers)
    return write_wav(out_path, base64.b64decode(data["audioContent"]), 24000)


def say_espeak(text, out_path, voice="mb-hb2", model=None, style=None,
               rate=140):
    """Offline stand-in: robotic, but real speech with real durations."""
    subprocess.run(["espeak-ng", "-v", voice, "-s", str(int(rate)), "-w", out_path,
                    text], check=True, capture_output=True)
    return out_path


ENGINES = {"gemini": say_gemini, "cloud": say_cloud, "espeak": say_espeak}
# mb-hb2 is the MBROLA Hebrew female diphone voice (apt: mbrola-hb2);
# far more natural than espeak's built-in "he" formant synthesis.
DEFAULT_VOICE = {"gemini": "Kore", "cloud": "he-IL-Chirp3-HD-Achernar",
                 "espeak": "mb-hb2"}


def list_voices(engine):
    """Ask the API what it actually offers — don't guess voice names."""
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if engine == "gemini":
        if not key:
            raise SystemExit("set GEMINI_API_KEY first")
        with urllib.request.urlopen(f"{GEMINI_ENDPOINT}/models?key={key}",
                                    timeout=60) as resp:
            for m in json.loads(resp.read()).get("models", []):
                if "tts" in m["name"].lower():
                    print(f"  {m['name']:<52} {m.get('displayName', '')}")
        print("\nvoice names are prebuilt (Kore, Puck, Charon, Aoede, Zephyr, …);"
              "\nthe TTS models are multilingual and take Hebrew directly.")
    elif engine == "cloud":
        url = f"{CLOUD_ENDPOINT}/voices?languageCode=he-IL"
        if key:
            url += f"&key={key}"
        with urllib.request.urlopen(url, timeout=60) as resp:
            for v in json.loads(resp.read()).get("voices", []):
                print(f"  {v['name']:<40} {v.get('ssmlGender', '')}")
    else:
        subprocess.run(["espeak-ng", "--voices=he"], check=False)


# ------------------------------------------------------------ synthesis ----
def synthesize(engine, voice=None, model=None, force=False):
    """Render every line, cached by a hash of everything that affects output."""
    os.makedirs(VO_DIR, exist_ok=True)
    voice = voice or DEFAULT_VOICE[engine]
    fn = ENGINES[engine]
    lines = []
    for i, (shot, at, text) in enumerate(SCRIPT):
        tag = hashlib.sha1(
            f"{engine}|{voice}|{model}|{STYLE}|{text}".encode()).hexdigest()[:12]
        path = os.path.join(VO_DIR, f"{i:02d}_{tag}.wav")
        if force or not os.path.exists(path):
            if engine == "espeak":
                fn(text, path, voice=voice)
            else:
                fn(text, path, voice=voice, model=model, style=STYLE)
            print(f"  synth {i:02d}  {text[:44]}")
        lines.append({"index": i, "shot": shot, "at": at, "text": text,
                      "wav": path, "seconds": duration(path),
                      "abs": scene_start(shot) + at})
    return lines


def fit_report(lines):
    """Does every line finish before its shot cuts? Overruns are the whole risk."""
    print(f"\n{'shot':>4} {'line':>4} {'starts':>7} {'len':>5} {'shot len':>9}  status")
    worst = 0.0
    for ln in lines:
        shot_len = TIMELINE[ln["shot"]][1]
        end = ln["at"] + ln["seconds"]
        over = end - shot_len
        worst = max(worst, over)
        flag = "OK" if over <= 0 else f"OVERRUN by {over:.2f}s"
        print(f"{ln['shot']:>4} {ln['index']:>4} {ln['at']:>7.1f} "
              f"{ln['seconds']:>5.1f} {shot_len:>9.1f}  {flag}")
    total_speech = sum(ln["seconds"] for ln in lines)
    print(f"\n{len(lines)} lines, {total_speech:.1f}s of speech "
          f"over a {sum(s[1] for s in TIMELINE):.0f}s film")
    print("worst overrun: " + (f"{worst:.2f}s — shorten that line or grow the shot"
                               if worst > 0 else "none"))
    return worst


def write_srt(lines, path=None):
    path = path or os.path.join(BUILD, "narration.srt")

    def stamp(t):
        h, rem = divmod(t, 3600)
        m, s = divmod(rem, 60)
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(s % 1 * 1000):03d}"

    with open(path, "w", encoding="utf-8") as fh:
        for n, ln in enumerate(sorted(lines, key=lambda x: x["abs"]), 1):
            fh.write(f"{n}\n{stamp(ln['abs'])} --> "
                     f"{stamp(ln['abs'] + ln['seconds'])}\n{ln['text']}\n\n")
    print(f"{path}")
    return path


# ------------------------------------------------------- speech clarity ---
def _band(sig, lo, hi, sr=SR):
    """Band-limited copy via FFT, with soft edges to avoid ringing."""
    spec = np.fft.rfft(sig)
    freq = np.fft.rfftfreq(len(sig), 1 / sr)
    mask = np.zeros_like(freq)
    edge = max(lo * 0.25, 60.0)
    mask[(freq >= lo) & (freq <= hi)] = 1.0
    rise = (freq > lo - edge) & (freq < lo)
    mask[rise] = 0.5 - 0.5 * np.cos(np.pi * (freq[rise] - (lo - edge)) / edge)
    fall = (freq > hi) & (freq < hi + edge)
    mask[fall] = 0.5 + 0.5 * np.cos(np.pi * (freq[fall] - hi) / edge)
    return np.fft.irfft(spec * mask, n=len(sig)).astype(np.float32)


def _smooth(x, n):
    """Boxcar smoothing in O(n) — the compressor's envelope detector."""
    n = max(1, int(n))
    pad = np.concatenate([np.full(n, x[0], np.float32), x,
                          np.full(n, x[-1], np.float32)])
    c = np.cumsum(np.concatenate([[0.0], pad.astype(np.float64)]))
    out = ((c[n:] - c[:-n]) / n).astype(np.float32)
    return out[n:n + len(x)]


def compress(sig, threshold=0.06, ratio=4.0, attack=0.004, release=0.10, sr=SR):
    """Level out the syllables. Synthetic speech has a wide dynamic range and
    the quiet syllables are exactly the ones that vanish under music."""
    env = _smooth(np.abs(sig), attack * sr) + 1e-9
    gain = np.where(env > threshold, (threshold / env) ** (1 - 1 / ratio), 1.0)
    return sig * _smooth(gain.astype(np.float32), release * sr)


def voice_shape(sig, sr=SR):
    """Make the voice legible: drop rumble, lift the consonant band."""
    sig = sig - _band(sig, 0.0, 90.0, sr)                    # high-pass
    sig = sig + _band(sig, 1600.0, 4500.0, sr) * 0.9         # presence lift
    return compress(sig, sr=sr)


# --------------------------------------------------------------- mixing ---
def duck(music, spans, depth_db=-8.0, ramp=0.30, scoop=0.40):
    """Get the score out of the way of the voice.

    Level alone is not enough: music and speech share the 300 Hz-3.5 kHz band
    where intelligibility lives, so the music is *also* carved in that band
    while someone is talking. Lows and highs stay, so the score still reads as
    music instead of just going quiet.

    These defaults put the voice ~15 dB above the bed inside the speech band —
    the broadcast range — while barely touching the music's overall level.
    """
    gain = np.ones_like(music)
    g = 10 ** (depth_db / 20)
    for start, end in spans:
        a, b = int(start * SR), int(end * SR)
        r = int(ramp * SR)
        gain[a:b] = g
        pre = gain[max(0, a - r):a]
        pre[:] = np.linspace(1, g, len(pre))
        post = gain[b:b + r]
        post[:] = np.linspace(g, 1, len(post))
    carve = (1 - gain) / (1 - g) * scoop           # 0 when open, `scoop` when ducked
    ducked = music * gain
    # carve the *ducked* signal: subtracting a band of the full-level music
    # from an already-quiet signal adds energy back instead of removing it.
    return ducked - _band(ducked, 300.0, 3500.0) * carve


def mix(lines, music_path=None, out_path=None, vo_gain=1.0):
    music_path = music_path or os.path.join(BUILD, "soundtrack.wav")
    out_path = out_path or os.path.join(BUILD, "mix.wav")
    music, rate = read_wav(music_path)
    music = resample(music, rate)

    vo = np.zeros_like(music)
    spans = []
    for ln in lines:
        sig, r = read_wav(ln["wav"])
        sig = resample(sig, r)
        # normalise by RMS, not peak: speech has a high crest factor, so
        # peak-matching leaves the voice sitting under the music even though
        # the meters look right.
        sig = voice_shape(sig)
        rms = float(np.sqrt((sig ** 2).mean()))
        if rms > 0:
            sig = sig * (0.20 * vo_gain / rms)
        # soft-limit the peaks instead of rescaling the line: rescaling to fit
        # the loudest consonant simply undoes the normalisation and puts the
        # voice back under the music.
        sig = np.tanh(sig / 0.9).astype(np.float32) * 0.9
        sig = sig + 0.16 * np.concatenate(
            [np.zeros(int(0.055 * SR), np.float32), sig])[:len(sig)]
        a = int(ln["abs"] * SR)
        b = min(len(vo), a + len(sig))
        vo[a:b] += sig[:b - a]
        spans.append((ln["abs"], ln["abs"] + len(sig) / SR))

    mixed = duck(music, spans) + vo
    peak = np.abs(mixed).max()
    if peak > 0.98:
        mixed *= 0.98 / peak
    write_wav(out_path, (np.clip(mixed, -1, 1) * 32000).astype(np.int16).tobytes(), SR)
    print(f"{out_path}  (speech covers {sum(e - s for s, e in spans):.0f}s "
          f"of {len(music) / SR:.0f}s)")
    return out_path


def mux(mix_path, out_path, silent=None):
    silent = silent or os.path.join(BUILD, "silent.mp4")
    if not os.path.exists(silent):
        raise SystemExit(f"{silent} missing — run render.py first")
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", silent, "-i", mix_path,
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart", "-shortest", out_path], check=True)
    print(f"{out_path}  ({os.path.getsize(out_path) / 1e6:.1f} MB)")
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", choices=list(ENGINES), default="gemini")
    ap.add_argument("--voice")
    ap.add_argument("--model", help="TTS model id (gemini/cloud engines)")
    ap.add_argument("--list-voices", action="store_true")
    ap.add_argument("--dry-run", action="store_true",
                    help="synthesise and report timing, but do not mix or mux")
    ap.add_argument("--force", action="store_true", help="ignore the cache")
    ap.add_argument("--out", default=os.path.join(HERE, "..",
                                                  "science_trailer_grade4_vo.mp4"))
    args = ap.parse_args()

    if args.list_voices:
        list_voices(args.engine)
        return

    model = args.model
    if args.engine == "gemini" and not model:
        model = "gemini-2.5-flash-preview-tts"

    lines = synthesize(args.engine, args.voice, model, args.force)
    fit_report(lines)
    write_srt(lines)
    if args.dry_run:
        return
    mux(mix(lines), os.path.abspath(args.out))


if __name__ == "__main__":
    main()
