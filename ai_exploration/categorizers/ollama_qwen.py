"""Text-only categorization with local qwen3-vl via Ollama, one call per product (no image)."""
from ollama import chat

from categorizers import categorize_with
from categorizers.prompts import build_category_prompt
from core.schema import Category, ItemCategory

MODEL = 'qwen3-vl:2b-instruct'
OPTIONS = {
    # Must match the extractor's num_ctx: Ollama reloads the model when it changes.
    'num_ctx': 8192,
    'temperature': 0,
}


def classify(raw_text: str, name: str) -> Category | None:
    response = chat(
        model=MODEL,
        messages=[
            {'role': 'system', 'content': build_category_prompt()},
            {'role': 'user', 'content': f'Printed: {raw_text}\nExpanded: {name}'},
        ],
        format=ItemCategory.model_json_schema(),
        options=OPTIONS,
    )
    try:
        return ItemCategory.model_validate_json(response.message.content).category
    except ValueError:
        return None


def categorize(receipt: dict) -> tuple[dict, dict]:
    receipt, seconds = categorize_with(receipt, classify)
    return receipt, {'categorizer': 'ollama_qwen', 'model': MODEL, 'options': OPTIONS, 'seconds': seconds}
