from ocr_llm.chat_with_llm import chat_with_llm
from backend.supabase_client import query_summary
from datetime import date, datetime, timedelta
import json
import pandas as pd
import re
from datetime import date, timedelta

def parse_date_from_input(user_input: str):
    """ตัดสินใจว่าผู้ใช้ถามวันที่ไหน"""
    today = date.today()
    print(f"Parsing date from: '{user_input}'")
    print(f"Today is: {today}")
    user_input_lower = user_input.lower()
    #แยกวิเคราะห์คำถามหาวันที่
    # วันนี้
    if any(k in user_input_lower for k in ["วันนี้", "today"]):
        print(f"   → Matched 'today': {today}")
        return today, today
    # เมื่อวาน
    if any(k in user_input_lower for k in ["เมื่อวาน", "yesterday"]):
        yesterday = today - timedelta(days=1)
        print(f"   → Matched 'yesterday': {yesterday}")
        return yesterday, yesterday
    # วันที่ D MONTH YYYY
    month_map = {
        "มกราคม": 1, "กุมภาพันธ์": 2, "มีนาคม": 3, "เมษายน": 4,
        "พฤษภาคม": 5, "มิถุนายน": 6, "กรกฎาคม": 7, "สิงหาคม": 8,
        "กันยายน": 9, "ตุลาคม": 10, "พฤศจิกายน": 11, "ธันวาคม": 12,
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12,
    }
    # format "วันที่ 3 ตุลาคม 2025" หรือ "3 october 2025" to "3/10/2025"
    pattern1 = r'วันที่\s+(\d{1,2})\s+(\w+)\s+(\d{4})|(\d{1,2})\s+(\w+)\s+(\d{4})'
    match = re.search(pattern1, user_input, re.IGNORECASE)
    if match:
        day = int(match.group(1) or match.group(4))
        month_str = (match.group(2) or match.group(5)).lower()
        year = int(match.group(3) or match.group(6))

        month = month_map.get(month_str)
        if month:
            try:
                target_date = date(year, month, day)
                print(f"   → Matched 'วันที่ D MONTH YYYY': {target_date}")
                return target_date, target_date
            except:
                print(f"   → Invalid date {day}/{month}/{year}")
                return None, None

    # format DD/MM/YYYY หรือ D/M/YYYY to "3/10/2025"
    match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', user_input)
    if match:
        day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
        try:
            target_date = date(year, month, day)
            print(f"   → Matched DD/MM/YYYY: {target_date}")
            return target_date, target_date
        except:
            print(f"   → Invalid date {day}/{month}/{year}")
            return None, None

    # วันที่ X (เดือนปัจจุบัน)
    for i in range(1, 32):
        if f"วันที่ {i}" in user_input or f"{i}/" in user_input:
            try:
                target_date = date(today.year, today.month, i)
                print(f"   → Matched day {i}: {target_date}")
                return target_date, target_date
            except:
                print(f"   → Invalid day {i}")
                return None, None
    # สัปดาห์นี้
    if any(k in user_input_lower for k in ["สัปดาห์นี้", "this week"]):
        start = today - timedelta(days=today.weekday())
        end = today
        print(f"   → Matched 'this week': {start} to {end}")
        return start, end
    # สัปดาห์ที่แล้ว
    if any(k in user_input_lower for k in ["สัปดาห์ที่แล้ว", "last week"]):
        end = today - timedelta(days=today.weekday() + 1)
        start = end - timedelta(days=6)
        print(f"   → Matched 'last week': {start} to {end}")
        return start, end
    # เดือนนี้
    if any(k in user_input_lower for k in ["เดือนนี้", "this month"]):
        start = date(today.year, today.month, 1)
        print(f"   → Matched 'this month': {start} to {today}")
        return start, today
    # เดือนที่แล้ว
    if any(k in user_input_lower for k in ["เดือนที่แล้ว", "last month"]):
        first = date(today.year, today.month, 1)
        last_month_end = first - timedelta(days=1)
        last_month_start = date(last_month_end.year, last_month_end.month, 1)
        print(f"   → Matched 'last month': {last_month_start} to {last_month_end}")
        return last_month_start, last_month_end
    # ปีนี้
    if any(k in user_input_lower for k in ["ปีนี้", "this year"]):
        start = date(today.year, 1, 1)
        print(f"   → Matched 'this year': {start} to {today}")
        return start, today
    # ปีที่แล้ว
    if any(k in user_input_lower for k in ["ปีที่แล้ว", "last year"]):
        start = date(today.year - 1, 1, 1)
        end = date(today.year - 1, 12, 31)
        print(f"   → Matched 'last year': {start} to {end}")
        return start, end
    # ไม่ระบุ → return None
    print(f"   → No date matched, returning None")
    return None, None


def llm_query_supabase(user_input: str) -> str:
    user_id = None
    """
    RAG + Supabase + Chat พร้อมรองรับการถามวันที่
    ดึง user_id/department จากคำถามโดยไม่ต้องส่งมา
    """
    keywords = [
        "ยอด", "ร้าน", "ใบเสร็จ", "สรุป", "รายวัน", "รายเดือน", "รายสัปดาห์",
        "ใช้จ่าย", "รวม", "ซื้อ", "จ่าย", "เงิน", "เท่าไร", "อะไรบ้าง",
        "how much", "total", "summary", "spend", "spent", "receipt", "shop", "store", "buy", "purchase", "paid",
        "this month", "this week", "today", "yesterday", "last week", "last month",
        "เดือนนี้", "สัปดาห์นี้", "วันนี้", "เมื่อวาน", "สัปดาห์ที่แล้ว", "เดือนที่แล้ว",
        "this year", "last year", "ปีนี้", "ปีที่แล้ว", "วันที่"
    ]
    if not any(k in user_input for k in keywords):
        # คำถามทั่วไป
        return chat_with_llm(user_input)

    #แยกว่าผู้ใช้ถามอะไร โดยใช้ LLM แยก
    intent_prompt = f"""You are a JSON parser. Read the user input and determine :
        1. period: MUST be "daily", "weekly", or "monthly"
            - "วันนี้", "วันที่", "เมื่อวาน", "today", "yesterday", "date" → "daily"
            - "สัปดาห์", "week" → "weekly"
            - "เดือน", "month", "ปี", "year" → "monthly"
        2. shop_name: Store/shop name if mentioned (7-Eleven, Boots, etc), otherwise null
        3. user_id: User/department name if mentioned (ฝ่ายการเงิน, Sales, HR, Finance, etc)
        Map to: "finance", "sales", "hr", "it", "marketing", etc
        If not mentioned, return null

        User input: {user_input}

        RESPOND ONLY WITH VALID JSON, NO OTHER TEXT:
        {{"period": "monthly", "shop_name": null, "user_id": null}}
        """
    intent_json = chat_with_llm(intent_prompt).strip()
    # ลบ markdown เพราะบางที LLM จะใส่มา
    if intent_json.startswith("```"):
        intent_json = intent_json.split("```")[1]
        if intent_json.startswith("json"):
            intent_json = intent_json[4:]
    intent_json = intent_json.strip() #ลบ space ใหม่
    # แปลง JSON
    try:
        intent = json.loads(intent_json)
    except:
        intent = {"period": "monthly", "shop_name": None, "department": None}
    #กำหนดค่า default จาก JSON ของ LLM
    period = intent.get("period", "monthly")
    shop_name = intent.get("shop_name", None)
    #เอา user_id จาก intent มาแล้วเทียบกับชื่อในฐานข้อมูล
    if not user_id: #ถ้า user_id ยังไม่มี
        dept_map = { #สร้าง mapping เพื่อแปลงชื่อฝ่ายเป็น user_id
            "finance": "finance",
            "ฝ่ายการเงิน": "finance",
            "sales": "sales",
            "ฝ่ายขาย": "sales",
            "hr": "hr",
            "ทรัพยากรบุคคล": "hr",
            "it": "it",
            "ไอที": "it",
            "marketing": "marketing",
            "ฝ่ายการตลาด": "marketing",
            "บัญชี": "accounting",
            "accounting": "accounting",
            "operations": "operations",
            "ฝ่ายปฏิบัติการ": "operations",
            "admin": "admin",
            "แอดมิน": "admin",
            "management": "management",
            "ผู้บริหาร": "management",
            "market": "marketing",  # เผื่อพิมพ์ผิด
            "sale": "sales",        # เผื่อพิมพ์ผิด
            "hrm": "hr",            # เผื่อพิมพ์ผิด
            "การตลาด": "marketing",
        }
        user_input_lower = user_input.lower()
        for key, val in dept_map.items(): #วนลูปเช็คว่ามีคำไหนใน user_input บ้าง
            if key in user_input_lower:
                user_id = val
                print(f" search department: {user_id}")
                break

    #เอาแค่วันที่จาก user_input
    date_start, date_end = parse_date_from_input(user_input)
    print(f"🔍 Parsed: period={period}, shop_name={shop_name}, date_range={date_start} to {date_end}")

    # ถ้า parse_date_from_input เจอวันที่ เรียก query_summary ด้วย date range
    if date_start and date_end:
        print(f"📅 Querying from {date_start} to {date_end}")
        # ส่ง date range ไปยัง query_summary เพื่อดึงข้อมูลจาก Supabase
        df = query_summary(period, user_id=user_id, start_date=date_start, end_date=date_end)
    else:
        # ถ้าไม่มี date specific ก็เรียกแบบปกติ
        df = query_summary(period, user_id=user_id)
    # Filter by shop_name
    if shop_name and not df.empty:
        df = df[df["vendor"].str.lower() == shop_name.lower()]
        print(f"🏪 Filtered {len(df)} records for shop: {shop_name}")

    # สร้าง context_text จาก df
    if df.empty:
        context_text = "ไม่มีข้อมูลใบเสร็จที่เกี่ยวข้อง"
    else:
        df_summary = df.copy()
        df_summary.fillna("-", inplace=True)
        rows = []
        # สรุปรวมตามสกุลเงิน
        summary_by_currency = {}
        total_count = 0
        for _, row in df_summary.iterrows():
            total_count += 1
            currency = row.get("currency", "THB")
            total = row.get("total", 0)
            if currency not in summary_by_currency:
                summary_by_currency[currency] = 0
            summary_by_currency[currency] += total
            item_lines = ", ".join([f"{item['name']} x{item['qty']} @ {item['unit_price']}"
                                    for item in row.get("items", [])])
            row_date = row.get("date")
            # แปลง date ให้เป็น string
            if hasattr(row_date, "date"):  # Timestamp / datetime
                row_date = row_date.date()
            elif isinstance(row_date, int):
                try:
                    row_date = date.fromtimestamp(row_date)
                except:
                    row_date = str(row_date)
            else:
                row_date = str(row_date)
            rows.append(f"ร้าน: {row.get('vendor')}, วันที่: {row_date}, รวม: {row.get('total')} {currency}, รายการ: {item_lines}")

        # สร้างรายละเอียดและสรุปเพื่อส่งให้ LLM
        detail_text = "\n".join(rows)
        summary_text = f"\n📊 สรุปรวม: {total_count} รายการ\n"
        for currency, total in summary_by_currency.items():
            summary_text += f"  • {total:.2f} {currency}\n"
        context_text = f"{detail_text}\n{summary_text}"

    prompt = f"""คุณเป็นผู้ช่วยสรุปยอดขายจากใบเสร็จ
            ข้อมูลที่เกี่ยวข้อง:
            {context_text}

            วันนี้คือ {date.today().isoformat()}
            ตอบคำถามผู้ใช้: {user_input}
            ตอบเป็นภาษาไทยแบบสรุปยอด ให้เข้าใจง่าย
            """
    return chat_with_llm(prompt)