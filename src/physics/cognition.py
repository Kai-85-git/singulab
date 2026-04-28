"""認知限界(ダンバー数): 他者ごとに記憶するエントリを K 件に制限。

設計書 [05_3階-物理-重力/05_認知限界](../../docs/01_設計書/05_3階-物理-重力/05_認知限界.md) に基づく。

実装ポイント:
- 「覚えていられる他者の数」を K に制限
- 超過時は LRU(最後に関わってから時間が経った相手から忘却)
- 一度忘れた相手と再び関わると `memory_re_encountered` イベントを発火
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# 1 entry が保持する直近メッセージ数(プロンプト膨張防止)
MAX_RECENT_MESSAGES = 5


@dataclass
class MemoryEntry:
    """他エージェント 1 人分の記憶。"""

    other_id: int
    last_interaction_step: int
    summary: str = ""
    recent_messages: List[Dict[str, Any]] = field(default_factory=list)

    def update(self, msg: Optional[Dict[str, Any]], step: int) -> None:
        if msg is not None:
            self.recent_messages.append(msg)
            if len(self.recent_messages) > MAX_RECENT_MESSAGES:
                self.recent_messages.pop(0)
        self.last_interaction_step = step


class AgentMemory:
    """他者ごとの記憶を K 件に制限する LRU Memory。

    Args:
        k: ダンバー数(同時に覚えていられる他者数の上限)
    """

    def __init__(self, k: int):
        if not isinstance(k, int) or k <= 0:
            raise ValueError(f"k must be positive int, got {k!r}")
        self.k = k
        self.entries: Dict[int, MemoryEntry] = {}
        # 一度忘れた相手の最終接触ステップ(再接触検知用)
        self._evicted_history: Dict[int, int] = {}

    def record_interaction(
        self,
        other_id: int,
        step: int,
        msg: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """他エージェントとの接触を記録。発生したイベントを返す。

        イベント種別:
            - memory_added: 新規エントリ追加
            - memory_evicted: K 超過で 1 件追い出し(LRU)
            - memory_re_encountered: 過去に追い出された相手と再接触
        """
        events: List[Dict[str, Any]] = []

        if other_id in self.entries:
            self.entries[other_id].update(msg, step)
            return events  # 既知 → イベントなし

        # 新規追加(再接触含む)
        if other_id in self._evicted_history:
            gap = step - self._evicted_history[other_id]
            events.append(
                {
                    "type": "memory_re_encountered",
                    "other_id": other_id,
                    "gap_steps": gap,
                }
            )
            del self._evicted_history[other_id]

        if len(self.entries) >= self.k:
            evicted_id, evicted_step = self._evict_oldest()
            events.append(
                {
                    "type": "memory_evicted",
                    "other_id": evicted_id,
                    "last_interaction_step": evicted_step,
                    "current_step": step,
                }
            )

        self.entries[other_id] = MemoryEntry(
            other_id=other_id,
            last_interaction_step=step,
            recent_messages=[msg] if msg is not None else [],
        )
        events.append({"type": "memory_added", "other_id": other_id})
        return events

    def _evict_oldest(self) -> tuple[int, int]:
        oldest_id = min(self.entries, key=lambda k: self.entries[k].last_interaction_step)
        oldest_step = self.entries[oldest_id].last_interaction_step
        del self.entries[oldest_id]
        self._evicted_history[oldest_id] = oldest_step
        return oldest_id, oldest_step

    def known_ids(self) -> List[int]:
        """現在覚えている他者 ID のリスト。"""
        return list(self.entries.keys())

    def render_for_prompt(self) -> str:
        """LLM プロンプトに挿入する文字列を生成。"""
        if not self.entries:
            return "No agents known yet."
        lines: List[str] = []
        # 直近交流したエージェント順
        sorted_entries = sorted(
            self.entries.values(),
            key=lambda e: e.last_interaction_step,
            reverse=True,
        )
        for e in sorted_entries:
            recent = ""
            if e.recent_messages:
                last = e.recent_messages[-1]
                snippet = (last.get("content") or "")[:60]
                recent = f' last: "{snippet}"' if snippet else ""
            lines.append(
                f"- Agent {e.other_id} (last seen step {e.last_interaction_step}){recent}"
            )
        return "\n".join(lines)
