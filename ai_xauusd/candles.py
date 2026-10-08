from datetime import timedelta

from .models import Candle


class CandleBuilder:

    def __init__(self, minutes=5):
        self.minutes = minutes
        self.current = None

    def _bucket(self, ts):
        minute = (ts.minute // self.minutes) * self.minutes

        return ts.replace(
            minute=minute,
            second=0,
            microsecond=0,
        )

    def add_tick(self, tick):

        bucket = self._bucket(tick.ts)

        if self.current is None:

            self.current = {
                "open_ts": bucket,
                "close_ts": bucket + timedelta(minutes=self.minutes),
                "open": tick.mid,
                "high": tick.mid,
                "low": tick.mid,
                "close": tick.mid,
                "tick_count": 1,
            }

            return None

        if bucket == self.current["open_ts"]:

            price = tick.mid

            self.current["high"] = max(
                self.current["high"],
                price,
            )

            self.current["low"] = min(
                self.current["low"],
                price,
            )

            self.current["close"] = price
            self.current["tick_count"] += 1

            return None

        closed = self.current

        self.current = {
            "open_ts": bucket,
            "close_ts": bucket + timedelta(minutes=self.minutes),
            "open": tick.mid,
            "high": tick.mid,
            "low": tick.mid,
            "close": tick.mid,
            "tick_count": 1,
        }

        return Candle(
            closed["open_ts"],
            closed["close_ts"],
            closed["open"],
            closed["high"],
            closed["low"],
            closed["close"],
            closed["tick_count"],
        )
