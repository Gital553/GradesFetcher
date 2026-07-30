"""Render the 3-minute grade-4 science trailer to MP4.

Each shot is encoded independently (one ffmpeg per segment, in parallel), then
the parts are concatenated without re-encoding and the soundtrack is muxed in.
Frames are streamed to ffmpeg over a pipe — 5,400 raw 1080p frames on disk
would be ~33 GB.

    python3 render.py                 # full film -> ../science_trailer_grade4.mp4
    python3 render.py --frame 12.5    # single frame -> /tmp/frame.png (QA)
    python3 render.py --scenes 4,5    # only some shots (fast iteration)
"""

import argparse
import multiprocessing as mp
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import imageio_ffmpeg

import scenes
from draw import H, W, dim, ease_in, finish, smoothstep

FPS = 30
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
HERE = os.path.dirname(os.path.abspath(__file__))

# (function, duration seconds, fade-in seconds, fade-out seconds)
TIMELINE = [
    (scenes.s01_open, 6.0, 0.8, 0.0),
    (scenes.s02_desert_night, 9.0, 0.5, 0.0),
    (scenes.s03_dew, 6.0, 0.4, 0.3),
    (scenes.s04_boundary, 11.0, 0.4, 0.3),
    (scenes.s05_observation, 10.0, 0.4, 0.3),
    (scenes.s06_question_wall, 3.0, 0.3, 0.0),

    (scenes.s07_gate_a, 3.0, 0.4, 0.4),
    (scenes.s08_polar_bear, 8.0, 0.4, 0.0),
    (scenes.s09_camel, 8.0, 0.3, 0.0),
    (scenes.s10_goldfish, 7.0, 0.3, 0.0),
    (scenes.s11_five_needs, 13.0, 0.4, 0.3),
    (scenes.s12_big_idea, 6.0, 0.4, 0.0),

    (scenes.s13_gate_b, 3.0, 0.4, 0.4),
    (scenes.s14_design, 8.0, 0.4, 0.3),
    (scenes.s15_gears, 10.0, 0.3, 0.3),
    (scenes.s16_gate_c, 3.0, 0.4, 0.4),
    (scenes.s17_states, 10.0, 0.4, 0.3),
    (scenes.s18_water_cycle, 11.0, 0.4, 0.0),

    (scenes.s19_gate_d, 3.0, 0.4, 0.4),
    (scenes.s20_skin, 9.0, 0.4, 0.3),
    (scenes.s21_joints, 10.0, 0.4, 0.3),
    (scenes.s22_xray_run, 11.0, 0.4, 0.3),
    (scenes.s23_finale, 12.0, 0.6, 0.0),
]

TOTAL = sum(s[1] for s in TIMELINE)


def scene_start(index):
    return sum(s[1] for s in TIMELINE[:index])


def render_frame(index, local_frame):
    """One finished RGB frame of scene `index`."""
    fn, dur, fade_in, fade_out = TIMELINE[index]
    t = local_frame / FPS
    img = fn(t, min(t / dur, 1.0), int(scene_start(index) * FPS) + local_frame)
    if fade_in and t < fade_in:
        dim(img, 1 - smoothstep(t / fade_in))
    if fade_out and t > dur - fade_out:
        dim(img, ease_in((t - (dur - fade_out)) / fade_out))
    finish(img, int(scene_start(index) * FPS) + local_frame)
    return img.convert("RGB")


def frame_at(seconds):
    """Frame at an absolute timestamp — used by the QA checks."""
    acc = 0.0
    for i, (_fn, dur, _fi, _fo) in enumerate(TIMELINE):
        if seconds < acc + dur or i == len(TIMELINE) - 1:
            return render_frame(i, int(round((seconds - acc) * FPS)))
        acc += dur
    raise ValueError(seconds)


def _encode_segment(args):
    index, parts_dir, crf, preset = args
    _fn, dur, _fi, _fo = TIMELINE[index]
    n = int(round(dur * FPS))
    out = os.path.join(parts_dir, f"part_{index:02d}.mp4")
    cmd = [
        FFMPEG, "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
        "-i", "pipe:0",
        "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
        "-pix_fmt", "yuv420p", "-g", str(FPS * 2), "-keyint_min", str(FPS),
        "-x264-params", "scenecut=0", out,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    for f in range(n):
        proc.stdin.write(render_frame(index, f).tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError(f"ffmpeg failed on segment {index}")
    return index, n, time.time() - t0


def render(out_path, indices=None, crf=20, preset="medium", jobs=None,
           audio=None):
    """Encode the given shots, then concatenate the *whole* timeline.

    Shots not listed are reused from build/parts, so fixing one shot costs one
    shot's render time instead of five minutes.
    """
    parts_dir = os.path.join(HERE, "build", "parts")
    os.makedirs(parts_dir, exist_ok=True)
    part = lambda i: os.path.join(parts_dir, f"part_{i:02d}.mp4")  # noqa: E731
    indices = indices if indices is not None else list(range(len(TIMELINE)))
    # longest shots first so the pool drains evenly
    order = sorted(indices, key=lambda i: -TIMELINE[i][1])
    jobs = jobs or min(len(order), os.cpu_count() or 2)

    t0 = time.time()
    done = 0
    total_frames = sum(int(round(TIMELINE[i][1] * FPS)) for i in order)
    with mp.Pool(jobs) as pool:
        for index, n, secs in pool.imap_unordered(
                _encode_segment, [(i, parts_dir, crf, preset) for i in order]):
            done += n
            print(f"  shot {index:02d}  {n:4d} frames  {secs:6.1f}s  "
                  f"[{done}/{total_frames}]", flush=True)

    missing = [i for i in range(len(TIMELINE)) if not os.path.exists(part(i))]
    if missing:
        raise SystemExit(f"cannot assemble: shots {missing} have never been "
                         f"rendered. Run without --scenes once.")

    listing = os.path.join(HERE, "build", "parts.txt")
    with open(listing, "w") as fh:
        for i in range(len(TIMELINE)):
            fh.write(f"file '{part(i)}'\n")

    silent = os.path.join(HERE, "build", "silent.mp4")
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", listing, "-c", "copy", silent], check=True)

    if audio and os.path.exists(audio):
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", silent, "-i", audio,
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                        "-movflags", "+faststart", "-shortest", out_path], check=True)
    else:
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", silent,
                        "-c", "copy", "-movflags", "+faststart", out_path], check=True)

    print(f"\n{out_path}  ({os.path.getsize(out_path) / 1e6:.1f} MB) "
          f"in {time.time() - t0:.0f}s")
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "..", "science_trailer_grade4.mp4"))
    ap.add_argument("--audio", default=os.path.join(HERE, "build", "soundtrack.wav"))
    ap.add_argument("--scenes", help="comma separated shot indices")
    ap.add_argument("--frame", type=float, help="render a single timestamp to PNG")
    ap.add_argument("--png", default="/tmp/frame.png")
    ap.add_argument("--crf", type=int, default=20)
    ap.add_argument("--preset", default="medium")
    ap.add_argument("--jobs", type=int, default=None)
    args = ap.parse_args()

    if args.frame is not None:
        frame_at(args.frame).save(args.png)
        print(f"{args.png} @ {args.frame}s")
        return

    indices = ([int(x) for x in args.scenes.split(",")] if args.scenes
               else list(range(len(TIMELINE))))
    print(f"rendering {len(indices)} shots, {TOTAL:.0f}s total at {W}x{H}/{FPS}fps")
    render(os.path.abspath(args.out), indices, args.crf, args.preset, args.jobs,
           args.audio)


if __name__ == "__main__":
    main()
