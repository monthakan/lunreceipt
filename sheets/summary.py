# aggregation / pivot / summary
import datetime
import os
import streamlit as st
import re
import itertools
from datetime import datetime, date
from supabase import create_client, Client
from dotenv import load_dotenv

def S(key, default=None):
    return (st.secrets.get(key) if key in st.secrets else os.getenv(key, default))

def process_receipts(data):
    daily = {}
    weekly = {}
    monthly = {}

    for row in data:
        #check each row
        print("Date:", row["date"])
        print("Vendor:", row["vendor"])
        print("Total:", row["total"])
        print("Tax:", row["tax"])
        print("Currency:", row["currency"])
        print("Items:", row["items_json"])
        print("User_ID:", row["user_id"])
        print("------------")

        # Currency conversion
        if row["currency"] != "THB":
            from sheets.currency_utils import convert_fx
            conversion = convert_fx(row["total"], row["currency"], "THB")
            # print(f"Converted {row['total']} {row['currency']} to {conversion['converted_amount']:.2f} THB at rate {conversion['rate']:.4f}")
            row["total"] = conversion['converted_amount']

        #sum by day
        if row["date"] not in daily:
            daily[row["date"]] = {}
            daily[row["date"]]["expense"] = 0
            daily[row["date"]]["expense_ratio"] = 0
        daily[row["date"]]["expense"] += row["total"]

        date_str = row["date"]  # e.g., "2025-10-06"
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        year = date_obj.year
        if year not in weekly:
            weekly[year] = {} 
            monthly[year] = {} 

        #sum by week
        week = date_obj.isocalendar()[1]
        if week not in weekly[year]:
            weekly[year][week] = {}
            weekly[year][week]["expense"] = 0
            weekly[year][week]["expense_ratio"] = 0
        weekly[year][week]["expense"] += row["total"]

        #sum by month
        month = date_obj.month  # directly get month number
        if month not in monthly[year]:
            monthly[year][month] = {}
            monthly[year][month]["expense"] = 0
            monthly[year][month]["expense_ratio"] = 0
        monthly[year][month]["expense"] += row["total"]

    return daily, weekly, monthly

def _parse_date(x):
    if isinstance(x, datetime):
        return x
    if isinstance(x, date):
        return datetime(x.year, x.month, x.day)
    s = str(x)
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return datetime.max  # unknown format goes last
def _as_year(y):
    try:
        return int(y)
    except Exception:
        return 0  # push weird years first (or change to large number to push last)

def _week_index(v):
    # supports: 4, "4", "W04", "Week 4", "2025-W40"
    if isinstance(v, int): 
        return v
    s = str(v)
    m = re.search(r'(?:^|\D)(?:w|week)?\s*(\d{1,2})$', s, flags=re.I)
    if m:
        return int(m.group(1))
    digs = re.findall(r'\d{1,2}', s)
    return int(digs[-1]) if digs else 10**6  # unknown -> end

_MONTHS = {
    'jan':1,'january':1, 'feb':2,'february':2, 'mar':3,'march':3,
    'apr':4,'april':4, 'may':5, 'jun':6,'june':6, 'jul':7,'july':7,
    'aug':8,'august':8, 'sep':9,'sept':9,'september':9,
    'oct':10,'october':10, 'nov':11,'november':11, 'dec':12,'december':12
}
def _month_index(v):
    # supports: 3, "03", "Mar", "March", "2025-03", "03/2025"
    if isinstance(v, int):
        return v
    s = str(v).lower()
    # look for month name first (from the right)
    toks = re.split(r'[^a-z0-9]+', s)
    for tok in reversed(toks):
        if tok in _MONTHS:
            return _MONTHS[tok]
        if tok.isdigit():
            n = int(tok)
            if 1 <= n <= 12:
                return n
    return 10**6

def save_receipt(data, type):
    url: str = S("SUPABASE_URL")
    key: str = S("SUPABASE_SERVICE_KEY")
    supabase: Client = create_client(url, key)
    print(f"Mock save to Supabase ({type}):", data)

    if f"{type}" == "date":
        items = sorted(data.items(), key=lambda kv: _parse_date(kv[0]))

        # build list first
        data_list = list(map(lambda x: {
            f"{type}": x[0],
            "expense(THB)": float(x[1].get('expense', 0) or 0),
            "expense_ratio": None  # will fill below
        }, items))

        # compute % change vs previous (ascending time)
        prev_exp = None
        for i in range(len(data_list)):
            curr_exp = data_list[i]["expense(THB)"]
            if prev_exp is None or prev_exp == 0:
                # first row or previous expense is zero → undefined change
                data_list[i]["expense_ratio"] = 0   # or 0.0 if you prefer
            else:
                ratio = (curr_exp - prev_exp) / prev_exp
                data_list[i]["expense_ratio"] = round(ratio * 100, 2)
            prev_exp = curr_exp

        # upsert to supabase
        # (consider renaming "expense(THB)" column to expense_thb in your table)
        response = supabase.table(f"sum by {type}").upsert(data_list).execute()
        return 0
    else:
        data_list = [
        {
            "year": year,
            f"{type}": t,
            "expense(THB)": float(type_data.get("expense", 0) or 0),
            "expense_ratio": None,  # will fill below
        }
        for year, type_ in data.items()        # outer dict: by year
        for t, type_data in type_.items()      # inner dict: by week/month
    ]

        # ---------- 2) sort by (year, week) or (year, month) ----------
        if type == "week":
            data_list.sort(key=lambda r: (_as_year(r["year"]), _week_index(r["week"])))
        elif type == "month":
            data_list.sort(key=lambda r: (_as_year(r["year"]), _month_index(r["month"])))
        else:
            data_list.sort(key=lambda r: (_as_year(r["year"]), r[f"{type}"]))

        # ---------- 3) compute % change vs previous *within each year* ----------
        out = []
        for _, grp in itertools.groupby(data_list, key=lambda r: _as_year(r["year"])):
            prev = None
            for row in grp:
                curr = row["expense(THB)"]
                if prev in (None, 0):
                    row["expense_ratio"] = 0   # or 0.0 if you prefer
                else:
                    row["expense_ratio"] = round(((curr - prev) / prev) * 100, 2)
                prev = curr
                out.append(row)

        data_list = out


        response = supabase.table(f"sum by {type}".lower()).upsert(data_list).execute()
    print(response.data)

    print(f"Completed saving receipt and items to Supabase ({type}).")

def save_items_pivot(data):
    url: str = S("SUPABASE_URL")
    key: str = S("SUPABASE_SERVICE_KEY")
    supabase: Client = create_client(url, key)
    print("Mock save to Supabase (Item Pivot):", data)
    stored_items = {}
    for row in data:
        items = row["items_json"]

        if not items:
            continue
        for item in items:
            name = item.get("name")
            qty = item.get("qty", 1)
            print(row)
            # Currency conversion
            if row["currency"] != "THB":
                from sheets.currency_utils import convert_fx
                conversion = convert_fx(item["unit_price"], row["currency"], "THB")
                # print(f"Converted {row['total']} {row['currency']} to {conversion['converted_amount']:.2f} THB at rate {conversion['rate']:.4f}")
                print(conversion)
                item["unit_price"] = conversion['converted_amount']
            if name not in stored_items:
                stored_items[name] = {"qty": 0, "unit_price(THB)": item.get("unit_price", 0)}
            stored_items[name]["qty"] += qty
        
        data_list = list(map(lambda x: {
            "name": x[0], 
            "qty": x[1].get('qty', 0),        # use .get() to avoid KeyError
            "unit_price(THB)": x[1].get('unit_price(THB)', 0),
            "expense(THB)": x[1].get('qty', 0) * x[1].get('unit_price(THB)', 0)
            }, stored_items.items()))
        response = supabase.table("items_pivot").upsert(data_list).execute()
        print(response.data)

    print("Completed saving item pivot to Supabase.")

def sheet_summary() : 
    load_dotenv()

    url: str = S("SUPABASE_URL")
    key: str = S("SUPABASE_SERVICE_KEY")
    supabase: Client = create_client(url, key)

    response = supabase.table("receipts").select("*").execute()
    data = response.data

    day_dict, week_dict, month_dict = process_receipts(data)

    save_receipt(day_dict, "date")
    save_receipt(week_dict, "week")
    save_receipt(month_dict, "month")

    save_items_pivot(data)