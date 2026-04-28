"""FireEvent: 参考実装の fire_states ロジックを Event 派生クラスに集約。"""
import math
import random
from typing import Dict, Optional, Tuple

from .base import Event


class FireEvent(Event):
    """火事イベント。

    Args:
        name: 識別子
        start_step: 発火するステップ
        intensity: 0.0〜1.0
        radius: 知覚可能距離
        center: 中心座標(指定なしなら maybe_activate 時に乱数生成)
        random_position_range: 乱数生成時の範囲(half_space_size を渡す)
    """

    def __init__(
        self,
        name: str,
        start_step: int,
        intensity: float,
        radius: int,
        center: Optional[Tuple[int, int]] = None,
        random_position_range: int = 25,
    ):
        self.name = name
        self.start_step = start_step
        self.intensity = intensity
        self.radius = radius
        self.center = center
        self.random_position_range = random_position_range
        self.active = False
        self.activated_step: Optional[int] = None

    def maybe_activate(self, step: int) -> Optional[Dict]:
        if self.active or step < self.start_step:
            return None
        if self.center is None:
            r = self.random_position_range
            self.center = (random.randint(-r, r), random.randint(-r, r))
        self.active = True
        self.activated_step = step
        return self.state()

    def state(self) -> Dict:
        return {
            "name": self.name,
            "position": self.center,
            "intensity": self.intensity,
            "radius": self.radius,
            "start_step": self.start_step,
            "active": self.active,
        }

    def perceived_info(self, agent_position: Tuple[float, float]) -> Optional[Dict]:
        if not self.active or self.center is None:
            return None
        dx = agent_position[0] - self.center[0]
        dy = agent_position[1] - self.center[1]
        distance = math.sqrt(dx * dx + dy * dy)
        if distance > self.radius:
            return None
        return {
            "name": self.name,
            "fire_position": self.center,
            "intensity": self.intensity,
            "radius": self.radius,
            "agent_distance": round(distance, 2),
        }
