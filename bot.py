import time
import requests
from datetime import datetime, timezone

# =========================================================
# AI XAUUSD SIGNALS V1
# STEP 4
# LIVE FEED -> M5 -> CLOSED CANDLE -> TREND ENGINE
# ANALYSIS ONLY
# =========================================================

API_URL = "https://xaus.com/api/v1/spot"

POLL_SECONDS = 1.0

MAX_CANDLES = 50
MIN_CANDLES_FOR_TREND = 20

EMA_FAST = 20
EMA_SLOW = 50

RR = 2.0

# =========================================================
# STORAGE
# =========================================================

candles = []

current_candle = None


# =========================================================
# TIME
# =========================================================

def utc_now():
    return datetime.now(timezone.utc)


def parse_timestamp(value):
    if not value:
        return utc_now()

    try:
        value = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(value)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)

    except Exception:
        return utc_now()


# =========================================================
# M5 BUCKET
# =========================================================

def get_m5_bucket(dt):
    minute = (dt.minute // 5) * 5

    return dt.replace(
        minute=minute,
        second=0,
        microsecond=0
    )


# =========================================================
# LIVE DATA
# =========================================================

def get_live_tick():

    try:
        response = requests.get(
            API_URL,
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        # -------------------------------------------------
        # DATA STATE
        # -------------------------------------------------

        data_state = data.get("data_state", {})

        status = data_state.get(
            "status",
            data.get("status", "")
        )

        # -------------------------------------------------
        # PRICE
        # -------------------------------------------------

        price = data.get("spot_usd_oz")

        if price is None:
            price = data.get("price")

        if price is None:
            return None

        price = float(price)

        # -------------------------------------------------
        # PRICE TIME
        # -------------------------------------------------

        price_as_of = data.get("price_as_of")

        tick_time = parse_timestamp(price_as_of)

        # -------------------------------------------------
        # SPREAD
        # -------------------------------------------------

        spread = data.get("spread")

        if spread is not None:
            try:
                spread = float(spread)
            except Exception:
                spread = None

        # -------------------------------------------------
        # AGE
        # -------------------------------------------------

        age_ms = max(
            0,
            int(
                (utc_now() - tick_time).total_seconds()
                * 1000
            )
        )

        return {
            "price": price,
            "timestamp": tick_time,
            "status": status,
            "age_ms": age_ms,
            "spread": spread
        }

    except Exception as e:

        print(
            f"[DATI] ERRORE FEED: {e}",
            flush=True
        )

        return None


# =========================================================
# EMA
# =========================================================

def calculate_ema(values, period):

    if len(values) < period:
        return None

    multiplier = 2 / (period + 1)

    ema = sum(values[:period]) / period

    for price in values[period:]:
        ema = (
            (price - ema) * multiplier
        ) + ema

    return ema


# =========================================================
# TREND ENGINE
# =========================================================

def trend_engine():

    if len(candles) < MIN_CANDLES_FOR_TREND:
        return {
            "trend": "WAITING",
            "ema20": None,
            "ema50": None
        }

    closes = [
        candle["close"]
        for candle in candles
    ]

    ema20 = calculate_ema(
        closes,
        EMA_FAST
    )

    ema50 = calculate_ema(
        closes,
        EMA_SLOW
    )

    if ema20 is None or ema50 is None:

        return {
            "trend": "WAITING",
            "ema20": ema20,
            "ema50": ema50
        }

    price = closes[-1]

    if ema20 > ema50 and price > ema20:

        trend = "BUY"

    elif ema20 < ema50 and price < ema20:

        trend = "SELL"

    else:

        trend = "NEUTRAL"

    return {
        "trend": trend,
        "ema20": ema20,
        "ema50": ema50
    }


# =========================================================
# CANDLE ANALYSIS
# =========================================================

def analyze_candle(candle):

    open_price = candle["open"]
    high = candle["high"]
    low = candle["low"]
    close = candle["close"]

    candle_range = high - low
    body = abs(close - open_price)

    if candle_range <= 0:

        return {
            "direction": "DOJI",
            "body": 0.0,
            "range": 0.0,
            "body_ratio": 0.0
        }

    body_ratio = body / candle_range

    if close > open_price:
        direction = "BULLISH"

    elif close < open_price:
        direction = "BEARISH"

    else:
        direction = "DOJI"

    return {
        "direction": direction,
        "body": body,
        "range": candle_range,
        "body_ratio": body_ratio
    }


# =========================================================
# PRINT CLOSED CANDLE
# =========================================================

def print_closed_candle(candle):

    analysis = analyze_candle(candle)

    print(
        "----------------------------------------",
        flush=True
    )

    print(
        "M5 CANDLE CHIUSA",
        flush=True
    )

    print(
        f"TIME: {candle['bucket'].strftime('%Y-%m-%d %H:%M')}",
        flush=True
    )

    print(
        f"O: {candle['open']:.3f}",
        flush=True
    )

    print(
        f"H: {candle['high']:.3f}",
        flush=True
    )

    print(
        f"L: {candle['low']:.3f}",
        flush=True
    )

    print(
        f"C: {candle['close']:.3f}",
        flush=True
    )

    print(
        f"DIRECTION: {analysis['direction']}",
        flush=True
    )

    print(
        f"BODY: {analysis['body']:.3f}",
        flush=True
    )

    print(
        f"RANGE: {analysis['range']:.3f}",
        flush=True
    )

    print(
        f"BODY/RANGE: {analysis['body_ratio']:.2%}",
        flush=True
    )

    # -----------------------------------------------------
    # TREND
    # -----------------------------------------------------

    trend = trend_engine()

    if trend["trend"] == "WAITING":

        print(
            "TREND ENGINE: WAITING",
            flush=True
        )

    else:

        print(
            f"TREND ENGINE: {trend['trend']}",
            flush=True
        )

        if trend["ema20"] is not None:

            print(
                f"EMA20: {trend['ema20']:.3f}",
                flush=True
            )

        if trend["ema50"] is not None:

            print(
                f"EMA50: {trend['ema50']:.3f}",
                flush=True
            )

    print(
        "----------------------------------------",
        flush=True
    )


# =========================================================
# CLOSE M5 CANDLE
# =========================================================

def close_current_candle():

    global current_candle

    if current_candle is None:
        return

    closed = current_candle.copy()

    candles.append(closed)

    if len(candles) > MAX_CANDLES:
        candles.pop(0)

    print_closed_candle(closed)

    current_candle = None


# =========================================================
# PROCESS TICK
# =========================================================

def process_tick(tick):

    global current_candle

    price = tick["price"]
    timestamp = tick["timestamp"]

    bucket = get_m5_bucket(timestamp)

    # -----------------------------------------------------
    # FIRST CANDLE
    # -----------------------------------------------------

    if current_candle is None:

        current_candle = {
            "bucket": bucket,
            "open": price,
            "high": price,
            "low": price,
            "close": price
        }

        print(
            f"[M5] NUOVA CANDLE "
            f"{bucket.strftime('%Y-%m-%d %H:%M')} "
            f"OPEN={price:.3f}",
            flush=True
        )

        return

    # -----------------------------------------------------
    # SAME M5 BUCKET
    # -----------------------------------------------------

    if bucket == current_candle["bucket"]:

        current_candle["high"] = max(
            current_candle["high"],
            price
        )

        current_candle["low"] = min(
            current_candle["low"],
            price
        )

        current_candle["close"] = price

        return

    # -----------------------------------------------------
    # NEW M5 BUCKET
    # -----------------------------------------------------

    if bucket > current_candle["bucket"]:

        close_current_candle()

        current_candle = {
            "bucket": bucket,
            "open": price,
            "high": price,
            "low": price,
            "close": price
        }

        print(
            f"[M5] NUOVA CANDLE "
            f"{bucket.strftime('%Y-%m-%d %H:%M')} "
            f"OPEN={price:.3f}",
            flush=True
        )


# =========================================================
# MAIN
# =========================================================

print(
    "========================================",
    flush=True
)

print(
    "AI XAUUSD SIGNALS V1",
    flush=True
)

print(
    "========================================",
    flush=True
)

print(
    "LIVE XAU/USD",
    flush=True
)

print(
    "TIMEFRAME: M5",
    flush=True
)

print(
    "MODE: ANALYSIS ONLY",
    flush=True
)

print(
    "STEP: 4 - CLOSED M5 CANDLE ENGINE",
    flush=True
)

print(
    "========================================",
    flush=True
)


while True:

    tick = get_live_tick()

    if tick is None:

        time.sleep(POLL_SECONDS)

        continue

    # -----------------------------------------------------
    # VALIDATION
    # -----------------------------------------------------

    if tick["status"] != "fresh":

        print(
            f"[DATI] TICK RIFIUTATO "
            f"STATUS={tick['status']}",
            flush=True
        )

        time.sleep(POLL_SECONDS)

        continue

    # -----------------------------------------------------
    # LIVE DATA PASS
    # -----------------------------------------------------

    spread_text = (
        f"{tick['spread']:.3f}"
        if tick["spread"] is not None
        else "N/A"
    )

    print(
        f"[DATI] TICK LIVE: PASS "
        f"PREZZO={tick['price']:.3f} "
        f"ETÀ={tick['age_ms']}ms "
        f"SPREAD={spread_text}",
        flush=True
    )

    # -----------------------------------------------------
    # ACCEPT TICK
    # -----------------------------------------------------

    bucket = get_m5_bucket(
        tick["timestamp"]
    )

    print(
        f"[TICK ACCETTATO] "
        f"UTC={tick['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} "
        f"PREZZO={tick['price']:.3f} "
        f"BUCKET={bucket.strftime('%Y-%m-%d %H:%M')}",
        flush=True
    )

    process_tick(tick)

    time.sleep(POLL_SECONDS)
