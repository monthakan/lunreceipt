import requests

def convert_fx(amount, from_ccy, to_ccy):
    from_ccy = from_ccy.strip().upper()
    to_ccy = to_ccy.strip().upper()

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

    raise RuntimeError("All FX providers failed")
