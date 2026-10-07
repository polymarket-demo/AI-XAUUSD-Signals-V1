import requests
import time
from datetime import datetime

# ============================================================
# AI XAUUSD SIGNALS V1
# LIVE XAUUSD -> M5 -> MOMENTUM -> SIGNAL
# BUY / SELL -> ENTRY / SL / TP
# ANALYSIS ONLY - NO ORDER EXECUTION
# ============================================================

API_URL = "https://xaus.com/api/v1/spot"

# ============================================================
# SETTINGS
# ============================================================

CANDLE_SECONDS = 300

MIN_MOVE = 0.80

STOP_DISTANCE = 1.20

RISK_REWARD = 2.0

SIGNAL_COOLDOWN = 300

# ============================================================
# DATA
# ============================================================

prices = []

current_candle = None
current_candle_start = None

last_signal_time = None


print("========================================")
print("AI XAUUSD SIGNALS V1")
print("========================================")
print("LIVE XAU/USD")
print("M5 MOMENTUM")
print("BUY / SELL")
print("ENTRY / SL / TP")
print("MODE: ANALYSIS ONLY")
print("========================================")


# ============================================================
# LIVE PRICE
# ============================================================

def get_live_price():

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

    price = float(
        data["spot_usd_oz"]
    )

    price_time = data.get(
        "price_as_of",
        ""
    )

    status = data.get(
        "data_state",
        {}
    ).get(
        "status",
        "unknown"
    )

    return price, price_time, status


# ============================================================
# SIGNAL
# ============================================================

def generate_signal():

    global last_signal_time

    if len(prices) < 2:
        return

    previous = prices[-2]
    current = prices[-1]

    move = (
        current["close"]
        - previous["close"]
    )

    print("")
    print("========================================")
    print("SIGNAL ENGINE")
    print("========================================")

    print(
        "PREVIOUS CLOSE:",
        round(previous["close"], 4)
    )

    print(
        "CURRENT CLOSE :",
        round(current["close"], 4)
    )

    print(
        "MOVE          :",
        round(move, 4)
    )

    # ========================================================
    # COOLDOWN
    # ========================================================

    now = time.time()

    if (
        last_signal_time is not None
        and
        now - last_signal_time
        < SIGNAL_COOLDOWN
    ):

        remaining = int(
            SIGNAL_COOLDOWN
            - (
                now
                - last_signal_time
            )
        )

        print(
            "SIGNAL: COOLDOWN",
            remaining,
            "sec"
        )

        print("========================================")

        return

    # ========================================================
    # BUY
    # ========================================================

    if move >= MIN_MOVE:

        signal = "BUY"

        entry = current["close"]

        sl = (
            entry
            - STOP_DISTANCE
        )

        risk = (
            entry
            - sl
        )

        tp = (
            entry
            + risk * RISK_REWARD
        )

    # ========================================================
    # SELL
    # ========================================================

    elif move <= -MIN_MOVE:

        signal = "SELL"

        entry = current["close"]

        sl = (
            entry
            + STOP_DISTANCE
        )

        risk = (
            sl
            - entry
        )

        tp = (
            entry
            - risk * RISK_REWARD
        )

    # ========================================================
    # NO SIGNAL
    # ========================================================

    else:

        print(
            "SIGNAL: WAIT"
        )

        print(
            "REASON: MOVE BELOW THRESHOLD"
        )

        print("========================================")

        return

    # ========================================================
    # CONFIRMED SIGNAL
    # ========================================================

    last_signal_time = now

    print("")
    print("******** SIGNAL ********")

    print(
        "SIGNAL:",
        signal
    )

    print(
        "ENTRY:",
        round(entry, 4)
    )

    print(
        "SL:",
        round(sl, 4)
    )

    print(
        "TP:",
        round(tp, 4)
    )

    print(
        "RISK:",
        round(risk, 4)
    )

    print(
        "R/R: 1:",
        RISK_REWARD
    )

    print(
        "MOVE:",
        round(move, 4)
    )

    print(
        "MODE: ANALYSIS ONLY"
    )

    print("************************")
    print("========================================")


# ============================================================
# START CANDLE
# ============================================================

def start_candle(price, timestamp):

    global current_candle
    global current_candle_start

    minute = (
        timestamp.minute
    )

    candle_minute = (
        minute // 5
    ) * 5

    current_candle_start = (
        timestamp.replace(
            minute=candle_minute,
            second=0,
            microsecond=0
        )
    )

    current_candle = {
        "time": current_candle_start,
        "open": price,
        "high": price,
        "low": price,
        "close": price
    }


# ============================================================
# UPDATE CANDLE
# ============================================================

def update_candle(price):

    current_candle["high"] = max(
        current_candle["high"],
        price
    )

    current_candle["low"] = min(
        current_candle["low"],
        price
    )

    current_candle["close"] = price


# ============================================================
# MAIN
# ============================================================

while True:

    try:

        price, price_time, status = (
            get_live_price()
        )

        if status != "fresh":

            print(
                "WARNING: DATA NOT FRESH",
                status
            )

            time.sleep(30)

            continue

        timestamp = datetime.fromisoformat(
            price_time.replace(
                "Z",
                "+00:00"
            )
        )

        print("")
        print("----------------------------------------")

        print(
            "LIVE PRICE:",
            price
        )

        print(
            "TIME:",
            price_time
        )

        print(
            "STATUS:",
            status
        )

        # ====================================================
        # FIRST CANDLE
        # ====================================================

        if current_candle is None:

            start_candle(
                price,
                timestamp
            )

            print(
                "M5 CANDLE: STARTED"
            )

        else:

            minute = timestamp.minute

            candle_minute = (
                minute // 5
            ) * 5

            # =================================================
            # NEW CANDLE
            # =================================================

            if (
                candle_minute
                != current_candle_start.minute
            ):

                print("")
                print("========================================")
                print("M5 COMPLETED")
                print("========================================")

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

                prices.append(
                    current_candle.copy()
                )

                if len(prices) > 20:

                    prices.pop(0)

                generate_signal()

                start_candle(
                    price,
                    timestamp
                )

                print(
                    "NEW M5 CANDLE: STARTED"
                )

            else:

                update_candle(
                    price
                )

                print(
                    "M5 CURRENT:",
                    current_candle["open"],
                    current_candle["high"],
                    current_candle["low"],
                    current_candle["close"]
                )

        print("----------------------------------------")

    except Exception as e:

        print(
            "ERROR:",
            e
        )

    time.sleep(30)
