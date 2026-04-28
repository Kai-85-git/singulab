"""3階(世界の法則)の値オブジェクト。

設計書 [05_3階-物理-重力/07_実装方針 §3.1](../../docs/01_設計書/05_3階-物理-重力/07_実装方針.md) に基づく。

Phase 2-3 で B3-04(WorldLaws + バリデーション)・B3-01(communication_radius_overrides)を実装。
B3-02(message_delay 強制)は値の保持だけで、配送キューは Phase 3 以降に後送。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional


_DEFAULTS: Dict[str, Any] = {
    "communication_radius": 5.0,
    "communication_radius_overrides": {},
    "cognitive_limit": 30,
    "message_delay": {
        "same_place_near": 0,
        "same_place_far": 1,
        "cross_place": 3,
    },
}


@dataclass(frozen=True)
class MessageDelay:
    """情報伝達の遅延設定(Phase 2-3 では値の保持のみ。配送キューは未実装)。"""

    same_place_near: int = 0
    same_place_far: int = 1
    cross_place: int = 3

    def __post_init__(self) -> None:
        for name in ("same_place_near", "same_place_far", "cross_place"):
            v = getattr(self, name)
            if not isinstance(v, int) or v < 0:
                raise ValueError(f"message_delay.{name} must be non-negative int (got {v!r})")


@dataclass(frozen=True)
class WorldLaws:
    """3 階(世界の法則)の値オブジェクト。1 シミュレーション中で不変(frozen)。"""

    communication_radius: float = 5.0
    communication_radius_overrides: Dict[str, float] = field(default_factory=dict)
    cognitive_limit: int = 30
    message_delay: MessageDelay = field(default_factory=MessageDelay)

    def __post_init__(self) -> None:
        if not isinstance(self.communication_radius, (int, float)) or self.communication_radius <= 0:
            raise ValueError(
                f"communication_radius must be positive (got {self.communication_radius!r})"
            )
        for k, v in self.communication_radius_overrides.items():
            if not isinstance(v, (int, float)) or v <= 0:
                raise ValueError(
                    f"communication_radius_overrides[{k!r}] must be positive (got {v!r})"
                )
        if not isinstance(self.cognitive_limit, int) or self.cognitive_limit <= 0:
            raise ValueError(
                f"cognitive_limit must be positive int (got {self.cognitive_limit!r})"
            )

    @classmethod
    def from_config(cls, cfg: Optional[Mapping[str, Any]]) -> "WorldLaws":
        """`config['world_laws']` の dict から構築。設定なしなら全項目デフォルト。"""
        cfg = cfg or {}
        delay_cfg = cfg.get("message_delay") or _DEFAULTS["message_delay"]
        delay = MessageDelay(
            same_place_near=delay_cfg.get("same_place_near", _DEFAULTS["message_delay"]["same_place_near"]),
            same_place_far=delay_cfg.get("same_place_far", _DEFAULTS["message_delay"]["same_place_far"]),
            cross_place=delay_cfg.get("cross_place", _DEFAULTS["message_delay"]["cross_place"]),
        )
        return cls(
            communication_radius=cfg.get("communication_radius", _DEFAULTS["communication_radius"]),
            communication_radius_overrides=dict(cfg.get("communication_radius_overrides", {}) or {}),
            cognitive_limit=cfg.get("cognitive_limit", _DEFAULTS["cognitive_limit"]),
            message_delay=delay,
        )

    def comm_radius_for(self, place_id: Optional[str]) -> float:
        """指定 place の到達距離を返す(override があれば上書き)。"""
        if place_id and place_id in self.communication_radius_overrides:
            return self.communication_radius_overrides[place_id]
        return self.communication_radius

    def to_metadata(self) -> Dict[str, Any]:
        return {
            "communication_radius": self.communication_radius,
            "communication_radius_overrides": dict(self.communication_radius_overrides),
            "cognitive_limit": self.cognitive_limit,
            "message_delay": {
                "same_place_near": self.message_delay.same_place_near,
                "same_place_far": self.message_delay.same_place_far,
                "cross_place": self.message_delay.cross_place,
            },
        }
