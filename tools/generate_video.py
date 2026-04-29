"""PNG フレーム群を FFmpeg で mp4 に連結する CLI。

Usage:
    python -m tools.generate_video output/phase3-3_local_startup
    python -m tools.generate_video output/phase3-3_local_startup --fps 5 --out demo.mp4

挙動:
    - <run_dir>/frames/frame_*.png を入力
    - 既定では <run_dir>/simulation.mp4 に出力
    - FFmpeg がパスに無い場合はエラー
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Combine PNG frames into mp4 via ffmpeg")
    parser.add_argument("run_dir", help="path to <run> directory containing frames/")
    parser.add_argument("--fps", type=int, default=3, help="frames per second (default: 3)")
    parser.add_argument(
        "--out",
        default=None,
        help="output mp4 path (default: <run_dir>/simulation.mp4)",
    )
    parser.add_argument(
        "--ffmpeg",
        default="ffmpeg",
        help="ffmpeg binary path (default: 'ffmpeg' from PATH)",
    )
    parser.add_argument("--overwrite", "-y", action="store_true", help="overwrite output")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    frames_dir = run_dir / "frames"
    if not frames_dir.is_dir():
        print(f"ERROR: no frames directory: {frames_dir}", file=sys.stderr)
        return 1

    pngs = sorted(frames_dir.glob("frame_*.png"))
    if not pngs:
        print(f"ERROR: no frame_*.png in {frames_dir}", file=sys.stderr)
        return 1
    print(f"Found {len(pngs)} frames in {frames_dir}")

    ffmpeg = args.ffmpeg if shutil.which(args.ffmpeg) else None
    if ffmpeg is None:
        print(
            f"ERROR: ffmpeg not found. Install ffmpeg or pass --ffmpeg <path>.",
            file=sys.stderr,
        )
        return 2

    out_path = Path(args.out) if args.out else (run_dir / "simulation.mp4")
    if out_path.exists() and not args.overwrite:
        print(
            f"ERROR: output already exists: {out_path} (use --overwrite or -y)",
            file=sys.stderr,
        )
        return 3

    cmd = [
        ffmpeg,
        "-y" if args.overwrite or not out_path.exists() else "-n",
        "-framerate",
        str(args.fps),
        "-i",
        str(frames_dir / "frame_%04d.png"),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        # 偶数解像度に揃える(matplotlib の出力サイズが奇数のときに失敗するのを防ぐ)
        "-vf",
        "pad=ceil(iw/2)*2:ceil(ih/2)*2",
        str(out_path),
    ]
    print(f"Running: {' '.join(cmd)}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print("FFmpeg stderr:")
        print(proc.stderr[-2000:])
        return proc.returncode
    if os.path.exists(out_path):
        size_kb = os.path.getsize(out_path) / 1024
        print(f"Wrote {out_path} ({size_kb:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
