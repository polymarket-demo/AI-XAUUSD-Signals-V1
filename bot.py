import os
import json
import time
from datetime import datetime, timezone

import websocket


# ============================================================
# AI XAUUSD SIGNALS V1.2
# LIVE DATA ENGINE + M5 BUILDER
# ============================================================

API_KEY = os.getenv("SIFTING_API_KEY")

if not API_KEY:
    print("ERROR: SIFTING_API_KEY NOT CONFIGURED")
    raise SystemExit(1)


WS_URL = f"wss://stream.sifting.io/ws/v1?key={API_KEY}"

SYMBOL = "XAUUSD"
PRODUCT = "com"

RECONNECT_WAIT = 15

# ------------------------------------------------------------
# M5 STATE
# ------------------------------------------------------------

current_bucket = None
current_bar = None
last_tick_ms = 0


# ============================================================
# M5 FUNCTIONS
# ============================================================

def get_m5_bucket(dt):
    minute = (dt.minute // 5) * 5

    return dt.replace(
        minute=minute,
        second=0,
        microsecond=0
    )


def print_bar(bar, status="M5 CLOSED"):
    print("----------------------------------------")
    print(f"[{status}] PASS")
    print(f"TIME: {bar['time']}")
    print(f"OPEN: {bar['open']}")
    print(f"HIGH: {bar['high']}")
    print(f"LOW: {bar['low']}")
    print(f"CLOSE: {bar['close']}")
    print(f"TICKS: {bar['ticks']}")
    print("----------------------------------------")


def process_tick(price, tick_ms):

    global current_bucket
    global current_bar
    global last_tick_ms

    # --------------------------------------------------------
    # Reject old/replayed ticks
    # --------------------------------------------------------

    if tick_ms <= last_tick_ms:
        print(
            f"[M5 WARNING] OLD TICK IGNORED "
            f"TICK_MS={tick_ms} LAST={last_tick_ms}"
        )
        return

    last_tick_ms = tick_ms

    # --------------------------------------------------------
    # Convert timestamp
    # --------------------------------------------------------

    tick_dt = datetime.fromtimestamp(
        tick_ms / 1000,
        tz=timezone.utc
    )

    bucket = get_m5_bucket(tick_dt)

    print(
        f"[M5 DEBUG] "
        f"TICK_UTC={tick_dt.strftime('%Y-%m-%d %H:%M:%S')} "
        f"BUCKET={bucket.strftime('%Y-%m-%d %H:%M:%S')} "
        f"CURRENT={current_bucket.strftime('%Y-%m-%d %H:%M:%S') if current_bucket else 'NONE'}"
    )

    # --------------------------------------------------------
    # FIRST BAR
    # --------------------------------------------------------

    if current_bucket is None:

        current_bucket = bucket

        current_bar = {
            "time": bucket.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "open": price,
            "high": price,
            "low": price,
            "close": price,
            "ticks": 1
        }

        print("[M5 START] PASS")
        print(f"TIME: {current_bar['time']}")
        print(f"OPEN: {price}")

        return

    # --------------------------------------------------------
    # SAME M5
    # --------------------------------------------------------

    if bucket == current_bucket:

        if price > current_bar["high"]:
            current_bar["high"] = price

        if price < current_bar["low"]:
            current_bar["low"] = price

        current_bar["close"] = price
        current_bar["ticks"] += 1

        return

    # --------------------------------------------------------
    # NEW M5 BUCKET
    # --------------------------------------------------------

    if bucket > current_bucket:

        print("[M5 CHANGE] NEW 5-MINUTE BUCKET DETECTED")

        # Close previous candle
        print_bar(current_bar, "M5 CLOSED")

        # Start new candle
        current_bucket = bucket

        current_bar = {
            "time": bucket.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "open": price,
            "high": price,
            "low": price,
            "close": price,
            "ticks": 1
        }

        print("[M5 START] PASS")
        print(f"TIME: {current_bar['time']}")
        print(f"OPEN: {price}")

        return

    # --------------------------------------------------------
    # BUCKET MOVED BACKWARDS
    # --------------------------------------------------------

    if bucket < current_bucket:

        print(
            "[M5 WARNING] "
            "BUCKET MOVED BACKWARDS - IGNORED"
        )

        return


# ============================================================
# WEBSOCKET CALLBACKS
# ============================================================

def on_open(ws):

    print("----------------------------------------")
    print("WEBSOCKET: CONNECTED")
    print(f"SYMBOL: {SYMBOL}")
    print(f"PRODUCT: {PRODUCT}")

    subscribe_message = {
        "op": "subscribe",
        "product": PRODUCT,
        "symbols": [SYMBOL]
    }

    ws.send(json.dumps(subscribe_message))

    print("[SUBSCRIBE] XAUUSD")


def on_message(ws, message):

    try:

        data = json.loads(message)

        # ----------------------------------------------------
        # AUTH
        # ----------------------------------------------------

        if data.get("f") == "ack":

            if data.get("op") == "auth":

                print("[AUTH] PASS")

            return

        # ----------------------------------------------------
        # ERROR
        # ----------------------------------------------------

        if data.get("f") == "error":

            print(
                f"[ERROR] "
                f"CODE={data.get('code')} "
                f"MESSAGE={data.get('message')}"
            )

            return

        # ----------------------------------------------------
        # TICK
        # ----------------------------------------------------

        if "p" not in data:

            return

        price = float(data["p"])

        tick_ms = int(data["t"])

        bid = data.get("b")
        ask = data.get("a")

        now_ms = int(time.time() * 1000)

        age = now_ms - tick_ms

        print(
            f"[TICK] "
            f"PRICE={price:.2f} "
            f"BID={float(bid):.2f} "
            f"ASK={float(ask):.2f} "
            f"AGE={age}ms"
            if bid is not None and ask is not None
            else
            f"[TICK] PRICE={price:.2f} AGE={age}ms"
        )

        if bid is not None and ask is not None:

            spread = float(ask) - float(bid)

            print(
                f"[SPREAD] {spread:.4f}"
            )

        print("[DATA] LIVE TICK: PASS")

        # ----------------------------------------------------
        # M5
        # ----------------------------------------------------

        process_tick(
            price,
            tick_ms
        )

    except Exception as e:

        print(
            f"[MESSAGE ERROR] {type(e).__name__}: {e}"
        )


def on_error(ws, error):

    print(
        f"[WEBSOCKET ERROR] {error}"
    )


def on_close(ws, close_status_code, close_msg):

    print("----------------------------------------")
    print("[WEBSOCKET CLOSED]")
    print(f"CODE: {close_status_code}")
    print(f"MESSAGE: {close_msg}")
    print(
        f"[RECONNECT] Waiting {RECONNECT_WAIT} seconds..."
    )
    print("----------------------------------------")


# ============================================================
# MAIN CONNECTION LOOP
# ============================================================

def run():

    print("========================================")
    print("AI XAUUSD SIGNALS V1.2")
    print("LIVE DATA ENGINE + M5 BUILDER")
    print("========================================")
    print("API KEY: CONFIGURED")
    print(f"SYMBOL: {SYMBOL}")
    print(f"PRODUCT: {PRODUCT}")
    print("MODE: LIVE DATA ONLY")
    print("========================================")

    while True:

        ws = None

        try:

            print("[CONNECTING]")

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
                f"[CONNECTION EXCEPTION] "
                f"{type(e).__name__}: {e}"
            )

        finally:

            # Explicitly release this connection
            if ws is not None:

                try:
                    ws.close()
                except Exception:
                    pass

            ws = None

        time.sleep(RECONNECT_WAIT)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    run()
