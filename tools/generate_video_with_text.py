"""フィールド画像 + 右側にメッセージ・思考パネルを並べた動画を生成する CLI。

参考実装(`docs/10_共有資料/.../simulation.mp4`)と同じくフィールドを左に置きつつ、
右側に「直近のメッセージ」と「現 step の思考(reasoning / memory)」を表示することで、
動画 1 本で会話の流れと内面が同時に追えるようにする。

Usage:
    python -m tools.generate_video_with_text output/04_本番v2_創発イベント/prod_v3_alien_5
    python -m tools.generate_video_with_text <run_dir> --fps 2 --recent 6

入出力:
    入力: <run_dir>/frames/frame_*.png + messages.jsonl + memory_reasoning.jsonl
    中間: <run_dir>/frames_with_text/frame_*.png
    出力: <run_dir>/simulation_with_text.mp4(既定)
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import textwrap
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

import matplotlib.image as mpimg
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt


# Agent ID ごとの色(色覚配慮で識別性高い色を選定)
AGENT_COLORS = [
    "#1f77b4",  # 0: 青
    "#ff7f0e",  # 1: 橙
    "#2ca02c",  # 2: 緑
    "#d62728",  # 3: 赤
    "#9467bd",  # 4: 紫
    "#8c564b",  # 5: 茶
    "#e377c2",  # 6: ピンク
    "#7f7f7f",  # 7: 灰
    "#bcbd22",  # 8: 黄緑
    "#17becf",  # 9: 水
]


def _agent_color(agent_id: int) -> str:
    return AGENT_COLORS[agent_id % len(AGENT_COLORS)]


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in open(path, encoding="utf-8")]


def _load_personas(run_dir: Path) -> List[Dict[str, Any]]:
    """run_metadata.json から personas を読み込む。"""
    meta_path = run_dir / "run_metadata.json"
    if not meta_path.exists():
        return []
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        return meta.get("personas") or []
    except Exception:
        return []


_GENDER_JP = {"male": "男", "female": "女"}


def _agent_label(agent_id: int, personas: List[Dict[str, Any]]) -> str:
    """例:`Agent 2 (55歳 男 ISFP)` のような表示用ラベル。"""
    if not personas or agent_id < 0 or agent_id >= len(personas):
        return f"Agent {agent_id}"
    p = personas[agent_id]
    age = p.get("age")
    gender_jp = _GENDER_JP.get(p.get("gender", ""), "")
    mbti = p.get("mbti", "")
    parts = []
    if age is not None:
        parts.append(f"{age}歳")
    if gender_jp:
        parts.append(gender_jp)
    if mbti:
        parts.append(mbti)
    suffix = " / ".join(parts)
    return f"Agent {agent_id} ({suffix})" if suffix else f"Agent {agent_id}"


def _wrap(text: str, width: int) -> str:
    """日本語混じりテキストを width 文字程度で折り返す。"""
    if not text:
        return ""
    text = text.replace("\n", " ").strip()
    return "\n".join(textwrap.wrap(text, width=width, break_long_words=True, break_on_hyphens=False))


def _wrap_fixed_lines(text: str, width: int, max_lines: int) -> str:
    """text を width で折り返し、必ず max_lines 行にする(短ければ空行で埋め、長ければ省略)。"""
    if not text:
        return "\n" * (max_lines - 1)
    text = text.replace("\n", " ").strip()
    lines = textwrap.wrap(text, width=width, break_long_words=True, break_on_hyphens=False)
    if len(lines) > max_lines:
        # 最終行末尾を「…」で省略
        lines = lines[:max_lines]
        last = lines[-1]
        if len(last) > width - 1:
            last = last[:width - 1]
        lines[-1] = last + "…"
    while len(lines) < max_lines:
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compose field frames + side text panel into mp4"
    )
    parser.add_argument("run_dir", help="path to <run> directory")
    parser.add_argument("--fps", type=int, default=2)
    parser.add_argument(
        "--recent",
        type=int,
        default=6,
        help="サイドに表示する直近メッセージ件数(default: 6)",
    )
    parser.add_argument("--out", default=None, help="出力 mp4 のパス")
    parser.add_argument("--overwrite", "-y", action="store_true")
    parser.add_argument("--ffmpeg", default="ffmpeg")
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

    msgs = _load_jsonl(run_dir / "messages.jsonl")
    mr = _load_jsonl(run_dir / "memory_reasoning.jsonl")
    personas = _load_personas(run_dir)
    if personas:
        print(f"Loaded {len(personas)} personas from run_metadata.json")
    msgs_by_step: Dict[int, List[Dict]] = defaultdict(list)
    for m in msgs:
        msgs_by_step[m["step"]].append(m)
    mr_by_step: Dict[int, List[Dict]] = defaultdict(list)
    for r in mr:
        mr_by_step[r["step"]].append(r)

    # 日本語フォント候補(Windows / mac / Linux)
    plt.rcParams["font.family"] = [
        "Yu Gothic",
        "Meiryo",
        "MS Gothic",
        "Hiragino Sans",
        "Noto Sans CJK JP",
        "sans-serif",
    ]
    plt.rcParams["axes.unicode_minus"] = False

    out_frames_dir = run_dir / "frames_with_text"
    out_frames_dir.mkdir(exist_ok=True)

    # レイアウト定数
    WRAP_WIDTH = 32  # テキスト折り返し幅(文字)

    for png_path in pngs:
        step = int(png_path.stem.split("_")[1])

        # 横長の大きめキャンバス。フィールドと右パネルを 1:1.1 で
        fig = plt.figure(figsize=(20, 11), facecolor="#fafafa")
        gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.1], wspace=0.04)
        ax_img = fig.add_subplot(gs[0, 0])
        ax_txt = fig.add_subplot(gs[0, 1])

        # 左:フィールド画像
        img = mpimg.imread(str(png_path))
        ax_img.imshow(img)
        ax_img.axis("off")

        # 右:テキストパネル
        ax_txt.axis("off")
        ax_txt.set_xlim(0, 1)
        ax_txt.set_ylim(0, 1)

        # ============ ヘッダ ============
        ax_txt.add_patch(mpatches.Rectangle(
            (0, 0.955), 1, 0.045,
            transform=ax_txt.transAxes,
            facecolor="#2c3e50", edgecolor="none",
        ))
        ax_txt.text(
            0.5, 0.978, f"Step {step}",
            transform=ax_txt.transAxes, fontsize=22, fontweight="bold",
            verticalalignment="center", horizontalalignment="center",
            color="white",
        )

        # ============ メッセージセクション ============
        msg_section_top = 0.94
        msg_section_bottom = 0.46
        ax_txt.add_patch(mpatches.Rectangle(
            (0, msg_section_bottom), 1, msg_section_top - msg_section_bottom,
            transform=ax_txt.transAxes,
            facecolor="#eef5fc", edgecolor="#1f4e79", linewidth=1,
        ))
        ax_txt.text(
            0.015, msg_section_top - 0.018, "📨 メッセージ(直近)",
            transform=ax_txt.transAxes, fontsize=14, fontweight="bold",
            verticalalignment="top", color="#1f4e79",
        )

        # 直近メッセージ抽出
        recent_msgs: List[tuple] = []
        for s in range(1, step + 1):
            for m in msgs_by_step.get(s, []):
                recent_msgs.append((s, m))
        recent_msgs = recent_msgs[-args.recent:]

        # 固定スロット配置:長さによらず毎フレーム同じ位置に
        # スロット 1 つ = ヘッダ(2 行)+ 本文(2 行)= 約 4 行ぶん。スロット間に少しの余白。
        n_slots = args.recent
        section_inner_top = msg_section_top - 0.04
        section_inner_bottom = msg_section_bottom + 0.01
        slot_height = (section_inner_top - section_inner_bottom) / n_slots
        for i in range(n_slots):
            slot_y_top = section_inner_top - i * slot_height
            if i >= len(recent_msgs):
                continue  # 空スロットは描かない(位置はキープ)
            s, m = recent_msgs[i]
            from_id = m["from"]
            to_id = m["to"]
            from_color = _agent_color(from_id)
            to_color = _agent_color(to_id)
            # ヘッダ 1 行目:送信者
            ax_txt.text(
                0.018, slot_y_top, f"step{s:2d}  {_agent_label(from_id, personas)}",
                transform=ax_txt.transAxes, fontsize=11, fontweight="bold",
                verticalalignment="top", color=from_color,
            )
            # ヘッダ 2 行目:→ 受信者
            ax_txt.text(
                0.04, slot_y_top - 0.020, f"→ {_agent_label(to_id, personas)}",
                transform=ax_txt.transAxes, fontsize=10, fontweight="bold",
                verticalalignment="top", color=to_color,
            )
            # 本文:**常に 2 行**(短ければ空行 / 長ければ省略)
            wrapped = _wrap_fixed_lines(m["message"], WRAP_WIDTH, 2)
            ax_txt.text(
                0.04, slot_y_top - 0.042, wrapped,
                transform=ax_txt.transAxes, fontsize=11,
                verticalalignment="top", color="#222222",
            )

        # ============ 思考セクション ============
        thought_section_top = 0.44
        thought_section_bottom = 0.0
        ax_txt.add_patch(mpatches.Rectangle(
            (0, thought_section_bottom), 1, thought_section_top - thought_section_bottom,
            transform=ax_txt.transAxes,
            facecolor="#f5eef9", edgecolor="#7d3c98", linewidth=1,
        ))
        ax_txt.text(
            0.015, thought_section_top - 0.018, "🧠 思考(現 step)",
            transform=ax_txt.transAxes, fontsize=14, fontweight="bold",
            verticalalignment="top", color="#7d3c98",
        )

        # 固定スロット配置:エージェント数ぶん常に同じ位置
        thoughts = mr_by_step.get(step, [])
        # id でソート(描画順を一定に)
        thoughts_sorted = sorted(thoughts, key=lambda r: r.get("id", 0))
        n_thought_slots = max(len(personas) if personas else len(thoughts_sorted), 1)
        thought_inner_top = thought_section_top - 0.04
        thought_inner_bottom = thought_section_bottom + 0.01
        thought_slot_height = (thought_inner_top - thought_inner_bottom) / n_thought_slots

        # personas があればそれを基準に全エージェントぶんスロットを並べる
        # thoughts は id で索引引き
        thought_by_id: Dict[int, Dict] = {r.get("id", -1): r for r in thoughts_sorted}
        for i in range(n_thought_slots):
            slot_y_top = thought_inner_top - i * thought_slot_height
            aid = i  # スロット i = Agent i
            color = _agent_color(aid)
            label = _agent_label(aid, personas)
            # ヘッダ
            ax_txt.text(
                0.018, slot_y_top, label,
                transform=ax_txt.transAxes, fontsize=11, fontweight="bold",
                verticalalignment="top", color=color,
            )
            r = thought_by_id.get(aid)
            mem = (r.get("memory", "") or "").strip() if r else ""
            rsn = (r.get("reasoning", "") or "").strip() if r else ""
            # 本文を **常に 2 行**(memory が空なら reasoning を出す)
            body = mem if mem else rsn
            prefix = "💭 " if mem else ("📝 " if rsn else "")
            wrapped = _wrap_fixed_lines(f"{prefix}{body}" if body else "", WRAP_WIDTH, 2)
            ax_txt.text(
                0.04, slot_y_top - 0.022, wrapped,
                transform=ax_txt.transAxes, fontsize=10,
                verticalalignment="top", color="#333333",
            )

        out_png = out_frames_dir / png_path.name
        plt.savefig(out_png, dpi=110, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)

    print(f"Composed {len(pngs)} frames -> {out_frames_dir}")

    # ffmpeg で連結
    ffmpeg = args.ffmpeg if shutil.which(args.ffmpeg) else None
    if ffmpeg is None:
        print("ERROR: ffmpeg not found.", file=sys.stderr)
        return 2

    out_path = Path(args.out) if args.out else (run_dir / "simulation_with_text.mp4")
    cmd = [
        ffmpeg,
        "-y" if args.overwrite or not out_path.exists() else "-n",
        "-framerate", str(args.fps),
        "-i", str(out_frames_dir / "frame_%04d.png"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
        str(out_path),
    ]
    print(f"Running: {' '.join(cmd)}")
    proc = subprocess.run(cmd, capture_output=True, text=False)
    if proc.returncode != 0:
        print("FFmpeg failed:")
        try:
            print(proc.stderr.decode("utf-8", errors="replace")[-2000:])
        except Exception:
            print(proc.stderr[-2000:])
        return proc.returncode
    if out_path.exists():
        print(f"Wrote {out_path} ({out_path.stat().st_size / 1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
