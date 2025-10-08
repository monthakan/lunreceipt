import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def structure_text(text: str) -> dict:
    prompt = f"""
    Extract the following fields from the receipt text (English or Thai):
    - date (YYYY-MM-DD)
    - shop (store name)
    - items (list of name, qty, price)
    - total (total amount)
    - 

    Receipt Text:
    {text}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that extracts structured data from receipts."},
            {"role": "user", "content": prompt}
        ],
        functions=[ # Define the function schema
            {
                "name": "extract_receipt",
                "description": "Extract receipt fields",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string"},
                        "shop": {"type": "string"},
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "qty": {"type": "integer"},
                                    "price": {"type": "number"}
                                },
                                "required": ["name", "qty", "price"]
                            }
                        },
                        "total": {"type": "number"}
                    },
                    "required": ["date", "shop", "items", "total"]
                }
            }
        ],
        function_call={"name": "extract_receipt"}
    )

    # ดึง arguments จาก function_call และแปลงเป็น JSON
    result_text = response.choices[0].message.function_call.arguments
    try:
        result_json = json.loads(result_text)
        return result_json
    except json.JSONDecodeError:
        return {
            "date": None,
            "shop": None,
            "items": [],
            "total": None,
            "error": result_text
        }
