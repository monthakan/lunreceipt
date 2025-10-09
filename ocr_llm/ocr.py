from PIL import Image
import pytesseract
import io
import base64
import json
from datetime import date
from dateutil import parser as dparse
from openai import OpenAI
import streamlit as st
import re

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# แผนที่เดือนภาษาไทย
THAI_MONTHS = {
    "มกราคม":1, "กุมภาพันธ์":2, "มีนาคม":3, "เมษายน":4,
    "พฤษภาคม":5, "มิถุนายน":6, "กรกฎาคม":7, "สิงหาคม":8,
    "กันยายน":9, "ตุลาคม":10, "พฤศจิกายน":11, "ธันวาคม":12,
    "ม.ค.":1, "ก.พ.":2, "มี.ค.":3, "เม.ย.":4,
    "พ.ค.":5, "มิ.ย.":6, "ก.ค.":7, "ส.ค.":8,
    "ก.ย.":9, "ต.ค.":10, "พ.ย.":11, "ธ.ค.":12
}

def extract_thai_or_slash_date(text: str) -> str:
    """รองรับทั้งรูปแบบไทยและ DD/MM/YY"""
    # รูปแบบ "วันที่ X เดือน พ.ศ."
    pattern_thai = r"วันที่\s*(\d{1,2})\s*([ก-ฮ\.]+)\s*(\d{2,5})"
    match = re.search(pattern_thai, text)
    if match:
        day = int(match.group(1))
        month_str = match.group(2).replace(".", "")
        raw_year = int(match.group(3))
        month = THAI_MONTHS.get(match.group(2), 1)

        # ปีสั้น
        if raw_year < 100:
            if raw_year > 25:
                raw_year += 2500  # สมมติเป็น พ.ศ.
            else:
                raw_year += 2000  # สมมติเป็น ค.ศ.

        # แปลง พ.ศ. → ค.ศ.
        if raw_year >= 2500:
            year = raw_year - 543
        else:
            year = raw_year

        return f"{year:04d}-{month:02d}-{day:02d}"

    # ถ้ามันเป็นรูปแบบ DD/MM/YY 
    pattern_slash = r"(\d{1,2})/(\d{1,2})/(\d{2,4})"
    match = re.search(pattern_slash, text)
    if match:
        day = int(match.group(1))
        month = int(match.group(2))
        raw_year = int(match.group(3))

        if raw_year < 100:
            if raw_year > 25:
                raw_year += 2500
            else:
                raw_year += 2000

        if raw_year >= 2500:
            year = raw_year - 543
        else:
            year = raw_year

        return f"{year:04d}-{month:02d}-{day:02d}"

    # --- fallback ---
    return date.today().isoformat()

def vision_extract_json(file_bytes: bytes, mime: str = "image/png") -> dict:
    """
    ให้ prompt ปกติก่อน ถ้าไม่ได้ผลค่อย fallback ไป function calling
    """
    # OCR 
    img = Image.open(io.BytesIO(file_bytes))
    ocr_text = pytesseract.image_to_string(img, lang="tha+eng")

    # date 
    date_iso = extract_thai_or_slash_date(ocr_text)

    # convert image to base64 
    b64 = base64.b64encode(file_bytes).decode()
    data_url = f"data:{mime};base64,{b64}"

    #ปกติ
    prompt = (
        "You are a receipt parser for Thai receipts. "
        "Extract STRICT JSON with keys: vendor, date, items[{name, qty, unit_price}], "
        "subtotal, tax, total, currency. Return ONLY JSON."
    )
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[{
                "role":"user",
                "content":[
                    {"type":"text","text":prompt},
                    {"type":"image_url","image_url":{"url":data_url}}
                ]
            }]
        )
        raw = resp.choices[0].message.content
        data = json.loads(raw)
        required_fields = ["vendor","items","subtotal","tax","total","currency"]
        if not all(field in data for field in required_fields):
            raise ValueError("Missing field")
    except Exception:
        # fallback Tool Calling
        functions = [
            {
                "name": "extract_receipt",
                "description": "Extract structured fields from a receipt",
                "parameters": {
                    "type":"object",
                    "properties":{
                        "vendor":{"type":"string"},
                        "items":{
                            "type":"array",
                            "items":{
                                "type":"object",
                                "properties":{
                                    "name":{"type":"string"},
                                    "qty":{"type":"integer"},
                                    "unit_price":{"type":"number"}
                                },
                                "required":["name","qty","unit_price"]
                            }
                        },
                        "subtotal":{"type":"number"},
                        "tax":{"type":"number"},
                        "total":{"type":"number"},
                        "currency":{"type":"string"}
                    },
                    "required":["vendor","items","subtotal","tax","total","currency"]
                }
            }
        ]
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role":"user",
                "content":[
                    {"type":"text","text":"Extract JSON according to 'extract_receipt'. Do NOT include date."},
                    {"type":"image_url","image_url":{"url":data_url}}
                ]
            }],
            functions=functions,
            function_call={"name":"extract_receipt"}
        )
        raw_json = resp.choices[0].message.function_call.arguments
        try:
            data = json.loads(raw_json)
        except:
            data = {"vendor":None,"items":[],"subtotal":None,"tax":None,"total":None,"currency":None,"error":raw_json}

    # ---------- ใส่วันที่ ----------
    data["date"] = date_iso
    return data
