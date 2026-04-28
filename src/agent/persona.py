"""Persona: エージェントの人格属性。

設計書 [03_1階-物/06_4象限との関係](../../docs/01_設計書/03_1階-物/06_4象限との関係.md) と
[04_2階-環境/04_象限ごとのデフォルト](../../docs/01_設計書/04_2階-環境/04_象限ごとのデフォルト.md)
に基づく。

- 4 象限(都心/地方 × 大企業/スタートアップ)はペルソナで吸収
- 役職・社歴は乱数生成、状況記述として system prompt に注入
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional


_GENDER_JP = {"male": "男性", "female": "女性"}


@dataclass(frozen=True)
class Persona:
    """1 エージェント分の人格設定。"""

    name: str
    role: str
    tenure_years: int
    gender: str
    location_label: str  # 例: "都心" / "地方"
    company_type_label: str  # 例: "大企業" / "スタートアップ"

    @property
    def gender_jp(self) -> str:
        return _GENDER_JP.get(self.gender, self.gender)

    def to_prompt(self) -> str:
        """system prompt に挿入する状態記述(日本語)。"""
        return (
            f"あなたは{self.name}({self.gender_jp})、"
            f"{self.location_label}にある{self.company_type_label}で働く"
            f"{self.tenure_years}年目の{self.role}です。"
        )

    def to_metadata(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "tenure_years": self.tenure_years,
            "gender": self.gender,
            "location_label": self.location_label,
            "company_type_label": self.company_type_label,
        }


class PersonaFactory:
    """config の `agents.persona` セクションから Persona を乱数生成する。

    Config schema:
        agents:
          persona:
            location_label: "都心"
            company_type_label: "大企業"
            name_pool: ["田中", "佐藤", ...]
            role_distribution:
              "エンジニア": 0.6
              "リーダー": 0.2
              "マネージャー": 0.1
              "平社員": 0.1
            tenure_range: [1, 25]
    """

    def __init__(
        self,
        location_label: str,
        company_type_label: str,
        name_pool: List[str],
        role_distribution: Dict[str, float],
        tenure_range: tuple[int, int],
    ):
        if not name_pool:
            raise ValueError("name_pool must not be empty")
        if not role_distribution:
            raise ValueError("role_distribution must not be empty")
        total = sum(role_distribution.values())
        if total <= 0:
            raise ValueError("role_distribution values must sum to > 0")
        # 重みは正規化しておく(合計 1.0 でなくても OK)
        self.location_label = location_label
        self.company_type_label = company_type_label
        self.name_pool = list(name_pool)
        self._roles = list(role_distribution.keys())
        self._weights = [role_distribution[r] / total for r in self._roles]
        lo, hi = tenure_range
        if lo < 0 or hi < lo:
            raise ValueError(f"tenure_range invalid: {tenure_range!r}")
        self.tenure_range = (int(lo), int(hi))

    @classmethod
    def from_config(cls, persona_cfg: Mapping[str, Any]) -> "PersonaFactory":
        return cls(
            location_label=persona_cfg["location_label"],
            company_type_label=persona_cfg["company_type_label"],
            name_pool=list(persona_cfg["name_pool"]),
            role_distribution=dict(persona_cfg["role_distribution"]),
            tenure_range=tuple(persona_cfg["tenure_range"]),
        )

    def generate(
        self,
        agent_id: int,
        gender: str,
        rng: Optional[random.Random] = None,
    ) -> Persona:
        rng = rng or random
        # 重複を許容(本物の組織でも同姓多数あり)
        name = rng.choice(self.name_pool)
        role = rng.choices(self._roles, weights=self._weights, k=1)[0]
        tenure = rng.randint(self.tenure_range[0], self.tenure_range[1])
        return Persona(
            name=name,
            role=role,
            tenure_years=tenure,
            gender=gender,
            location_label=self.location_label,
            company_type_label=self.company_type_label,
        )
