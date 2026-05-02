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

# Alien(2026-04-30 追補:UFO っぽい marker)
ALIEN_MARKER_SIZE = 400
ALIEN_HALO_RADIUS_RATIO = 0.3  # half_space_size に対する円のサイズ
ALIEN_COLOR = "#7B2CBF"          # 紫(SF っぽい)
ALIEN_HALO_ALPHA = 0.15

# Zero Gravity(全体に効く効果なので枠 + バナー)
ZERO_GRAVITY_BORDER_COLOR = "#0096C7"  # 青系
ZERO_GRAVITY_BORDER_LW = 6
ZERO_GRAVITY_BORDER_ALPHA = 0.4

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

    def _draw_aliens(self, ax, alien_states: List[Dict], current_step: int) -> None:
        """宇宙人イベントの視覚化。

        2026-05-01 追補(ユーザフィードバック):**発火 step では「ARRIVED!」フラッシュ**を出す。
        以降の step は通常の UFO 表示。これでイベント発生の瞬間が一目でわかる。
        """
        for ali in alien_states:
            if not ali.get("active"):
                continue
            pos = ali.get("position")
            if pos is None:
                continue
            x, y = pos
            activated_step = ali.get("activated_step")
            is_arrival = activated_step is not None and current_step == activated_step
            radius = max(2, int(self.half_space_size * ALIEN_HALO_RADIUS_RATIO))

            # ハロ(降下範囲のような円)— 発火 step は赤強調、以降は紫
            halo_color = "red" if is_arrival else ALIEN_COLOR
            halo_alpha = 0.35 if is_arrival else ALIEN_HALO_ALPHA
            ax.add_patch(
                patches.Circle(
                    (x, y),
                    radius * (1.4 if is_arrival else 1.0),
                    linewidth=3 if is_arrival else 2,
                    edgecolor=halo_color,
                    facecolor=halo_color,
                    alpha=halo_alpha,
                    linestyle=":",
                )
            )

            # UFO マーカー
            ax.scatter(
                x, y,
                c=ALIEN_COLOR,
                s=ALIEN_MARKER_SIZE * (1.5 if is_arrival else 1.0),
                marker="D",
                edgecolors="white",
                linewidths=2,
                zorder=11,
            )
            ax.scatter(
                x, y,
                c="white",
                s=ALIEN_MARKER_SIZE * 0.4 * (1.5 if is_arrival else 1.0),
                marker="o",
                edgecolors=ALIEN_COLOR,
                linewidths=2,
                zorder=12,
            )

            # 発火 step は「ARRIVED!」を画面中央上部に大きく
            if is_arrival:
                ax.text(
                    0,
                    self.half_space_size - 1.0,
                    f"👽 ALIEN ARRIVED at ({x}, {y})!",
                    fontsize=18,
                    ha="center",
                    va="top",
                    color="red",
                    fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.5",
                              facecolor="yellow",
                              edgecolor="red",
                              linewidth=3,
                              alpha=0.95),
                    zorder=20,
                )
                ax.text(
                    x,
                    y - radius * 1.4 - 0.5,
                    f"👽 {ali.get('name', 'alien')} 着地!",
                    fontsize=12,
                    ha="center",
                    va="top",
                    color="red",
                    fontweight="bold",
                )
            else:
                # 通常表示(発火後)
                steps_since = (current_step - activated_step) if activated_step else 0
                ax.text(
                    x,
                    y - radius - 0.5,
                    f"👽 {ali.get('name', 'alien')}\n(着地+{steps_since})",
                    fontsize=10,
                    ha="center",
                    va="top",
                    color=ALIEN_COLOR,
                    fontweight="bold",
                )

    def _draw_zero_gravity(self, ax, zg_states: List[Dict], current_step: int) -> None:
        """無重力イベントの視覚化(全体は局所性なし → 枠を青く塗る + 上部にバナー)。

        2026-05-01 追補(ユーザフィードバック):**発火 step では赤い「STARTED!」フラッシュ**で
        瞬間がわかるようにする。以降の step は通常の青枠 + バナー(step+N 表示)。
        """
        active_zgs = [z for z in zg_states if z.get("active")]
        if not active_zgs:
            return

        h = self.half_space_size

        # 発火 step かどうかを判定(複数 zero_gravity event の最初の発火)
        is_start = any(
            z.get("activated_step") is not None and current_step == z["activated_step"]
            for z in active_zgs
        )
        # 発火後の経過 step
        first_zg = active_zgs[0]
        activated_step = first_zg.get("activated_step")
        steps_since = (current_step - activated_step) if activated_step else 0

        # 枠 — 発火 step は赤太枠、以降は青枠
        border_color = "red" if is_start else ZERO_GRAVITY_BORDER_COLOR
        border_lw = ZERO_GRAVITY_BORDER_LW * 2 if is_start else ZERO_GRAVITY_BORDER_LW
        border_alpha = 0.7 if is_start else ZERO_GRAVITY_BORDER_ALPHA
        border = patches.Rectangle(
            (-h - 0.5, -h - 0.5),
            2 * h + 1,
            2 * h + 1,
            linewidth=border_lw,
            edgecolor=border_color,
            facecolor="none",
            alpha=border_alpha,
        )
        ax.add_patch(border)

        # バナー — 発火 step は赤大きく、以降は青小さく
        if is_start:
            ax.text(
                0,
                h - 1.0,
                "⚠️ ZERO GRAVITY STARTED! ⚠️",
                fontsize=20,
                ha="center",
                va="top",
                color="red",
                fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.6",
                          facecolor="yellow",
                          edgecolor="red",
                          linewidth=3,
                          alpha=0.95),
                zorder=20,
            )
            # フィールド全体に薄い赤オーバーレイ(危機感を演出)
            overlay = patches.Rectangle(
                (-h - 0.5, -h - 0.5),
                2 * h + 1,
                2 * h + 1,
                linewidth=0,
                facecolor="red",
                alpha=0.08,
                zorder=1,
            )
            ax.add_patch(overlay)
        else:
            ax.text(
                0,
                h - 1.0,
                f"⚠️ ZERO GRAVITY (step {activated_step}〜 / +{steps_since}) ⚠️",
                fontsize=14,
                ha="center",
                va="top",
                color=ZERO_GRAVITY_BORDER_COLOR,
                fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.4",
                          facecolor="white",
                          edgecolor=ZERO_GRAVITY_BORDER_COLOR,
                          alpha=0.9),
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
        # 2026-05-02 追加:エージェント数に応じてマーカーサイズを動的に縮小。
        # 100 体規模で「ぎゅうぎゅう詰め」に見える視覚バイアスを軽減。
        # 5 体ランは従来サイズを維持(後方互換)。
        n = len(agents)
        if n <= 10:
            size_in_place = AGENT_SIZE_IN_PLACE
            size_outside = AGENT_SIZE_OUTSIDE
        elif n <= 30:
            size_in_place = 80
            size_outside = 40
        elif n <= 60:
            size_in_place = 45
            size_outside = 22
        else:  # 60+(100 体クラス)
            size_in_place = 25
            size_outside = 12
        for agent in agents:
            color = "blue" if agent.gender == "male" else "red"
            if agent.in_place and agent.current_place:
                marker = "*"
                size = size_in_place
            else:
                marker = "o"
                size = size_outside
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
        event_states: Optional[List[Dict]] = None,
    ) -> Optional[str]:
        """1 ステップ分のフレームを保存。frame_interval を満たさない場合は何もしない。

        2026-04-30 改訂(ユーザフィードバック):
        `event_states`(全 event 種別)を受け取り、`kind` で振り分けて描画する。
        旧 `fire_states` は後方互換のため残す(火事のみ渡された場合の経路)。
        """
        if step % self.frame_interval != 0:
            return None

        # 後方互換:`fire_states` のみ渡されたら `event_states` に統合する
        merged_events: List[Dict] = list(event_states or [])
        if fire_states:
            for fs in fire_states:
                if "kind" not in fs:
                    fs = {**fs, "kind": "fire"}
                merged_events.append(fs)

        fig, ax = plt.subplots(figsize=FIGURE_SIZE)
        try:
            self._setup_axes(ax)
            self._draw_places(ax)
            # kind 別に振り分け
            fires = [e for e in merged_events if e.get("kind") == "fire" and e.get("active")]
            aliens = [e for e in merged_events if e.get("kind") == "alien" and e.get("active")]
            zgs = [e for e in merged_events if e.get("kind") == "zero_gravity" and e.get("active")]
            if fires:
                self._draw_fires(ax, fires)
            if aliens:
                self._draw_aliens(ax, aliens, current_step=step)
            if zgs:
                self._draw_zero_gravity(ax, zgs, current_step=step)
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
            active_fires = [f for f in merged_events if f.get("kind") == "fire" and f.get("active")]
            for f in active_fires:
                legend_elements.append(
                    Line2D([0], [0], marker="^", color="w", markerfacecolor="red",
                           markeredgecolor="darkred", markersize=10,
                           label=f"{f.get('name', 'Fire')} (int={f.get('intensity', 1)})")
                )
            for a in aliens:
                legend_elements.append(
                    Line2D([0], [0], marker="D", color="w", markerfacecolor=ALIEN_COLOR,
                           markeredgecolor="white", markersize=10,
                           label=f"👽 {a.get('name', 'alien')}")
                )
            if zgs:
                legend_elements.append(
                    Line2D([0], [0], marker="s", color="w",
                           markerfacecolor="none", markeredgecolor=ZERO_GRAVITY_BORDER_COLOR,
                           markersize=10, markeredgewidth=2,
                           label="⚠️ Zero Gravity")
                )
            ax.legend(handles=legend_elements, loc="upper right", fontsize=8)

            path = os.path.join(self.frames_dir, f"frame_{step:04d}.png")
            fig.savefig(path, dpi=DPI, bbox_inches="tight")
            self.saved_frames += 1
            return path
        finally:
            plt.close(fig)
