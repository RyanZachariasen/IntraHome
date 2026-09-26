"""Run one extractor + one categorizer on one receipt image and save the result under runs/.

Pipeline: extract (image -> raw receipt) -> clean (drop non-item lines)
-> categorize (text-only pass) -> check (flag inconsistencies).

    python run.py --extractor ollama_qwen --image data/receipts/IMG_8680.jpg
    python run.py --extractor ollama_qwen --categorizer ollama_qwen --image data/receipts/IMG_8680.jpg
"""
import argparse
import importlib
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from core import postprocess

RUNS_DIR = Path(__file__).parent / "runs"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extractor", required=True, help="module name in extractors/, e.g. ollama_qwen")
    parser.add_argument("--categorizer", default="ollama_qwen", help="module name in categorizers/")
    parser.add_argument("--image", required=True, type=Path)
    args = parser.parse_args()

    extractor = importlib.import_module(f"extractors.{args.extractor}")
    categorizer = importlib.import_module(f"categorizers.{args.categorizer}")

    print("Sending request...")
    result = extractor.extract(args.image)
    # Keep the raw extractor output as-is; the pipeline's result goes under "final".
    output = asdict(result)

    if result.parsed is not None:
        cleaned, dropped = postprocess.clean(result.parsed)
        print(f"Dropped non-item lines: {dropped or 'none'}")
        print("Categorizing...")
        final, categorizer_meta = categorizer.categorize(cleaned)
        checks = postprocess.check(final)
        for warning in checks:
            print(f"CHECK: {warning}")
        output |= {"final": final, "dropped_lines": dropped, "checks": checks, "categorizer": categorizer_meta}

    RUNS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = RUNS_DIR / f"{args.extractor}+{args.categorizer}__{args.image.stem}__{stamp}.json"
    out_path.write_text(
        json.dumps(output, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    print(f"Saved {out_path} ({result.seconds}s, parsed={'yes' if result.parsed else 'no'})")


if __name__ == "__main__":
    main()
