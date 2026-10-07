import os
import json
import time
import websocket

API_KEY = os.getenv("SIFTING_API_KEY")

if not API_KEY:
    print("ERROR: SIFTING_API_KEY is missing.")
    raise SystemExit(1)

print("Starting LIVE DATA ENGINE...")
print("API KEY: CONFIGURED")
print("API KEY VALUE: HIDDEN")
print("=" * 60)
print("AI XAUUSD SIGNALS V1")
print("LIVE DATA ENGINE V1")
print("=" * 60)

WS_URL = f"wss://stream.sifting.io/ws/v1?key={API_KEY}"

SYMBOL = "XAUUSD"
PRODUCT = "com"

last_tick_time = None
last_ping_time = 0


def send_ping(ws):
    global last_ping_time

    message = {
        "op": "ping"
    }

    ws.send(json.dumps(message))
    last_ping_time = time.time()

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
    global last_tick_time

    try:
        data = json.loads(message)
    except Exception:
        print("[RAW INVALID]", message)
        return

    print("[RAW]", data)

    frame = data.get("f")

    # -----------------------------
    # AUTH
    # -----------------------------
    if frame == "ack" and data.get("op") == "auth":
        print("[AUTH] PASS")

    # -----------------------------
    # SUBSCRIBE
    # -----------------------------
    elif frame == "ack" and data.get("op") == "subscribe":
        print("[SUBSCRIBE] PASS")
        print("[SUBSCRIBE] XAUUSD LIVE STREAM ACTIVE")

    # -----------------------------
    # PONG
    # -----------------------------
    elif frame == "pong":
        print("[PONG] PASS")

    # -----------------------------
    # TICK
    # -----------------------------
    elif frame == "tick":

        symbol = data.get("s")
        price = data.get("p")
        bid = data.get("b")
        ask = data.get("a")
        timestamp_ms = data.get("t")

        if symbol != SYMBOL:
            return

        now_ms = int(time.time() * 1000)

        if timestamp_ms is not None:
            age_ms = now_ms - int(timestamp_ms)
        else:
            age_ms = -1

        if bid is not None and ask is not None:
            spread = float(ask) - float(bid)
        else:
            spread = None

        print("=" * 60)
        print("[XAUUSD TICK]")
        print(f"PRICE: {price}")
        print(f"BID: {bid}")
        print(f"ASK: {ask}")

        if spread is not None:
            print(f"SPREAD: {spread:.4f}")

        print(f"TIMESTAMP: {timestamp_ms}")
        print(f"AGE: {age_ms} ms")

        # First tick is potentially the cached snapshot.
        if last_tick_time is None:
            print("[DATA] FIRST TICK RECEIVED")
            print("[DATA] SNAPSHOT / INITIAL FRAME")

        elif timestamp_ms is not None and timestamp_ms > last_tick_time:
            print("[DATA] LIVE TICK: PASS")

        else:
            print("[DATA] STALE / REPLAYED TICK")

        last_tick_time = timestamp_ms

        print("=" * 60)

    # -----------------------------
    # ERROR
    # -----------------------------
    elif frame == "error":
        print(
            f"[SIFTING ERROR] "
            f"code={data.get('code')} "
            f"message={data.get('message')}"
        )

    else:
        print("[INFO] Unhandled frame:", data)


def on_error(ws, error):
    print("[WEBSOCKET ERROR]", error)


def on_close(ws, close_status_code, close_msg):
    print("[WEBSOCKET CLOSED]")
    print("CODE:", close_status_code)
    print("MESSAGE:", close_msg)


def run():

    global last_ping_time

    while True:

        print("[CONNECTING]", WS_URL.split("?")[0])

        ws = websocket.WebSocketApp(
            WS_URL,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )

        try:
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
