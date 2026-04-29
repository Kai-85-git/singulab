"""Visualizer: 1 ステップごとの状態を PNG フレームとして保存する。

参考実装 [docs/10_共有資料/2d-multi-places-simulation-on-fire-public/visualization.py] を
本プロジェクトの構造に合わせて移植 + クロスプラットフォーム化したもの。

- Windows / Linux / WSL / headless どこでも動くよう **常に Agg バックエンドを採用**
  (フレーム保存が目的で GUI 表示は不要)
- 1 ステップあたり 1 PNG を `<output_dir>/frames/frame_XXXX.png` に書き出す
- mp4 化は別スクリプト [tools/generate_video.py](../../tools/generate_video.py) で実施
"""
from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

import matplotlib

# フレーム保存専用に固定(GUI 表示は不要)
matplotlib.use("Agg")

import matplotlib.patches as patches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

if TYPE_CHECKING:
    from src.agent.agent import Agent

logger = logging.getLogger(__name__)

FIGURE_SIZE = (10, 10)
DPI = 120  # 参考実装は 150 だがファイルサイズを抑える

# Agent
AGENT_SIZE_IN_PLACE = 150
AGENT_SIZE_OUTSIDE = 80
AGENT_ALPHA = 0.7
COMMUNICATION_LINK_ALPHA = 0.3

# Place
PLACE_LINEWIDTH = 2
PLACE_ALPHA = 0.3

# Fire
FIRE_MARKER_SIZE = 200
FIRE_CIRCLE_ALPHA = 0.15
FIRE_CIRCLE_LINEWIDTH = 2

# place type → 背景色
_PLACE_TYPE_COLORS = {
    "office": "lightblue",
    "meeting": "lightgreen",
    "bar": "lightcoral",
    "cafe": "lightyellow",
    "library": "lightpink",
}
_DEFAULT_COLORS = ["lightblue", "lightcoral", "lightgreen", "lightyellow", "lightpink"]


class Visualizer:
    """1 ステップごとに `frame_XXXX.png` を書き出すフレーム保存器。"""

    def __init__(
        self,
        output_dir: str,
        half_space_size: int,
        places: List[Dict],
        frame_interval: int = 1,
    ):
        """
        Args:
            output_dir: run の出力ディレクトリ(ここの下に `frames/` を作る)
            half_space_size: フィールド境界
            places: place 設定リスト
            frame_interval: N ステップに 1 枚保存(1 なら毎ステップ)
        """
        self.frames_dir = os.path.join(output_dir, "frames")
        os.makedirs(self.frames_dir, exist_ok=True)
        self.half_space_size = half_space_size
        self.places = places
        self.frame_interval = max(1, int(frame_interval))
        self.saved_frames = 0

    # ---------- 描画パーツ ----------

    def _setup_axes(self, ax) -> None:
        h = self.half_space_size
        ax.set_xlim(-h, h)
        ax.set_ylim(-h, h)
        ax.set_aspect("equal")
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.grid(True, alpha=0.3)

    def _draw_places(self, ax) -> None:
        for i, place in enumerate(self.places):
            half_size = place["half_size"]
            cx = place["center_x"]
            cy = place["center_y"]
            place_type = place["type"]
            face_color = _PLACE_TYPE_COLORS.get(
                place_type, _DEFAULT_COLORS[i % len(_DEFAULT_COLORS)]
            )
            width = 2 * half_size + 1
            rect = patches.Rectangle(
                (cx - half_size - 0.5, cy - half_size - 0.5),
                width,
                width,
                linewidth=PLACE_LINEWIDTH,
                edgecolor="blue",
                facecolor=face_color,
                alpha=PLACE_ALPHA,
                label=f"{place['name']} ({place_type})",
            )
            ax.add_patch(rect)
            ax.text(
                cx,
                cy,
                f"{place['name']}\n({place_type})",
                fontsize=9,
                ha="center",
                va="center",
                weight="bold",
                color="darkblue",
            )

    def _draw_fires(self, ax, fire_states: List[Dict]) -> None:
        try:
            cmap = matplotlib.colormaps["YlOrRd"]
        except (AttributeError, KeyError):
            cmap = matplotlib.cm.get_cmap("YlOrRd")
        for fire in fire_states:
            if not fire.get("active"):
                continue
            fx, fy = fire["position"]
            radius = fire["radius"]
            intensity = float(fire["intensity"])
            face_color = cmap(intensity)
            circle = patches.Circle(
                (fx, fy),
                radius,
                linewidth=FIRE_CIRCLE_LINEWIDTH,
                edgecolor="red",
                facecolor=face_color,
                alpha=FIRE_CIRCLE_ALPHA + 0.1,
                linestyle="--",
            )
            ax.add_patch(circle)
            ax.scatter(
                fx,
                fy,
                c="red",
                s=FIRE_MARKER_SIZE,
                marker="^",
                edgecolors="darkred",
                linewidths=2,
                zorder=10,
            )
            ax.text(
                fx,
                fy - 1.5,
                f"{fire.get('name', 'fire')}\n(int={intensity})",
                fontsize=8,
                ha="center",
                va="top",
                color="darkred",
                fontweight="bold",
            )

    def _draw_communication_links(
        self, ax, agents: List["Agent"], comm_radius: float
    ) -> None:
        if comm_radius is None or comm_radius <= 0:
            return
        for i, a1 in enumerate(agents):
            for a2 in agents[i + 1 :]:
                dist = a1.distance_to(a2.position)
                same_area = (not a1.in_place and not a2.in_place) or (
                    a1.in_place
                    and a2.in_place
                    and a1.current_place == a2.current_place
                )
                if dist <= comm_radius and same_area:
                    ax.plot(
                        [a1.position[0], a2.position[0]],
                        [a1.position[1], a2.position[1]],
                        "gray",
                        alpha=COMMUNICATION_LINK_ALPHA,
                        linewidth=1,
                    )

    def _draw_agents(self, ax, agents: List["Agent"]) -> None:
        for agent in agents:
            color = "blue" if agent.gender == "male" else "red"
            if agent.in_place and agent.current_place:
                marker = "*"
                size = AGENT_SIZE_IN_PLACE
            else:
                marker = "o"
                size = AGENT_SIZE_OUTSIDE
            ax.scatter(
                agent.position[0],
                agent.position[1],
                c=color,
                s=size,
                marker=marker,
                alpha=AGENT_ALPHA,
                edgecolors="black",
                linewidths=1,
            )
            ax.text(
                agent.position[0] + 0.5,
                agent.position[1] + 0.5,
                str(agent.id),
                fontsize=8,
                ha="left",
            )

    # ---------- メイン API ----------

    def save_frame(
        self,
        step: int,
        agents: List["Agent"],
        place_status: Dict,
        fire_states: Optional[List[Dict]] = None,
        comm_radius: Optional[float] = None,
    ) -> Optional[str]:
        """1 ステップ分のフレームを保存。frame_interval を満たさない場合は何もしない。"""
        if step % self.frame_interval != 0:
            return None

        fig, ax = plt.subplots(figsize=FIGURE_SIZE)
        try:
            self._setup_axes(ax)
            self._draw_places(ax)
            if fire_states:
                self._draw_fires(ax, fire_states)
            if comm_radius:
                self._draw_communication_links(ax, agents, comm_radius)
            self._draw_agents(ax, agents)

            # タイトル
            title_parts = [f"Step {step}"]
            if "places" in place_status:
                title_parts.append(
                    f"in places: {place_status['agents_in_place']} "
                    f"({place_status['occupancy_rate']:.0%})"
                )
                for pname, st in place_status["places"].items():
                    title_parts.append(
                        f"{pname}: {st['agents_in_place']}/{st['capacity']}"
                    )
            ax.set_title(" | ".join(title_parts), fontsize=11, fontweight="bold")

            # 凡例(性別 × in_place)
            legend_elements = [
                Line2D([0], [0], marker="o", color="w", markerfacecolor="blue",
                       markersize=8, label="Male (outside)"),
                Line2D([0], [0], marker="o", color="w", markerfacecolor="red",
                       markersize=8, label="Female (outside)"),
                Line2D([0], [0], marker="*", color="w", markerfacecolor="blue",
                       markersize=12, label="Male (in place)"),
                Line2D([0], [0], marker="*", color="w", markerfacecolor="red",
                       markersize=12, label="Female (in place)"),
            ]
            active_fires = [f for f in (fire_states or []) if f.get("active")]
            if active_fires:
                for f in active_fires:
                    legend_elements.append(
                        Line2D([0], [0], marker="^", color="w", markerfacecolor="red",
                               markeredgecolor="darkred", markersize=10,
                               label=f"{f.get('name', 'Fire')} (int={f['intensity']})")
                    )
            ax.legend(handles=legend_elements, loc="upper right", fontsize=8)

            path = os.path.join(self.frames_dir, f"frame_{step:04d}.png")
            fig.savefig(path, dpi=DPI, bbox_inches="tight")
            self.saved_frames += 1
            return path
        finally:
            plt.close(fig)
