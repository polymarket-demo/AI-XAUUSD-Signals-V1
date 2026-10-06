import requests
import pandas as pd
import time
from datetime import datetime, timezone


# ============================================================
# AI XAUUSD SIGNALS V1
# LIVE DATA ENGINE
# ============================================================

API_URL = "https://xaus.com/api/v1/spot"

last_price = None
last_price_time = None

print("========================================")
print("AI XAUUSD SIGNALS V1")
print("LIVE XAU/USD DATA ENGINE")
print("========================================")


def get_live_xau_price():
    """
    Get live XAU/USD spot price from XAUS.
    No API key required.
    """

    cache_buster = int(time.time())

    response = requests.get(
        API_URL,
        params={"fresh": cache_buster, "compact": "1"},
        timeout=10
    )

    response.raise_for_status()

    data = response.json()

    if "spot_usd_oz" not in data:
        raise ValueError("XAU price not found in API response")

    price = float(data["spot_usd_oz"])

    data_state = data.get("data_state", {})
    status = data_state.get("status", "unknown")

    price_as_of = data.get(
        "price_as_of",
        data_state.get("as_of", "")
    )

    return price, price_as_of, status


while True:

    try:

        price, price_time, status = get_live_xau_price()

        now = datetime.now(timezone.utc).isoformat()

        print("")
        print("========================================")
        print("LIVE XAU/USD")
        print("========================================")
        print(f"PRICE       : {price}")
        print(f"PRICE TIME  : {price_time}")
        print(f"DATA STATUS : {status}")
        print(f"CHECKED     : {now}")

        # ----------------------------------------------------
        # Check if the price/timestamp actually changed
        # ----------------------------------------------------

        if last_price is not None:

            if price == last_price and price_time == last_price_time:
                print("DATA        : SAME AS PREVIOUS CHECK")
            else:
                print("DATA        : UPDATED")

        else:
            print("DATA        : FIRST LIVE READING")

        # ----------------------------------------------------
        # Safety: do not continue if XAUS says data is stale
        # ----------------------------------------------------

        if status == "stale":
            print("WARNING     : DATA IS STALE")
        elif status == "unavailable":
            print("WARNING     : DATA UNAVAILABLE")
        elif status == "fresh":
            print("FEED        : LIVE / FRESH")

        last_price = price
        last_price_time = price_time

        print("========================================")

    except Exception as e:

        print("")
        print("ERROR:", e)
        print("========================================")

    # XAUS asks consumers to cache/use at least 30 seconds.
    time.sleep(30)
