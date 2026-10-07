import requests
import time
from datetime import datetime

# ============================================================
# AI XAUUSD SIGNALS V1
# LIVE -> M5 -> TREND -> FIBONACCI
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

FIB_TOLERANCE = 0.30

HISTORY_CANDLES = 100


print("========================================")
print("AI XAUUSD SIGNALS V1")
print("LIVE XAU/USD -> M5 CANDLES")
print("TREND -> FIBONACCI")
print("PULLBACK -> CONFIRMATION")
print("ENTRY -> SL -> TP")
print("MODE -> ANALYSIS ONLY")
print("========================================")


# ============================================================
# LOAD HISTORICAL M5 DATA
# ============================================================

def load_history():

    global prices

    print("")
    print("========================================")
    print("LOADING M5 HISTORY")
    print("========================================")

    try:

        url = (
            "https://query1.finance.yahoo.com/v8/finance/"
            "chart/GC=F"
        )

        params = {
            "range": "1d",
            "interval": "5m"
        }

        response = requests.get(
            url,
            params=params,
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        result = (
            data["chart"]["result"][0]
        )

        timestamps = result["timestamp"]

        quote = (
            result["indicators"]["quote"][0]
        )

        opens = quote["open"]
        highs = quote["high"]
        lows = quote["low"]
        closes = quote["close"]

        candles = []

        for i in range(
            len(timestamps)
        ):

            if (
                opens[i] is None
                or highs[i] is None
                or lows[i] is None
                or closes[i] is None
            ):

                continue

            candle_time = datetime.fromtimestamp(
                timestamps[i]
            )

            candle = {
                "time": candle_time,
                "open": float(opens[i]),
                "high": float(highs[i]),
                "low": float(lows[i]),
                "close": float(closes[i])
            }

            candles.append(candle)

        if len(candles) < TEST_CANDLES:

            print(
                "ERROR: HISTORY TOO SHORT"
            )

            print(
                "Candles loaded:",
                len(candles)
            )

            return False

        prices = candles[
            -HISTORY_CANDLES:
        ]

        print(
            "HISTORY LOADED:",
            len(prices),
            "M5 CANDLES"
        )

        print(
            "FIRST:",
            prices[0]["time"]
        )

        print(
            "LAST:",
            prices[-1]["time"]
        )

        print("========================================")

        return True

    except Exception as e:

        print("")
        print(
            "HISTORY ERROR:",
            e
        )

        print(
            "Bot will continue with LIVE data."
        )

        print("========================================")

        return False


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
# START NEW M5 CANDLE
# ============================================================

def start_new_candle(price, timestamp):

    global current_candle
    global current_candle_minute

    minute = timestamp.minute

    candle_start_minute = (
        minute // 5
    ) * 5

    current_candle_minute = (
        candle_start_minute
    )

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
# EMA
# ============================================================

def calculate_ema(values, period):

    if len(values) == 0:

        return None

    ema = values[0]

    multiplier = (
        2 / (period + 1)
    )

    for price in values[1:]:

        ema = (
            (price - ema)
            * multiplier
        ) + ema

    return ema


# ============================================================
# TREND ENGINE
# ============================================================

def calculate_trend():

    candle_count = len(prices)

    if candle_count < TEST_CANDLES:

        print(
            "TREND: WAITING"
        )

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

    if (
        ema20 > ema50
        and current_price > ema20
    ):

        trend = "BUY"

    elif (
        ema20 < ema50
        and current_price < ema20
    ):

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
        "PRICE:",
        round(
            current_price,
            4
        )
    )

    print(
        "EMA20:",
        round(
            ema20,
            4
        )
    )

    print(
        "EMA50:",
        round(
            ema50,
            4
        )
    )

    print(
        "TREND:",
        trend
    )

    print(
        "STATUS: ACTIVE"
    )

    print("========================================")

    return trend


# ============================================================
# FIBONACCI
# ============================================================

def calculate_fibonacci(trend):

    if len(prices) < SWING_LOOKBACK:

        return None

    candles = prices[
        -SWING_LOOKBACK:
    ]

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

    movement = (
        swing_high - swing_low
    )

    if trend == "BUY":

        fib382 = (
            swing_high
            - movement * FIB_382
        )

        fib500 = (
            swing_high
            - movement * FIB_500
        )

        fib618 = (
            swing_high
            - movement * FIB_618
        )

    elif trend == "SELL":

        fib382 = (
            swing_low
            + movement * FIB_382
        )

        fib500 = (
            swing_low
            + movement * FIB_500
        )

        fib618 = (
            swing_low
            + movement * FIB_618
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

    candle_high = candle["high"]
    candle_low = candle["low"]
    candle_close = candle["close"]

    levels = [
        ("38.2", fib["fib382"]),
        ("50.0", fib["fib500"]),
        ("61.8", fib["fib618"])
    ]

    closest_name = None
    closest_distance = None
    closest_level = None

    pullback = False
    touched_name = None
    touched_level = None

    for name, level in levels:

        distance = min(
            abs(candle_low - level),
            abs(candle_high - level),
            abs(candle_close - level)
        )

        if (
            closest_distance is None
            or distance < closest_distance
        ):

            closest_distance = distance
            closest_name = name
            closest_level = level

        touched = (
            candle_low
            <= level + FIB_TOLERANCE
            and
            candle_high
            >= level - FIB_TOLERANCE
        )

        if touched:

            pullback = True

            if touched_name is None:

                touched_name = name
                touched_level = level

    print("")
    print("----------------------------------------")
    print("PULLBACK DEBUG")
    print("----------------------------------------")

    print(
        "TREND:",
        trend
    )

    print(
        "CANDLE HIGH:",
        round(
            candle_high,
            4
        )
    )

    print(
        "CANDLE LOW:",
        round(
            candle_low,
            4
        )
    )

    print(
        "CANDLE CLOSE:",
        round(
            candle_close,
            4
        )
    )

    if touched_name is not None:

        print(
            "TOUCHED FIB:",
            touched_name
        )

        print(
            "TOUCHED LEVEL:",
            round(
                touched_level,
                4
            )
        )

    else:

        print(
            "TOUCHED FIB: NONE"
        )

    print(
        "FIB TOUCHED:",
        "YES"
        if pullback
        else "NO"
    )

    print("----------------------------------------")

    return pullback, (
        touched_name
        if touched_name is not None
        else closest_name,

        touched_level
        if touched_level is not None
        else closest_level
    )


# ============================================================
# CONFIRMATION
# ============================================================

def check_confirmation(trend):

    if len(prices) < 2:

        return False

    previous = prices[-2]

    current = prices[-1]

    if trend == "BUY":

        bullish = (
            current["close"]
            > current["open"]
        )

        breakout = (
            current["close"]
            > previous["high"]
        )

        return (
            bullish
            and breakout
        )

    if trend == "SELL":

        bearish = (
            current["close"]
            < current["open"]
        )

        breakout = (
            current["close"]
            < previous["low"]
        )

        return (
            bearish
            and breakout
        )

    return False


# ============================================================
# SIGNAL ENGINE
# ============================================================

def analyze_signal(trend):

    if trend not in [
        "BUY",
        "SELL"
    ]:

        print(
            "SIGNAL: WAIT | TREND NEUTRAL"
        )

        return

    fib = calculate_fibonacci(
        trend
    )

    if fib is None:

        print(
            "SIGNAL: WAIT | NO FIB"
        )

        return

    pullback, fib_info = (
        check_pullback(
            trend,
            fib
        )
    )

    confirmation = (
        check_confirmation(
            trend
        )
    )

    current_price = (
        prices[-1]["close"]
    )

    print("")
    print("========================================")
    print("AI SIGNAL ANALYSIS")
    print("========================================")

    print(
        "TREND:",
        trend
    )

    print(
        "SWING HIGH:",
        round(
            fib["high"],
            4
        )
    )

    print(
        "SWING LOW:",
        round(
            fib["low"],
            4
        )
    )

    print(
        "FIB 38.2:",
        round(
            fib["fib382"],
            4
        )
    )

    print(
        "FIB 50.0:",
        round(
            fib["fib500"],
            4
        )
    )

    print(
        "FIB 61.8:",
        round(
            fib["fib618"],
            4
        )
    )

    print(
        "PULLBACK:",
        "YES"
        if pullback
        else "NO"
    )

    print(
        "CONFIRM:",
        "YES"
        if confirmation
        else "NO"
    )

    # ========================================================
    # WAIT
    # ========================================================

    if (
        not pullback
        or not confirmation
    ):

        print(
            "SIGNAL: WAIT"
        )

        if not pullback:

            print(
                "REASON: NO FIB PULLBACK"
            )

        elif not confirmation:

            print(
                "REASON: NO CONFIRMATION"
            )

        print(
            "MODE: ANALYSIS ONLY"
        )

        print(
            "========================================"
        )

        return

    # ========================================================
    # ENTRY / SL / TP
    # ========================================================

    entry = current_price

    candle = prices[-1]

    if trend == "BUY":

        sl = min(
            candle["low"],
            fib["low"]
        )

        risk = (
            entry - sl
        )

        if risk <= 0:

            print(
                "SIGNAL: INVALID"
            )

            return

        tp = (
            entry
            + risk * RISK_REWARD
        )

        signal = "BUY"

    else:

        sl = max(
            candle["high"],
            fib["high"]
        )

        risk = (
            sl - entry
        )

        if risk <= 0:

            print(
                "SIGNAL: INVALID"
            )

            return

        tp = (
            entry
            - risk * RISK_REWARD
        )

        signal = "SELL"

    # ========================================================
    # CONFIRMED SIGNAL
    # ========================================================

    print("")
    print("******** SIGNAL CONFIRMED ********")

    print(
        "SIGNAL:",
        signal
    )

    print(
        "ENTRY:",
        round(
            entry,
            4
        )
    )

    print(
        "SL:",
        round(
            sl,
            4
        )
    )

    print(
        "TP:",
        round(
            tp,
            4
        )
    )

    print(
        "RISK:",
        round(
            risk,
            4
        )
    )

    print(
        "R/R: 1:",
        RISK_REWARD
    )

    print(
        "MODE: ANALYSIS ONLY"
    )

    print(
        "*************************************"
    )

    print(
        "========================================"
    )


# ============================================================
# INITIAL HISTORY
# ============================================================

load_history()


# ============================================================
# MAIN LOOP
# ============================================================

while True:

    try:

        price, price_time, status = (
            get_live_xau_price()
        )

        if status != "fresh":

            print("")
            print(
                "WARNING: XAU DATA NOT FRESH"
            )

            print(
                "STATUS:",
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
        # START LIVE M5
        # ====================================================

        if current_candle is None:

            start_new_candle(
                price,
                timestamp
            )

            print(
                "LIVE M5 CANDLE: STARTED"
            )

            print(
                "LIVE M5 OPEN:",
                price
            )

        else:

            minute = timestamp.minute

            candle_minute = (
                minute // 5
            ) * 5

            # =================================================
            # NEW M5 CANDLE
            # =================================================

            if (
                candle_minute
                != current_candle_minute
            ):

                print("")
                print("========================================")
                print("LIVE M5 CANDLE COMPLETED")
                print("========================================")

                print(
                    "TIME:",
                    current_candle[
                        "time"
                    ].isoformat()
                )

                print(
                    "OPEN:",
                    current_candle[
                        "open"
                    ]
                )

                print(
                    "HIGH:",
                    current_candle[
                        "high"
                    ]
                )

                print(
                    "LOW:",
                    current_candle[
                        "low"
                    ]
                )

                print(
                    "CLOSE:",
                    current_candle[
                        "close"
                    ]
                )

                print(
                    "========================================"
                )

                # ---------------------------------------------
                # ADD COMPLETED LIVE CANDLE
                # ---------------------------------------------

                prices.append(
                    current_candle.copy()
                )

                if len(prices) > HISTORY_CANDLES:

                    prices.pop(0)

                # ---------------------------------------------
                # ANALYSIS
                # ---------------------------------------------

                trend = calculate_trend()

                if trend is not None:

                    analyze_signal(
                        trend
                    )

                # ---------------------------------------------
                # START NEW CANDLE
                # ---------------------------------------------

                start_new_candle(
                    price,
                    timestamp
                )

                print(
                    "NEW LIVE M5 CANDLE: STARTED"
                )

                print(
                    "NEW LIVE M5 OPEN:",
                    price
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

        print(
            "----------------------------------------"
        )

    except Exception as e:

        print("")
        print(
            "ERROR:",
            e
        )

    time.sleep(30)
