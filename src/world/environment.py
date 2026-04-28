"""2階(環境): 景気を含む環境量。

設計書 [04_2階-環境/06_実装方針](../../docs/01_設計書/04_2階-環境/06_実装方針.md) に基づく。

Phase 2 では `economy: good/bad/neutral` のみ実装。
- enum 3 値で表現
- system prompt 末尾に状態記述を挿入(命令形を含めない)
- シミュレーション中は不変(frozen)
- テンプレートは config から上書き可能
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Literal, Mapping, Optional


EconomyLevel = Literal["good", "bad", "neutral"]
_VALID_LEVELS: tuple[str, ...] = ("good", "bad", "neutral")

DEFAULT_ECONOMY_TEXT: Dict[str, str] = {
    "good": "現在、景気は良い。",
    "bad": "現在、景気は悪く、予算・雇用に緊張感がある。",
    "neutral": "現在、景気は可もなく不可もない。",
}


@dataclass(frozen=True)
class Environment:
    """2 階の環境量を表す値オブジェクト。

    Attributes:
        economy: 景気レベル(`good` / `bad` / `neutral`)
        economy_text: レベル別の挿入文。デフォルト + config 上書きをマージしたもの
    """

    economy: str
    economy_text: Dict[str, str] = field(default_factory=lambda: dict(DEFAULT_ECONOMY_TEXT))

    def __post_init__(self) -> None:
        if self.economy not in _VALID_LEVELS:
            raise ValueError(
                f"invalid economy: {self.economy!r} (must be one of {_VALID_LEVELS})"
            )
        # 必須キーが揃っていること
        for k in _VALID_LEVELS:
            if k not in self.economy_text:
                raise ValueError(f"economy_text missing key '{k}'")

    @classmethod
    def from_config(cls, cfg: Optional[Mapping[str, Any]]) -> "Environment":
        """`config['environment']` の dict から構築。設定なしなら neutral。"""
        env_cfg: Mapping[str, Any] = cfg or {}
        economy = env_cfg.get("economy", "neutral")
        # default + override マージ
        merged = dict(DEFAULT_ECONOMY_TEXT)
        merged.update(env_cfg.get("economy_text", {}) or {})
        return cls(economy=economy, economy_text=merged)

    def prompt_fragment(self) -> str:
        """system prompt 末尾に挿入する 1〜2 文を返す。"""
        return self.economy_text[self.economy]

    def to_metadata(self) -> Dict[str, Any]:
        """run_metadata.json に書き出す要約。"""
        return {
            "economy": self.economy,
            "economy_text_used": self.economy_text[self.economy],
        }
