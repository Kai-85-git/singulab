"""議事録 → 要件定義 → 設計書 → 実装 の鮮度整合チェック。

ステージ F-4(問題解決ToDo §F-4 / 問題点リスト §2-D)。
直近の議事録(`docs/02_ミーティング/.../02_議事録/`)の更新時刻と、
要件定義書(`docs/01_設計書/01_要件定義/`)の更新時刻を比較し、
**議事録の方が新しければ「要件定義に反映されていない可能性」を警告**する。

usage:
    python tools/check_design_freshness.py
    python tools/check_design_freshness.py --max-age-hours 48
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEETINGS = ROOT / "docs" / "02_ミーティング"
REQUIREMENTS = ROOT / "docs" / "01_設計書" / "01_要件定義"


def latest_mtime(directory: Path, pattern: str = "**/*.md") -> tuple[float, Path] | None:
    if not directory.exists():
        return None
    best: tuple[float, Path] | None = None
    for f in directory.glob(pattern):
        if not f.is_file():
            continue
        m = f.stat().st_mtime
        if best is None or m > best[0]:
            best = (m, f)
    return best


def main() -> int:
    parser = argparse.ArgumentParser(description="議事録と要件定義の鮮度整合チェック")
    parser.add_argument(
        "--max-age-hours",
        type=int,
        default=24,
        help="議事録がこの時間以内に更新されている場合、要件定義の更新を確認(default: 24)",
    )
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

    minutes_dir = MEETINGS  # 議事録は 02_議事録/ サブディレクトリにある想定
    latest_meeting = latest_mtime(minutes_dir, "**/02_議事録/*.md")
    latest_req = latest_mtime(REQUIREMENTS)

    if latest_meeting is None:
        print(f"[INFO] 議事録ディレクトリが空または存在しない: {minutes_dir}")
        return 0
    if latest_req is None:
        print(f"[WARN] 要件定義ディレクトリが空: {REQUIREMENTS}")
        return 1

    meeting_mtime, meeting_path = latest_meeting
    req_mtime, req_path = latest_req

    meeting_dt = datetime.fromtimestamp(meeting_mtime)
    req_dt = datetime.fromtimestamp(req_mtime)
    now = datetime.now()
    meeting_age_h = (now - meeting_dt).total_seconds() / 3600
    diff_h = (meeting_mtime - req_mtime) / 3600

    print(f"=== 議事録 / 要件定義 鮮度チェック ===")
    print(f"  最新議事録: {meeting_path.relative_to(ROOT)}")
    print(f"           更新: {meeting_dt:%Y-%m-%d %H:%M:%S}({meeting_age_h:.1f} 時間前)")
    print(f"  最新要件定義: {req_path.relative_to(ROOT)}")
    print(f"           更新: {req_dt:%Y-%m-%d %H:%M:%S}")
    print()

    if meeting_age_h > args.max_age_hours:
        print(f"[OK] 議事録は {args.max_age_hours} 時間より古いので新規変更の懸念は低い")
        return 0

    if meeting_mtime > req_mtime:
        print(
            f"[WARN] 議事録 ({meeting_dt:%Y-%m-%d %H:%M}) が要件定義 ({req_dt:%Y-%m-%d %H:%M}) "
            f"より {diff_h:.1f} 時間 新しい"
        )
        print(
            f"  → 議事録の決定が要件定義に未反映の可能性。"
            f"\n     本番ランを実行する前に、議事録を読み、必要なら要件定義を更新してください。"
        )
        print(
            f"  → 詳細は CLAUDE.md §4「議事録 → 要件定義 → 実装の流れ」参照。"
        )
        return 2

    print(f"[OK] 要件定義は議事録より新しい / 同じくらい(差 {diff_h:.1f} 時間)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
