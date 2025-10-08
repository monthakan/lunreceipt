import os, base64, json
from datetime import datetime, timedelta
from dateutil import parser as dparse
import pandas as pd
import streamlit as st
from ocr_llm.llm_supabase import llm_query_supabase
from ocr_llm.ocr import vision_extract_json
from backend.supabase_client import save_to_supabase, query_summary, get_period_range
from sheets.summary import sheet_summary
# 1) ต้องเรียก set_page_config ให้เร็วที่สุด (ก่อนมี output ใด ๆ)
st.set_page_config(page_title="📸 Receipt Bot", page_icon="🧾", layout="centered")

st.title("📸 Receipt Bot")
st.write("อัปโหลดใบเสร็จ → LLM Extract → บันทึกที่ Supabase → ดูสรุป")

# ---------- UI: Upload ----------
st.subheader("📥 Upload")
col1, col2 = st.columns([2,1])
with col1:
    uploaded = st.file_uploader("อัปโหลดรูปใบเสร็จ", type=["jpg","jpeg","png","webp"])
with col2:
    user_id = st.text_input("User ID", value="") # must edit เปลี่ยนเป็น requester_user_id

if uploaded:
    st.image(uploaded, caption="Uploaded Receipt", use_column_width=True)
    if st.button("Process Receipt"):
        try:
            with st.spinner("Extracting with GPT-4o..."):
                data = vision_extract_json(uploaded.getvalue(), uploaded.type)
                data["user_id"] = user_id
            st.session_state["pending_receipt"] = data
            st.success("✅ Extracted")
            st.subheader("📑 Extracted Data")
            st.json(data)
        except Exception as e:
            st.error(f"ไม่สามารถสกัด JSON ได้: {e}")

            """
                ให้ผู้ใช้อัปโหลดรูป + ใส่ user_id (ถ้าต้องการ)

                แสดงรูป preview

                เมื่อกด Process:

                เรียก vision_extract_json(...)

                เก็บผลลัพธ์ไว้ใน st.session_state["pending_receipt"] (จำค่าข้าม interaction ได้)

                โชว์ JSON ให้ตรวจสอบ
                            """

# ---------- UI: Confirm & Save ----------
st.subheader("✅ Confirm & Save")
pending = st.session_state.get("pending_receipt")
if not pending:
    st.info("ยังไม่มีข้อมูลรอยืนยัน (กด Process ก่อน)")
else:
    # ให้แก้ไขได้เล็กน้อยก่อนบันทึก
    edited_total = st.number_input("total", value=float(pending.get("total", 0) or 0.0))
    pending["total"] = edited_total
    if st.button("Save to Supabase"):
        ok = save_to_supabase(pending)
        if ok:
            st.success("บันทึกสำเร็จที่ Supabase")
            st.session_state.pop("pending_receipt", None)
        else:
            st.error("บันทึกล้มเหลว ตรวจตาราง/สิทธิ์ใน Supabase")
        sheet_summary()
    

# ---------- UI: Summary ----------
st.subheader("📊 Summary")
period = st.selectbox("เลือกช่วงเวลา", ["daily", "weekly", "monthly"], index=2)
filter_user = st.text_input("Filter user_id (optional)", value="")
if st.button("Get Summary"):
    df = query_summary(period, filter_user or None)
    if df.empty:
        st.info("ไม่มีข้อมูลในช่วงนี้")
    else:
        total = float(df["total"].sum()) if "total" in df.columns else 0.0
        start, end = get_period_range(period)
        st.write(f"ช่วง: {start} – {end} | รายการ: {len(df)}")
        st.metric("รวมทั้งหมด (THB)", f"{total:,.2f}")
        if "date" in df.columns and "total" in df.columns:
            df["date"]  = pd.to_datetime(df["date"], errors="coerce")   # ถ้าเป็น ISO ที่มี Z/เขตเวลา จะ parse ได้เอง
            df["total"] = pd.to_numeric(df["total"], errors="coerce").fillna(0)

            # ตัดแถวที่ parse วันที่ไม่สำเร็จ (NaT)
            df = df.dropna(subset=["date"])

            # --- สรุปรายวัน ---
            daily = df.groupby(df["date"].dt.date)["total"].sum().sort_index()
            st.line_chart(daily)
        st.dataframe(df)

st.subheader("💬 Ask about sales")
query_text = st.text_input("ถามยอดขาย / สรุป")
if st.button("Ask LLM"):
    if query_text:
        resp = llm_query_supabase(query_text)
        st.write(resp)