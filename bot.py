import requests
import time
from datetime import datetime, timezone

# ============================================================
# AI XAUUSD SIGNALS V1
# STEP 4 - LIVE -> M5 -> TREND -> IMPULSE -> FIBONACCI
# PULLBACK -> CONFIRMATION -> ENTRY / SL / TP
# ANALYSIS ONLY - NO ORDER EXECUTION
# ============================================================

API_URL = "https://xaus.com/api/v1/spot"

prices = []

current_candle_minute = None
current_candle = None

# ============================================================
# SETTINGS
# ============================================================

TEST_CANDLES = 10
SWING_LOOKBACK = 10

RISK_REWARD = 2.0

FIB_382 = 0.382
FIB_500 = 0.500
FIB_618 = 0.618

# Tolleranza per riconoscere il prezzo vicino a un livello Fibonacci
FIB_TOLERANCE = 0.30

print("========================================")
print("AI XAUUSD SIGNALS V1")
print("LIVE XAU/USD -> M5 CANDLES")
print("TREND -> IMPULSE -> FIBONACCI")
print("PULLBACK -> CONFIRMATION")
print("ENTRY -> SL -> TP")
print("MODE -> ANALYSIS ONLY")
print("========================================")


# ============================================================
# LIVE XAU PRICE
# ============================================================

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
# START NEW M5 CANDLE
# ============================================================

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


# ============================================================
# UPDATE CURRENT M5 CANDLE
# ============================================================

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


# ============================================================
# EMA CALCULATION
# ============================================================

def calculate_ema(values, period):

    if len(values) == 0:
        return None

    if len(values) < period:

        ema = values[0]

        multiplier = 2 / (period + 1)

        for price in values[1:]:

            ema = (
                (price - ema) * multiplier
            ) + ema

        return ema

    ema = sum(
        values[:period]
    ) / period

    multiplier = 2 / (period + 1)

    for price in values[period:]:

        ema = (
            (price - ema) * multiplier
        ) + ema

    return ema


# ============================================================
# TREND ENGINE
# ============================================================

def calculate_trend():

    candle_count = len(prices)

    if candle_count < TEST_CANDLES:

        return None

    closes = [
        candle["close"]
        for candle in prices
    ]

    ema20 = calculate_ema(
        closes,
        20
    )

    ema50 = calculate_ema(
        closes,
        50
    )

    current_price = closes[-1]

    if ema20 > ema50 and current_price > ema20:

        trend = "BUY"

    elif ema20 < ema50 and current_price < ema20:

        trend = "SELL"

    else:

        trend = "NEUTRAL"

    print("")
    print("========================================")
    print("TREND ENGINE")
    print("========================================")

    print(
        "M5 CANDLES:",
        candle_count
    )

    print(
        "PRICE :",
        round(current_price, 4)
    )

    print(
        "EMA20 :",
        round(ema20, 4)
    )

    print(
        "EMA50 :",
        round(ema50, 4)
    )

    print(
        "TREND :",
        trend
    )

    print(
        "STATUS: PROVISIONAL"
    )

    print("========================================")

    return trend


# ============================================================
# FIBONACCI / SWING ENGINE
# ============================================================

def calculate_fibonacci(trend):

    if len(prices) < SWING_LOOKBACK:
        return None

    candles = prices[-SWING_LOOKBACK:]

    swing_high = max(
        candle["high"]
        for candle in candles
    )

    swing_low = min(
        candle["low"]
        for candle in candles
    )

    if swing_high <= swing_low:
        return None

    movement = swing_high - swing_low

    # BUY:
    # pullback da HIGH verso LOW
    #
    # SELL:
    # pullback da LOW verso HIGH

    if trend == "BUY":

        fib382 = swing_high - (
            movement * FIB_382
        )

        fib500 = swing_high - (
            movement * FIB_500
        )

        fib618 = swing_high - (
            movement * FIB_618
        )

    elif trend == "SELL":

        fib382 = swing_low + (
            movement * FIB_382
        )

        fib500 = swing_low + (
            movement * FIB_500
        )

        fib618 = swing_low + (
            movement * FIB_618
        )

    else:

        return None

    return {
        "high": swing_high,
        "low": swing_low,
        "fib382": fib382,
        "fib500": fib500,
        "fib618": fib618
    }


# ============================================================
# PULLBACK ENGINE
# ============================================================

def check_pullback(trend, fib):

    if fib is None:
        return False, None

    candle = prices[-1]

    price = candle["close"]

    levels = [
        ("38.2", fib["fib382"]),
        ("50.0", fib["fib500"]),
        ("61.8", fib["fib618"])
    ]

    closest_name = None
    closest_distance = None
    closest_level = None

    for name, level in levels:

        distance = abs(
            price - level
        )

        if closest_distance is None or distance < closest_distance:

            closest_distance = distance
            closest_name = name
            closest_level = level

    pullback = (
        closest_distance <= FIB_TOLERANCE
    )

    return pullback, (
        closest_name,
        closest_level
    )


# ============================================================
# CONFIRMATION ENGINE
# ============================================================

def check_confirmation(trend):

    if len(prices) < 2:
        return False

    previous = prices[-2]
    current = prices[-1]

    # BUY confirmation:
    # candela rialzista e close sopra il massimo
    # della candela precedente

    if trend == "BUY":

        bullish = (
            current["close"] > current["open"]
        )

        breakout = (
            current["close"] > previous["high"]
        )

        return bullish and breakout

    # SELL confirmation:
    # candela ribassista e close sotto il minimo
    # della candela precedente

    if trend == "SELL":

        bearish = (
            current["close"] < current["open"]
        )

        breakout = (
            current["close"] < previous["low"]
        )

        return bearish and breakout

    return False


# ============================================================
# SIGNAL ENGINE
# ============================================================

def analyze_signal(trend):

    if trend not in ["BUY", "SELL"]:
        return

    fib = calculate_fibonacci(
        trend
    )

    if fib is None:
        return

    pullback, fib_info = check_pullback(
        trend,
        fib
    )

    confirmation = check_confirmation(
        trend
    )

    current_price = prices[-1]["close"]

    print("")
    print("========================================")
    print("AI SIGNAL ANALYSIS")
    print("========================================")

    print(
        "TREND      :",
        trend
    )

    print(
        "SWING HIGH :",
        round(fib["high"], 4)
    )

    print(
        "SWING LOW  :",
        round(fib["low"], 4)
    )

    print(
        "FIB 38.2   :",
        round(fib["fib382"], 4)
    )

    print(
        "FIB 50.0   :",
        round(fib["fib500"], 4)
    )

    print(
        "FIB 61.8   :",
        round(fib["fib618"], 4)
    )

    if fib_info:

        print(
            "NEAREST FIB:",
            fib_info[0],
            "LEVEL",
            round(fib_info[1], 4)
        )

    print(
        "PULLBACK   :",
        "YES" if pullback else "NO"
    )

    print(
        "CONFIRM    :",
        "YES" if confirmation else "NO"
    )

    # ========================================================
    # NO SIGNAL
    # ========================================================

    if not pullback or not confirmation:

        print(
            "SIGNAL     : WAIT"
        )

        print(
            "MODE       : ANALYSIS ONLY"
        )

        print("========================================")

        return

    # ========================================================
    # VALID SIGNAL
    # ========================================================

    entry = current_price

    candle = prices[-1]

    if trend == "BUY":

        sl = min(
            candle["low"],
            fib["low"]
        )

        risk = entry - sl

        if risk <= 0:
            print("SIGNAL     : INVALID")
            print("========================================")
            return

        tp = entry + (
            risk * RISK_REWARD
        )

        signal = "BUY"

    else:

        sl = max(
            candle["high"],
            fib["high"]
        )

        risk = sl - entry

        if risk <= 0:
            print("SIGNAL     : INVALID")
            print("========================================")
            return

        tp = entry - (
            risk * RISK_REWARD
        )

        signal = "SELL"

    print("")
    print("******** SIGNAL CONFIRMED ********")

    print(
        "SIGNAL     :",
        signal
    )

    print(
        "ENTRY      :",
        round(entry, 4)
    )

    print(
        "SL         :",
        round(sl, 4)
    )

    print(
        "TP         :",
        round(tp, 4)
    )

    print(
        "RISK       :",
        round(risk, 4)
    )

    print(
        "R/R        : 1:",
        RISK_REWARD
    )

    print(
        "MODE       : ANALYSIS ONLY"
    )

    print("*************************************")
    print("========================================")


# ============================================================
# MAIN LOOP
# ============================================================

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
            price_time.replace(
                "Z",
                "+00:00"
            )
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

            print(
                "M5 CANDLE: STARTED"
            )

        else:

            minute = timestamp.minute

            candle_minute = (
                minute // 5
            ) * 5

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

                # Save completed candle

                prices.append(
                    current_candle.copy()
                )

                # Keep last 50 candles

                if len(prices) > 50:

                    prices.pop(0)

                # Trend

                trend = calculate_trend()

                # Full AI analysis

                if trend is not None:

                    analyze_signal(
                        trend
                    )

                # Start next candle

                start_new_candle(
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

        print("")
        print("ERROR:", e)

    time.sleep(30)
