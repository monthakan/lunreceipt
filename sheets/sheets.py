# aggregation / pivot / summary
def save_receipt(data):
    print("Mock save to Google Sheets:", data)

def get_summary_sheet(period="daily"):
    return {"period": period, "total_spent": 999, "items_count": 12}
