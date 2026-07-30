"""Encoder skeleton: timeline -> parallel per-shot encode -> concat -> mux.

Copy into the project and replace TIMELINE with real scene functions. The design
choices that matter:

* One ffmpeg per shot, fed raw frames over a pipe. Writing frames to disk costs
  ~6 MB each (33 GB for a 3-minute film) and shipping them between processes is
  slower than encoding them.
* Parallelism is per shot, longest first, so the pool drains evenly.
* Shots not listed on the command line are reused from build/parts, so fixing
  one scene costs one shot's render time instead of a full re-render. This is
  the difference between a 60-second iteration and a 6-minute one.
* Concat with `-c copy`, which requires identical encoder settings per shot.

    python3 render_pipeline.py                  # whole film
    python3 render_pipeline.py --frame 72.5     # one frame to PNG, for review
    python3 render_pipeline.py --scenes 3,7     # re-encode two shots, reassemble
"""

import argparse
import multiprocessing as mp
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import imageio_ffmpeg  # provides a static ffmpeg binary; no apt needed

W, H, FPS = 1920, 1080, 30
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
HERE = os.path.dirname(os.path.abspath(__file__))

# (scene_function, duration_seconds, fade_in_seconds, fade_out_seconds)
TIMELINE = [
    # (scenes.s01_open, 6.0, 0.8, 0.0),
]
TOTAL = sum(s[1] for s in TIMELINE)


def scene_start(index):
    return sum(s[1] for s in TIMELINE[:index])


def render_frame(index, local_frame):
    """One finished RGB frame. Scenes are pure: f(t, progress, frame) -> RGBA."""
    fn, dur, fade_in, fade_out = TIMELINE[index]
    t = local_frame / FPS
    fi = int(scene_start(index) * FPS) + local_frame
    img = fn(t, min(t / dur, 1.0), fi)
    # apply grade / fades here (grain kept low: it dominates the bitrate)
    return img.convert("RGB")


def frame_at(seconds):
    acc = 0.0
    for i, (_fn, dur, _fi, _fo) in enumerate(TIMELINE):
        if seconds < acc + dur or i == len(TIMELINE) - 1:
            return render_frame(i, int(round((seconds - acc) * FPS)))
        acc += dur
    raise ValueError(seconds)


def _encode_segment(args):
    index, parts_dir, crf, preset = args
    n = int(round(TIMELINE[index][1] * FPS))
    out = os.path.join(parts_dir, f"part_{index:02d}.mp4")
    proc = subprocess.Popen([
        FFMPEG, "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
        "-i", "pipe:0",
        "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
        "-pix_fmt", "yuv420p", "-g", str(FPS * 2), "-keyint_min", str(FPS),
        "-x264-params", "scenecut=0", out,
    ], stdin=subprocess.PIPE)
    t0 = time.time()
    for f in range(n):
        proc.stdin.write(render_frame(index, f).tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError(f"ffmpeg failed on shot {index}")
    return index, n, time.time() - t0


def render(out_path, indices=None, crf=21, preset="medium", jobs=None, audio=None):
    parts_dir = os.path.join(HERE, "build", "parts")
    os.makedirs(parts_dir, exist_ok=True)
    part = lambda i: os.path.join(parts_dir, f"part_{i:02d}.mp4")  # noqa: E731
    indices = list(range(len(TIMELINE))) if indices is None else indices
    order = sorted(indices, key=lambda i: -TIMELINE[i][1])
    jobs = jobs or min(len(order), os.cpu_count() or 2)

    t0 = time.time()
    with mp.Pool(jobs) as pool:
        for index, n, secs in pool.imap_unordered(
                _encode_segment, [(i, parts_dir, crf, preset) for i in order]):
            print(f"  shot {index:02d}  {n:4d} frames  {secs:6.1f}s", flush=True)

    missing = [i for i in range(len(TIMELINE)) if not os.path.exists(part(i))]
    if missing:
        raise SystemExit(f"cannot assemble: shots {missing} were never rendered")

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
    ap.add_argument("--out", default=os.path.join(HERE, "out.mp4"))
    ap.add_argument("--audio", default=os.path.join(HERE, "build", "soundtrack.wav"))
    ap.add_argument("--scenes", help="comma separated shot indices to re-encode")
    ap.add_argument("--frame", type=float, help="render one timestamp to PNG")
    ap.add_argument("--png", default="/tmp/frame.png")
    ap.add_argument("--crf", type=int, default=21)
    ap.add_argument("--preset", default="medium")
    ap.add_argument("--jobs", type=int)
    args = ap.parse_args()

    if args.frame is not None:
        frame_at(args.frame).save(args.png)
        print(f"{args.png} @ {args.frame}s")
        return

    indices = ([int(x) for x in args.scenes.split(",")] if args.scenes else None)
    print(f"rendering {TOTAL:.0f}s at {W}x{H}/{FPS}fps")
    render(os.path.abspath(args.out), indices, args.crf, args.preset, args.jobs,
           args.audio)


if __name__ == "__main__":
    main()
