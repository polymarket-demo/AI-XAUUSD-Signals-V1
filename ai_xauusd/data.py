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
            f"wss://stream.sifting.com/"
            f"{self.product}/{self.symbol}"
        )

    @staticmethod
    def parse(data, received_ms=None):

        if not isinstance(data, dict):
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

        except (TypeError, ValueError, OverflowError):
            return None

    def __iter__(self):

        while True:

            received_ms = int(time.time() * 1000)

            try:

                ws = websocket.create_connection(
                    self.url,
                    header=[
                        f"Authorization: Bearer {self.api_key}"
                    ],
                    timeout=30,
                )

                while True:

                    raw = ws.recv()

                    received_ms = int(time.time() * 1000)

                    if not raw:
                        continue

                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    tick = self.parse(
                        data,
                        received_ms,
                    )

                    if tick is not None:
                        yield tick

            except Exception as exc:

                print(
                    f"[FEED ERROR] {type(exc).__name__}: {exc}",
                    flush=True,
                )

                time.sleep(5)
