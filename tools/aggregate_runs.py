"""複数の run ディレクトリを横並びで集計する CLI。

Usage:
    python -m tools.aggregate_runs output/
    python -m tools.aggregate_runs output/ --csv > runs.csv

挙動:
    - 指定ディレクトリ直下を走査し、`run_metadata.json` があるサブディレクトリを run と判定
    - 各 run について MetricsCalculator を回し、テーブル化
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.runlog.metrics import MetricsCalculator, RunMetrics  # noqa: E402


COLUMNS = [
    "run",
    "scenario",
    "agents",
    "steps",
    "msgs",
    "silent_rate",
    "gini",
    "top_share",
    "pair_stability",
    "place_change",
    "place_entry_denied",
    "memory_evicted",
    "memory_re_encountered",
    "clamp_to_field",
]


def _row_for(m: RunMetrics) -> Dict[str, str]:
    ev = m.event_counts
    return {
        "run": Path(m.run_dir).name,
        "scenario": m.scenario_label,
        "agents": str(m.num_agents),
        "steps": str(m.duration_steps),
        "msgs": str(m.total_messages),
        "silent_rate": f"{m.silent_agent_rate:.2f}",
        "gini": f"{m.gini_utterance:.3f}",
        "top_share": f"{m.top_speaker_share:.2f}",
        "pair_stability": f"{m.pair_stability:.3f}",
        "place_change": str(ev.get("place_change", 0)),
        "place_entry_denied": str(ev.get("place_entry_denied", 0)),
        "memory_evicted": str(ev.get("memory_evicted", 0)),
        "memory_re_encountered": str(ev.get("memory_re_encountered", 0)),
        "clamp_to_field": str(ev.get("clamp_to_field", 0)),
    }


def _print_table(rows: List[Dict[str, str]]) -> None:
    if not rows:
        print("No runs found.")
        return
    widths = {c: max(len(c), max(len(r[c]) for r in rows)) for c in COLUMNS}
    header = " | ".join(c.ljust(widths[c]) for c in COLUMNS)
    sep = "-+-".join("-" * widths[c] for c in COLUMNS)
    print(header)
    print(sep)
    for r in rows:
        print(" | ".join(r[c].ljust(widths[c]) for c in COLUMNS))


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate metrics across runs")
    parser.add_argument("root", help="parent dir containing run subdirectories")
    parser.add_argument("--csv", action="store_true", help="write CSV to stdout")
    parser.add_argument("--json", action="store_true", help="write JSON to stdout")
    args = parser.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        print(f"ERROR: not a directory: {root}", file=sys.stderr)
        return 1

    rows: List[Dict[str, str]] = []
    metrics_list: List[RunMetrics] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        meta_path = child / "run_metadata.json"
        if not meta_path.exists():
            continue
        m = MetricsCalculator(str(child)).compute()
        metrics_list.append(m)
        rows.append(_row_for(m))

    if args.csv:
        writer = csv.DictWriter(sys.stdout, fieldnames=COLUMNS)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    elif args.json:
        print(json.dumps([m.to_dict() for m in metrics_list], ensure_ascii=False, indent=2))
    else:
        _print_table(rows)

    return 0


if __name__ == "__main__":
    sys.exit(main())
