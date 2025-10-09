# chatbot UI, upload, preview
# frontend/ui.py
import html
import pandas as pd
import streamlit as st
import sheets.summary
from ocr_llm.llm_supabase import llm_query_supabase
from ocr_llm.ocr import vision_extract_json
from backend.supabase_client import save_to_supabase, query_summary, get_period_range
from sheets.summary import sheet_summary

def inject_theme_css() -> None:
    """ฉีด CSS ธีม (ยกมาจาก app.py เดิม เพื่อเรียกใช้ซ้ำได้)"""
    st.markdown(
        r"""
        <style>
        :root{
            --pink-50: #fff7fb;
            --pink-100: #ffe7f1;
            --pink-150: #ffe0ee;
            --pink-200: #ffd1e6;
            --border: #ffd7e6;
            --ink: #2b2b2b;
            --muted: #6b6b6b;
            --radius: 24px;
            --shadow: 0 12px 36px rgba(0,0,0,.08);

            /* frosted vars */
            --glass-bg: rgba(255,255,255,.35);
            --glass-border: rgba(255,182,193,.70);
            --glass-shadow: 0 10px 26px rgba(255,105,180,.30);
        }

        html, body, .stApp, [data-testid="stAppViewContainer"] {
        background: radial-gradient(1200px 600px at 10% -10%, var(--pink-50) 0%, var(--pink-100) 35%, var(--pink-200) 100%) !important;
        }
        [data-testid="stAppViewContainer"] > .main,
        [data-testid="stAppViewContainer"] .block-container { background: transparent !important; }

        [data-testid="stDecoration"]{ display:none; }
        header[data-testid="stHeader"], div[data-testid="stHeader"]{ background: transparent !important; box-shadow: none !important; }

        .main .block-container { max-width: 1180px; padding-top: 1.2rem; padding-bottom: 4rem; }

        .pink-card {
            background: color-mix(in srgb, var(--pink-150) 88%, white 12%);
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            border: 1px solid var(--border);
            padding: 20px 22px;
            margin-bottom: 18px;
        }

        .title-xl{ font-size: 44px; line-height: 1.1; margin: 0; }
        .subtitle{ color: var(--muted); font-size: 14px; margin-top: 6px; }

        .bubble{ display:inline-block; padding: 10px 14px; border-radius: 18px; margin: 6px 0; max-width: 92%; }
        .bubble-left{ background:#ffd6e7; }
        .bubble-right{ background:#ffdfee; float:right; clear:both; }

        .stButton>button { border-radius: 999px; padding: .6rem 1.1rem; font-weight: 600; box-shadow: 0 6px 20px rgba(255, 140, 190, .35); }
        .stTextInput>div>div>input, .stSelectbox > div > div { border-radius: 14px; }
        .hint{ color: var(--muted); font-size: 12px; margin-top: .25rem; }

        /* Chat card + offset (ดันลงใต้หัวข้อ) */
        .chat-offset{ height: 96px; } /* ปรับได้ */
        @media (max-width:1100px){ .chat-offset{ height: 12px; } }

        .chat-card{
            position: sticky; top: 12px;
            background: color-mix(in srgb, var(--pink-150) 88%, white 12%);
            border: 1px solid var(--border);
            border-radius: 28px;
            box-shadow: var(--shadow);
            padding: 18px 18px 12px 18px;
        }
        .chat-header{ position: relative; height: 28px; margin-bottom: 6px; }
        .chat-tag{
            position: absolute; right: 12px; top: -8px;
            background: #ff8eb5; color: #fff; font-weight: 700;
            padding: 6px 12px; border-radius: 14px;
        }
        .chat-scroll{ max-height: 420px; overflow-y: auto; padding: 4px 2px; }

        /* ===== Frosted glass skins ===== */
        /* uploader */
        .uploader-skin [data-testid="stFileUploader"] > div,
        .uploader-skin [data-testid="stFileUploader"] [data-testid="stFileDropzone"]{
        background: var(--glass-bg) !important;
        -webkit-backdrop-filter: blur(10px) saturate(120%);
        backdrop-filter: blur(10px) saturate(120%);
        border: 1px solid var(--glass-border) !important;
        border-radius: 18px !important;
        box-shadow: var(--glass-shadow);
        }
        .uploader-skin [data-testid="stFileUploader"] button{
        background: #ff8eb5 !important; border-color: #ff8eb5 !important; color:#fff !important;
        border-radius: 14px !important; box-shadow: 0 6px 16px rgba(255,142,181,.45);
        }
        .uploader-skin [data-testid="stFileUploader"] svg{ fill:#ff6fa5 !important; stroke:#ff6fa5 !important; }

        /* text input wrapper */
        .glass-field .stTextInput>div{
        background: var(--glass-bg);
        -webkit-backdrop-filter: blur(10px) saturate(120%);
        backdrop-filter: blur(10px) saturate(120%);
        border: 1px solid var(--glass-border);
        border-radius: 18px; box-shadow: var(--glass-shadow); padding: 2px 4px;
        }
        .glass-field .stTextInput input{ background: transparent !important; }

        /* select wrapper */
        .glass-select .stSelectbox>div{
        background: var(--glass-bg);
        -webkit-backdrop-filter: blur(10px) saturate(120%);
        backdrop-filter: blur(10px) saturate(120%);
        border: 1px solid var(--glass-border);
        border-radius: 18px; box-shadow: var(--glass-shadow);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_chat_panel(llm_query_fn) -> None:
    """เรนเดอร์แชทฝั่งซ้าย ใช้ฟังก์ชัน LLM ที่ฉีดเข้ามา (เช่น llm_query_supabase)"""
    if "chat_hist" not in st.session_state:
        st.session_state.chat_hist = [{"role": "assistant", "content": "สวัสดี! มีอะไรให้ช่วยไหมคะ?"}]
    if "department" not in st.session_state:
        st.session_state.department = ""

    st.markdown('<div class="chat-offset"></div>', unsafe_allow_html=True)
    st.markdown('<div class="chat-header"><div class="chat-tag">สวัสดี</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="chat-scroll">', unsafe_allow_html=True)
    for m in st.session_state.chat_hist:
        side = "bubble-left" if m["role"] == "assistant" else "bubble-right"
        safe = html.escape(m["content"]).replace("\n", "<br/>")
        st.markdown(f"<div class='bubble {side}'>{safe}</div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    def _send_message():
        txt = (st.session_state.get("chat_input") or "").strip()
        if not txt:
            return
        st.session_state.chat_hist.append({"role": "user", "content": txt})
        dept = st.session_state.get("department") or ""
        prompt = f"[department={dept}] {txt}" if dept else txt
        try:
            resp = llm_query_fn(prompt)
            ai_text = resp.get("content") if isinstance(resp, dict) else str(resp)
        except Exception as e:
            ai_text = f"เกิดข้อผิดพลาดจาก LLM: {e}"
        st.session_state.chat_hist.append({"role": "assistant", "content": ai_text})
        st.session_state.chat_input = ""
        st.rerun()


    c_in, c_btn = st.columns([6, 1])
    with c_in:
        st.text_input("Type a message…", key="chat_input", label_visibility="collapsed",
                    placeholder="Type a message…")
    with c_btn:
        st.button("➤", use_container_width=True, on_click=_send_message)

    st.write("")
    try:
        st.image("assets/cat.png", use_container_width=True)
    except Exception:
        st.info("ใส่รูปแมวของคุณที่ assets/cat.png เพื่อให้โชว์ตรงนี้ ✨")


def render_header() -> None:
    """ส่วนหัว Receipt Bot (ไอคอน + H1)"""
    c = st.columns([0.12, 2.0])
    with c[0]:
        try:
            st.image("assets/cat.png", width=60)
        except Exception:
            st.markdown("<div style='font-size:60px'>🐱</div>", unsafe_allow_html=True)
    with c[1]:
        st.markdown('<h1 class="title-xl">ลุ้นReceipt</h1>', unsafe_allow_html=True)


def render_upload_panel(max_mb: int, vision_extract_fn, department_key: str = "department") -> None:
    """
    พาเนลอัปโหลด: อัปโหลดรูป → vision_extract_fn → เซ็ต session_state['pending_receipt']
    """
    st.subheader("📥 Upload", anchor=False)
    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown('<div class="uploader-skin">', unsafe_allow_html=True)
        uploaded = st.file_uploader(
            "กรุณาอัปโหลดรูปใบเสร็จของคุณเพื่อบันทึกลงในสมุดบัญชี",
            type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=False
        )
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown(f"<div class='hint'>Limit {max_mb}MB per file • JPG, JPEG, PNG, WEBP</div>", unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="glass-field">', unsafe_allow_html=True)
        st.text_input("department", key=department_key, placeholder="เช่น finance / sales / hr")
        st.markdown('</div>', unsafe_allow_html=True)

    if uploaded:
        st.image(uploaded, caption="Uploaded Receipt", width=400)
        if hasattr(uploaded, 'size') and uploaded.size and uploaded.size > max_mb * 1024 * 1024:
            st.error(f"ไฟล์เกิน {max_mb}MB")
        elif st.button("Process Receipt"):
            try:
                with st.spinner("Extracting with GPT-4o…"):
                    data = vision_extract_fn(uploaded.getvalue(), uploaded.type)
                    data["department"] = st.session_state.get(department_key, "")
                st.session_state["pending_receipt"] = data
                #st.success("✅ Extracted")
                st.subheader("📑 Extracted Data", anchor=False)
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


def render_confirm_save_panel(save_fn) -> None:
    """
    พาเนลยืนยันและบันทึก: ใช้ save_fn(data) -> bool
    อ่านข้อมูลจาก st.session_state['pending_receipt']
    """
    st.subheader("✅ Confirm & Save", anchor=False)
    pending = st.session_state.get("pending_receipt")
    if not pending:
        st.info("กรุณาอัปโหลดใบเสร็จและกดปุ่ม Process ก่อน")
        return
    st.markdown("กรุณาตรวจสอบข้อมูลก่อนบันทึก")
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