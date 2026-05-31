"""Run detection pipeline for each camera defined in store_layout.json."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.detect import run_pipeline  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--layout", default="data/store_layout.json")
    parser.add_argument("--output", default="data/events.jsonl")
    parser.add_argument("--max-frames", type=int, default=0, help="Limit frames per clip (debug)")
    args = parser.parse_args()

    if args.max_frames:
        import pipeline.config as pc

        pc.MAX_FRAMES = args.max_frames

    stats = run_pipeline(ROOT / args.layout, ROOT / args.output, ROOT)
    print("Per camera:", stats)


if __name__ == "__main__":
    main()
