"""AlienEvent: 宇宙人(地球外生命体)が来た。

2026-04-29 議事録 §3.2 で採用された創発イベントの 1 つ(プラン B = 未知の発火点)。

設計指針(議事録 §3.4 兵頭氏アドバイス準拠):
- 「**指示を書きすぎない**」。「現在、地球外生命体との接触が確認されています。」程度の粗い投げ込み
- 全 agent に同時通達。位置依存(火事のような距離減衰)はない
"""
from typing import Dict, Optional, Tuple

from .base import Event


class AlienEvent(Event):
    """宇宙人接触イベント。`start_step` で発火し、以降は全 agent が知覚する。"""

    def __init__(
        self,
        name: str = "alien_contact",
        start_step: int = 1,
        prompt_text: str = "現在、地球外生命体との接触が確認されています。",
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
            "kind": "alien",
            "name": self.name,
            "start_step": self.start_step,
            "active": self.active,
            "prompt_text": self.prompt_text,
        }

    def perceived_info(self, agent_position: Tuple[float, float]) -> Optional[Dict]:
        if not self.active:
            return None
        # 位置依存なし。全員に同じ情報。
        return {
            "kind": "alien",
            "name": self.name,
            "prompt_text": self.prompt_text,
        }
