# หน้า summary รายวัน/สัปดาห์/เดือน
"""
หน้า Summary (รายวัน/สัปดาห์/เดือน) ดึงจาก /summary
ใช้ใน app.py: summary.render(api)
"""
from __future__ import annotations
import pandas as pd
import streamlit as st
from . import API

def _metric(value, label):
    if value is None:
        st.metric(label, "—")
    else:
        try:
            st.metric(label, f"{float(value):,.2f}")
        except Exception:
            st.metric(label, str(value))

def render(api: API):
    st.title("📊 Summary")
    period = st.selectbox("ช่วงเวลา", ["daily","weekly","monthly"], index=0)

    if st.button("Get Summary", type="primary"):
        try:
            with st.spinner("กำลังดึงสรุป..."):
                data = api.get_summary(period)  # {"total":..., "by_category":[...], "items":[...]}

            st.success("เรียบร้อย")

            # Metrics
            colA, colB, colC = st.columns(3)
            with colA: _metric(data.get("total"), "ยอดรวม")
            count_items = len(data.get("items") or [])
            with colB: _metric(count_items, "จำนวนรายการ")
            avg = (float(data["total"])/count_items) if data.get("total") is not None and count_items else None
            with colC: _metric(avg, "เฉลี่ย/รายการ")

            st.divider()

            # By category
            st.subheader("สรุปตามหมวดหมู่")
            by_cat = data.get("by_category") or []
            if by_cat:
                df_cat = pd.DataFrame(by_cat).rename(columns={
                    "category": "หมวดหมู่",
                    "amount": "จำนวนเงิน",
                })
                st.dataframe(df_cat, use_container_width=True)
            else:
                st.caption("— ไม่มีข้อมูลหมวดหมู่ —")

            st.divider()

            # Latest items
            st.subheader("รายการล่าสุด")
            items = data.get("items") or []
            if items:
                df_items = pd.DataFrame(items).rename(columns={
                    "date": "วันที่",
                    "merchant": "ร้านค้า",
                    "amount": "จำนวนเงิน",
                    "category": "หมวดหมู่",
                    "total": "ยอดรวม",
                })
                st.dataframe(df_items, use_container_width=True)
            else:
                st.caption("— ไม่มีรายการ —")

        except Exception as e:
            st.error(f"ดึงสรุปล้มเหลว: {e}")
