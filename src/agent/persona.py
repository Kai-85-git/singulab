"""Persona: エージェントの人格属性(2026-04-29 議事録改訂版)。

設計書 [01_要件定義/03_機能要件/02_エージェント属性](../../docs/01_設計書/01_要件定義/03_機能要件/02_エージェント属性.md) と
[06_システム設計/04_エージェント設計/07_ペルソナ拡張](../../docs/01_設計書/06_システム設計/04_エージェント設計/07_ペルソナ拡張.md)
に基づく新スキーマ。

採用するフィールド:
- age          : 数値(20〜70 を想定)
- gender       : male / female(LLM のジェンダーレス概念非対応のため生物学的のみ)
- nationality  : 国名(プールから抽選。「日本語で回答」プロンプトで言語のみ固定)
- mbti         : 16 タイプから1つ

意図的に入れない:
- role / job / position / tenure_years : 役職は自然発生を観察する
- location_label / company_type_label  : 4 象限切り廃止に伴い廃止
- name                                 : 役割を連想するため削除

旧スキーマ(role / tenure_years / location_label など)は受け取った際に
ValueError を投げて移行を促す(legacy/ に移したシナリオ yaml はそのまま使えない)。
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional


_GENDER_JP = {"male": "男性", "female": "女性"}

# MBTI 16 タイプ
MBTI_TYPES: List[str] = [
    "INTJ", "INTP", "ENTJ", "ENTP",
    "INFJ", "INFP", "ENFJ", "ENFP",
    "ISTJ", "ISFJ", "ESTJ", "ESFJ",
    "ISTP", "ISFP", "ESTP", "ESFP",
]


def _decade(age: int) -> int:
    """年齢 32 → 30(代)、年齢 27 → 20(代)。"""
    return (age // 10) * 10


@dataclass(frozen=True)
class Persona:
    """1 エージェント分の人格設定(新スキーマ)。"""

    age: int
    gender: str
    nationality: str
    mbti: str

    @property
    def gender_jp(self) -> str:
        return _GENDER_JP.get(self.gender, self.gender)

    def to_prompt(self) -> str:
        """system prompt の `=== PERSONA ===` セクションに挿入する状態記述(日本語)。

        2026-04-29 議事録 §4.4 の雛形をベースに、**MBTI を冒頭に配置**(B-3-1 / §7-E-5)。
        理由:性格次元(MBTI)を一番目立たせることで、エージェント間のばらつきを強化し、
        エコー(同じ発言の伝染)を抑制することを狙う。
        """
        return (
            f"MBTI: {self.mbti}\n"
            f"私は{_decade(self.age)}代の{self.gender_jp}です。\n"
            f"国籍: {self.nationality}\n"
            f"日本語で回答してください。"
        )

    def to_metadata(self) -> Dict[str, Any]:
        return {
            "age": self.age,
            "gender": self.gender,
            "nationality": self.nationality,
            "mbti": self.mbti,
        }


# ---- legacy 検出ユーティリティ -----------------------------------------------

_LEGACY_KEYS = {
    "role_distribution",
    "tenure_range",
    "location_label",
    "company_type_label",
    "name_pool",
}


def _is_legacy_config(persona_cfg: Mapping[str, Any]) -> bool:
    return any(k in persona_cfg for k in _LEGACY_KEYS)


# ---- PersonaFactory ----------------------------------------------------------


class PersonaFactory:
    """config の `agents.persona` セクションから Persona を乱数生成する(新スキーマ)。

    Config schema(2026-04-29 議事録準拠):

        agents:
          persona:
            age:
              range: [20, 60]            # uniform 整数範囲
            gender:
              values: [male, female]     # 抽選候補
            nationality:
              pool: [日本, 米国, 中国, ...]
            mbti:
              values: [INTJ, ENFP, ...]  # 省略時は 16 タイプ全部

    旧スキーマ(role / tenure_years / location_label など)を渡された場合は
    ValueError を投げて移行を促す。
    """

    def __init__(
        self,
        age_range: tuple[int, int],
        gender_values: List[str],
        nationality_pool: List[str],
        mbti_values: Optional[List[str]] = None,
    ) -> None:
        lo, hi = age_range
        if lo < 0 or hi < lo:
            raise ValueError(f"age_range invalid: {age_range!r}")
        self.age_range = (int(lo), int(hi))

        if not gender_values:
            raise ValueError("gender_values must not be empty")
        self.gender_values = list(gender_values)

        if not nationality_pool:
            raise ValueError("nationality_pool must not be empty")
        self.nationality_pool = list(nationality_pool)

        chosen = list(mbti_values) if mbti_values else list(MBTI_TYPES)
        for m in chosen:
            if m not in MBTI_TYPES:
                raise ValueError(f"unknown mbti type: {m!r} (valid: {MBTI_TYPES})")
        self.mbti_values = chosen

    @classmethod
    def from_config(cls, persona_cfg: Mapping[str, Any]) -> "PersonaFactory":
        if _is_legacy_config(persona_cfg):
            raise ValueError(
                "Legacy persona schema detected (role_distribution / location_label / "
                "company_type_label / name_pool / tenure_range). The schema was replaced "
                "by age / gender / nationality / mbti per the 2026-04-29 meeting minutes. "
                "Please migrate the scenario yaml. See "
                "docs/01_設計書/06_システム設計/04_エージェント設計/07_ペルソナ拡張.md"
            )

        age_cfg = persona_cfg.get("age", {})
        age_range = tuple(age_cfg.get("range", [20, 60]))

        gender_cfg = persona_cfg.get("gender", {})
        gender_values = list(gender_cfg.get("values", ["male", "female"]))

        nationality_cfg = persona_cfg.get("nationality", {})
        nationality_pool = list(nationality_cfg.get("pool", ["日本"]))

        mbti_cfg = persona_cfg.get("mbti", {})
        mbti_values = list(mbti_cfg.get("values", MBTI_TYPES))

        return cls(
            age_range=age_range,
            gender_values=gender_values,
            nationality_pool=nationality_pool,
            mbti_values=mbti_values,
        )

    def generate(
        self,
        agent_id: int,
        gender: Optional[str] = None,
        rng: Optional[random.Random] = None,
    ) -> Persona:
        """Persona を 1 体生成する。

        gender 引数は後方互換のため残す(simulation.py が乱択した値を渡す)。
        gender=None なら gender_values から抽選。
        """
        rng = rng or random
        age = rng.randint(self.age_range[0], self.age_range[1])
        if gender is None:
            gender = rng.choice(self.gender_values)
        nationality = rng.choice(self.nationality_pool)
        mbti = rng.choice(self.mbti_values)
        return Persona(
            age=age,
            gender=gender,
            nationality=nationality,
            mbti=mbti,
        )
