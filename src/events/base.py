"""Event 抽象基底。Phase 1 ではほぼ TypedDict のみ + 最小抽象。"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, TypedDict


class FireConfig(TypedDict, total=False):
    """火事イベントの設定(参考実装の utils.py から移植)。"""
    name: str
    start_step: int
    intensity: float
    radius: int
    center_x: int
    center_y: int


class Event(ABC):
    """Event 基底クラス。

    Phase 1 では fire のみ派生。Phase 2 以降で災害・ニュース等を追加する想定。
    """

    @abstractmethod
    def maybe_activate(self, step: int) -> Optional[Dict]:
        """ステップ進行時に呼ばれる。発火条件を満たせば state dict を返す。"""

    @abstractmethod
    def perceived_info(self, agent_position: Tuple[float, float]) -> Optional[Dict]:
        """エージェント位置に対する知覚可能情報を返す(範囲外なら None)。"""


def collect_perceived_events(
    events: List[Event], agent_position: Tuple[float, float]
) -> Optional[List[Dict]]:
    """各 Event から perceived_info を集めて空でないリストを返す。"""
    perceived: List[Dict] = []
    for ev in events:
        info = ev.perceived_info(agent_position)
        if info is not None:
            perceived.append(info)
    return perceived if perceived else None
