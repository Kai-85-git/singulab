"""Singulab CLI エントリポイント。

Phase 1: yaml を読み込んで Simulation を実行するだけの最小版。
"""
import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# ルートを sys.path に通す(`python -m src.main` でも `python src/main.py` でも動くように)
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.simulation import Simulation  # noqa: E402


def setup_logging(level: str, log_file: str | None = None) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Singulab simulation runner")
    parser.add_argument(
        "--config",
        "-c",
        default="config/scenario_bar_fire.yaml",
        help="path to config yaml",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default=None,
        help="output directory for jsonl logs (default: output/run_<timestamp>)",
    )
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    if args.output_dir is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output_dir = os.path.join("output", f"run_{ts}")
    os.makedirs(args.output_dir, exist_ok=True)
    setup_logging(args.log_level, log_file=os.path.join(args.output_dir, "simulation.log"))

    logging.info(f"config = {args.config}")
    logging.info(f"output_dir = {args.output_dir}")

    sim = Simulation(config_path=args.config, output_dir=args.output_dir)
    sim.run()

    stats = sim.get_statistics()
    if stats:
        logging.info("===== Statistics =====")
        for k, v in stats.items():
            logging.info(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
