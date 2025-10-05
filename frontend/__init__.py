"""
แพ็กเกจ Frontend helpers สำหรับ Receipt Bot
- API: ตัวช่วยเรียก backend ด้วย httpx
- map_to_schema: แปลงคีย์จาก OCR/LLM ให้ตรง schema DB
"""
from __future__ import annotations
import io
import os
from typing import Any, Dict, List, Optional
import httpx

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
TIMEOUT_S = int(os.getenv("HTTP_TIMEOUT", "120"))

def _url(base: str, path: str) -> str:
    return f"{base.rstrip('/')}/{path.lstrip('/')}"

class API:
    def __init__(self, base_url: Optional[str] = None, timeout: int = TIMEOUT_S):
        self.base_url = (base_url or BACKEND_URL).rstrip("/")
        self.timeout = timeout

    def ping(self) -> str:
        with httpx.Client(timeout=10) as c:
            r = c.get(_url(self.base_url, "/health"))
            r.raise_for_status()
            return r.text

    def process_receipt(self, uploaded_file) -> Dict[str, Any]:
        files = {"file": (uploaded_file.name, io.BytesIO(uploaded_file.getvalue()), uploaded_file.type)}
        with httpx.Client(timeout=self.timeout) as c:
            r = c.post(_url(self.base_url, "/process_receipt"), files=files)
            r.raise_for_status()
            return r.json()

    def send_to_sheets(self, uploaded_file) -> Dict[str, Any]:
        files = {"file": (uploaded_file.name, io.BytesIO(uploaded_file.getvalue()), uploaded_file.type)}
        with httpx.Client(timeout=self.timeout) as c:
            r = c.post(_url(self.base_url, "/send_to_sheets"), files=files)
            r.raise_for_status()
            return r.json()

    def save_receipt(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        with httpx.Client(timeout=60) as c:
            r = c.post(_url(self.base_url, "/save_receipt"), json=payload)
            r.raise_for_status()
            return r.json()

    def get_summary(self, period: str = "daily") -> Dict[str, Any]:
        with httpx.Client(timeout=60) as c:
            r = c.get(_url(self.base_url, "/summary"), params={"period": period})
            r.raise_for_status()
            return r.json()

    def chat(self, messages: List[Dict[str, str]], params: Optional[Dict[str, Any]] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        payload = {"messages": messages, "params": params or {}, "session_id": session_id}
        with httpx.Client(timeout=self.timeout) as c:
            r = c.post(_url(self.base_url, "/chat"), json=payload)
            r.raise_for_status()
            return r.json()

def map_to_schema(res: Dict[str, Any]) -> Dict[str, Any]:
    """แปลงคีย์จาก OCR/LLM → schema ที่ DB คาดหวัง (ปรับชื่อคอลัมน์ได้ที่นี่)"""
    items_out: List[Dict[str, Any]] = []
    for i, it in enumerate(res.get("items", []), start=1):
        items_out.append({
            "line_no": i,
            "item_name": it.get("item_name") or it.get("name"),
            "qty": it.get("qty", 1),
            "unit_price": it.get("unit_price") or it.get("price"),
            "category": it.get("category"),
        })
    return {
        "merchant": res.get("merchant"),
        "receipt_date": res.get("receipt_date") or res.get("date"),  # YYYY-MM-DD
        "total": res.get("total"),
        "currency": res.get("currency", "THB"),
        "items": items_out,
        "source_file_url": res.get("source_file_url"),
    }
