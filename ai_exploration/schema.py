# Closed vocabularies: single source of truth for the prompt now, and for validation later.
LINE_KINDS = ["item", "deposit", "discount"]
CATEGORIES = [
    "dairy", "meat_fish", "produce", "bakery", "beverage", "snacks_sweets",
    "frozen", "pantry", "household", "personal_care", "other",
]
PAYMENT_METHODS = ["card", "cash", "mobilepay", "other"]

SCHEMA_EXAMPLE = {
    "vendor": "string (store name as printed, usually at the top) or null",
    "line_items": [
        {
            "raw_text": "string, the line copied exactly as printed, including abbreviations",
            "kind": f"exactly one of: {' | '.join(LINE_KINDS)}",
            "name": "string, expanded item name in Danish (for deposit/discount lines, the printed label)",
            "quantity": "number (pieces, or kg for weighed goods); 1 if no quantity is printed",
            "unit_price": "number, only if a per-unit price is printed on the receipt, otherwise null",
            "total_price": "number in DKK as printed (negative for kind=discount), or null if unreadable",
            "category": f"exactly one of: {' | '.join(CATEGORIES)}; use other for deposit and discount lines"
        }
    ],
    "subtotal": "number, only if a subtotal is printed before discount/total, otherwise null",
    "discount": "number, positive, only if a total discount amount is printed, otherwise null",
    "moms": "number, the VAT amount in DKK as printed (not the percentage), or null",
    "total": "number, the final amount paid as printed, or null if unreadable",
    "payment_method": f"exactly one of: {' | '.join(PAYMENT_METHODS)}, or null if not printed",
    "uncertain_fields": [
        "string, a path to the field you were not confident about: a top-level name like total, or line_items[i].field with i counting from 0, e.g. line_items[2].total_price. Empty list if fully confident."
    ]
}
