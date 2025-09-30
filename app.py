import streamlit as st
# backend/services.py
from sheets.sheets import save_receipt, get_summary_sheet
from backend.services import process_receipt, save_to_sheet, get_summary

st.title("📸 Receipt Bot")
st.write("อัพโหลดใบเสร็จ → ระบบจะ OCR + LLM + ส่งเข้า Google Sheets")

uploaded_file = st.file_uploader("Upload Receipt", type=["jpg", "jpeg", "png"])

if uploaded_file:
    st.image(uploaded_file, caption="Uploaded Receipt", use_column_width=True)

    if st.button("Process Receipt"):
        with st.spinner("Processing..."):
            data = process_receipt(uploaded_file)

        st.subheader("📑 Extracted Data")
        st.json(data)

        if st.button("Save to Google Sheets"):
            save_to_sheet(data)
            st.success("✅ Saved to Google Sheets")

st.subheader("📊 Summary")
period = st.selectbox("เลือกช่วงเวลา", ["daily", "weekly", "monthly"])
if st.button("Get Summary"):
    summary = get_summary(period)
    st.write(summary)
