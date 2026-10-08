import os
import json
import time
import threading
from datetime import datetime, timezone, timedelta

import websocket


# =========================================================
# AI XAUUSD SIGNALS V1
# M5 BUILDER
# =========================================================

API_KEY = os.getenv("SIFTING_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "SIFTING_API_KEY non trovata nelle Railway Variables"
    )


WS_URL = f"wss://stream.sifting.io/ws/v1?key={API_KEY}"

SYMBOL = "XAUUSD"
PRODUCT = "com"

RECONNECT_WAIT = 15
PING_INTERVAL = 30
PING_TIMEOUT = 10

# Controllo orologio M5 indipendente dai tick
BOUNDARY_CHECK_INTERVAL = 0.20


# =========================================================
# STATO
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
# TIME / BUCKET
# =========================================================

def bucket_from_timestamp_ms(timestamp_ms):

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


def current_wall_clock_bucket():

    now = datetime.now(timezone.utc)

    minute = (now.minute // 5) * 5

    return now.replace(
        minute=minute,
        second=0,
        microsecond=0
    )


def next_boundary_after(bucket):

    return bucket + timedelta(minutes=5)


def format_bucket(bucket):

    if bucket is None:
        return "NONE"

    return bucket.strftime(
        "%Y-%m-%d %H:%M"
    )


# =========================================================
# CHIUSURA M5
# =========================================================

def close_current_bar(reason="TIME_BOUNDARY", close_time=None):

    global current_bucket
    global current_bar
    global last_closed_bucket

    if current_bucket is None:
        return False

    if current_bar is None:
        return False

    closed_bucket = current_bucket
    bar = current_bar.copy()

    if close_time is None:
        close_time = datetime.now(timezone.utc)

    print("")
    print("========================================")

    if reason == "TIME_BOUNDARY":
        print("[M5 TIME CLOSE] PASS")
    else:
        print("[M5 CLOSED] PASS")

    print(f"REASON: {reason}")
    print(f"BUCKET: {format_bucket(closed_bucket)}")
    print(
        f"CLOSE_TIME: "
        f"{close_time.strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )
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

    return True


# =========================================================
# M5 CLOCK
#
# Questa funzione NON dipende dall'arrivo dei tick.
#
# Alle 01:45:00 UTC chiude la candela 01:40.
# Non aspetta il primo tick della 01:45.
# =========================================================

def m5_boundary_monitor():

    global current_bucket

    print(
        "[M5 CLOCK] Monitor confini temporali attivo"
    )

    while True:

        try:

            now = datetime.now(timezone.utc)

            wall_bucket = current_wall_clock_bucket()

            with state_lock:

                if (
                    current_bucket is not None
                    and current_bar is not None
                    and current_bucket < wall_bucket
                ):

                    boundary_time = next_boundary_after(
                        current_bucket
                    )

                    # Se il processo è arrivato oltre il confine
                    # previsto, il close_time rappresenta comunque
                    # il confine reale della candela.
                    close_current_bar(
                        reason="TIME_BOUNDARY",
                        close_time=boundary_time
                    )

                    print(
                        f"[M5 WAITING] NEXT BUCKET: "
                        f"{format_bucket(wall_bucket)}"
                    )

            # Calcolo del prossimo confine.
            next_boundary = (
                wall_bucket
                + timedelta(minutes=5)
            )

            seconds_to_boundary = (
                next_boundary - now
            ).total_seconds()

            # Controllo frequente vicino al confine,
            # senza creare un loop aggressivo.
            sleep_time = min(
                BOUNDARY_CHECK_INTERVAL,
                max(0.05, seconds_to_boundary)
            )

            time.sleep(sleep_time)

        except Exception as e:

            print(
                f"[M5 CLOCK ERROR] "
                f"{type(e).__name__}: {e}"
            )

            time.sleep(
                BOUNDARY_CHECK_INTERVAL
            )


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

    # -----------------------------------------------------
    # DUPLICATO
    # -----------------------------------------------------

    if timestamp_ms == last_tick_ms:

        ignored_duplicates += 1

        print(
            f"[TICK DUPLICATE IGNORED] "
            f"t={timestamp_ms}"
        )

        return False

    # -----------------------------------------------------
    # OUT OF ORDER
    # -----------------------------------------------------

    if timestamp_ms < last_tick_ms:

        ignored_out_of_order += 1

        print(
            f"[TICK OUT OF ORDER IGNORED] "
            f"t={timestamp_ms} "
            f"last={last_tick_ms}"
        )

        return False

    # -----------------------------------------------------
    # TICK VALIDO
    # -----------------------------------------------------

    last_tick_ms = timestamp_ms

    return True


# =========================================================
# PROCESS TICK
# =========================================================

def process_tick(msg):

    global current_bucket
    global current_bar
    global accepted_ticks

    try:

        timestamp_ms = int(msg["t"])
        price = float(msg["p"])

    except (KeyError, TypeError, ValueError):

        print(
            "[TICK ERROR] formato tick non valido"
        )

        return

    # =====================================================
    # FILTER
    # =====================================================

    if not filter_tick(timestamp_ms):
        return

    accepted_ticks += 1

    tick_dt = datetime.fromtimestamp(
        timestamp_ms / 1000.0,
        tz=timezone.utc
    )

    bucket = bucket_from_timestamp_ms(
        timestamp_ms
    )

    print(
        f"[TICK ACCETTATO] "
        f"UTC={tick_dt.strftime('%Y-%m-%d %H:%M:%S')} "
        f"PREZZO={price:.3f} "
        f"BUCKET={format_bucket(bucket)}"
    )

    # =====================================================
    # LOCK
    # =====================================================

    with state_lock:

        # =================================================
        # PRIMO TICK
        # =================================================

        if current_bucket is None:

            # Non riaprire una candela già chiusa.

            if (
                last_closed_bucket is not None
                and bucket <= last_closed_bucket
            ):

                print(
                    f"[M5 OLD TICK IGNORED] "
                    f"BUCKET={format_bucket(bucket)} "
                    f"LAST_CLOSED="
                    f"{format_bucket(last_closed_bucket)}"
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
            print(
                f"BUCKET: "
                f"{format_bucket(bucket)}"
            )
            print(
                f"OPEN:   {price:.3f}"
            )
            print("")

            return

        # =================================================
        # STESSO BUCKET
        # =================================================

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

        # =================================================
        # BUCKET SUCCESSIVO
        #
        # Normalmente la candela precedente sarà già stata
        # chiusa dal M5 CLOCK.
        #
        # Se il tick arriva prima che il monitor temporale
        # abbia eseguito il close, facciamo comunque una
        # chiusura di sicurezza.
        # =================================================

        if bucket > current_bucket:

            old_bucket = current_bucket
            new_bucket = bucket

            print("")
            print("[M5 TRANSITION]")
            print(
                f"OLD BUCKET: "
                f"{format_bucket(old_bucket)}"
            )
            print(
                f"NEW BUCKET: "
                f"{format_bucket(new_bucket)}"
            )
            print("")

            close_current_bar(
                reason="NEXT_BUCKET",
                close_time=(
                    new_bucket
                )
            )

            # =================================================
            # NUOVA CANDELA
            # =================================================

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
            print(
                f"BUCKET: "
                f"{format_bucket(bucket)}"
            )
            print(
                f"OPEN:   {price:.3f}"
            )
            print("")

            return

        # =================================================
        # BUCKET VECCHIO
        # =================================================

        if bucket < current_bucket:

            print(
                f"[M5 OLD BUCKET IGNORED] "
                f"TICK={format_bucket(bucket)} "
                f"CURRENT={format_bucket(current_bucket)}"
            )

            return


# =========================================================
# WEBSOCKET OPEN
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

    ws.send(
        json.dumps(subscribe_message)
    )

    print(
        "[SUBSCRIBE] XAUUSD SENT"
    )


# =========================================================
# WEBSOCKET MESSAGE
# =========================================================

def on_message(ws, message):

    try:

        msg = json.loads(message)

    except json.JSONDecodeError:

        print(
            "[JSON ERROR]"
        )

        return

    frame_type = msg.get("f")

    # =====================================================
    # ACK
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

            return

        if op == "subscribe":

            print(
                f"[SUBSCRIBE PASS] "
                f"{msg.get('symbols')}"
            )

            return

        return

    # =====================================================
    # PONG
    # =====================================================

    if frame_type == "pong":

        print(
            "[PING/PONG] PASS"
        )

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

            timestamp_ms = int(
                msg["t"]
            )

            price = float(
                msg["p"]
            )

        except (
            KeyError,
            TypeError,
            ValueError
        ):

            print(
                "[TICK ERROR] dati mancanti"
            )

            return

        # =================================================
        # AGE
        # =================================================

        now_ms = int(
            time.time() * 1000
        )

        age_ms = (
            now_ms - timestamp_ms
        )

        # =================================================
        # BID / ASK / SPREAD
        # =================================================

        bid = msg.get("b")
        ask = msg.get("a")

        spread = None

        try:

            if (
                bid is not None
                and ask is not None
            ):

                spread = (
                    float(ask)
                    -
                    float(bid)
                )

        except (
            TypeError,
            ValueError
        ):

            spread = None

        # =================================================
        # LIVE DATA LOG
        # =================================================

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

        # =================================================
        # STALE
        # =================================================

        if age_ms > 5000:

            print(
                f"[STALE TICK IGNORED] "
                f"AGE={age_ms}ms"
            )

            return

        # =================================================
        # PROCESS
        # =================================================

        process_tick(msg)

        return

    # =====================================================
    # UNKNOWN FRAME
    # =====================================================

    print(
        f"[FRAME IGNORED] {msg}"
    )


# =========================================================
# WEBSOCKET ERROR
# =========================================================

def on_error(ws, error):

    print(
        f"[WEBSOCKET ERROR] {error}"
    )


# =========================================================
# WEBSOCKET CLOSE
# =========================================================

def on_close(
    ws,
    close_status_code,
    close_msg
):

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

    # =====================================================
    # AVVIO MONITOR TEMPORALE M5
    # =====================================================

    boundary_thread = threading.Thread(
        target=m5_boundary_monitor,
        name="M5BoundaryMonitor",
        daemon=True
    )

    boundary_thread.start()

    attempt = 0

    while True:

        ws = None

        try:

            print("")
            print("========================================")
            print("AI XAUUSD SIGNALS V1")
            print("M5 BUILDER")
            print("LIVE XAUUSD")
            print("========================================")

            print(
                f"[CONNECTING] "
                f"attempt={attempt + 1}"
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
                f"[RUN ERROR] "
                f"{type(e).__name__}: {e}"
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

        time.sleep(
            RECONNECT_WAIT
        )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    run()
