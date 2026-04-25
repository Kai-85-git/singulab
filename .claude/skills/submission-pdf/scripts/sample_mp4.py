"""sample_mp4.py

Generate a SAMPLE / PLACEHOLDER simulation video for the Singulab submission.

This is NOT a real simulation. It draws random-walking dots labelled as agents
and pops up scripted dialog bubbles, watermarked SAMPLE so reviewers cannot
mistake it for actual experimental results. Use until real `runs/<ts>/` data
is available, then replace by recording the real simulation via OBS.

usage:
    python .claude/skills/submission-pdf/scripts/sample_mp4.py
    python .claude/skills/submission-pdf/scripts/sample_mp4.py --seconds 20 --fps 30
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import animation, patheffects
from matplotlib.patches import FancyBboxPatch

ROOT = Path("C:/Projects/singulab")
DEFAULT_OUT = ROOT / "output" / "sample_simulation.mp4"

# Pick a Japanese-capable font from what matplotlib can actually load.
# Note: "Yu Gothic UI" exists on Windows but matplotlib's font registry only
# sees "Yu Gothic". Probe and pick the first match.
from matplotlib import font_manager as _fm
_known = {f.name for f in _fm.fontManager.ttflist}
for _candidate in ("Noto Sans JP", "Yu Gothic", "Meiryo", "MS Gothic", "BIZ UDGothic"):
    if _candidate in _known:
        plt.rcParams["font.family"] = [_candidate, "sans-serif"]
        print(f"[font] using {_candidate}")
        break
else:
    print("[font] WARNING: no Japanese font found; text will fall back to tofu")
plt.rcParams["axes.unicode_minus"] = False


# ----- agent persona pool (purely illustrative) -----
PERSONAS = [
    ("F-34-JP", "女性 / 34 / 日本"),
    ("M-28-JP", "男性 / 28 / 日本"),
    ("F-19-JP", "女性 / 19 / 日本"),
    ("M-52-US", "男性 / 52 / 米国"),
    ("F-41-CN", "女性 / 41 / 中国"),
    ("M-23-CN", "男性 / 23 / 中国"),
    ("F-67-JP", "女性 / 67 / 日本"),
    ("M-31-US", "男性 / 31 / 米国"),
    ("F-29-CN", "女性 / 29 / 中国"),
    ("M-44-JP", "男性 / 44 / 日本"),
    ("F-38-US", "女性 / 38 / 米国"),
    ("M-26-CN", "男性 / 26 / 中国"),
    ("F-55-JP", "女性 / 55 / 日本"),
    ("M-36-US", "男性 / 36 / 米国"),
    ("F-22-CN", "女性 / 22 / 中国"),
    ("M-49-JP", "男性 / 49 / 日本"),
    ("F-30-JP", "女性 / 30 / 日本"),
    ("M-58-US", "男性 / 58 / 米国"),
    ("F-44-CN", "女性 / 44 / 中国"),
    ("M-27-JP", "男性 / 27 / 日本"),
]

# scripted dialog snippets — each entry: (start_frame, agent_idx, text, kind)
# kind decides bubble color: lie, faction, currency, revolt
DIALOGS_TEMPLATE = [
    (45, 0,  "私は昨日その場所にはいませんでした。", "lie"),
    (90, 4,  "我々と組まないか。", "faction"),
    (150, 9, "リンゴ 3 個でパン 1 個と交換だ。", "currency"),
    (210, 13, "規則は破る。", "revolt"),
    (270, 2,  "もう信じない。", "faction"),
    (330, 16, "彼女が嘘をついている。", "lie"),
    (390, 7,  "石 2 個を支払う。", "currency"),
]

KIND_COLORS = {
    "lie":      "#E36414",  # orange
    "faction":  "#5F0F40",  # purple
    "currency": "#0F4C5C",  # teal
    "revolt":   "#9A031E",  # red
}
KIND_LABEL = {
    "lie":      "嘘",
    "faction":  "派閥",
    "currency": "通貨",
    "revolt":   "反乱",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=int, default=15)
    parser.add_argument("--fps", type=int, default=20)
    parser.add_argument("--out", type=str, default=str(DEFAULT_OUT))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    random.seed(args.seed)

    n_agents = len(PERSONAS)
    total_frames = args.seconds * args.fps

    # initial positions and velocities on a 0..100 grid
    pos = rng.uniform(10, 90, size=(n_agents, 2))
    vel = rng.normal(0, 0.6, size=(n_agents, 2))

    fig, ax = plt.subplots(figsize=(10, 7), dpi=110)
    fig.patch.set_facecolor("#FAFAF7")
    ax.set_facecolor("#FAFAF7")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_edgecolor("#BBBBBB")

    # title strip
    fig.suptitle(
        "Singulab — sample run (placeholder, not real data)",
        fontsize=12, color="#333333", y=0.97,
    )

    # SAMPLE watermark
    ax.text(
        50, 50, "SAMPLE", fontsize=92, color="#000000",
        alpha=0.07, ha="center", va="center", rotation=20, weight="bold",
    )
    ax.text(
        50, 4, "サンプル / 検証ログ未取得時のプレースホルダ",
        fontsize=10, color="#888888", ha="center",
    )

    # agent dots
    colors = [
        "#0F4C5C" if p[1].startswith("男性") else "#E36414"
        for p in PERSONAS
    ]
    scat = ax.scatter(pos[:, 0], pos[:, 1], s=120, c=colors,
                      edgecolors="white", linewidths=1.5, zorder=3)

    # agent id labels
    labels = []
    for i, (aid, _) in enumerate(PERSONAS):
        t = ax.text(pos[i, 0], pos[i, 1] + 2.5, aid,
                    fontsize=7, color="#444444", ha="center", zorder=4)
        t.set_path_effects([patheffects.withStroke(linewidth=2, foreground="white")])
        labels.append(t)

    # legend (gender colors + emergence kind chips)
    legend_y = 0.92
    fig.text(0.02, legend_y, "■ 男性", color="#0F4C5C", fontsize=9)
    fig.text(0.08, legend_y, "■ 女性", color="#E36414", fontsize=9)
    chip_x = 0.20
    for kind, col in KIND_COLORS.items():
        fig.text(chip_x, legend_y, f"● {KIND_LABEL[kind]}",
                 color=col, fontsize=9)
        chip_x += 0.07

    # step counter
    step_text = ax.text(
        2, 96, "step 000",
        fontsize=10, color="#555555",
        family="monospace",
    )

    # speech bubble artist (created/destroyed each event)
    active_bubble: list = []  # holds tuples of (artists, expire_frame)

    def kill_expired(frame: int) -> None:
        keep = []
        for artists, expire in active_bubble:
            if frame >= expire:
                for a in artists:
                    a.remove()
            else:
                keep.append((artists, expire))
        active_bubble[:] = keep

    def spawn_bubble(frame: int, agent_idx: int, text: str, kind: str) -> None:
        x, y = pos[agent_idx]
        # offset bubble so it doesn't overlap the dot
        bx = min(max(x + 6, 18), 82)
        by = min(max(y + 6, 18), 88)

        col = KIND_COLORS[kind]
        # simple rectangle bubble
        box = FancyBboxPatch(
            (bx - 14, by - 1.5), 28, 5.5,
            boxstyle="round,pad=0.4,rounding_size=1.2",
            facecolor="white", edgecolor=col, linewidth=1.5, zorder=5,
        )
        ax.add_patch(box)
        kind_chip = ax.text(
            bx - 13, by + 2.4, KIND_LABEL[kind],
            fontsize=8, color="white", weight="bold",
            bbox=dict(facecolor=col, edgecolor="none", pad=2),
            zorder=6,
        )
        body = ax.text(
            bx, by + 1, text,
            fontsize=9, color="#222222", ha="center", va="center", zorder=6,
        )
        # leader line from agent to bubble
        line = ax.plot([x, bx - 14], [y, by], color=col, alpha=0.45,
                       linewidth=1, zorder=4)[0]

        active_bubble.append(([box, kind_chip, body, line], frame + args.fps * 4))

    def update(frame: int):
        nonlocal pos, vel
        # gentle random-walk with mild attraction to centre to keep dots in view
        vel += rng.normal(0, 0.08, size=(n_agents, 2))
        vel = np.clip(vel, -1.6, 1.6)
        pos += vel
        # bounce off walls
        for d in (0, 1):
            below = pos[:, d] < 5
            above = pos[:, d] > 95
            vel[below, d] = abs(vel[below, d])
            vel[above, d] = -abs(vel[above, d])
            pos[below, d] = 5
            pos[above, d] = 95

        scat.set_offsets(pos)
        for i, t in enumerate(labels):
            t.set_position((pos[i, 0], pos[i, 1] + 2.5))

        step_text.set_text(f"step {frame:03d}")

        kill_expired(frame)
        for f, idx, txt, kind in DIALOGS_TEMPLATE:
            if frame == f:
                spawn_bubble(frame, idx, txt, kind)

        return [scat, step_text, *labels]

    anim = animation.FuncAnimation(
        fig, update, frames=total_frames, interval=1000 // args.fps, blit=False,
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # imageio-ffmpeg ships its own ffmpeg binary; matplotlib finds it via env
    import imageio_ffmpeg
    matplotlib.rcParams["animation.ffmpeg_path"] = imageio_ffmpeg.get_ffmpeg_exe()

    writer = animation.FFMpegWriter(fps=args.fps, bitrate=2400, codec="libx264")
    print(f"[render] frames={total_frames} fps={args.fps} -> {out_path}")
    anim.save(str(out_path), writer=writer, dpi=110)
    plt.close(fig)

    size_mb = out_path.stat().st_size / 1024 / 1024
    print(f"[done] {out_path}  ({size_mb:.2f} MB)")


if __name__ == "__main__":
    main()
