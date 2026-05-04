"""architecture.drawio と等価なアーキテクチャ図を PNG として描画する。

draw.io CLI が無い環境用に matplotlib で同レイアウトを再現する。
配色は draw.io デフォルトパレットに合わせ、PDF 埋め込みでも見やすい高解像度で保存する。

Usage:
    python docs/01_設計書/06_システム設計/01_アーキテクチャ概要/render_architecture.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
from matplotlib.path import Path as MPath


def _box(ax, x, y, w, h, label, fill, edge, fontsize=11, fontweight="normal"):
    """角丸長方形 + ラベル(中央揃え)を描画する。"""
    rect = mpatches.FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.15",
        linewidth=1.6, facecolor=fill, edgecolor=edge,
    )
    ax.add_patch(rect)
    ax.text(
        x + w / 2, y + h / 2, label,
        ha="center", va="center",
        fontsize=fontsize, fontweight=fontweight,
        color="#222222",
    )
    return (x, y, w, h)


def _cylinder(ax, x, y, w, h, label, fill, edge, fontsize=10):
    """データストア風シリンダ + ラベル。"""
    # 円弧の高さ
    cap_h = h * 0.18
    body_top_y = y + h - cap_h / 2
    # 本体(長方形部分)
    rect = mpatches.Rectangle(
        (x, y + cap_h / 2), w, h - cap_h,
        linewidth=1.5, facecolor=fill, edgecolor=edge,
    )
    ax.add_patch(rect)
    # 上ふた(楕円)
    top = mpatches.Ellipse(
        (x + w / 2, body_top_y),
        w, cap_h,
        linewidth=1.5, facecolor=fill, edgecolor=edge,
    )
    ax.add_patch(top)
    # 底ふた(楕円の下半分のみ見えるように後ろに置く)
    bottom = mpatches.Ellipse(
        (x + w / 2, y + cap_h / 2),
        w, cap_h,
        linewidth=1.5, facecolor=fill, edgecolor=edge,
    )
    ax.add_patch(bottom)
    # ラベル
    ax.text(
        x + w / 2, y + h / 2, label,
        ha="center", va="center",
        fontsize=fontsize, color="#222222",
    )


def _arrow(ax, src, dst, color="#666666"):
    """L 字型のオルソゴナル矢印(箱の縁から箱の縁へ)。"""
    sx, sy, sw, sh = src
    dx, dy, dw, dh = dst
    src_cx = sx + sw / 2
    src_cy = sy + sh / 2
    dst_cx = dx + dw / 2
    dst_cy = dy + dh / 2

    # 出口・入口の補正:src の下端から、dst の上端へ
    # ただし水平方向にずれている場合は L 字
    start = (src_cx, sy)  # src 下端中央
    end = (dst_cx, dy + dh)  # dst 上端中央

    if abs(src_cx - dst_cx) > 5:
        # L 字経路
        verts = [start, (src_cx, (sy + dy + dh) / 2), (dst_cx, (sy + dy + dh) / 2), end]
        codes = [MPath.MOVETO, MPath.LINETO, MPath.LINETO, MPath.LINETO]
        path = MPath(verts, codes)
        patch = mpatches.PathPatch(path, fill=False, edgecolor=color, linewidth=1.4)
        ax.add_patch(patch)
        # 矢印先端
        arrow = FancyArrowPatch(
            (dst_cx, (sy + dy + dh) / 2 - 0.5), end,
            arrowstyle="-|>", mutation_scale=14, color=color, linewidth=1.4,
        )
        ax.add_patch(arrow)
    else:
        # 直線
        arrow = FancyArrowPatch(
            start, end,
            arrowstyle="-|>", mutation_scale=14, color=color, linewidth=1.4,
        )
        ax.add_patch(arrow)


def render(out_path: Path) -> None:
    plt.rcParams["font.family"] = [
        "Yu Gothic", "Meiryo", "MS Gothic", "Hiragino Sans",
        "Noto Sans CJK JP", "sans-serif",
    ]
    plt.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(14, 6.5), dpi=180)
    ax.set_xlim(0, 120)
    ax.set_ylim(8, 60)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor("#ffffff")

    # 配色は Draw.io デフォルトパレットに準拠
    BLUE_F, BLUE_E = "#dae8fc", "#6c8ebf"
    GREEN_F, GREEN_E = "#d5e8d4", "#82b366"
    YELLOW_F, YELLOW_E = "#fff2cc", "#d6b656"
    RED_F, RED_E = "#f8cecc", "#b85450"
    PURPLE_F, PURPLE_E = "#e1d5e7", "#9673a6"
    ORANGE_F, ORANGE_E = "#fad7ac", "#b46504"

    # 上段:Simulation Engine(中央)
    sim = _box(ax, 46, 50, 28, 7,
               "Simulation Engine\n5 体・100 体 × 30 step",
               BLUE_F, BLUE_E, fontsize=12, fontweight="bold")

    # 左ブランチ:LLM スタック
    llm = _box(ax, 14, 38, 24, 6,
               "AsyncLLMClient\nOpenAI 互換 + Semaphore 8",
               GREEN_F, GREEN_E, fontsize=10)
    ollama = _box(ax, 16, 26, 20, 6,
                  "Ollama\nlocalhost:11434",
                  YELLOW_F, YELLOW_E, fontsize=10)
    qwen = _box(ax, 6, 14, 16, 5,
                "Qwen3 4B\nabliterated",
                RED_F, RED_E, fontsize=9)
    llama = _box(ax, 28, 14, 16, 5,
                 "Llama 3.2 3B\nabliterated",
                 RED_F, RED_E, fontsize=9)

    # 右ブランチ:RunLogger + 5 jsonl(1 段に横並び)
    rl = _box(ax, 60, 38, 50, 6,
              "RunLogger",
              PURPLE_F, PURPLE_E, fontsize=12, fontweight="bold")

    # 5 jsonl を 1 行に
    log_w, log_h = 11, 5
    y_log = 22
    logs = [
        ("llm_io.jsonl",     54, y_log),
        ("perf.jsonl",       66.5, y_log),
        ("vram.jsonl",       79, y_log),
        ("events.jsonl",     91.5, y_log),
        ("emergence.jsonl", 104, y_log),
    ]

    log_boxes = []
    for label, lx, ly in logs:
        _cylinder(ax, lx, ly, log_w, log_h, label, ORANGE_F, ORANGE_E, fontsize=9)
        log_boxes.append((lx, ly, log_w, log_h))

    # 矢印
    _arrow(ax, sim, llm)
    _arrow(ax, llm, ollama)
    _arrow(ax, ollama, qwen)
    _arrow(ax, ollama, llama)
    _arrow(ax, sim, rl)
    for box in log_boxes:
        _arrow(ax, rl, box)

    # 図のキャプションは PDF 側で付ける(ここでは余白だけ)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    here = Path(__file__).parent
    render(here / "architecture.png")
