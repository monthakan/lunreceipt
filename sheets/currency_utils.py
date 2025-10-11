import requests

def convert_fx(amount, from_ccy, to_ccy):
    from_ccy = from_ccy.strip().upper()
    to_ccy = to_ccy.strip().upper()

    FALLBACK_RATES = {
        ("USD", "THB"): 35.50,
        ("EUR", "THB"): 38.00,
        ("GBP", "THB"): 44.50,
        ("JPY", "THB"): 0.24,
        ("SGD", "THB"): 26.50,
        ("MYR", "THB"): 7.80,
        ("IDR", "THB"): 0.0022,
        ("CNY", "THB"): 4.90,
        ("KRW", "THB"): 0.027,
        ("VND", "THB"): 0.0014,
        ("AUD", "THB"): 23.00,
        ("CAD", "THB"): 27.00,
        ("CHF", "THB"): 40.00,
        ("NZD", "THB"): 22.00,
        ("HKD", "THB"): 4.50,
        ("THB", "USD"): 0.028,
        ("THB", "EUR"): 0.026,
        ("THB", "GBP"): 0.022,
        ("THB", "JPY"): 4.17,
        ("THB", "SGD"): 0.038,
        ("THB", "MYR"): 0.13,
        ("THB", "IDR"): 450.0,
        ("THB", "CNY"): 0.20,
        ("THB", "KRW"): 37.0,
        ("THB", "VND"): 720.0,
        ("THB", "AUD"): 0.044,
        ("THB", "CAD"): 0.037,
        ("THB", "CHF"): 0.025,
        ("THB", "NZD"): 0.045,
        ("THB", "HKD"): 0.22,
    }

    # 1) Frankfurter (no key)
    try:
        r = requests.get(
            "https://api.frankfurter.app/latest",
            params={"amount": float(amount), "from": from_ccy, "to": to_ccy},
            timeout=15,
            allow_redirects=False,
            proxies={}  # กัน proxy ที่อาจพาไปโดเมนอื่น
        )
        r.raise_for_status()
        data = r.json()
        if "rates" in data and to_ccy in data["rates"]:
            converted = float(data["rates"][to_ccy])
            rate = converted / float(amount) if float(amount) != 0 else None
            return {"provider": "frankfurter", "rate": rate, "converted_amount": converted}
    except Exception as e:
        print("Frankfurter failed:", e)

    # 2) Fallback: open.er-api.com (no key)
    try:
        r = requests.get(
            f"https://open.er-api.com/v6/latest/{from_ccy}",
            timeout=15,
            allow_redirects=False,
            proxies={}
        )
        r.raise_for_status()
        data = r.json()
        if data.get("result") == "success" and to_ccy in data["rates"]:
            rate = float(data["rates"][to_ccy])
            return {"provider": "er-api", "rate": rate, "converted_amount": float(amount) * rate}
        raise RuntimeError(f"er-api error: {data}")
    except Exception as e:
        print("ER-API failed:", e)


    # 3) Fallback using hardcoded rates
    key = (from_ccy, to_ccy)
    if key in FALLBACK_RATES:
        rate = FALLBACK_RATES[key]
        return {
            "provider": "fallback",
            "rate": rate,
            "converted_amount": float(amount) * rate
        }

    # 4) สุดท้าย ถ้าไม่มี rate เลย
    print(f"Warning: No rate found for {from_ccy}/{to_ccy}, using 1.0")
    return {
        "provider": "no_conversion",
        "rate": 1.0,
        "converted_amount": float(amount),
        "warning": f"No rate for {from_ccy}/{to_ccy}"
    }