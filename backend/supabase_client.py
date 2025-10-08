import os
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client
import streamlit as st
from openai import OpenAI

def S(key, default=None):
    return (st.secrets.get(key) if key in st.secrets else os.getenv(key, default))

OPENAI_API_KEY = S("OPENAI_API_KEY")
SUPABASE_URL = S("SUPABASE_URL")
SUPABASE_SERVICE_KEY = S("SUPABASE_SERVICE_KEY")

if not (OPENAI_API_KEY and SUPABASE_URL and SUPABASE_SERVICE_KEY):
    st.error("Missing secrets: ต้องตั้งค่า OPENAI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY")
    st.stop()

# 3) สร้าง clients
client = OpenAI(api_key=OPENAI_API_KEY)
sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def save_to_supabase(rec: dict) -> bool:  # save at supabase
    payload = {                           # จัดรูป payload ให้ตรง schema ของตาราง receipt ใน supabase
        "date": rec.get("date"),          # ตอนนี้ยังไม่ได้จัด ลุ้นจัดเด้อ
        "vendor": rec.get("vendor"),
        "total": rec.get("total"),
        "tax": rec.get("tax"),
        "currency": rec.get("currency", "THB"),
        "items_json": rec.get("items", []),       # items_json เก็บ items ทั้ง array ลงคอลัมน์ JSONB
        "user_id": rec.get("user_id", ""),
    }
    try:
        res = sb.table("receipts").upsert(payload).execute()
        # แสดงผลลัพธ์เพื่อวินิจฉัย
        st.write("Insert result:", res.data)
        return bool(res.data)
    except Exception as e:
        st.error("Insert failed:")
        st.exception(e)  # โชว์ stacktrace/ข้อความจาก Supabase
        return False        # เพื่อบอกว่าบันทึกสำเร็จไหม

def get_period_range(kind: str):          # สร้างกรอบช่วงเวลา
    today = datetime.utcnow().date()
    if kind == "daily":
        start, end = today, today
    elif kind == "weekly":
        start = today - timedelta(days=6)
        end = today
    else:  # monthly
        start = today.replace(day=1)
        end = today
    return start, end

def query_summary(kind: str, user_id: str | None = None) -> pd.DataFrame:   # ดึงสรุปจาก Supabase
    start, end = get_period_range(kind)
    cols = ["user_id", "date", "vendor", "total", "tax", "currency"]
    q = sb.table("receipts").select(",".join(cols)).gte("date", str(start)).lte("date", str(end)).order("date", desc=False)
    if user_id:
        q = q.eq("user_id", user_id)
    rows = q.execute().data or []
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for col in cols:
        if col in df.columns:
            if col in ["user_id", "vendor", "currency"]:
                df[col] = df[col].astype("string").str.strip()
            else :
                df[col] = pd.to_numeric(df[col], errors="coerce")
    return df