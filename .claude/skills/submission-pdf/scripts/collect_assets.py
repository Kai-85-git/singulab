"""collect_assets.py

Singulab 提出 PDF 用に、`docs/` と `runs/` から素材を収集して `build/assets.json` に集約する。

usage:
    python .claude/skills/submission-pdf/scripts/collect_assets.py
    python .claude/skills/submission-pdf/scripts/collect_assets.py --runs runs/2026-05-01_001
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path("C:/Projects/singulab")
DOCS = ROOT / "docs"
RUNS = ROOT / "runs"
BUILD = ROOT / "build"


def find_latest_run(runs_dir: Path) -> Path | None:
    if not runs_dir.exists():
        return None
    candidates = sorted([p for p in runs_dir.iterdir() if p.is_dir()], reverse=True)
    return candidates[0] if candidates else None


def collect_meeting_minutes() -> list[dict[str, Any]]:
    minutes_dir = DOCS / "02_ミーティング"
    if not minutes_dir.exists():
        return []
    out: list[dict[str, Any]] = []
    for md in sorted(minutes_dir.rglob("*.md")):
        if "議事録" in str(md) or md.parent.name == "02_議事録":
            out.append({
                "path": str(md.relative_to(ROOT)).replace("\\", "/"),
                "title": md.stem,
                "size": md.stat().st_size,
            })
    return out


def collect_design_docs() -> dict[str, list[str]]:
    design_dir = DOCS / "01_設計書"
    if not design_dir.exists():
        return {}
    sections: dict[str, list[str]] = {}
    for sub in sorted(design_dir.iterdir()):
        if sub.is_dir():
            files = [
                str(p.relative_to(ROOT)).replace("\\", "/")
                for p in sorted(sub.rglob("*.md"))
            ]
            sections[sub.name] = files
    return sections


def collect_emergence_scenarios() -> list[str]:
    ideas_dir = DOCS / "00_アイデア"
    if not ideas_dir.exists():
        return []
    return [
        str(p.relative_to(ROOT)).replace("\\", "/")
        for p in sorted(ideas_dir.glob("*.md"))
    ]


def parse_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def summarise_perf(perf: list[dict[str, Any]]) -> dict[str, Any]:
    if not perf:
        return {"status": "TBD"}
    tps = [r.get("tokens_per_second") for r in perf if r.get("tokens_per_second")]
    lat = [r.get("latency_ms") for r in perf if r.get("latency_ms")]
    return {
        "samples": len(perf),
        "tok_per_sec_mean": (sum(tps) / len(tps)) if tps else None,
        "tok_per_sec_max": max(tps) if tps else None,
        "latency_ms_mean": (sum(lat) / len(lat)) if lat else None,
    }


def summarise_vram(vram: list[dict[str, Any]]) -> dict[str, Any]:
    if not vram:
        return {"status": "TBD"}
    used = [r.get("used_mb") for r in vram if r.get("used_mb")]
    return {
        "samples": len(vram),
        "used_mb_peak": max(used) if used else None,
        "used_mb_mean": (sum(used) / len(used)) if used else None,
    }


def summarise_emergence(em: list[dict[str, Any]]) -> dict[str, Any]:
    if not em:
        return {"status": "TBD"}
    return {
        "samples": len(em),
        "metrics": list({k for r in em for k in r.keys() if k != "step"}),
    }


def pick_emergence_excerpts(llm_io: list[dict[str, Any]], n: int = 8) -> list[dict[str, Any]]:
    """嘘・派閥・通貨・反乱 関連のキーワードでフィルタしてサンプル抽出"""
    keywords = re.compile(r"(嘘|偽|派閥|通貨|反乱|裏切|交換|同盟)")
    hits = [
        r for r in llm_io
        if keywords.search(json.dumps(r, ensure_ascii=False))
    ]
    return hits[:n]


def collect_run_metrics(run_dir: Path | None) -> dict[str, Any]:
    if run_dir is None:
        return {
            "status": "TBD: 実行ログがまだありません",
            "run_dir": None,
        }
    perf = parse_jsonl(run_dir / "perf.jsonl")
    vram = parse_jsonl(run_dir / "vram.jsonl")
    emergence = parse_jsonl(run_dir / "emergence.jsonl")
    llm_io = parse_jsonl(run_dir / "llm_io.jsonl")
    events = parse_jsonl(run_dir / "events.jsonl")

    return {
        "run_dir": str(run_dir.relative_to(ROOT)).replace("\\", "/"),
        "perf": summarise_perf(perf),
        "vram": summarise_vram(vram),
        "emergence": summarise_emergence(emergence),
        "llm_io_count": len(llm_io),
        "events_count": len(events),
        "emergence_excerpts": pick_emergence_excerpts(llm_io),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=str, default=None, help="特定の runs/<ts> を指定。省略時は最新")
    parser.add_argument("--out", type=str, default=str(BUILD / "assets.json"))
    args = parser.parse_args()

    if args.runs:
        run_dir = ROOT / args.runs
        run_dir = run_dir if run_dir.exists() else None
    else:
        run_dir = find_latest_run(RUNS)

    assets = {
        "minutes": collect_meeting_minutes(),
        "design_docs": collect_design_docs(),
        "emergence_scenarios": collect_emergence_scenarios(),
        "metrics": collect_run_metrics(run_dir),
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(assets, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[done] wrote {out_path}")
    print(f"  minutes:   {len(assets['minutes'])} files")
    print(f"  design:    {sum(len(v) for v in assets['design_docs'].values())} files")
    print(f"  scenarios: {len(assets['emergence_scenarios'])} files")
    print(f"  run_dir:   {assets['metrics'].get('run_dir')}")


if __name__ == "__main__":
    main()
