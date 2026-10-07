import os
import json
import time
import threading
from datetime import datetime, timezone

import websocket


API_KEY = os.getenv("SIFTING_API_KEY")

WS_URL = f"wss://stream.sifting.io/ws/v1?key={API_KEY}"

SYMBOL = "XAUUSD"
PRODUCT = "com"

PING_INTERVAL = 30
STALE_SECONDS = 10


last_tick_time = None
last_price = None
last_bid = None
last_ask = None

m5 = {
    "start": None,
    "open": None,
    "high": None,
    "low": None,
    "close": None,
}


def utc_now():
    return datetime.now(timezone.utc)


def print_status():
    if last_tick_time is None:
        return

    age = time.time() - last_tick_time

    status = "FRESH" if age <= STALE_SECONDS else "STALE"

    print(
        f"[DATA] "
        f"PRICE={last_price} "
        f"BID={last_bid} "
        f"ASK={last_ask} "
        f"AGE={age:.2f}s "
        f"STATUS={status}"
    )


def update_m5(price, tick_time):
    global m5

    dt = datetime.fromtimestamp(tick_time, timezone.utc)

    minute = (dt.minute // 5) * 5

    candle_start = dt.replace(
        minute=minute,
        second=0,
        microsecond=0
    )

    if m5["start"] != candle_start:

        if m5["start"] is not None:
            print(
                f"[M5 CLOSED] "
                f"{m5['start'].isoformat()} "
                f"O={m5['open']} "
                f"H={m5['high']} "
                f"L={m5['low']} "
                f"C={m5['close']}"
            )

        m5 = {
            "start": candle_start,
            "open": price,
            "high": price,
            "low": price,
            "close": price,
        }

        print(
            f"[M5 NEW] {candle_start.isoformat()} "
            f"O={price}"
        )

    else:
        m5["high"] = max(m5["high"], price)
        m5["low"] = min(m5["low"], price)
        m5["close"] = price


def on_open(ws):

    print("=" * 60)
    print("AI XAUUSD SIGNALS V1")
    print("LIVE DATA ENGINE V1")
    print("=" * 60)
    print("WEBSOCKET: CONNECTED")
    print("SYMBOL: XAUUSD")
    print("PRODUCT: COM")

    subscribe = {
        "action": "subscribe",
        "product": PRODUCT,
        "symbols": [SYMBOL]
    }

    ws.send(json.dumps(subscribe))

    print("[SUBSCRIBE] XAUUSD")


def on_message(ws, message):

    global last_tick_time
    global last_price
    global last_bid
    global last_ask

    try:
        data = json.loads(message)
    except Exception:
        print("[ERROR] Invalid JSON:", message)
        return

    print("[RAW]", data)

    # ACK / system messages
    if data.get("type") in ("ack", "subscribed"):
        print("[SYSTEM]", data)
        return

    # Tick
    if data.get("type") == "tick":

        try:
            price = float(data["p"])
            bid = float(data["b"])
            ask = float(data["a"])
            tick_timestamp = float(data["t"])

        except Exception as e:
            print("[ERROR] Invalid tick:", e)
            return

        last_price = price
        last_bid = bid
        last_ask = ask

        last_tick_time = time.time()

        spread = ask - bid

        receive_time = utc_now().isoformat()

        print(
            f"[LIVE TICK] "
            f"PRICE={price:.5f} "
            f"BID={bid:.5f} "
            f"ASK={ask:.5f} "
            f"SPREAD={spread:.5f} "
            f"PROVIDER_TS={tick_timestamp} "
            f"RECEIVED={receive_time}"
        )

        update_m5(price, tick_timestamp)


def on_error(ws, error):
    print("[WEBSOCKET ERROR]", error)


def on_close(ws, close_status_code, close_msg):
    print(
        "[WEBSOCKET CLOSED]",
        close_status_code,
        close_msg
    )


def ping_loop(ws):

    while True:

        try:
            time.sleep(PING_INTERVAL)

            if ws.sock and ws.sock.connected:
                ws.send(
                    json.dumps(
                        {
                            "action": "ping"
                        }
                    )
                )

                print("[PING] sent")

        except Exception as e:
            print("[PING ERROR]", e)
            break


def run():

    if not API_KEY:
        print("ERROR: SIFTING_API_KEY is missing.")
        print("Add it in Railway Variables.")
        return

    print("Starting LIVE DATA ENGINE...")
    print("API KEY: CONFIGURED")
    print("API KEY VALUE: HIDDEN")

    while True:

        try:

            ws = websocket.WebSocketApp(
                WS_URL,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )

            ping_thread = threading.Thread(
                target=ping_loop,
                args=(ws,),
                daemon=True
            )

            ping_thread.start()

            ws.run_forever(
                ping_interval=None,
                ping_timeout=None
            )

        except Exception as e:

            print("[CONNECTION ERROR]", e)

        print("[RECONNECT] Waiting 5 seconds...")
        time.sleep(5)


if __name__ == "__main__":
    run()
