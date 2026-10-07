import os
import json
import time
from datetime import datetime, timezone

import websocket


API_KEY = os.getenv("SIFTING_API_KEY")

if not API_KEY:
    print("ERROR: SIFTING_API_KEY is missing.")
    raise SystemExit(1)


WS_URL = f"wss://stream.sifting.io/ws/v1?key={API_KEY}"

SYMBOL = "XAUUSD"
PRODUCT = "com"

current_bucket = None
current_bar = None

last_tick_timestamp = None
last_ping = 0


print("Starting M5 BUILDER V1...")
print("API KEY: CONFIGURED")
print("API KEY VALUE: HIDDEN")
print("=" * 60)
print("AI XAUUSD SIGNALS V1")
print("LIVE DATA + M5 BUILDER V1")
print("=" * 60)


def get_m5_bucket(timestamp_ms):
    """
    Converts tick timestamp into the beginning of its 5-minute candle.
    """
    dt = datetime.fromtimestamp(
        timestamp_ms / 1000,
        tz=timezone.utc
    )

    minute = (dt.minute // 5) * 5

    return dt.replace(
        minute=minute,
        second=0,
        microsecond=0
    )


def print_bar(bar):
    print("")
    print("=" * 60)
    print("[M5 CLOSED] PASS")
    print(f"TIME:  {bar['time']}")
    print(f"OPEN:  {bar['open']:.2f}")
    print(f"HIGH:  {bar['high']:.2f}")
    print(f"LOW:   {bar['low']:.2f}")
    print(f"CLOSE: {bar['close']:.2f}")
    print(f"TICKS: {bar['ticks']}")
    print("=" * 60)
    print("")


def process_tick(data):
    global current_bucket
    global current_bar
    global last_tick_timestamp

    timestamp_ms = data.get("t")
    price = data.get("p")

    if timestamp_ms is None or price is None:
        return

    timestamp_ms = int(timestamp_ms)
    price = float(price)

    # Reject old/replayed ticks.
    if last_tick_timestamp is not None:
        if timestamp_ms <= last_tick_timestamp:
            print("[DATA] OLD/REPLAYED TICK - IGNORED")
            return

    last_tick_timestamp = timestamp_ms

    bucket = get_m5_bucket(timestamp_ms)

    # First tick received.
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

        print("")
        print("[M5 START] PASS")
        print(f"TIME: {current_bar['time']}")
        print(f"OPEN: {price:.2f}")

        return

    # Same M5 candle.
    if bucket == current_bucket:

        current_bar["high"] = max(
            current_bar["high"],
            price
        )

        current_bar["low"] = min(
            current_bar["low"],
            price
        )

        current_bar["close"] = price
        current_bar["ticks"] += 1

        return

    # New M5 candle detected.
    if bucket > current_bucket:

        # Close previous candle.
        print_bar(current_bar)

        # Start new candle.
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
        print(f"OPEN: {price:.2f}")

        return


def send_ping(ws):
    global last_ping

    ws.send(json.dumps({
        "op": "ping"
    }))

    last_ping = time.time()
    print("[PING] sent")


def on_open(ws):

    print("WEBSOCKET: CONNECTED")
    print(f"SYMBOL: {SYMBOL}")
    print(f"PRODUCT: {PRODUCT}")

    subscribe = {
        "op": "subscribe",
        "product": PRODUCT,
        "symbols": [SYMBOL]
    }

    print("[SUBSCRIBE] XAUUSD")

    ws.send(json.dumps(subscribe))


def on_message(ws, message):

    try:
        data = json.loads(message)
    except Exception:
        print("[RAW INVALID]", message)
        return

    frame = data.get("f")

    # AUTH
    if frame == "ack" and data.get("op") == "auth":

        print("[AUTH] PASS")

        return

    # SUBSCRIBE
    if frame == "ack" and data.get("op") == "subscribe":

        print("[SUBSCRIBE] PASS")
        print("[XAUUSD] STREAM ACTIVE")

        return

    # PONG
    if frame == "pong":

        print("[PONG] PASS")

        return

    # TICK
    if frame == "tick":

        if data.get("s") != SYMBOL:
            return

        price = data.get("p")
        bid = data.get("b")
        ask = data.get("a")
        timestamp_ms = data.get("t")

        if price is None or timestamp_ms is None:
            return

        age_ms = int(time.time() * 1000) - int(timestamp_ms)

        spread = None

        if bid is not None and ask is not None:
            spread = float(ask) - float(bid)

        print(
            f"[TICK] "
            f"PRICE={float(price):.2f} "
            f"BID={float(bid):.2f} "
            f"ASK={float(ask):.2f} "
            f"AGE={age_ms}ms"
        )

        if spread is not None:
            print(f"[SPREAD] {spread:.4f}")

        if age_ms <= 1000:
            print("[DATA] LIVE TICK: PASS")
        else:
            print("[DATA] STALE TICK")

        process_tick(data)

        return

    # ERROR
    if frame == "error":

        print(
            "[SIFTING ERROR]",
            data.get("code"),
            data.get("message")
        )

        return


def on_error(ws, error):

    print("[WEBSOCKET ERROR]", error)


def on_close(ws, close_status_code, close_msg):

    print("[WEBSOCKET CLOSED]")
    print("CODE:", close_status_code)
    print("MESSAGE:", close_msg)


def run():

    global last_ping

    while True:

        print("[CONNECTING]")

        ws = websocket.WebSocketApp(
            WS_URL,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )

        try:

            # websocket-client handles the transport ping.
            # Our application-level SiftingIO ping is also sent below.
            ws.run_forever(
                ping_interval=30,
                ping_timeout=10
            )

        except Exception as e:

            print("[RUN ERROR]", e)

        print("[RECONNECT] Waiting 5 seconds...")
        time.sleep(5)


if __name__ == "__main__":
    run()
