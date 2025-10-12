import os
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client
import streamlit as st
from openai import OpenAI
from sheets.currency_utils import convert_fx

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
        "user_id": rec.get("user_id", ""), # user_id (department)
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

def query_summary(kind: str, user_id: str | None = None, start_date: 'date | None' = None, end_date: 'date | None' = None) -> pd.DataFrame:
    """ดึงสรุปจาก Supabase ด้วย date range หรือ period"""
    # ถ้าส่ง start_date/end_date มาให้ใช้ start_date/end_date
    if start_date and end_date:
        start = start_date
        end = end_date
    else:
        start, end = get_period_range(kind)
    cols = ["user_id", "date", "vendor", "total", "tax", "currency"] # คอลัมน์ที่ต้องการดึงมา
    # Supabase ต้องการ ISO format string แม้ว่าจะเก็บเป็น nanosecond
    start_iso = start.isoformat()
    end_iso = end.isoformat()
    # สร้าง query เพื่อดึงข้อมูล
    q = (sb.table("receipts").select(",".join(cols)).gte("date", start_iso).lte("date", end_iso).order("date", desc=False))

    if user_id: # กรองด้วย user_id ถ้ามี
        q = q.eq("user_id", user_id)
    rows = q.execute().data or []
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    # แปลง date - Supabase เก็บเป็น nanosecond
    if "date" in df.columns:
        if df['date'].dtype in ['int64', 'float64']: # nanosecond
            df["date"] = pd.to_datetime(df["date"], unit='ns') # แปลงจาก nanosecond เป็น datetime
        else:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
    # แปลง data type เพราะบางคอลัมน์อาจมี NaN
    for col in cols:
        if col in df.columns:
            if col in ["user_id", "vendor", "currency"]:
                df[col] = df[col].astype("string").str.strip()
            else:
                df[col] = pd.to_numeric(df[col], errors="coerce")
    if "currency" in df.columns: # แปลงสกุลเงินเป็น THBให้หมด
        records = []
        for idx, row in df.iterrows():
            if pd.notna(row["currency"]) and row["currency"].upper() != "THB":
                ccy = row["currency"]
                try:
                    if pd.notna(row["total"]):
                        result = convert_fx(row["total"], ccy, "THB")
                        # ให้เอา converted_amount จากฟังก์ชัน convert_fx มาใช้แทน
                        row["total"] = result.get("converted_amount", row["total"]) if isinstance(result, dict) else result
                    if pd.notna(row["tax"]):
                        result = convert_fx(row["tax"], ccy, "THB")
                        row["tax"] = result.get("converted_amount", row["tax"]) if isinstance(result, dict) else result
                    row["currency"] = "THB"
                except Exception as e:
                    st.warning(f"Currency conversion failed for row {idx}: {e}")
            records.append(row)
        df = pd.DataFrame(records).reset_index(drop=True)
    return df