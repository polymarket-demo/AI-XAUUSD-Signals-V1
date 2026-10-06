import requests
import time
from datetime import datetime, timezone

# ============================================================
# AI XAUUSD SIGNALS V1
# STEP 2 - LIVE PRICE -> M5 CANDLES
# ============================================================

API_URL = "https://xaus.com/api/v1/spot"

prices = []

current_candle_minute = None
current_candle = None

print("========================================")
print("AI XAUUSD SIGNALS V1")
print("LIVE XAU/USD -> M5 CANDLES")
print("========================================")


def get_live_xau_price():

    response = requests.get(
        API_URL,
        params={
            "fresh": int(time.time()),
            "compact": "1"
        },
        timeout=10
    )

    response.raise_for_status()

    data = response.json()

    price = float(data["spot_usd_oz"])
    price_time = data.get("price_as_of", "")
    status = data.get("data_state", {}).get("status", "unknown")

    return price, price_time, status


def start_new_candle(price, timestamp):

    global current_candle
    global current_candle_minute

    minute = timestamp.minute

    candle_start_minute = (minute // 5) * 5

    current_candle_minute = candle_start_minute

    current_candle = {
        "time": timestamp.replace(
            minute=candle_start_minute,
            second=0,
            microsecond=0
        ),
        "open": price,
        "high": price,
        "low": price,
        "close": price
    }


def update_candle(price):

    global current_candle

    current_candle["high"] = max(
        current_candle["high"],
        price
    )

    current_candle["low"] = min(
        current_candle["low"],
        price
    )

    current_candle["close"] = price


while True:

    try:

        price, price_time, status = get_live_xau_price()

        if status != "fresh":

            print("")
            print("WARNING: XAU DATA NOT FRESH")
            print("STATUS:", status)

            time.sleep(30)
            continue

        timestamp = datetime.fromisoformat(
            price_time.replace("Z", "+00:00")
        )

        print("")
        print("----------------------------------------")
        print("LIVE PRICE:", price)
        print("TIME:", price_time)
        print("STATUS:", status)

        # ====================================================
        # FIRST PRICE
        # ====================================================

        if current_candle is None:

            start_new_candle(
                price,
                timestamp
            )

            print("M5 CANDLE: STARTED")

        else:

            minute = timestamp.minute
            candle_minute = (minute // 5) * 5

            # =================================================
            # NEW M5 CANDLE
            # =================================================

            if candle_minute != current_candle_minute:

                print("")
                print("========================================")
                print("M5 CANDLE COMPLETED")
                print("========================================")

                print(
                    "TIME :",
                    current_candle["time"].isoformat()
                )

                print(
                    "OPEN :",
                    current_candle["open"]
                )

                print(
                    "HIGH :",
                    current_candle["high"]
                )

                print(
                    "LOW  :",
                    current_candle["low"]
                )

                print(
                    "CLOSE:",
                    current_candle["close"]
                )

                print("========================================")

                prices.append(current_candle.copy())

                # Keep only last 50 candles
                if len(prices) > 50:
                    prices.pop(0)

                start_new_candle(
                    price,
                    timestamp
                )

                print("NEW M5 CANDLE: STARTED")

            else:

                update_candle(price)

                print(
                    "M5 CURRENT:",
                    current_candle["open"],
                    current_candle["high"],
                    current_candle["low"],
                    current_candle["close"]
                )

        print("----------------------------------------")

    except Exception as e:

        print("")
        print("ERROR:", e)

    time.sleep(30)
