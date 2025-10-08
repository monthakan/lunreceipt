from ocr_llm.llm import chat_with_llm, structure_text
from backend.supabase_client import query_summary
import pandas as pd

def llm_query_supabase(user_input: str) -> str:
    """
    1) ให้ LLM วิเคราะห์ intent (period, shop_name) → structure_text / chat_with_llm
    2) ดึงข้อมูลจาก Supabase
    3) ส่งข้อมูลกลับให้ LLM สรุป
    """
    # 1️⃣ ใช้ LLM วิเคราะห์ intent
    intent_prompt = f"""
    แปลงคำสั่งภาษาไทยเป็น JSON:
    {user_input}
    keys: period (daily/weekly/monthly), shop_name (string or null)
    """
    intent_json = chat_with_llm(intent_prompt)
    try:
        import json
        intent = json.loads(intent_json)
    except:
        intent = {"period":"monthly","shop_name":None}

    period = intent.get("period","monthly")
    shop_name = intent.get("shop_name",None)

    # 2️⃣ query Supabase
    df = query_summary(period)
    if shop_name and not df.empty:
        df = df[df["vendor"]==shop_name]

    # 3️⃣ ส่งข้อมูลให้ LLM สรุป
    summary_prompt = f"""
    ข้อมูลจาก Supabase:
    {df.to_dict(orient='records')}
    สรุปยอดขาย {period} สำหรับร้าน {shop_name or 'ทุกร้าน'} เป็นข้อความสั้นเข้าใจง่าย
    """
    return chat_with_llm(summary_prompt)
