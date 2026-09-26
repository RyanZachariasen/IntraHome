import json
import time
from pathlib import Path

from ollama import chat

from core.schema import Receipt
from extractors import Result
from extractors.prompts import build_system_prompt

MODEL = 'qwen3-vl:2b-instruct'
OPTIONS = {
    'num_ctx': 8192,
    'temperature': 0.1,
}


def extract(image_path: Path) -> Result:
    start = time.perf_counter()

    stream = chat(
        model=MODEL,
        messages=[
            {
                'role': 'system',
                'content': build_system_prompt(),
            },
            {
                'role': 'user',
                'content': 'Extract the following receipt text into a JSON object according to the schema above:\n\n',
                'images': [str(image_path)],
            },
        ],
        # Constrained decoding: output can only match the Receipt JSON Schema.
        format=Receipt.model_json_schema(),
        options=OPTIONS,
        stream=True,
    )

    chunks = []
    for chunk in stream:
        piece = chunk.message.content
        print(piece, end='', flush=True)
        chunks.append(piece)
    print()

    raw_text = "".join(chunks)

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as e:
        print(f"Model did not return valid JSON: {e}")
        parsed = None

    return Result(
        extractor='ollama_qwen',
        model=MODEL,
        image=image_path,
        raw_text=raw_text,
        parsed=parsed,
        seconds=round(time.perf_counter() - start, 2),
        options=OPTIONS,
    )
