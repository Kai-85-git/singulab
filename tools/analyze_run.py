"""単一 run ディレクトリを解析し、指標を出力する CLI。

Usage:
    python -m tools.analyze_run output/phase3_local_startup
    python -m tools.analyze_run output/phase3_local_startup --json   # 機械可読出力

出力:
    - 標準出力にサマリ
    - <run_dir>/metrics.json に集計値を書き出し
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.runlog.metrics import MetricsCalculator  # noqa: E402


def _print_summary(m) -> None:
    print(f"=== Run: {m.run_dir} ===")
    print(f"  scenario:           {m.scenario_label or '(unlabeled)'}")
    print(f"  duration_steps:     {m.duration_steps}")
    print(f"  num_agents:         {m.num_agents}")
    print()
    print(f"  total_messages:     {m.total_messages}")
    print(f"  unique_speakers:    {m.unique_speakers} / {m.num_agents}")
    print(f"  silent_agent_rate:  {m.silent_agent_rate:.2%}")
    print(f"  gini_utterance:     {m.gini_utterance:.3f}  (0=均等, ~1=独占)")
    print(f"  top_speaker_share:  {m.top_speaker_share:.2%}")
    print()
    print(f"  pair_stability:     {m.pair_stability:.3f}  (n_windows={m.pair_stability_n_windows})")
    print()
    if m.event_counts:
        print(f"  events:")
        for ev_type, count in sorted(m.event_counts.items()):
            print(f"    {ev_type:30s} {count}")
        if m.re_encountered_avg_gap:
            print(f"    (re_encountered_avg_gap = {m.re_encountered_avg_gap:.2f} steps)")
    else:
        print(f"  events: (none)")
    print()
    if m.utterances_per_agent:
        sorted_pairs = sorted(m.utterances_per_agent.items(), key=lambda x: -x[1])
        head = sorted_pairs[:5]
        print(f"  top utterers:")
        for aid, cnt in head:
            print(f"    Agent {aid}: {cnt}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze a single run directory")
    parser.add_argument("run_dir", help="path to output/<run> directory")
    parser.add_argument("--json", action="store_true", help="output as JSON to stdout")
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="do not write metrics.json into run_dir",
    )
    args = parser.parse_args()

    if not Path(args.run_dir).is_dir():
        print(f"ERROR: not a directory: {args.run_dir}", file=sys.stderr)
        return 1

    metrics = MetricsCalculator(args.run_dir).compute()

    if args.json:
        print(json.dumps(metrics.to_dict(), ensure_ascii=False, indent=2))
    else:
        _print_summary(metrics)

    if not args.no_write:
        out = Path(args.run_dir) / "metrics.json"
        out.write_text(
            json.dumps(metrics.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if not args.json:
            print(f"  -> wrote {out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
