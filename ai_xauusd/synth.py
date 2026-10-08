from datetime import datetime, timedelta, timezone


def make_candles(n=1000, seed=1):

    import random

    rng = random.Random(seed)

    candles = []

    ts = datetime(
        2025,
        1,
        1,
        tzinfo=timezone.utc,
    )

    price = 2650.0

    for i in range(n):

        drift = 0.02

        if (i // 100) % 2 == 0:
            drift = 0.05
        else:
            drift = -0.05

        noise = rng.gauss(0, 0.35)

        open_price = price

        close_price = (
            price
            + drift
            + noise
        )

        high = max(
            open_price,
            close_price,
        ) + abs(rng.gauss(0, 0.15))

        low = min(
            open_price,
            close_price,
        ) - abs(rng.gauss(0, 0.15))

        candles.append(
            _candle(
                ts,
                open_price,
                high,
                low,
                close_price,
            )
        )

        price = close_price

        ts += timedelta(minutes=5)

    return candles


def _candle(
    ts,
    open_price,
    high,
    low,
    close_price,
):

    from .models import Candle

    return Candle(
        open_ts=ts,
        close_ts=ts + timedelta(minutes=5),
        open=open_price,
        high=high,
        low=low,
        close=close_price,
        tick_count=1,
    )
