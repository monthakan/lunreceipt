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
        .chat-offset{ height: 96px; }
        @media (max-width:1100px){ .chat-offset{ height: 12px; } }

        /* ===== กล่องแชทสไตล์ฟรอสต์ (ใช้ container + :has(marker)) ===== */
        .chat-card-marker{ display:none; } /* ตัวระบุ container */
        /* เลือก container ที่มี marker ข้างใน แล้วทำเป็นการ์ด */
        section.main div[data-testid="stVerticalBlock"]:has(.chat-card-marker){
          background: var(--glass-bg) !important;
          -webkit-backdrop-filter: blur(10px) saturate(120%);
          backdrop-filter: blur(10px) saturate(120%);
          border: 1px solid var(--glass-border);
          border-radius: 28px;
          box-shadow: var(--glass-shadow);
          padding: 18px 18px 14px 18px;
          margin-bottom: 18px;
        }

        .chat-header{ position: relative; height: 28px; margin-bottom: 6px; }
        .chat-tag{
          position: absolute; right: 12px; top: -8px;
          background: #ff8eb5; color: #fff; font-weight: 700;
          padding: 6px 12px; border-radius: 14px;
        }
        .chat-scroll{ max-height: 420px; overflow-y: auto; padding: 4px 2px; }

        /* ===== Frosted glass skins ===== */
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

        .glass-field .stTextInput>div{
          background: var(--glass-bg);
          -webkit-backdrop-filter: blur(10px) saturate(120%);
          backdrop-filter: blur(10px) saturate(120%);
          border: 1px solid var(--glass-border);
          border-radius: 18px; box-shadow: var(--glass-shadow); padding: 2px 4px;
        }
        .glass-field .stTextInput input{ background: transparent !important; }

        .glass-select .stSelectbox>div{
          background: var(--glass-bg);
          -webkit-backdrop-filter: blur(10px) saturate(120%);
          backdrop-filter: blur(10px) saturate(120%);
          border: 1px solid var(--glass-border);
          border-radius: 18px; box-shadow: var(--glass-shadow);
        }

        /* ขยับหัวข้อ ไม่ให้ชนแมว และกันแตกตัวอักษรแนวตั้ง */
        .title-shift{ margin-left:14px; }
        .title-xl{ white-space:nowrap; word-break:normal; overflow:hidden; }

        @media (max-width:700px){
          .title-shift{ margin-left:8px; }
          .title-xl{ font-size:32px; }
        }
        /* --- FIX: อย่าให้ ancestor ทั้งหมดติดสไตล์การ์ด --- */
section.main div[data-testid="stVerticalBlock"]:has(.chat-card-marker){
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
}

/* ✅ สไตล์เฉพาะบล็อกที่มี marker เป็น 'ลูกโดยตรง' เท่านั้น */
section.main div[data-testid="stVerticalBlock"]:has(> .chat-card-marker){
  background: var(--glass-bg) !important;
  -webkit-backdrop-filter: blur(10px) saturate(120%);
  backdrop-filter: blur(10px) saturate(120%);
  border: 1px solid var(--glass-border) !important;
  border-radius: 28px !important;
  box-shadow: var(--glass-shadow) !important;
  padding: 18px 18px 14px 18px !important;
  margin-bottom: 18px !important;
}
/* ขยับหัวข้อให้ชิดไอคอนแมวมากขึ้น */
.title-shift{ margin-left: 0; }
.brand-title{ margin-left: 4px; }    /* เว้นนิดเดียวพอให้ไม่ชน */
@media (max-width:700px){
  .brand-title{ margin-left: 2px; }
}

/* ระยะว่างหลังเฮดเดอร์ ใช้ดันส่วน Upload ลง */
.section-after-header{ height: 18px; }
@media (min-width:1200px){
  .section-after-header{ height: 28px; }
}
/* ให้หัวข้อขยับเข้าใกล้แมวมากขึ้น */
.title-shift{ margin-left: 0; }
.brand-tight{ margin-left: -10px; }   /* ถ้ายังอยากชิดอีก เปลี่ยนเป็น -14px ได้ */
@media (max-width:700px){
  .brand-tight{ margin-left: -6px; }
}
/* ระยะว่างหลังส่วนหัว */
.section-after-header{ height: 36px; }       /* เดิม 18/28 -> ดันลงชัดขึ้น */
@media (min-width:1200px){
  .section-after-header{ height: 48px; }
}
/* ===== Summary: light pink theme ===== */
.summary-skin .stSelectbox label,
.summary-skin .stTextInput label{
  color: #f3a8be;              /* ชมพูอ่อนมาก */
  font-weight: 600;
}

/* พื้นหลัง & เส้นกรอบของ input/select */
.summary-skin .stSelectbox>div>div,
.summary-skin .stTextInput>div{
  background: rgba(255, 182, 193, .16);     /* ชมพูอ่อนโปร่ง ๆ */
  border: 1px solid #ffd2e1 !important;     /* กรอบชมพูอ่อน */
  border-radius: 14px;
  box-shadow: none;
}

/* สีตัวหนังสือภายในช่อง */
.summary-skin .stTextInput input,
.summary-skin .stSelectbox div[role="combobox"]{
  color: #c36e87;                            /* ชมพูหม่นอ่านง่าย */
}

/* placeholder */
.summary-skin .stTextInput input::placeholder{
  color: #f1b8c8;
  opacity: 1;
}

/* ปุ่ม Get Summary เป็นชมพูอ่อน */
.summary-skin .stButton>button{
  background: #ffd6e6 !important;
  border: 1px solid #ffc6da !important;
  color: #b5496a !important;
  border-radius: 999px;
  box-shadow: 0 6px 16px rgba(255,142,181,.35);
}
.summary-skin .stButton>button:hover{
  background: #ffcfe1 !important;
}
}
/* การ์ดห่อกราฟ – พื้นหลังขาว ขอบโค้ง เงานุ่ม */
.chart-card{
  background:#fff;
  border:1px solid #ffd7e6;
  border-radius:18px;
  box-shadow:0 8px 24px rgba(255, 232, 242, 1.2);
  padding:12px;
  overflow:hidden; /* ให้มุมกราฟโค้งตามการ์ด */
}

/* โทนชมพูอ่อนเฉพาะบล็อก Summary (ถ้ายังไม่มี) */
.summary-skin label{ color:#f3a8be; font-weight:600; }
.summary-skin [data-testid="stSelectbox"]>div,
.summary-skin [data-testid="stTextInput"]>div{
  background:rgba(255,182,193,.16);
  border:1px solid #ffd2e1;
  border-radius:14px;
}
.summary-skin .stButton>button{
  background:#ffd6e6; border:1px solid #ffc6da; color:#b5496a; border-radius:999px;
  box-shadow:0 6px 16px rgba(255,142,181,.35);
}
.summary-skin .stButton>button:hover{ background:#ffcfe1; }


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

    # ✅ ใช้ container ครอบทุกอย่าง แล้วแปะ marker ให้ CSS จับ
    with st.container():
        st.markdown('<span class="chat-card-marker"></span>', unsafe_allow_html=True)

        st.markdown('<div class="chat-header"><div class="chat-tag">สวัสดี</div></div>', unsafe_allow_html=True)

        st.markdown('<div class="chat-scroll">', unsafe_allow_html=True)
        for m in st.session_state.chat_hist:
            side = "bubble-left" if m["role"] == "assistant" else "bubble-right"
            safe = html.escape(m["content"]).replace("\n", "<br/>")
            st.markdown(f"<div class='bubble {side}'>{safe}</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)  # ปิด .chat-scroll

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
        # try:
        #     st.image("assets/cat.png", use_container_width=False)
        # except Exception:
        #     st.info("ใส่รูปแมวของคุณที่ assets/cat.png เพื่อให้โชว์ตรงนี้ ✨")

def render_header() -> None:
    # เดิมมี 3 คอลัมน์ -> เอาให้เหลือ 2
    c = st.columns([0.26, 2.0])   # อยากชิดกว่านี้ลดเป็น 0.22 ได้

    with c[0]:
        try:
            st.image("assets/cat.png", width=60)
        except Exception:
            st.markdown("<div style='font-size:50px'>🐱</div>", unsafe_allow_html=True)

    with c[1]:
        # เพิ่มคลาส brand-tight เพื่อติดแมวมากขึ้น
        st.markdown('<h1 class="title-xl title-shift brand-tight">ลุ้นReceipt</h1>', unsafe_allow_html=True)


def render_upload_panel(max_mb: int, vision_extract_fn, department_key: str = "department") -> None:
    st.subheader("📥 Upload", anchor=False)

    c1, c2 = st.columns([2, 1])   
    with c1:
        st.markdown('<div class="uploader-skin">', unsafe_allow_html=True)
        nonce = st.session_state.get("uploader_nonce", 0)
        uploaded = st.file_uploader(
            "กรุณาอัปโหลดรูปใบเสร็จของคุณเพื่อบันทึกลงในสมุดบัญชี",
            type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=False,
            key=f"receipt_uploader_{nonce}",
        )
        st.markdown('</div>', unsafe_allow_html=True)

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
                    # ใช้ department ด้านบน (สำหรับติดแท็กบันทึก)
                    data["user_id"] = st.session_state.get(department_key, "")
                st.session_state["pending_receipt"] = data
                st.success("สำเร็จ! กรุณาตรวจสอบข้อมูลด้านล่าง")
                #เพิ่มส่วนแสดง JSON ด้านล่าง
                st.subheader("📑 Extracted Data", anchor=False)
                st.json(data)
            except Exception as e:
                st.error(f"ไม่สามารถสกัด JSON ได้: {e}")



def render_confirm_save_panel(save_fn) -> None:
    st.subheader("✅ Confirm & Save", anchor=False)

    pending = st.session_state.get("pending_receipt")
    if not pending:
        st.info("กรุณาอัปโหลดใบเสร็จและกดปุ่ม Process ก่อน")
        return

    st.markdown("กรุณาตรวจสอบข้อมูลก่อนบันทึก")

    edited_total = st.number_input( #เอาค่า total มาจาก pending
        "total",
        value=float(pending.get("total", 0) or 0.0),
        step=0.01,
        format="%.2f",
    )
    pending["total"] = edited_total
    if st.button("Save to Supabase", use_container_width=True):
        try:
            ok = save_fn(pending)
        except Exception as e:
            st.error(f"บันทึกล้มเหลว: {e}")
            return

        if ok:
            st.session_state["flash_saved"] = True
            st.session_state.pop("pending_receipt", None)
            st.session_state["uploader_nonce"] = st.session_state.get("uploader_nonce", 0) + 1
            st.rerun()
        else:
            st.error("บันทึกล้มเหลว ตรวจตาราง/สิทธิ์ใน Supabase")