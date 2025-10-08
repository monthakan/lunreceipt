# test_chat.py
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))  # เพิ่ม recript-bot
from . import llm_supabase

# ทดสอบเรียกใช้งาน
if __name__ == "__main__":
    test_data = {
        "date": "2025-10-05",
        "shop": "Lotus Rama 2",
        "items": [
            {"name": "Milk", "qty": 2, "price": 30},
            {"name": "Bread", "qty": 1, "price": 25},
        ],
        "total": 85
    }

    response = llm_supabase.process_receipt(test_data)
    print(response)
