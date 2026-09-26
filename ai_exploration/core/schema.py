from typing import Literal, get_args

from pydantic import BaseModel

# Closed vocabularies: single source of truth for the prompt, the output grammar, and validation.
LineKind = Literal["item", "deposit", "discount"]
Category = Literal[
    "dairy", "meat_fish", "produce", "bakery", "beverage", "snacks_sweets",
    "frozen", "pantry", "household", "personal_care", "other",
]
PaymentMethod = Literal["card", "cash", "mobilepay", "other"]

LINE_KINDS = list(get_args(LineKind))
CATEGORIES = list(get_args(Category))
PAYMENT_METHODS = list(get_args(PaymentMethod))

# Category -> what belongs there, with Danish examples. Keep examples out of the
# test receipts in data/receipts/, or the prompt leaks answers into the score.
CATEGORY_GUIDE = {
    "dairy": "milk, cheese, yoghurt, butter, eggs, cream (e.g. letmælk, skyr, smør, æg, fløde)",
    "meat_fish": "meat, poultry, sausages, cold cuts, fish (e.g. hakket oksekød, kylling, pølser, leverpostej, laks)",
    "produce": "fresh fruit, vegetables, herbs (e.g. æbler, gulerødder, agurk, kartofler)",
    "bakery": "bread and baked goods, including filled or topped pastries (e.g. rundstykker, franskbrød, wienerbrød, croissant, kage)",
    "beverage": "drinks (e.g. sodavand, juice, kaffe, øl, vand)",
    "snacks_sweets": "chips, candy, chocolate, cookies (e.g. slik, chokolade, kiks)",
    "frozen": "frozen food (e.g. frosne ærter, is, frossen pizza)",
    "pantry": "dry and canned goods, spices, oils (e.g. pasta, ris, mel, nødder, konserves)",
    "household": "cleaning and paper goods (e.g. opvaskemiddel, køkkenrulle, vaskepulver)",
    "personal_care": "hygiene and cosmetics (e.g. shampoo, tandpasta, deodorant)",
    "other": "deposit and discount lines, or products that fit nowhere else",
}
assert list(CATEGORY_GUIDE) == CATEGORIES, "CATEGORY_GUIDE must describe every Category, in order"

SCHEMA_EXAMPLE = {
    "vendor": "string (store name as printed, usually at the top) or null",
    "line_items": [
        {
            "raw_text": "string, the line copied exactly as printed, including abbreviations",
            "kind": f"exactly one of: {' | '.join(LINE_KINDS)}",
            "name": "string, expanded item name in Danish (for deposit/discount lines, the printed label)",
            "quantity": "number (pieces, or kg for weighed goods); 1 if no quantity is printed",
            "unit_price": "number, only if a per-unit price is printed on the receipt, otherwise null",
            "total_price": "number in DKK as printed (negative for kind=discount), or null if unreadable"
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


# Same shape as SCHEMA_EXAMPLE, as types. Receipt.model_json_schema() is passed to
# Ollama as format=, so the model can only emit these fields and vocabulary values.
# Categories are not extracted from the image; categorize.py adds them afterwards.
class LineItem(BaseModel):
    raw_text: str
    kind: LineKind
    name: str
    quantity: float
    unit_price: float | None
    total_price: float | None


class Receipt(BaseModel):
    vendor: str | None
    line_items: list[LineItem]
    subtotal: float | None
    discount: float | None
    moms: float | None
    total: float | None
    payment_method: PaymentMethod | None
    uncertain_fields: list[str]


class ItemCategory(BaseModel):
    """Output of the text-only categorization pass, one product at a time."""
    category: Category | None
