"""Vendored from the `video-soundtrack` skill so this project renders standalone.

Tiny synth for short video soundtracks. numpy + stdlib only, no assets, no network.

    from score import Track, bowed, blip, note, melody, SAD_VIOLIN, room

    t = Track(20)
    melody(t, SAD_VIOLIN, at=6.9)          # the sad-violin cue
    t.add(blip(0.18, 520), at=0.25)
    t.normalize().write("track.wav")
"""
import numpy as np, wave

SR = 44100

# ---------------------------------------------------------------- notes
_STEPS = {"C":0,"C#":1,"Db":1,"D":2,"D#":3,"Eb":3,"E":4,"F":5,"F#":6,
          "Gb":6,"G":7,"G#":8,"Ab":8,"A":9,"A#":10,"Bb":10,"B":11}

def note(name):
    """'A4' -> 440.0 ; 'C#5' -> 554.37"""
    for i, ch in enumerate(name):
        if ch.isdigit():
            step, octv = _STEPS[name[:i]], int(name[i:])
            break
    return 440.0 * 2 ** ((step - 9 + (octv - 4) * 12) / 12)

# ---------------------------------------------------------------- instruments
def bowed(dur, freq, vol=0.26, vibrato=5.4, depth=0.0055,
          attack=0.14, release=0.18, tremolo=0.05,
          harmonics=(1.0, 0.55, 0.40, 0.26, 0.16, 0.11, 0.07), sr=SR):
    """Bowed string (violin / viola / cello depending on register + vol).

    The character comes from three things together — drop any one and it
    stops sounding like a violin:
      1. a full harmonic stack (a bare sine sounds like a test tone)
      2. vibrato as *frequency* modulation, ~5-6 Hz, very shallow (~0.5%)
      3. a soft attack (~0.14 s) — the bow takes time to grip the string
    """
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    vib = 1 + depth * np.sin(2 * np.pi * vibrato * t + np.random.rand())
    phase = 2 * np.pi * freq * np.cumsum(vib) / sr
    wave_ = sum(a * np.sin((n + 1) * phase) for n, a in enumerate(harmonics))
    wave_ /= sum(harmonics)
    env = np.minimum(1, t / attack) * np.minimum(1, (dur - t) / release)
    trem = 1 + tremolo * np.sin(2 * np.pi * 4.6 * t)
    return vol * env * trem * wave_

def blip(dur, freq, vol=0.32, wobble=0.0, sr=SR):
    """Short cartoon beep. wobble>0 gives the queasy 'uh-oh' warble."""
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    p = t / dur
    env = np.minimum(1, p * 12) * (1 - p) ** 1.6
    return vol * env * np.sin(2 * np.pi * freq * t * (1 + wobble * np.sin(p * 40)))

def pluck(dur, freq, vol=0.30, sr=SR):
    """Pizzicato-ish: same harmonics, instant attack, fast decay."""
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    harmonics = (1.0, 0.6, 0.35, 0.2, 0.12)
    w = sum(a * np.sin((n + 1) * 2 * np.pi * freq * t) for n, a in enumerate(harmonics))
    return vol * (w / sum(harmonics)) * np.exp(-t * 6.5)

# ---------------------------------------------------------------- space
def room(sig, mix=0.28, taps=((0.085, 0.30), (0.155, 0.18), (0.24, 0.10)), sr=SR):
    """Cheap 3-tap reverb. Strings sound thin and synthetic without it."""
    out = sig.copy()
    for d, g in taps:
        s = int(d * sr)
        if s < len(sig):
            out[s:] += mix * g * sig[:-s]
    return out

# ---------------------------------------------------------------- track
class Track:
    def __init__(self, seconds, sr=SR):
        self.sr = sr
        self.buf = np.zeros(int(seconds * sr))

    def add(self, sig, at=0.0, gain=1.0):
        a = int(at * self.sr)
        b = min(len(self.buf), a + len(sig))
        if b > a:
            self.buf[a:b] += gain * sig[:b - a]
        return self

    def add_wet(self, sig, at=0.0, mix=0.28):
        """Add through the room reverb — use for anything sustained."""
        return self.add(room(sig, mix=mix, sr=self.sr), at)

    def normalize(self, peak=0.92):
        m = np.abs(self.buf).max()
        if m > 0:
            self.buf *= peak / m
        return self

    def rms(self, start, end):
        seg = self.buf[int(start * self.sr):int(end * self.sr)]
        return float(np.sqrt((seg ** 2).mean())) if len(seg) else 0.0

    def write(self, path):
        pcm = (np.clip(self.buf, -1, 1) * 32000).astype(np.int16)
        with wave.open(path, "w") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(self.sr)
            w.writeframes(pcm.tobytes())
        return path

def melody(track, notes, at=0.0, inst=bowed, wet=0.28, **kw):
    """notes = [(offset_seconds, 'D4', duration), ...] — offsets are relative to `at`."""
    lead = np.zeros_like(track.buf)
    for off, name, dur in notes:
        seg = inst(dur, note(name), **kw)
        a = int((at + off) * track.sr)
        b = min(len(lead), a + len(seg))
        if b > a:
            lead[a:b] += seg[:b - a]
    track.buf += room(lead, mix=wet, sr=track.sr) if wet else lead
    return track

# ---------------------------------------------------------------- presets
# The "world's smallest violin" gag: descending D-minor line that never resolves.
SAD_VIOLIN = [
    (0.00, "A4",  0.95),
    (0.95, "F4",  0.95),
    (1.90, "E4",  0.70),
    (2.60, "D4",  1.30),
    (3.95, "F4",  0.60),
    (4.55, "E4",  0.60),
    (5.15, "D4",  0.75),
    (5.90, "C#4", 0.55),   # leading tone, left hanging on purpose
]
SAD_VIOLIN_DRONE = [(0.00, "D3", 3.40), (3.40, "F3", 3.00)]   # play at vol≈0.10

HAPPY_ARPEGGIO = [(0.00, "C5", 0.50), (0.16, "E5", 0.50),
                  (0.32, "G5", 0.50), (0.48, "C6", 0.50)]

def entry_blips(track, at=0.0, n=4, base=520, step=110, gap=0.42):
    for k in range(n):
        track.add(blip(0.18, base + k * step), at + k * gap)
    return track

def panic(track, at=0.0, dur=1.2):
    return track.add(blip(dur, 180, 0.30, wobble=0.35), at)

def run_up(track, at=0.0, n=5, base=330, step=90, gap=0.20):
    for k in range(n):
        track.add(blip(0.16, base + k * step, 0.34), at + k * gap)
    return track
