"""Score pipeline runs in runs/ against the hand-labeled receipts in data/ground_truth/.

By default only the newest run per (pipeline, receipt) is scored: repeated runs of the
same receipt give the same output, so they add no information. Runs without a "final"
field (made before the current pipeline) and receipts without ground truth are skipped.

    python score.py            # newest run per pipeline and receipt
    python score.py --all      # every run
"""
import argparse
import json
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

from core.postprocess import MONEY_TOLERANCE

ROOT = Path(__file__).parent
RUNS_DIR = ROOT / "runs"
TRUTH_DIR = ROOT / "data" / "ground_truth"

TEXT_FIELDS = ("vendor", "payment_method")
MONEY_FIELDS = ("total", "moms", "subtotal", "discount")
# Two lines count as the same printed line from this raw_text similarity (0-1) upwards.
MATCH_THRESHOLD = 0.6


def _norm(text: str | None) -> str:
    return " ".join((text or "").upper().split())


def _same_money(a: float | None, b: float | None) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= MONEY_TOLERANCE


def align(pred: list[dict], truth: list[dict]) -> list[tuple[int, int]]:
    """Pair predicted and true lines in printed order, maximising total raw_text similarity.

    Order-preserving (like a diff), so one missing or extra line doesn't shift every
    pairing after it, and repeated labels such as "Aftenrabat" pair up by position.
    """
    sim = [[SequenceMatcher(None, _norm(p["raw_text"]), _norm(t["raw_text"])).ratio() for t in truth]
           for p in pred]
    n, m = len(pred), len(truth)
    # best[i][j] = best total similarity pairing pred[i:] with truth[j:]
    best = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            best[i][j] = max(best[i + 1][j], best[i][j + 1])
            if sim[i][j] >= MATCH_THRESHOLD:
                best[i][j] = max(best[i][j], sim[i][j] + best[i + 1][j + 1])

    pairs, i, j = [], 0, 0
    while i < n and j < m:
        if sim[i][j] >= MATCH_THRESHOLD and best[i][j] == sim[i][j] + best[i + 1][j + 1]:
            pairs.append((i, j))
            i, j = i + 1, j + 1
        elif best[i + 1][j] >= best[i][j + 1]:
            i += 1
        else:
            j += 1
    return pairs


def score_run(final: dict, truth: dict) -> dict:
    """Compare one run's "final" receipt with its ground truth. Counts plus readable errors."""
    s = {"fields": {}, "errors": []}
    for f in TEXT_FIELDS:
        s["fields"][f] = _norm(final.get(f)) == _norm(truth.get(f))
    for f in MONEY_FIELDS:
        s["fields"][f] = _same_money(final.get(f), truth.get(f))
    s["errors"] += [f"{f}: {final.get(f)!r} (truth {truth.get(f)!r})" for f, ok in s["fields"].items() if not ok]

    pred, true = final["line_items"], truth["line_items"]
    pairs = align(pred, true)
    paired_pred = {i for i, _ in pairs}
    paired_true = {j for _, j in pairs}
    products = [(i, j) for i, j in pairs if true[j]["kind"] == "item"]

    s["true_lines"], s["pred_lines"], s["matched"] = len(true), len(pred), len(pairs)
    s["price_ok"] = sum(_same_money(pred[i]["total_price"], true[j]["total_price"]) for i, j in pairs)
    s["kind_ok"] = sum(pred[i]["kind"] == true[j]["kind"] for i, j in pairs)
    s["qty_ok"] = sum(_same_money(pred[i]["quantity"], true[j]["quantity"]) for i, j in pairs)
    s["text_ok"] = sum(_norm(pred[i]["raw_text"]) == _norm(true[j]["raw_text"]) for i, j in pairs)
    s["products"] = len(products)
    s["category_ok"] = sum(pred[i].get("category") == true[j]["category"] for i, j in products)

    s["errors"] += [f"extra line: {pred[i]['raw_text']} {pred[i]['total_price']}"
                    for i in range(len(pred)) if i not in paired_pred]
    s["errors"] += [f"missing line: {true[j]['raw_text']} {true[j]['total_price']}"
                    for j in range(len(true)) if j not in paired_true]
    wrong_price = [(i, j) for i, j in pairs if not _same_money(pred[i]["total_price"], true[j]["total_price"])]
    s["errors"] += [f"price: {true[j]['raw_text']} {pred[i]['total_price']} (truth {true[j]['total_price']})"
                    for i, j in wrong_price]
    s["errors"] += [f"category: {true[j]['raw_text']} {pred[i].get('category')} (truth {true[j]['category']})"
                    for i, j in products if pred[i].get("category") != true[j]["category"]]
    s["errors"] += [f"text: {pred[i]['raw_text']!r} (truth {true[j]['raw_text']!r})"
                    for i, j in pairs if _norm(pred[i]["raw_text"]) != _norm(true[j]["raw_text"])]

    s["amounts_ok"] = (s["matched"] == len(true) == len(pred) and not wrong_price
                       and s["fields"]["total"] and s["fields"]["moms"])

    # Did the model flag what it got wrong? Only fields that have a single path are counted.
    wrong_paths = [f for f, ok in s["fields"].items() if not ok]
    wrong_paths += [f"line_items[{i}].total_price" for i, _ in wrong_price]
    flagged = set(final.get("uncertain_fields", []))
    s["wrong_values"], s["wrong_flagged"], s["flags"] = len(wrong_paths), len(flagged & set(wrong_paths)), len(flagged)
    return s


def load_runs(all_runs: bool) -> list[tuple[str, str, Path]]:
    """(pipeline, image, path) for every scorable run, or only the newest per pipeline and receipt."""
    runs = []
    for path in sorted(RUNS_DIR.glob("*.json")):
        pipeline, image, stamp = path.stem.split("__")
        runs.append((pipeline, image, stamp, path))
    if not all_runs:
        newest = {}
        for run in runs:  # sorted by filename, so later stamps overwrite earlier ones
            newest[run[:2]] = run
        runs = list(newest.values())
    return [(pipeline, image, path) for pipeline, image, _, path in runs]


def _pct(ok: int, total: int) -> str:
    return f"{ok}/{total} ({100 * ok / total:.0f}%)" if total else "n/a"


def report(pipeline: str, scores: list[dict], seconds: list[float]) -> None:
    n = len(scores)
    total = lambda key: sum(s[key] for s in scores)
    print(f"\n=== {pipeline}: {n} run(s)")
    for f in TEXT_FIELDS + MONEY_FIELDS:
        print(f"  {f:22s} {_pct(sum(s['fields'][f] for s in scores), n)}")
    print(f"  {'lines found (recall)':22s} {_pct(total('matched'), total('true_lines'))}")
    print(f"  {'lines real (precision)':22s} {_pct(total('matched'), total('pred_lines'))}")
    for key, label in (("price_ok", "line price"), ("kind_ok", "line kind"), ("qty_ok", "line quantity"),
                       ("text_ok", "raw_text exact")):
        print(f"  {label:22s} {_pct(total(key), total('matched'))}")
    print(f"  {'category (products)':22s} {_pct(total('category_ok'), total('products'))}")
    print(f"  {'all amounts right':22s} {_pct(sum(s['amounts_ok'] for s in scores), n)}")
    print(f"  {'wrong values flagged':22s} {_pct(total('wrong_flagged'), total('wrong_values'))}"
          f"  ({total('flags')} flag(s) raised in total)")
    print(f"  {'extract seconds':22s} {min(seconds)}-{max(seconds)} (includes model load on a cold start)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--all", action="store_true", help="score every run, not just the newest per receipt")
    args = parser.parse_args()

    by_pipeline = defaultdict(list)
    for pipeline, image, path in load_runs(args.all):
        run = json.loads(path.read_text(encoding="utf-8"))
        truth_path = TRUTH_DIR / f"{image}.json"
        if "final" not in run or not truth_path.exists():
            reason = "no final (older pipeline)" if "final" not in run else "no ground truth"
            print(f"skip {path.name}: {reason}")
            continue
        s = score_run(run["final"], json.loads(truth_path.read_text(encoding="utf-8")))
        by_pipeline[pipeline].append((s, run["seconds"]))
        print(f"\n{path.name}")
        for error in s["errors"] or ["no errors"]:
            print(f"  {error}")

    for pipeline, results in sorted(by_pipeline.items()):
        report(pipeline, [s for s, _ in results], [sec for _, sec in results])


if __name__ == "__main__":
    main()
