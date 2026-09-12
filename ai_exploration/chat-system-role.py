from ollama import chat

SCHEMA_EXAMPLE = {
    "vendor": "string or null",
    "line_items": [
        {
            "raw_text": "string, exactly as printed on the receipt including abbreviations",
            "name": "string, the expanded/normalized item name in Danish",
            "quantity": "number or null",
            "unit_price": "number or null",
            "total_price": "number",
            "category": "string, a general category guess (e.g. dairy, meat, produce, bakery, beverage, household, other)"
        }
    ],
    "subtotal": "number or null",
    "discount": "number or null",
    "moms": "number or null",
    "total": "number",
    "payment_method": "string or null",
    "uncertain_fields": [
        "string, name the field or line item text you were not confident about"
    ]
}

# Define a system prompt
system_prompt = f"""
You are a receipt-scanning extraction engine for Danish grocery and retail receipts.
You read an image of a receipt and output ONLY a single valid JSON object, with no markdown code fences, no explanation, and no text before or after the JSON.

Output schema (values below describe the expected type/content, not literal output):
{json.dumps(SCHEMA_EXAMPLE, indent=2, ensure_ascii=False)}

Danish receipt conventions to know:
- Decimal separator is a comma, not a period (e.g. "24,95" means 24.95). Convert to standard numeric format (period as decimal separator) in your output.
- Common abbreviations you will see printed on receipts, and what they mean:
  - "M/" = "med" (with)
  - "U/" = "uden" (without)
  - "UDL." = "udenlandsk" (foreign, e.g. a foreign transaction or foreign goods)
  - "ØKO" = "økologisk" (organic)
  - "STK" = "stykker" (pieces/units)
  - "RAB" or "RABAT" = "rabat" (discount)
  - "PANT" = bottle/can deposit
  - "MOMS" = Danish VAT
- Do not guess numeric values you cannot read clearly. Use null and flag it in "uncertain_fields" instead of fabricating a plausible-looking number.
- These abbreviations are common but not exhaustive. When you encounter an abbreviation you recognize with confidence, expand it in "name" while preserving the original in "raw_text". When you encounter an abbreviation or truncated word you are not confident about, keep "raw_text" as printed, make your best guess at "name", and add that line item to "uncertain_fields" rather than inventing a confident-sounding expansion.
"""

print("Sending request...")

stream = chat(
    model='qwen3-vl:2b-instruct',
    messages=[
        {
            'role': 'system',
            'content': system_prompt,
        },
        {
            'role': 'user',
            'content': 'Extract the following receipt text into a JSON object according to the schema above:\n\n',
            'images': ['imgs/IMG_8680.jpg'],
        },
    ],
    options={
        'num_ctx': 8192,
        'temperature': 0.1,
    },
    stream=True,
)

for chunk in stream:
   print(chunk.message.content, end='', flush=True)
  

print() 