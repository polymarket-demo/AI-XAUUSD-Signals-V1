import os
import json
import time
from datetime import datetime, timezone

import websocket


# ============================================================
# AI XAUUSD SIGNALS V1
# LIVE DATA + M5 CANDLE ENGINE
# ============================================================

API_KEY = os.getenv("SIFTING_API_KEY")

WS_URL = f"wss://stream.sifting.io/ws/v1?key={API_KEY}"

PRODUCT = "com"
SYMBOL = "XAUUSD"

RECONNECT_WAIT = 15

# ============================================================
# M5 STATE
# ============================================================

current_bucket = None

m5_open = None
m5_high = None
m5_low = None
m5_close = None

last_tick_ms = 0

closed_candles = []

MAX_CANDLES = 50


# ============================================================
# UTILS
# ============================================================

def get_m5_bucket(tick_ms):
    dt = datetime.fromtimestamp(
        tick_ms / 1000,
        timezone.utc
    )

    minute = (dt.minute // 5) * 5

    return dt.replace(
        minute=minute,
        second=0,
        microsecond=0
    )


def add_closed_candle(bucket):
    global m5_open
    global m5_high
    global m5_low
    global m5_close

    if (
        m5_open is None
        or m5_high is None
        or m5_low is None
        or m5_close is None
    ):
        return

    candle = {
        "time": bucket.isoformat(),
        "open": m5_open,
        "high": m5_high,
        "low": m5_low,
        "close": m5_close
    }

    closed_candles.append(candle)

    if len(closed_candles) > MAX_CANDLES:
        closed_candles.pop(0)

    analyze_closed_candle(candle)


# ============================================================
# M5 CANDLE ANALYSIS
# ============================================================

def analyze_closed_candle(candle):

    o = candle["open"]
    h = candle["high"]
    l = candle["low"]
    c = candle["close"]

    candle_range = h - l
    body = abs(c - o)

    if candle_range > 0:
        body_ratio = body / candle_range
    else:
        body_ratio = 0

    if c > o:
        direction = "BULLISH"
    elif c < o:
        direction = "BEARISH"
    else:
        direction = "DOJI"

    print("----------------------------------------")
    print("M5 CANDLE CLOSED")
    print("----------------------------------------")
    print(f"TIME: {candle['time']}")
    print(f"O: {o:.3f}")
    print(f"H: {h:.3f}")
    print(f"L: {l:.3f}")
    print(f"C: {c:.3f}")
    print(f"RANGE: {candle_range:.3f}")
    print(f"BODY: {body:.3f}")
    print(f"BODY/RANGE: {body_ratio:.2%}")
    print(f"DIRECTION: {direction}")
    print("----------------------------------------")


# ============================================================
# START NEW M5 CANDLE
# ============================================================

def start_new_candle(bucket, price):

    global current_bucket
    global m5_open
    global m5_high
    global m5_low
    global m5_close

    current_bucket = bucket

    m5_open = price
    m5_high = price
    m5_low = price
    m5_close = price

    print(
        f"[M5 START] "
        f"BUCKET={bucket.strftime('%Y-%m-%d %H:%M:%S')} "
        f"O={price:.3f}"
    )


# ============================================================
# PROCESS TICK
# ============================================================

def process_tick(message):

    global last_tick_ms
    global current_bucket
    global m5_open
    global m5_high
    global m5_low
    global m5_close

    try:
        price = float(message["p"])
        tick_ms = int(message["t"])
    except (KeyError, TypeError, ValueError):
        return

    # --------------------------------------------------------
    # Reject old / duplicate ticks
    # --------------------------------------------------------

    if tick_ms <= last_tick_ms:
        return

    last_tick_ms = tick_ms

    # --------------------------------------------------------
    # Timestamp / age
    # --------------------------------------------------------

    now_ms = int(time.time() * 1000)

    age_ms = now_ms - tick_ms

    # --------------------------------------------------------
    # Bid / Ask / Spread
    # --------------------------------------------------------

    bid = message.get("b")
    ask = message.get("a")

    spread = None

    try:
        if bid is not None and ask is not None:
            bid = float(bid)
            ask = float(ask)
            spread = ask - bid
    except (TypeError, ValueError):
        spread = None

    # --------------------------------------------------------
    # M5 bucket
    # --------------------------------------------------------

    bucket = get_m5_bucket(tick_ms)

    # --------------------------------------------------------
    # Live tick
    # --------------------------------------------------------

    if spread is not None:
        print(
            f"[DATI] TICK LIVE: PASS "
            f"PREZZO={price:.3f} "
            f"ETÀ={age_ms}ms "
            f"SPREAD={spread:.3f}"
        )
    else:
        print(
            f"[DATI] TICK LIVE: PASS "
            f"PREZZO={price:.3f} "
            f"ETÀ={age_ms}ms"
        )

    # --------------------------------------------------------
    # First M5 candle
    # --------------------------------------------------------

    if current_bucket is None:

        start_new_candle(bucket, price)

        return

    # --------------------------------------------------------
    # Same M5 candle
    # --------------------------------------------------------

    if bucket == current_bucket:

        if price > m5_high:
            m5_high = price

        if price < m5_low:
            m5_low = price

        m5_close = price

        print(
            f"[TICK ACCETTATO] "
            f"BUCKET={bucket.strftime('%Y-%m-%d %H:%M:%S')} "
            f"PRICE={price:.3f}"
        )

        return

    # --------------------------------------------------------
    # New M5 candle
    # --------------------------------------------------------

    if bucket > current_bucket:

        previous_bucket = current_bucket

        # Close previous candle
        add_closed_candle(previous_bucket)

        # Start new candle
        start_new_candle(bucket, price)


# ============================================================
# WEBSOCKET CALLBACKS
# ============================================================

def on_open(ws):

    print("----------------------------------------")
    print("WEBSOCKET CONNECTED")
    print("----------------------------------------")

    subscribe_message = {
        "op": "subscribe",
        "product": PRODUCT,
        "symbols": [SYMBOL]
    }

    ws.send(json.dumps(subscribe_message))

    print("[SUBSCRIBE] XAUUSD SENT")


def on_message(ws, raw_message):

    try:
        message = json.loads(raw_message)
    except json.JSONDecodeError:
        return

    # --------------------------------------------------------
    # AUTH
    # --------------------------------------------------------

    if message.get("f") == "ack":
        print("[AUTH PASS] ACK")
        return

    if message.get("op") == "auth":
        print("[AUTH PASS]")
        return

    # --------------------------------------------------------
    # ERROR
    # --------------------------------------------------------

    if message.get("f") == "error":

        print(
            f"[WEBSOCKET ERROR] "
            f"{message}"
        )

        return

    # --------------------------------------------------------
    # Tick
    # --------------------------------------------------------

    if "p" in message and "t" in message:

        process_tick(message)


def on_error(ws, error):

    print(
        f"[WEBSOCKET ERROR] {error}"
    )


def on_close(ws, close_status_code, close_msg):

    print("----------------------------------------")
    print("WEBSOCKET CLOSED")
    print(
        f"CODE={close_status_code} "
        f"MSG={close_msg}"
    )
    print("----------------------------------------")


# ============================================================
# MAIN LOOP
# ============================================================

def run():

    if not API_KEY:

        print(
            "ERRORE: SIFTING_API_KEY non configurata."
        )

        return

    print("========================================")
    print("AI XAUUSD SIGNALS V1")
    print("========================================")
    print("LIVE XAU/USD")
    print("M5 CANDLE ENGINE")
    print("MODE: ANALYSIS ONLY")
    print("========================================")

    while True:

        try:

            ws = websocket.WebSocketApp(
                WS_URL,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )

            ws.run_forever(
                ping_interval=30,
                ping_timeout=10
            )

        except Exception as e:

            print(
                f"[CONNECTION EXCEPTION] {e}"
            )

        print(
            f"[RECONNECT] "
            f"attendo {RECONNECT_WAIT}s..."
        )

        time.sleep(RECONNECT_WAIT)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    run()
