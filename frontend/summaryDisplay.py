# frontend/summary.py
import pandas as pd
import streamlit as st
from ocr_llm.llm_supabase import llm_query_supabase
from ocr_llm.ocr import vision_extract_json
from backend.supabase_client import save_to_supabase, query_summary, get_period_range
from sheets.summary import sheet_summary

def render_summary_panel(query_summary, get_period_range) -> None:
    # ---------- UI: Summary ----------
    st.subheader("📊 Summary")
    period = st.selectbox("เลือกช่วงเวลา", ["daily", "weekly", "monthly"], index=2)
    filter_user = st.text_input("department", value="", placeholder="เช่น finance/marketing/hr)")
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