"""コミュニケーション物理: 到達距離 + 同一エリア判定。

設計書 [05_3階-物理-重力/03_コミュニケーション到達距離 §5](../../docs/01_設計書/05_3階-物理-重力/03_コミュニケーション到達距離.md) に基づく。

Phase 2-3 で実装するのは determine_recipients のみ。遅延キュー(B3-02)は Phase 3 以降。
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING, List

from .base import WorldLaws

if TYPE_CHECKING:
    from src.agent.agent import Agent


class CommunicationPhysics:
    """発話の到達範囲を判定する物理層。"""

    def __init__(self, laws: WorldLaws):
        self.laws = laws

    def determine_recipients(
        self,
        sender: "Agent",
        all_agents: List["Agent"],
    ) -> List["Agent"]:
        """sender の発話が届く受信者リストを返す。

        ルール:
            1. 同一エリア(両者とも outside、または両者とも同じ place 内)
            2. ユークリッド距離が `comm_radius_for(sender.current_place)` 以下

        Phase 1 までの `Agent.get_nearby_agents` の責務を引き取った形。
        """
        r = self.laws.comm_radius_for(sender.current_place)
        recipients: List["Agent"] = []
        for a in all_agents:
            if a.id == sender.id:
                continue
            same_area = (not sender.in_place and not a.in_place) or (
                sender.in_place
                and a.in_place
                and sender.current_place == a.current_place
            )
            if not same_area:
                continue
            if self._distance(sender.position, a.position) <= r:
                recipients.append(a)
        return recipients

    @staticmethod
    def _distance(p1, p2) -> float:
        dx = p1[0] - p2[0]
        dy = p1[1] - p2[1]
        return math.sqrt(dx * dx + dy * dy)
