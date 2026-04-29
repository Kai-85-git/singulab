"""創発指標の集計。Phase 3-2(B5-03)で導入。

設計書 [06_システム設計/06_ロギング・出力/05_創発指標](../../docs/01_設計書/06_システム設計/06_ロギング・出力/05_創発指標.md) に基づく。

Phase 3-2 MVP では以下の **定量・再現可能な指標** に絞る:

1. **発言頻度 Gini 係数**: 発言が誰かに偏ると上昇(=発言権の偏り)
2. **沈黙率(silent_agent_rate)**: 一度も発話しなかったエージェントの割合
3. **トップ発話者シェア**: 最大発話エージェントが全発話の何 % か
4. **ペア相互作用安定度**: 各エージェントの「最も話した相手」が時間窓を跨いでどれだけ変わらないか(=派閥の安定度)
5. **events 統計**: place_change / place_entry_denied / clamp_to_field / memory_added / memory_evicted / memory_re_encountered

合意成立判定と伝播速度は NLP が必要なため Phase 3 後段で実装する想定。
"""
from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RunMetrics:
    """1 ラン分の集計指標。"""

    # メタ
    run_dir: str
    duration_steps: int
    num_agents: int
    scenario_label: str = ""

    # 発言頻度
    total_messages: int = 0
    unique_speakers: int = 0
    silent_agent_rate: float = 0.0
    gini_utterance: float = 0.0
    top_speaker_share: float = 0.0
    utterances_per_agent: Dict[int, int] = field(default_factory=dict)

    # ペア相互作用
    pair_stability: float = 0.0  # 0..1、高いほど派閥が安定
    pair_stability_n_windows: int = 0  # 評価に使った時間窓数

    # events.jsonl 集計
    event_counts: Dict[str, int] = field(default_factory=dict)
    re_encountered_avg_gap: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _load_jsonl(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    out: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def _load_json(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def gini_coefficient(values: List[float]) -> float:
    """Gini 係数(0 = 完全均等、~1 = 1 人に集中)。

    `2 * Σ i * x_i / (n * Σ x_i) - (n + 1) / n` のソート公式を使う。
    全要素 0 のとき 0.0 を返す(発話ゼロの run 用)。
    """
    n = len(values)
    if n == 0:
        return 0.0
    s = sum(values)
    if s <= 0:
        return 0.0
    sorted_v = sorted(values)
    cum = sum((i + 1) * v for i, v in enumerate(sorted_v))
    return (2.0 * cum) / (n * s) - (n + 1) / n


def _scenario_label(metadata: Optional[Dict[str, Any]]) -> str:
    """run_metadata から「都心×大企業×bad」のような短いラベルを作る。"""
    if metadata is None:
        return ""
    parts: List[str] = []
    personas = metadata.get("personas")
    if personas:
        first = next((p for p in personas if p), None)
        if first:
            parts.append(first.get("location_label", ""))
            parts.append(first.get("company_type_label", ""))
    env = metadata.get("environment") or {}
    econ = env.get("economy")
    if econ:
        parts.append(econ)
    return "×".join(p for p in parts if p)


def _utterance_counts(messages: List[Dict[str, Any]]) -> Dict[int, int]:
    """messages.jsonl から「from agent_id → 発話数」を返す。

    同 step・同 from・同 message のレコードは複数の to に対し 1 行ずつ書かれているので、
    `(step, from, message)` 単位で重複排除する。
    """
    seen: set = set()
    counts: Counter = Counter()
    for m in messages:
        key = (m.get("step"), m.get("from"), m.get("message"))
        if key in seen:
            continue
        seen.add(key)
        from_id = m.get("from")
        if isinstance(from_id, int):
            counts[from_id] += 1
    return dict(counts)


def _pair_stability(
    messages: List[Dict[str, Any]],
    duration_steps: int,
    n_windows: int = 4,
) -> tuple[float, int]:
    """各エージェントの「最も話した相手」が時間窓を跨いでどれだけ安定しているかを測る。

    Args:
        messages: messages.jsonl 全レコード
        duration_steps: 全ステップ数
        n_windows: 時間窓の数(均等分割)

    Returns:
        (stability, used_windows): 0..1 の安定度 + 実際に評価できた窓数
    """
    if duration_steps < n_windows or not messages:
        return (0.0, 0)
    window_size = max(1, duration_steps // n_windows)

    # window index → from_id → Counter[to_id]
    per_window: Dict[int, Dict[int, Counter]] = defaultdict(lambda: defaultdict(Counter))
    for m in messages:
        step = m.get("step")
        from_id = m.get("from")
        to_id = m.get("to")
        if not isinstance(step, int) or not isinstance(from_id, int) or not isinstance(to_id, int):
            continue
        wi = min(n_windows - 1, max(0, (step - 1) // window_size))
        per_window[wi][from_id][to_id] += 1

    # 各エージェントの top-1 partner を窓ごとに記録
    top_by_window: Dict[int, Dict[int, int]] = defaultdict(dict)
    for wi, by_from in per_window.items():
        for from_id, ctr in by_from.items():
            if not ctr:
                continue
            top_partner, _ = ctr.most_common(1)[0]
            top_by_window[from_id][wi] = top_partner

    # 連続する窓 (wi, wi+1) で top-1 が同じか確認
    matches = 0
    transitions = 0
    for from_id, top_map in top_by_window.items():
        windows = sorted(top_map.keys())
        for a, b in zip(windows, windows[1:]):
            if b - a != 1:
                continue
            transitions += 1
            if top_map[a] == top_map[b]:
                matches += 1

    if transitions == 0:
        return (0.0, len(per_window))
    return (matches / transitions, len(per_window))


class MetricsCalculator:
    """1 ラン(output/<dir>/)から各種指標を計算する。"""

    def __init__(self, run_dir: str):
        self.run_dir = run_dir
        self.metadata = _load_json(os.path.join(run_dir, "run_metadata.json"))
        self.messages = _load_jsonl(os.path.join(run_dir, "messages.jsonl"))
        self.events = _load_jsonl(os.path.join(run_dir, "events.jsonl"))

    def compute(self) -> RunMetrics:
        meta = self.metadata or {}
        duration = int(meta.get("duration", 0))
        num_agents = int(meta.get("num_agents", 0))

        m = RunMetrics(
            run_dir=self.run_dir,
            duration_steps=duration,
            num_agents=num_agents,
            scenario_label=_scenario_label(meta),
        )

        # 発言頻度
        counts = _utterance_counts(self.messages)
        m.utterances_per_agent = counts
        # num_agents が分かっているならゼロ発話 agent も補完
        if num_agents > 0:
            for i in range(num_agents):
                counts.setdefault(i, 0)
        speaker_values = list(counts.values())
        m.total_messages = sum(speaker_values)
        m.unique_speakers = sum(1 for v in speaker_values if v > 0)
        if num_agents > 0:
            m.silent_agent_rate = (num_agents - m.unique_speakers) / num_agents
        m.gini_utterance = gini_coefficient(speaker_values)
        if speaker_values and m.total_messages > 0:
            m.top_speaker_share = max(speaker_values) / m.total_messages

        # ペア相互作用
        m.pair_stability, m.pair_stability_n_windows = _pair_stability(
            self.messages, duration_steps=duration
        )

        # events 集計
        ev_counter: Counter = Counter()
        gap_sum = 0
        gap_n = 0
        for ev in self.events:
            ev_type = ev.get("type", "unknown")
            ev_counter[ev_type] += 1
            if ev_type == "memory_re_encountered":
                gap = ev.get("gap_steps")
                if isinstance(gap, int):
                    gap_sum += gap
                    gap_n += 1
        m.event_counts = dict(ev_counter)
        m.re_encountered_avg_gap = gap_sum / gap_n if gap_n else 0.0

        return m
