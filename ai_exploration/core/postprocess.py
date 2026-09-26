"""Deterministic cleanup and checks on an extracted receipt. No model calls.

clean() drops lines the model wrongly emits as line items (TOTAL, payment, MOMS...)
and nulls unit prices that merely repeat the line total.
check() flags inconsistencies for human review; it never changes numbers.
"""
import copy
import re

# Everything from the TOTAL line onwards is summary, payment and VAT, never products.
TOTAL_LINE = re.compile(r"^TOTAL\b")
# Summary lines that can also appear before TOTAL, or when the model skipped TOTAL.
NON_ITEM_PREFIXES = (
    "SUBTOTAL", "MELLEMSUM", "MOMS", "HERAF", "BETALINGSKORT", "KREDITKORT",
    "DANKORT", "KONTANT", "MOBILEPAY", "BYTTEPENGE", "RABAT I ALT",
)
LINE_PATH = re.compile(r"^line_items\[(\d+)\](.*)$")

MONEY_TOLERANCE = 0.01
# Danish VAT is 25% on the net amount, i.e. 20% of the gross total.
MOMS_SHARE = 0.20
MOMS_TOLERANCE = 0.05


def _is_non_item(raw_text: str) -> bool:
    return raw_text.strip().upper().startswith(NON_ITEM_PREFIXES)


def clean(receipt: dict) -> tuple[dict, list[str]]:
    """Return a copy without non-item lines, plus the raw_text of each dropped line."""
    receipt = copy.deepcopy(receipt)
    kept, dropped, new_index = [], [], {}
    past_total = False
    for i, item in enumerate(receipt["line_items"]):
        past_total = past_total or bool(TOTAL_LINE.match(item["raw_text"].strip().upper()))
        if past_total or _is_non_item(item["raw_text"]):
            dropped.append(item["raw_text"])
            continue
        # A unit price equal to the line total on a single item adds nothing and
        # is almost always copied rather than printed; the schema wants null.
        if item["quantity"] == 1 and item["unit_price"] == item["total_price"]:
            item["unit_price"] = None
        new_index[i] = len(kept)
        kept.append(item)
    receipt["line_items"] = kept

    # uncertain_fields point at line indices; renumber them and forget dropped lines.
    remapped = []
    for path in receipt.get("uncertain_fields", []):
        m = LINE_PATH.match(path)
        if not m:
            remapped.append(path)
        elif int(m.group(1)) in new_index:
            remapped.append(f"line_items[{new_index[int(m.group(1))]}]{m.group(2)}")
    receipt["uncertain_fields"] = remapped
    return receipt, dropped


def check(receipt: dict) -> list[str]:
    """Return human-readable warnings; empty means every check passed."""
    warnings = []
    items = receipt["line_items"]
    total = receipt.get("total")

    unreadable = [i for i, item in enumerate(items) if item["total_price"] is None]
    if unreadable:
        warnings.append(f"line_items {unreadable} have no total_price; sum check is incomplete")
    line_sum = round(sum(item["total_price"] or 0 for item in items), 2)
    if total is None:
        warnings.append("total is missing")
    elif abs(line_sum - total) > MONEY_TOLERANCE:
        warnings.append(f"line items sum to {line_sum}, printed total is {total}")

    discount = receipt.get("discount")
    discount_lines = round(-sum(item["total_price"] or 0 for item in items if item["kind"] == "discount"), 2)
    if discount is not None and abs(discount - discount_lines) > MONEY_TOLERANCE:
        warnings.append(f"discount is {discount}, discount lines add up to {discount_lines}")

    moms = receipt.get("moms")
    if moms is not None and total is not None and abs(moms - total * MOMS_SHARE) > MOMS_TOLERANCE:
        warnings.append(f"moms {moms} is not ~20% of total {total} (expected ~{round(total * MOMS_SHARE, 2)})")
    return warnings
