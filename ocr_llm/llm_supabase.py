from ocr_llm.chat_with_llm import chat_with_llm
from backend.supabase_client import query_summary
from datetime import date
import json
import pandas as pd

def llm_query_supabase(user_input: str) -> str:
    """
    RAG + Supabase + Chat พร้อมรองรับการถามวันที่
    """
    keywords = [
        "ยอด", "ร้าน", "ใบเสร็จ", "สรุป", "รายวัน", "รายเดือน", "รายสัปดาห์",
        "ใช้จ่าย", "รวม", "ซื้อ", "จ่าย", "เงิน", "เท่าไร", "อะไรบ้าง",
        "how much", "total", "summary", "spend", "spent", "receipt", "shop", "store", "buy", "purchase", "paid",
        "this month", "this week", "today", "yesterday", "last week", "last month",
        "เดือนนี้", "สัปดาห์นี้", "วันนี้", "เมื่อวาน", "สัปดาห์ที่แล้ว", "เดือนที่แล้ว",
        "this year", "last year", "ปีนี้", "ปีที่แล้ว","วันที่"
    ]
    if not any(k in user_input for k in keywords):
        # คำถามทั่วไป 
        return chat_with_llm(user_input)

    intent_prompt = f"""
    แปลงคำสั่งภาษาไทยเป็น JSON:
    {user_input}
    keys: period (daily/weekly/monthly), shop_name (string or null)
    """
    intent_json = chat_with_llm(intent_prompt)
    try:
        intent = json.loads(intent_json)
    except:
        intent = {"period": "monthly", "shop_name": None}

    period = intent.get("period", "monthly")
    shop_name = intent.get("shop_name", None)

    # ----------------- Query Supabase -----------------
    df = query_summary(period)
    if shop_name and not df.empty:
        df = df[df["vendor"] == shop_name]

    # rag
    if df.empty:
        context_text = "ไม่มีข้อมูลใบเสร็จที่เกี่ยวข้อง"
    else:
        df_summary = df.copy()
        df_summary.fillna("-", inplace=True)
        rows = []
        for _, row in df_summary.iterrows():
            item_lines = ", ".join([f"{item['name']} x{item['qty']} @ {item['unit_price']}" 
                                    for item in row.get("items", [])])
            row_date = row.get("date")
            # แปลง date ให้เป็น string ปลอดภัย
            if hasattr(row_date, "date"):  # Timestamp / datetime
                row_date = row_date.date()
            elif isinstance(row_date, int):
                try:
                    row_date = date.fromtimestamp(row_date)
                except:
                    row_date = str(row_date)
            else:
                row_date = str(row_date)

            rows.append(f"ร้าน: {row.get('vendor')}, วันที่: {row_date}, รวม: {row.get('total')} {row.get('currency')}, รายการ: {item_lines}")

        context_text = "\n".join(rows)

    prompt = f"""
        คุณเป็นผู้ช่วยสรุปยอดขายจากใบเสร็จ
        ข้อมูลที่เกี่ยวข้อง:
        {context_text}

        วันนี้คือ {date.today().isoformat()}
        ตอบคำถามผู้ใช้: {user_input}
        """
    return chat_with_llm(prompt)
