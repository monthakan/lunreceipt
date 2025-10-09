# app.py
import streamlit as st

# ====== BACKEND FUNCS ======
from ocr_llm.llm_supabase import llm_query_supabase
from ocr_llm.ocr import vision_extract_json
from backend.supabase_client import query_summary, get_period_range
from backend.supabase_client import save_to_supabase
from sheets.summary import save_receipt

# ====== FRONTEND (ไฟล์ที่เราสร้างให้) ======
from frontend import (
    inject_theme_css,
    render_chat_panel,
    render_header,
    render_upload_panel,
    render_confirm_save_panel,
    render_summary_panel,
)

# ---- CONFIG ----
st.set_page_config(page_title="ลุ้นReceipt", page_icon="🐱", layout="wide")
inject_theme_css()

MAX_MB = 20

# ---- STATE ----
if "chat_hist" not in st.session_state:
    st.session_state.chat_hist = [{"role": "assistant", "content": "สวัสดี! มีอะไรให้ช่วยไหมคะ?"}]
if "department" not in st.session_state:
    st.session_state.department = ""

# ---- LAYOUT ----
left, right = st.columns([1, 2], gap="large")

with left:
    render_chat_panel(llm_query_supabase)

with right:
    render_header()
    render_upload_panel(MAX_MB, vision_extract_json)           # → st.session_state["pending_receipt"]
    render_confirm_save_panel(save_to_supabase)                 # → บันทึก Supabase
    render_summary_panel(query_summary, get_period_range)       # → ดึงสรุป

st.caption("ลุ้นRecript • ทีมเพื่อนโฟล์ค ✨")