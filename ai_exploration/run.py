"""Run one extractor on one receipt image and save the result under runs/.

    python run.py --extractor ollama_qwen --image data/receipts/IMG_8680.jpg
"""
import argparse
import importlib
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

RUNS_DIR = Path(__file__).parent / "runs"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extractor", required=True, help="module name in extractors/, e.g. ollama_qwen")
    parser.add_argument("--image", required=True, type=Path)
    args = parser.parse_args()

    extractor = importlib.import_module(f"extractors.{args.extractor}")

    print("Sending request...")
    result = extractor.extract(args.image)

    RUNS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = RUNS_DIR / f"{args.extractor}__{args.image.stem}__{stamp}.json"
    out_path.write_text(
        json.dumps(asdict(result), indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    print(f"Saved {out_path} ({result.seconds}s, parsed={'yes' if result.parsed else 'no'})")


if __name__ == "__main__":
    main()
