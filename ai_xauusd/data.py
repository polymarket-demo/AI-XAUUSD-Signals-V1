import json
import time
from datetime import datetime, timezone

import websocket

from .models import Tick


class SiftingFeed:

    def __init__(
        self,
        api_key,
        product="com",
        symbol="XAUUSD",
    ):
        self.api_key = api_key
        self.product = product
        self.symbol = symbol

        self.url = (
            "wss://stream.sifting.io/ws/v1"
            f"?key={self.api_key}"
        )

    @staticmethod
    def parse(data, received_ms=None):

        if not isinstance(data, dict):
            return None

        if data.get("f") != "tick":
            return None

        try:
            price = data.get("p")
            timestamp_ms = data.get("t")

            if price is None or timestamp_ms is None:
                return None

            price = float(price)
            timestamp_ms = int(timestamp_ms)

            bid = data.get("b")
            ask = data.get("a")

            if bid is None or ask is None:
                bid = price
                ask = price

            bid = float(bid)
            ask = float(ask)

            ts = datetime.fromtimestamp(
                timestamp_ms / 1000,
                tz=timezone.utc,
            )

            latency_ms = None

            if received_ms is not None:
                latency_ms = received_ms - timestamp_ms

            return Tick(
                ts=ts,
                bid=bid,
                ask=ask,
                latency_ms=latency_ms,
            )

        except (
            TypeError,
            ValueError,
            OverflowError,
        ):
            return None

    def __iter__(self):

        while True:

            ws = None

            try:

                print(
                    "[SIFTING] Connessione WebSocket...",
                    flush=True,
                )

                ws = websocket.create_connection(
                    self.url,
                    timeout=30,
                )

                print(
                    "[SIFTING] WebSocket connesso.",
                    flush=True,
                )

                subscription = {
                    "op": "subscribe",
                    "product": self.product,
                    "symbols": [self.symbol],
                }

                ws.send(
                    json.dumps(subscription)
                )

                print(
                    f"[SIFTING] Subscription "
                    f"{self.product}/{self.symbol} inviata.",
                    flush=True,
                )

                last_ping = time.time()

                while True:

                    if time.time() - last_ping >= 45:

                        ws.send(
                            json.dumps({
                                "op": "ping",
                            })
                        )

                        last_ping = time.time()

                    ws.settimeout(5)

                    try:
                        raw = ws.recv()

                    except websocket.WebSocketTimeoutException:
                        continue

                    received_ms = int(
                        time.time() * 1000
                    )

                    if not raw:
                        continue

                    try:
                        data = json.loads(raw)

                    except json.JSONDecodeError:
                        continue

                    frame = data.get("f")

                    if frame == "ack":
                        print(
                            f"[SIFTING ACK] {data}",
                            flush=True,
                        )
                        continue

                    if frame == "pong":
                        continue

                    if frame == "error":
                        print(
                            f"[SIFTING ERROR] {data}",
                            flush=True,
                        )
                        continue

                    tick = self.parse(
                        data,
                        received_ms,
                    )

                    if tick is not None:
                        yield tick

            except Exception as exc:

                print(
                    f"[FEED ERROR] "
                    f"{type(exc).__name__}: {exc}",
                    flush=True,
                )

                time.sleep(5)

            finally:

                if ws is not None:

                    try:
                        ws.close()

                    except Exception:
                        pass
