"""JSONL ロガー。参考実装 simulation.py 内の `_log_message` /
`_log_memory_reasoning_batch` を独立クラス化。
"""
import json
import os
from typing import Any, Dict, Iterable, Optional


class JsonlLogger:
    """指定ディレクトリ配下に jsonl ファイルを追記する単純ロガー。

    Phase 1 ではメッセージ・メモリ・推論ログを既存 2 ファイル
    (`messages.jsonl`, `memory_reasoning.jsonl`) に追記する責務だけ持つ。
    Phase 2 で `events.jsonl` / `run_metadata.json` を追加する想定。
    """

    def __init__(self, output_dir: Optional[str]):
        self.output_dir = output_dir
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

    def _path(self, filename: str) -> Optional[str]:
        if not self.output_dir:
            return None
        return os.path.join(self.output_dir, filename)

    def _append_one(self, filename: str, record: Dict[str, Any]) -> None:
        path = self._path(filename)
        if path is None:
            return
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _append_many(self, filename: str, records: Iterable[Dict[str, Any]]) -> None:
        path = self._path(filename)
        if path is None:
            return
        with open(path, "a", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def log_message(
        self,
        step: int,
        from_id: int,
        to_id: int,
        message: str,
        reasoning: str = "",
    ) -> None:
        self._append_one(
            "messages.jsonl",
            {
                "step": step,
                "from": from_id,
                "to": to_id,
                "message": message,
                "reasoning": reasoning,
            },
        )

    def log_memory_reasoning_batch(self, records: Iterable[Dict[str, Any]]) -> None:
        self._append_many("memory_reasoning.jsonl", records)

    def log_event(self, step: int, event: Dict[str, Any]) -> None:
        """events.jsonl に 1 イベントを追記。

        Phase 2-1 で扱うイベント種別:
            - place_change: from, to
            - place_entry_denied: place_id, occupancy, capacity
            - clamp_to_field: attempted_pos, clamped_pos
        """
        record = {"step": step, **event}
        self._append_one("events.jsonl", record)

    def log_event_batch(self, step: int, events: Iterable[Dict[str, Any]]) -> None:
        records = ({"step": step, **ev} for ev in events)
        self._append_many("events.jsonl", records)

    def log_run_metadata(self, metadata: Dict[str, Any]) -> None:
        """run_metadata.json を 1 回だけ書き出し(上書き)。"""
        path = self._path("run_metadata.json")
        if path is None:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
