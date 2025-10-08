from PIL import Image
import pytesseract
import io
import os
import base64
import json
from datetime import datetime, timedelta
from dateutil import parser as dparse
from openai import OpenAI
import streamlit as st
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def vision_extract_json(file_bytes: bytes, mime: str) -> dict:
    """ให้ GPT-4o อ่านรูปใบเสร็จและคืน JSON ตามสคีมา"""
    if not mime:
        mime = "image/png"
    b64 = base64.b64encode(file_bytes).decode()
    data_url = f"data:{mime};base64,{b64}"

    prompt = (
        "You are a receipt parser for Thai receipts. "
        "Extract STRICT JSON with keys: vendor, date (YYYY-MM-DD), "
        "items[{name, qty, unit_price}], subtotal, tax, total, currency. "
        "Return ONLY JSON (no markdown/prose)."
    )

    resp = client.chat.completions.create(   # << new SDK call
        model="gpt-4o-mini",
        temperature=0,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_url}}
            ]
        }]
    )

    raw = resp.choices[0].message.content
    # บางรุ่นอาจส่งเป็นชิ้น ๆ; ที่นี่คาดหวังเป็นสตริงเดียว
    try:
        data = json.loads(raw)
    except Exception:
        # ถ้าตอบไม่ใช่ JSON ล้วน แสดงผลดิบไว้ช่วยดีบั๊ก
        raise ValueError(f"Model did not return pure JSON:\n{raw}")

    # normalize วันที่
    try:
        data["date"] = dparse.parse(str(data.get("date"))).date().isoformat()
    except Exception:
        pass
    return data