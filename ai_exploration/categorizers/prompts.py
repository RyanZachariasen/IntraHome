"""Prompt shared by every LLM categorizer."""
from core.schema import CATEGORY_GUIDE


def build_category_prompt() -> str:
    category_guide = "\n".join(f"- {name}: {desc}" for name, desc in CATEGORY_GUIDE.items())
    return f"""
You categorize one product from a Danish grocery receipt.
You get the product name as printed and an expanded name. Answer with the single category it belongs to.
Decide by what the product is, not by single words in its name (a pastry with cream is bakery, not dairy).
If you do not know what the product is, answer null rather than guessing.

Categories:
{category_guide}
"""
