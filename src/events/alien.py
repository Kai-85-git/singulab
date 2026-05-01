"""AlienEvent: 宇宙人(地球外生命体)が来た。

2026-04-29 議事録 §3.2 で採用された創発イベントの 1 つ(プラン B = 未知の発火点)。

設計指針(議事録 §3.4 兵頭氏アドバイス準拠):
- 「**指示を書きすぎない**」。「現在、地球外生命体との接触が確認されています。」程度の粗い投げ込み

2026-04-30 追補(ユーザフィードバック):
火事のように **着地位置** を持たせて視覚化できるようにした。
prompt_text には「○○の方角に降りた」を含める。

2026-05-01 改訂(要件定義 02_エージェント属性 §6.5、段 3):
旧設計「全 agent に同時通達。位置依存なし」を撤回。
seg2_check_alien_5 で全員同一インプットによるエコーループが残ったため、距離依存に変更。
- Near(距離 ≤ near_radius): 詳細視認
- Mid(near_radius < 距離 ≤ visible_radius): 遠望
- Far(visible_radius < 距離): 直接観察不可。会話経由のみで伝播
"""
import math
import random
from typing import Dict, Optional, Tuple

from .base import Event


class AlienEvent(Event):
    """宇宙人接触イベント。`start_step` で発火。距離帯ごとに知覚内容が異なる。

    Args:
        name: 識別子
        start_step: 発火ステップ
        prompt_text: 状態記述のテンプレート(指示は書きすぎない)
        position: UFO の着地位置(指定なしなら maybe_activate 時に乱数生成)
        random_position_range: 乱数生成時の範囲(half_space_size を渡す)
        move_step_size: 着地後の毎 step ランダムウォーク量(±)
        near_radius: この距離以内のエージェントは詳細視認(既定 8.0)
        visible_radius: この距離以内なら遠望できる。これより遠い人は知覚しない(既定 18.0)
    """

    def __init__(
        self,
        name: str = "alien_contact",
        start_step: int = 1,
        prompt_text: Optional[str] = None,
        position: Optional[Tuple[int, int]] = None,
        random_position_range: int = 25,
        move_step_size: int = 2,
        near_radius: float = 8.0,
        visible_radius: float = 18.0,
    ) -> None:
        self.name = name
        self.start_step = start_step
        self.position = position
        self.random_position_range = random_position_range
        self.active = False
        self.activated_step: Optional[int] = None
        # prompt_text は position 確定後に決まる場合があるので保管
        self._prompt_text_template = prompt_text
        # UFO 移動量(±step_size の乱数ウォーク)
        self.move_step_size = max(0, int(move_step_size))
        # 知覚距離帯(段 3, 2026-05-01)
        if near_radius < 0 or visible_radius < near_radius:
            raise ValueError(
                f"AlienEvent radii invalid: near={near_radius}, visible={visible_radius}"
            )
        self.near_radius = float(near_radius)
        self.visible_radius = float(visible_radius)

    @property
    def prompt_text(self) -> str:
        """位置が決まっていれば座標を含む(着地後は移動中という表現)。"""
        base = self._prompt_text_template or "現在、地球外生命体との接触が確認されています。"
        if self.position is not None:
            # active 化されていれば「移動中」、最初の発火 step では「着地点」
            if self.active:
                return f"{base} UFO は座標 ({self.position[0]}, {self.position[1]}) 付近を移動中。"
            return f"{base} 着地点は座標 ({self.position[0]}, {self.position[1]}) 付近。"
        return base

    def maybe_move(self, rng: Optional[object] = None) -> None:
        """active 状態で UFO 位置を 1 ステップ分動かす(ランダムウォーク)。

        2026-05-01 追補(ユーザフィードバック):
        着地後に UFO がフィールド内を動き回る様子を観察するための演出。
        毎ステップ ±move_step_size の範囲で乱数移動。境界では反射しないでクランプ。
        """
        if not self.active or self.position is None or self.move_step_size <= 0:
            return
        r = rng if rng is not None else random
        s = self.move_step_size
        dx = r.randint(-s, s)
        dy = r.randint(-s, s)
        h = self.random_position_range
        new_x = max(-h, min(h, self.position[0] + dx))
        new_y = max(-h, min(h, self.position[1] + dy))
        self.position = (new_x, new_y)

    def maybe_activate(self, step: int) -> Optional[Dict]:
        if self.active or step < self.start_step:
            return None
        if self.position is None:
            r = self.random_position_range
            self.position = (random.randint(-r, r), random.randint(-r, r))
        self.active = True
        self.activated_step = step
        return self.state()

    def state(self) -> Dict:
        return {
            "kind": "alien",
            "name": self.name,
            "start_step": self.start_step,
            "activated_step": self.activated_step,  # 発生フラッシュ判定用(2026-05-01)
            "active": self.active,
            "position": self.position,
            "prompt_text": self.prompt_text,
        }

    def perceived_info(self, agent_position: Tuple[float, float]) -> Optional[Dict]:
        """エージェント位置から見た知覚情報を返す。

        2026-05-01(段 3)で位置依存に変更。距離帯ごとに異なる prompt_text を返し、
        遠方のエージェントは None(直接観察できない=会話経由でのみ知る)。
        """
        if not self.active or self.position is None:
            return None
        dx = agent_position[0] - self.position[0]
        dy = agent_position[1] - self.position[1]
        distance = math.sqrt(dx * dx + dy * dy)
        if distance > self.visible_radius:
            return None  # 直接観察不可。他者の発話経由でのみ伝わる

        base = self._prompt_text_template or "現在、地球外生命体との接触が確認されています。"
        pos = self.position
        if distance <= self.near_radius:
            band = "near"
            prompt = (
                f"{base} 目の前に UFO がいる。座標 ({pos[0]}, {pos[1]}) でほぼ静止して見える。"
            )
        else:
            band = "mid"
            prompt = (
                f"{base} 遠くに UFO らしきものが見える。座標 ({pos[0]}, {pos[1]}) 付近。"
            )
        return {
            "kind": "alien",
            "name": self.name,
            "activated_step": self.activated_step,
            "position": self.position,
            "agent_distance": round(distance, 2),
            "perception_band": band,
            "prompt_text": prompt,
        }
