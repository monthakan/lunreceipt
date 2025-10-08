from ocr_llm.llm import chat_with_llm
from backend.supabase_client import query_summary
import json
def llm_query_supabase(user_input: str, chat_history: list) -> str:
    # วิเคราะห์ intent
    intent_prompt = f"""
    แปลงคำถามผู้ใช้เป็น JSON STRICT:
    {user_input}
    keys: period (daily/weekly/monthly), shop_name, amount, user_id
    Return ONLY JSON.
    """
    intent_json = chat_with_llm(chat_history + [{"role":"user","content":intent_prompt}])
    try:
        intent = json.loads(intent_json)
    except:
        intent = {}

    # query Supabase
    period = intent.get("period","monthly")
    df = query_summary(period)
    if shop := intent.get("shop_name"):
        df = df[df["vendor"]==shop]
    if amount := intent.get("amount"):
        df = df[df["total"]==amount]
    if user_id := intent.get("user_id"):
        df = df[df["user_id"]==user_id]

    # ส่งข้อมูล + history ให้ LLM สรุป
    summary_prompt = f"""
    ข้อมูลจาก Supabase:
    {df.to_dict(orient='records')}
    ตอบคำถามผู้ใช้: "{user_input}"
    ให้ตอบเป็นภาษาธรรมชาติ สั้น เข้าใจง่าย และตรงคำถาม
    """
    messages = chat_history + [{"role":"user","content":summary_prompt}]
    return chat_with_llm(messages)
