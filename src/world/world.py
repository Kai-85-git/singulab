"""World: 1 階(物)の中央管理クラス。

設計書 [03_1階-物/07_実装方針 §2.3](../../docs/01_設計書/03_1階-物/07_実装方針.md) に基づく。

- place の所在判定(入れ子優先順位を含む)
- フィールド境界(clamp)
- capacity 強制 + 入室拒否
- 移動の中央管理(World.attempt_move)+ events 発生

Phase 2 で導入。Phase 1 の Simulation から `agent.move()` 直叩きを廃止する。
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from .field import Field
from .place import PlaceConfig, get_place_at_position

if TYPE_CHECKING:
    from src.agent.agent import Agent

# Direction → (dx, dy)
_DIRECTION_MAP: Dict[str, Tuple[int, int]] = {
    "up": (0, 1),
    "down": (0, -1),
    "left": (-1, 0),
    "right": (1, 0),
}


class World:
    """1 階(物)の中央管理クラス。

    Args:
        places: place 設定のリスト
        half_space_size: フィールド境界(中心 0、±half_space_size)
    """

    def __init__(self, places: List[PlaceConfig], half_space_size: int):
        self.places = places
        self.field = Field(half_space_size)
        self._validate()

    def _validate(self) -> None:
        names = [p["name"] for p in self.places]
        if len(names) != len(set(names)):
            raise ValueError("Place name must be unique")
        for p in self.places:
            if p["half_size"] <= 0:
                raise ValueError(f"Place '{p['name']}' has non-positive half_size")
            if p["capacity"] <= 0:
                raise ValueError(f"Place '{p['name']}' has non-positive capacity")

    # ---------- 所在判定 ----------

    def resolve_place(self, position: Tuple[int, int]) -> Optional[PlaceConfig]:
        """位置を含む place を返す(入れ子優先 = half_size 最小)。"""
        return get_place_at_position(position, self.places)

    def occupancy(self, agents: List["Agent"]) -> Dict[str, int]:
        """place 名 → 現在の人数。"""
        result: Dict[str, int] = {p["name"]: 0 for p in self.places}
        for a in agents:
            if a.current_place and a.current_place in result:
                result[a.current_place] += 1
        return result

    def get_place(self, name: str) -> Optional[PlaceConfig]:
        return next((p for p in self.places if p["name"] == name), None)

    # ---------- 移動 ----------

    def attempt_move(
        self,
        agent: "Agent",
        direction: str,
        all_agents: List["Agent"],
    ) -> Tuple[Tuple[int, int], List[Dict]]:
        """エージェントを direction 方向に 1 ステップ動かそうと試みる。

        Returns:
            (final_position, events): 最終位置と発生したイベントのリスト

        ルール:
            1. フィールド境界外なら clamp(`clamp_to_field` イベント)
            2. 移動先に **別の** place があり、そこが capacity 上限に達していれば
               入室拒否(`place_entry_denied` イベント、位置は元のまま)
            3. 異なる place への遷移成立で `place_change` イベント
        """
        events: List[Dict] = []
        x, y = agent.position
        dx, dy = _DIRECTION_MAP.get(direction, (0, 0))
        intended = (x + dx, y + dy)
        clamped = self.field.clamp(intended)

        # Clamp 検出
        if clamped != intended:
            events.append(
                {
                    "type": "clamp_to_field",
                    "agent_id": agent.id,
                    "attempted_pos": list(intended),
                    "clamped_pos": list(clamped),
                }
            )

        # 移動先の place を判定
        target_place = self.resolve_place(clamped)
        current_place_name = agent.current_place

        # capacity 強制(別の place に入ろうとする場合のみチェック)
        if target_place is not None and target_place["name"] != current_place_name:
            others = sum(
                1
                for a in all_agents
                if a.current_place == target_place["name"] and a.id != agent.id
            )
            if others >= target_place["capacity"]:
                events.append(
                    {
                        "type": "place_entry_denied",
                        "agent_id": agent.id,
                        "place_id": target_place["name"],
                        "current_place": current_place_name,
                        "occupancy": others,
                        "capacity": target_place["capacity"],
                    }
                )
                # 入室拒否 → 元位置維持(place_change も発火しない)
                return (agent.position, events)

        # 通常の遷移完了
        new_place_name = target_place["name"] if target_place else None
        if new_place_name != current_place_name:
            events.append(
                {
                    "type": "place_change",
                    "agent_id": agent.id,
                    "from": current_place_name,
                    "to": new_place_name,
                }
            )

        agent.position = clamped
        agent.total_moves += 1
        return (clamped, events)

    # ---------- 初期配置 ----------

    def random_position_in_place(
        self,
        place_name: str,
        rng,  # random module / Random instance
    ) -> Tuple[int, int]:
        """指定 place 内の一様乱数位置を返す。"""
        p = self.get_place(place_name)
        if p is None:
            raise ValueError(f"Unknown place: {place_name}")
        return (
            rng.randint(p["center_x"] - p["half_size"], p["center_x"] + p["half_size"]),
            rng.randint(p["center_y"] - p["half_size"], p["center_y"] + p["half_size"]),
        )

    def random_position_outside_places(self, rng, max_attempts: int = 1000) -> Optional[Tuple[int, int]]:
        """場所外の一様乱数位置を返す(見つからなければ None)。"""
        h = self.field.half_space_size
        for _ in range(max_attempts):
            pos = (rng.randint(-h, h), rng.randint(-h, h))
            if self.resolve_place(pos) is None:
                return pos
        return None
