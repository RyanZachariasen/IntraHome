"""Categorizers: receipt in, same receipt with a category on every line out.

Each module in this package exposes
    categorize(receipt: dict) -> tuple[dict, dict]    # (categorized receipt, run metadata)
and usually implements it by passing its own classify() to categorize_with() below,
so the rules shared by every approach live in one place.
"""
import copy
import time
from typing import Callable

from core.schema import Category

# (raw_text, expanded name) -> category, or None when the categorizer isn't sure.
Classify = Callable[[str, str], Category | None]


def categorize_with(receipt: dict, classify: Classify) -> tuple[dict, float]:
    """Apply classify() to every product line. Returns a copy and the seconds it took."""
    start = time.perf_counter()
    receipt = copy.deepcopy(receipt)
    for i, item in enumerate(receipt["line_items"]):
        if item["kind"] != "item":
            item["category"] = "other"
            continue
        item["category"] = classify(item["raw_text"], item["name"])
        if item["category"] is None:
            receipt["uncertain_fields"].append(f"line_items[{i}].category")
        print(f"  {item['raw_text']} -> {item['category']}")
    return receipt, round(time.perf_counter() - start, 2)
