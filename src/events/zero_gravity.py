"""ZeroGravityEvent: 無重力状態が発生。

2026-04-29 議事録 §3.2 で採用された創発イベントの 1 つ(プラン B = 未知の発火点)。

設計指針(議事録 §3.4 兵頭氏アドバイス準拠):
- 「**指示を書きすぎない**」。「現在、無重力状態が発生しています。物理法則が崩壊しています。」程度の粗い投げ込み
- 全 agent に同時通達
- 移動を物理的に止める実装は今回入れない(プロンプトのみで反応を観察)
"""
from typing import Dict, Optional, Tuple

from .base import Event


class ZeroGravityEvent(Event):
    """無重力イベント。`start_step` で発火し、以降は全 agent が知覚する。"""

    def __init__(
        self,
        name: str = "zero_gravity",
        start_step: int = 1,
        prompt_text: str = "現在、無重力状態が発生しています。物理法則が崩壊しています。",
    ) -> None:
        self.name = name
        self.start_step = start_step
        self.prompt_text = prompt_text
        self.active = False
        self.activated_step: Optional[int] = None

    def maybe_activate(self, step: int) -> Optional[Dict]:
        if self.active or step < self.start_step:
            return None
        self.active = True
        self.activated_step = step
        return self.state()

    def state(self) -> Dict:
        return {
            "kind": "zero_gravity",
            "name": self.name,
            "start_step": self.start_step,
            "activated_step": self.activated_step,  # 発生フラッシュ判定用(2026-05-01)
            "active": self.active,
            "position": None,  # global event = 位置なし。視覚化は枠 + バナー
            "prompt_text": self.prompt_text,
        }

    def perceived_info(self, agent_position: Tuple[float, float]) -> Optional[Dict]:
        if not self.active:
            return None
        return {
            "kind": "zero_gravity",
            "name": self.name,
            "prompt_text": self.prompt_text,
        }
