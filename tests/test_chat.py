# test_chat.py
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))  # เพิ่ม recript-bot
from ocr_llm.llm_supabase import llm_query_supabase

# ทดสอบเรียกใช้งาน
if __name__ == "__main__":
    # result = llm_query_supabase("ฝ่ายการเงินใช้ไปกี่บาท", user_id="ฝ่ายการเงิน")
    # print(result)
    result = llm_query_supabase("ฝ่ายการเงินใช้ไปกี่บาท")
    print(result)
