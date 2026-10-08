import os
import json
import time
import threading
from datetime import datetime, timezone

import websocket


# =========================================================
# AI XAUUSD SIGNALS V1
# M5 BUILDER V1.4
# =========================================================

API_KEY = os.getenv("SIFTING_API_KEY")

if not API_KEY:
    raise RuntimeError("SIFTING_API_KEY non trovata nelle Railway Variables")


WS_URL = f"wss://stream.sifting.io/ws/v1?key={API_KEY}"

SYMBOL = "XAUUSD"
PRODUCT = "com"

RECONNECT_WAIT = 15
PING_INTERVAL = 30
PING_TIMEOUT = 10


# =========================================================
# STATO GLOBALE
# =========================================================

state_lock = threading.Lock()

current_bucket = None
current_bar = None

last_tick_ms = None
last_closed_bucket = None

accepted_ticks = 0
ignored_duplicates = 0
ignored_out_of_order = 0


# =========================================================
# UTILITY
# =========================================================

def utc_now():
    return datetime.now(timezone.utc)


def bucket_from_timestamp_ms(timestamp_ms):
    """
    Trasforma il timestamp del tick nel relativo bucket M5.
    """

    dt = datetime.fromtimestamp(
        timestamp_ms / 1000.0,
        tz=timezone.utc
    )

    minute = (dt.minute // 5) * 5

    return dt.replace(
        minute=minute,
        second=0,
        microsecond=0
    )


def format_bucket(bucket):
    if bucket is None:
        return "NONE"

    return bucket.strftime("%Y-%m-%d %H:%M")


# =========================================================
# LOG STATO
# =========================================================

def print_state(prefix="[M5 STATE]"):

    with state_lock:

        if current_bar is None:
            print(
                f"{prefix} "
                f"BUCKET={format_bucket(current_bucket)} "
                f"BAR=NONE"
            )
            return

        print(
            f"{prefix} "
            f"BUCKET={format_bucket(current_bucket)} "
            f"OPEN={current_bar['open']:.3f} "
            f"HIGH={current_bar['high']:.3f} "
            f"LOW={current_bar['low']:.3f} "
            f"CLOSE={current_bar['close']:.3f} "
            f"TICKS={current_bar['ticks']}"
        )


# =========================================================
# CHIUSURA M5
# =========================================================

def close_current_bar(reason="NEXT_BUCKET"):

    global current_bucket
    global current_bar
    global last_closed_bucket

    if current_bucket is None or current_bar is None:
        return

    closed_bucket = current_bucket
    bar = current_bar.copy()

    print("")
    print("========================================")
    print("[M5 CLOSED] PASS")
    print(f"REASON: {reason}")
    print(f"BUCKET: {format_bucket(closed_bucket)}")
    print(f"OPEN:   {bar['open']:.3f}")
    print(f"HIGH:   {bar['high']:.3f}")
    print(f"LOW:    {bar['low']:.3f}")
    print(f"CLOSE:  {bar['close']:.3f}")
    print(f"TICKS:  {bar['ticks']}")
    print("========================================")
    print("")

    last_closed_bucket = closed_bucket

    current_bucket = None
    current_bar = None


# =========================================================
# FILTRO TICK
# =========================================================

def filter_tick(timestamp_ms):

    global last_tick_ms
    global ignored_duplicates
    global ignored_out_of_order

    if last_tick_ms is None:

        last_tick_ms = timestamp_ms

        return True

    if timestamp_ms == last_tick_ms:

        ignored_duplicates += 1

        print(
            f"[TICK DUPLICATE IGNORED] "
            f"t={timestamp_ms}"
        )

        return False

    if timestamp_ms < last_tick_ms:

        ignored_out_of_order += 1

        print(
            f"[TICK OUT OF ORDER IGNORED] "
            f"t={timestamp_ms} "
            f"last={last_tick_ms}"
        )

        return False

    last_tick_ms = timestamp_ms

    return True


# =========================================================
# PROCESSAMENTO TICK
# =========================================================

def process_tick(msg):

    global current_bucket
    global current_bar
    global accepted_ticks

    try:

        timestamp_ms = int(msg["t"])
        price = float(msg["p"])

    except (KeyError, TypeError, ValueError):

        print("[TICK ERROR] formato tick non valido")

        return


    # -----------------------------------------------------
    # FILTRO
    # -----------------------------------------------------

    if not filter_tick(timestamp_ms):
        return


    accepted_ticks += 1


    tick_dt = datetime.fromtimestamp(
        timestamp_ms / 1000.0,
        tz=timezone.utc
    )

    bucket = bucket_from_timestamp_ms(timestamp_ms)


    print(
        f"[TICK ACCETTATO] "
        f"UTC={tick_dt.strftime('%Y-%m-%d %H:%M:%S')} "
        f"PRICE={price:.3f} "
        f"BUCKET={format_bucket(bucket)}"
    )


    with state_lock:

        # -------------------------------------------------
        # PRIMO TICK
        # -------------------------------------------------

        if current_bucket is None:

            # Se il tick appartiene a una candela già chiusa,
            # lo ignoriamo.
            if (
                last_closed_bucket is not None
                and bucket <= last_closed_bucket
            ):

                print(
                    f"[M5 OLD TICK IGNORED] "
                    f"BUCKET={format_bucket(bucket)} "
                    f"LAST_CLOSED={format_bucket(last_closed_bucket)}"
                )

                return


            current_bucket = bucket

            current_bar = {
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "ticks": 1
            }

            print("")
            print("[M5 START] PASS")
            print(f"BUCKET: {format_bucket(bucket)}")
            print(f"OPEN:   {price:.3f}")
            print("")

            return


        # -------------------------------------------------
        # STESSO BUCKET
        # -------------------------------------------------

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


        # -------------------------------------------------
        # BUCKET SUCCESSIVO
        # -------------------------------------------------

        if bucket > current_bucket:

            old_bucket = current_bucket
            new_bucket = bucket

            print("")
            print("[M5 TRANSITION]")
            print(
                f"OLD BUCKET: {format_bucket(old_bucket)}"
            )
            print(
                f"NEW BUCKET: {format_bucket(new_bucket)}"
            )
            print("")

            # Chiude la candela precedente
            close_current_bar(
                reason="NEXT_BUCKET"
            )

            # Nuova candela
            current_bucket = bucket

            current_bar = {
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "ticks": 1
            }

            print("")
            print("[M5 START] PASS")
            print(f"BUCKET: {format_bucket(bucket)}")
            print(f"OPEN:   {price:.3f}")
            print("")

            return


        # -------------------------------------------------
        # TICK DI UN BUCKET VECCHIO
        # -------------------------------------------------

        if bucket < current_bucket:

            print(
                f"[M5 OLD BUCKET IGNORED] "
                f"TICK={format_bucket(bucket)} "
                f"CURRENT={format_bucket(current_bucket)}"
            )

            return


# =========================================================
# WEBSOCKET
# =========================================================

def on_open(ws):

    print("")
    print("========================================")
    print("[WEBSOCKET OPEN]")
    print("========================================")
    print("")

    subscribe_message = {
        "op": "subscribe",
        "product": PRODUCT,
        "symbols": [SYMBOL]
    }

    ws.send(json.dumps(subscribe_message))

    print("[SUBSCRIBE] XAUUSD SENT")


def on_message(ws, message):

    global ignored_duplicates
    global ignored_out_of_order

    try:

        msg = json.loads(message)

    except json.JSONDecodeError:

        print("[JSON ERROR]")
        return


    frame_type = msg.get("f")


    # =====================================================
    # AUTH
    # =====================================================

    if frame_type == "ack":

        op = msg.get("op")

        if op == "auth":

            print(
                f"[AUTH PASS] "
                f"TIER={msg.get('tier')} "
                f"MAX_CONN={msg.get('max_conn')} "
                f"ACTIVE_CONN={msg.get('active_conn')}"
            )

        elif op == "subscribe":

            print(
                "[SUBSCRIBE PASS] "
                f"{msg.get('symbols')}"
            )

        return


    # =====================================================
    # PONG
    # =====================================================

    if frame_type == "pong":

        print("[PING/PONG] PASS")

        return


    # =====================================================
    # ERROR
    # =====================================================

    if frame_type == "error":

        print(
            f"[SIFTING ERROR] "
            f"CODE={msg.get('code')} "
            f"MESSAGE={msg.get('message')}"
        )

        return


    # =====================================================
    # TICK
    # =====================================================

    if frame_type == "tick":

        symbol = msg.get("s")

        if symbol != SYMBOL:
            return


        try:

            timestamp_ms = int(msg["t"])
            price = float(msg["p"])

        except (KeyError, TypeError, ValueError):

            print("[TICK ERROR] dati mancanti")

            return


        now_ms = int(time.time() * 1000)

        age_ms = now_ms - timestamp_ms


        bid = msg.get("b")
        ask = msg.get("a")


        spread = None

        try:

            if bid is not None and ask is not None:

                spread = float(ask) - float(bid)

        except (TypeError, ValueError):

            spread = None


        if spread is not None:

            print(
                f"[DATA] LIVE TICK: PASS "
                f"PRICE={price:.3f} "
                f"AGE={age_ms}ms "
                f"SPREAD={spread:.3f}"
            )

        else:

            print(
                f"[DATA] LIVE TICK: PASS "
                f"PRICE={price:.3f} "
                f"AGE={age_ms}ms"
            )


        # -------------------------------------------------
        # BLOCCO STALE
        # -------------------------------------------------

        if age_ms > 5000:

            print(
                f"[STALE TICK IGNORED] "
                f"AGE={age_ms}ms"
            )

            return


        process_tick(msg)

        return


    # =====================================================
    # FRAME SCONOSCIUTO
    # =====================================================

    print(
        f"[FRAME IGNORED] "
        f"{msg}"
    )


def on_error(ws, error):

    print(
        f"[WEBSOCKET ERROR] {error}"
    )


def on_close(ws, close_status_code, close_msg):

    print("")
    print("========================================")
    print(
        f"[WEBSOCKET CLOSED] "
        f"CODE={close_status_code} "
        f"MESSAGE={close_msg}"
    )
    print("========================================")
    print("")


# =========================================================
# MAIN
# =========================================================

def run():

    attempt = 0

    while True:

        ws = None

        try:

            print("")
            print("========================================")
            print("AI XAUUSD SIGNALS V1")
            print("M5 BUILDER V1.4")
            print("LIVE XAUUSD")
            print("========================================")
            print(
                f"[CONNECTING] attempt={attempt + 1}"
            )

            ws = websocket.WebSocketApp(
                WS_URL,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )

            ws.run_forever(
                ping_interval=PING_INTERVAL,
                ping_timeout=PING_TIMEOUT
            )

        except Exception as e:

            print(
                f"[RUN ERROR] {type(e).__name__}: {e}"
            )

        finally:

            if ws is not None:

                try:
                    ws.close()

                except Exception:
                    pass


        attempt += 1

        print(
            f"[RECONNECT] waiting "
            f"{RECONNECT_WAIT}s"
        )

        time.sleep(RECONNECT_WAIT)


if __name__ == "__main__":
    run()
