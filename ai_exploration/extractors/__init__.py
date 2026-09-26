"""Extractors: receipt image in, raw receipt JSON out.

Each module in this package exposes
    extract(image_path: Path) -> Result
LLM-based extractors share the prompt in extractors/prompts.py.
"""
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Result:
    """What every extractor returns: image in, structured receipt out."""
    extractor: str
    model: str
    image: Path
    raw_text: str
    parsed: dict | None
    seconds: float
    options: dict = field(default_factory=dict)
