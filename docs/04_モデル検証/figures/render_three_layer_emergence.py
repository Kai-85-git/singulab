"""three_layer_emergence.drawio と等価な「3 層 + 専門家」図を PNG として描画する。

draw.io CLI が無い環境用に matplotlib で同レイアウトを再現する。
配色は Draw.io デフォルトパレットに合わせ、PDF 埋め込み用に高解像度で保存する。

Usage:
    python docs/04_モデル検証/figures/render_three_layer_emergence.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch


def _box(ax, x, y, w, h, label, fill, edge, fontsize=12, fontweight="normal", dashed=False):
    rect = mpatches.FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.3",
        linewidth=1.8, facecolor=fill, edgecolor=edge,
        linestyle="--" if dashed else "-",
    )
    ax.add_patch(rect)
    ax.text(
        x + w / 2, y + h / 2, label,
        ha="center", va="center",
        fontsize=fontsize, fontweight=fontweight,
        color="#222222",
    )
    return (x, y, w, h)


def _down_arrow(ax, x_center, y_top, y_bottom, label=None, color="#666666"):
    arrow = FancyArrowPatch(
        (x_center, y_top), (x_center, y_bottom),
        arrowstyle="-|>", mutation_scale=22, color=color, linewidth=2.0,
    )
    ax.add_patch(arrow)
    if label:
        ax.text(
            x_center + 1.0, (y_top + y_bottom) / 2, label,
            ha="left", va="center", fontsize=10,
            fontstyle="italic", color="#555555",
        )


def render(out_path: Path) -> None:
    plt.rcParams["font.family"] = [
        "Yu Gothic", "Meiryo", "MS Gothic", "Hiragino Sans",
        "Noto Sans CJK JP", "sans-serif",
    ]
    plt.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(10, 9), dpi=180)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor("#ffffff")

    # Draw.io デフォルト配色
    RED_F, RED_E = "#f8cecc", "#b85450"
    YEL_F, YEL_E = "#fff2cc", "#d6b656"
    BLU_F, BLU_E = "#dae8fc", "#6c8ebf"
    GRN_F, GRN_E = "#d5e8d4", "#82b366"

    # タイトル
    ax.text(50, 95, "UFO 出現後の集団分化(Step 21、ピーク 39 体)",
            ha="center", va="center", fontsize=16, fontweight="bold", color="#222222")

    box_w, box_h = 70, 11
    x_left = 15

    # 層 1
    layer1 = _box(ax, x_left, 78, box_w, box_h,
                  "層 1:見た人(~20–40 体)\n"
                  "Mid + Near 圏で UFO を直接視認\n"
                  "UFO の詳細を発話する",
                  RED_F, RED_E, fontsize=12, fontweight="bold")
    _down_arrow(ax, 50, 78, 70, label="会話で伝わる")

    # 層 2
    layer2 = _box(ax, x_left, 59, box_w, box_h,
                  "層 2:聞いた人(~30 体)\n"
                  "会話伝播で UFO を知る\n"
                  "確認質問・伝聞型の発話",
                  YEL_F, YEL_E, fontsize=12, fontweight="bold")
    _down_arrow(ax, 50, 59, 51, label="話題が届かない")

    # 層 3
    layer3 = _box(ax, x_left, 40, box_w, box_h,
                  "層 3:無関心 / 別話題継続(~30–40 体)\n"
                  "personal_context に基づく日常会話を続ける\n"
                  "(犬の散歩・天気・仕事 など)",
                  BLU_F, BLU_E, fontsize=12, fontweight="bold")

    # ＋(別軸)
    ax.text(50, 33, "＋", ha="center", va="center",
            fontsize=30, fontweight="bold", color="#82b366")

    # 専門家モード(別軸として点線で)
    expert = _box(ax, x_left, 16, box_w, 11,
                  "専門家モード(自然発生 / A5 のような役回り)\n"
                  "集団規模ゆえに発生する「説明者役」\n"
                  "周囲の質問に答え続けることでハブ化していく",
                  GRN_F, GRN_E, fontsize=12, fontweight="bold", dashed=True)

    # 注記
    ax.text(50, 9,
            "※ 100 体 × 30 step / prod_v3_alien_100_v2 観察結果",
            ha="center", va="center", fontsize=10, color="#666666")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    here = Path(__file__).parent
    render(here / "three_layer_emergence.png")
