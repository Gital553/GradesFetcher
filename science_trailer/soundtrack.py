"""The 3-minute score, synthesised from scratch (numpy only, no audio assets).

Four movements matching the four acts of the film:

    0:00–0:45  desert night     D minor, sparse, wide — curiosity
    0:45–1:30  the animals      F major, warmer, a steady heartbeat underneath
    1:30–2:15  technology/water A minor with a mechanical eighth-note pulse
    2:15–3:00  the body/finale  C major anthem, rising, resolved at the end

Run directly to (re)build build/soundtrack.wav.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from score import SR, Track, bowed, note, pluck, room  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DURATION = 181.0
ACTS = (0.0, 45.0, 90.0, 135.0, 180.0)


# ------------------------------------------------------------- textures ----
def pad(track, names, at, dur, vol=0.10):
    """A sustained bowed chord — the bed each movement sits on."""
    for i, name in enumerate(names):
        track.add_wet(bowed(dur, note(name), vol=vol, attack=1.1, release=1.4,
                            tremolo=0.03),
                      at=at + i * 0.05, mix=0.34)
    return track


def arp(track, names, at, step=0.34, dur=0.9, vol=0.16, inst=pluck):
    for i, name in enumerate(names):
        track.add_wet(inst(dur, note(name), vol=vol), at=at + i * step, mix=0.3)
    return track


def line(track, notes, at, vol=0.20, **kw):
    """A bowed melodic phrase: [(offset, name, dur), ...]."""
    for off, name, dur in notes:
        track.add_wet(bowed(dur, note(name), vol=vol, **kw), at=at + off, mix=0.32)
    return track


def pulse(track, at, dur, bpm=100, names=("D3", "A3"), vol=0.11):
    """Eighth-note mechanical tick — the gears of act 3."""
    step = 30.0 / bpm
    k = 0
    while k * step < dur:
        track.add(pluck(0.26, note(names[k % len(names)]), vol=vol), at=at + k * step)
        k += 1
    return track


def whoosh(track, at, dur=1.1, vol=0.22, rise=True):
    """Filtered-noise transition between acts."""
    n = int(dur * SR)
    t = np.linspace(0, 1, n, endpoint=False)
    rng = np.random.default_rng(int(at * 100) % 9973)
    noise = rng.normal(0, 1, n)
    # crude sweeping filter: blend a smoothed (dark) and differenced (bright) copy
    dark = np.convolve(noise, np.ones(90) / 90, mode="same")
    bright = np.diff(noise, prepend=noise[0])
    k = t if rise else 1 - t
    sig = dark * (1 - k) + bright * k * 0.35
    env = np.sin(np.pi * t) ** 1.6
    return track.add(room(vol * env * sig / (np.abs(sig).max() + 1e-9), mix=0.35), at=at)


def swell(track, at, name="D2", dur=3.0, vol=0.13):
    return track.add_wet(bowed(dur, note(name), vol=vol, attack=1.6, release=1.0),
                         at=at, mix=0.4)


# ------------------------------------------------------------ movements ----
def act1_desert(t):
    """Sparse, minor, wide. Room for the question to land."""
    chords = [(0.0, 7.0, ["D3", "A3", "D4"]), (7.0, 7.0, ["D3", "A3", "F4"]),
              (14.0, 7.0, ["Bb2", "F3", "D4"]), (21.0, 7.0, ["Bb2", "F3", "D4"]),
              (28.0, 7.0, ["G2", "D3", "Bb3"]), (35.0, 6.0, ["A2", "E3", "C#4"]),
              (41.0, 5.0, ["A2", "E3", "C#4"])]
    for at, dur, names in chords:
        pad(t, names, at, dur, vol=0.085)

    swell(t, 0.4, "D2", 4.0, 0.15)
    line(t, [(0.0, "A4", 1.4), (1.6, "D5", 1.8), (3.8, "F4", 1.2)], at=7.6, vol=0.15)
    arp(t, ["D5", "F5", "A5"], at=13.4, step=0.5, dur=1.0, vol=0.10)
    # the boundary-card section: tighter, more questioning
    line(t, [(0.0, "Bb4", 1.0), (1.1, "A4", 1.0), (2.2, "G4", 1.4)], at=22.0, vol=0.15)
    arp(t, ["D4", "F4", "A4", "D5"], at=27.0, step=0.42, dur=0.8, vol=0.11)
    line(t, [(0.0, "E5", 1.6), (1.8, "D5", 2.2)], at=36.0, vol=0.16)
    arp(t, ["A4", "D5", "F5", "A5"], at=41.6, step=0.34, dur=0.7, vol=0.12)


def act2_animals(t):
    """Warmer and more curious — F major, with a light heartbeat."""
    prog = [["F3", "C4", "A4"], ["D3", "A3", "F4"], ["Bb2", "F3", "D4"],
            ["C3", "G3", "E4"]]
    at = 45.0
    while at < 89.0:
        pad(t, prog[int((at - 45) // 5.5) % 4], at, 5.6, vol=0.085)
        at += 5.5
    pulse(t, 46.0, 43.0, bpm=64, names=("F2", "C3"), vol=0.055)

    line(t, [(0.0, "F4", 1.3), (1.5, "A4", 1.3), (3.0, "C5", 2.0)], at=46.5, vol=0.17)
    arp(t, ["F4", "A4", "C5", "F5"], at=53.5, step=0.36, dur=0.8, vol=0.12)
    line(t, [(0.0, "D5", 1.6), (1.8, "C5", 1.2), (3.2, "A4", 1.8)], at=57.0, vol=0.16)
    arp(t, ["Bb4", "D5", "F5"], at=64.0, step=0.4, dur=0.9, vol=0.12)
    line(t, [(0.0, "F5", 1.4), (1.6, "E5", 1.2), (3.0, "D5", 2.2)], at=67.5, vol=0.16)
    # the five needs arriving one by one
    for k, name in enumerate(["C5", "D5", "F5", "G5", "A5"]):
        t.add_wet(pluck(1.0, note(name), vol=0.15), at=72.0 + k * 0.62, mix=0.3)
    line(t, [(0.0, "A4", 1.8), (2.0, "C5", 1.6), (3.8, "F5", 2.6)], at=83.0, vol=0.18)


def act3_technology(t):
    """Mechanical pulse for the gears, then flowing figures for the water."""
    prog = [["A2", "E3", "C4"], ["G2", "D3", "B3"], ["C3", "G3", "E4"],
            ["F2", "C3", "A3"]]
    at = 90.0
    while at < 134.0:
        pad(t, prog[int((at - 90) // 5.5) % 4], at, 5.6, vol=0.08)
        at += 5.5

    pulse(t, 92.0, 22.0, bpm=104, names=("A2", "E3", "A2", "C3"), vol=0.10)
    line(t, [(0.0, "E5", 1.2), (1.4, "C5", 1.2), (2.8, "D5", 1.8)], at=94.0, vol=0.16)
    # gears meshing: interlocking plucks
    for k in range(26):
        t.add(pluck(0.3, note(["A4", "E5", "C5", "G4"][k % 4]), vol=0.085),
              at=101.5 + k * 0.34)
    line(t, [(0.0, "A4", 1.6), (1.8, "C5", 1.4), (3.4, "E5", 2.0)], at=104.0, vol=0.16)

    # states of matter: the figures loosen up as the particles do
    arp(t, ["C4", "E4", "G4", "C5"], at=114.5, step=0.42, dur=0.9, vol=0.12)
    arp(t, ["D4", "G4", "B4", "D5"], at=118.0, step=0.34, dur=0.8, vol=0.12)
    arp(t, ["E4", "A4", "C5", "E5", "A5"], at=121.0, step=0.26, dur=0.7, vol=0.12)
    # water cycle: rolling, continuous
    for k in range(22):
        t.add_wet(pluck(0.8, note(["C5", "E5", "G5", "E5"][k % 4]), vol=0.10),
                  at=124.5 + k * 0.44, mix=0.34)
    line(t, [(0.0, "G4", 2.0), (2.2, "C5", 2.4), (4.8, "E5", 2.6)], at=125.0, vol=0.16)


def act4_body_and_finale(t):
    """C major anthem: rises through the body shots and resolves on the title."""
    prog = [["C3", "G3", "E4"], ["A2", "E3", "C4"], ["F2", "C3", "A3"],
            ["G2", "D3", "B3"]]
    at = 135.0
    while at < 167.0:
        pad(t, prog[int((at - 135) // 5.5) % 4], at, 5.6, vol=0.09)
        at += 5.5
    pulse(t, 137.0, 30.0, bpm=72, names=("C3", "G2"), vol=0.06)

    line(t, [(0.0, "E4", 1.6), (1.8, "G4", 1.6), (3.6, "C5", 2.4)], at=138.5, vol=0.17)
    line(t, [(0.0, "A4", 1.4), (1.6, "G4", 1.4), (3.2, "E5", 2.4)], at=147.5, vol=0.17)
    # the run: driving quavers under the skeleton
    for k in range(30):
        t.add(pluck(0.28, note(["C4", "G4", "E4", "G4"][k % 4]), vol=0.085),
              at=157.5 + k * 0.32)
    line(t, [(0.0, "C5", 1.6), (1.8, "E5", 1.6), (3.6, "G5", 2.8)], at=158.5, vol=0.18)

    # finale — full chord, then let the reverb tail carry the last card
    whoosh(t, 166.4, 1.4, vol=0.20)
    for name in ("C3", "G3", "C4", "E4", "G4", "C5"):
        t.add_wet(bowed(9.0, note(name), vol=0.10, attack=0.5, release=3.0),
                  at=168.2, mix=0.4)
    line(t, [(0.0, "E5", 2.0), (2.2, "G5", 2.2), (4.6, "C6", 4.6)], at=169.0, vol=0.17)
    for k, name in enumerate(["C5", "E5", "G5", "C6"]):
        t.add_wet(pluck(1.4, note(name), vol=0.14), at=174.6 + k * 0.3, mix=0.4)
    for name in ("C3", "G3", "C4", "E4"):
        t.add_wet(bowed(6.0, note(name), vol=0.09, attack=0.6, release=3.4),
                  at=175.0, mix=0.45)


def build(path=None):
    t = Track(DURATION)
    act1_desert(t)
    act2_animals(t)
    act3_technology(t)
    act4_body_and_finale(t)
    for boundary in ACTS[1:-1]:                     # act transitions
        whoosh(t, boundary - 0.9, 1.3, vol=0.20)
    t.normalize(0.88)

    # gentle fade so the film does not end on a cut
    tail = t.buf[int(178.0 * SR):]
    tail *= np.linspace(1, 0, len(tail))

    path = path or os.path.join(HERE, "build", "soundtrack.wav")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    t.write(path)

    print(f"{path}  {DURATION:.0f}s")
    print("section levels (RMS, keep within ~2x of each other):")
    for name, a, b in (("act1 desert", 2, 44), ("act2 animals", 46, 89),
                       ("act3 tech", 91, 134), ("act4 finale", 136, 178)):
        print(f"  {name:<14} {t.rms(a, b):.3f}")
    return path


if __name__ == "__main__":
    build()
