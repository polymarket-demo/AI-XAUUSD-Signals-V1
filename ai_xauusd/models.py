from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Tick:
    ts: datetime
    bid: float
    ask: float
    volume: float = 0.0
    latency_ms: float | None = None

    @property
    def mid(self):
        return (self.bid + self.ask) / 2

    @property
    def spread(self):
        return self.ask - self.bid


@dataclass
class Candle:
    open_ts: datetime
    close_ts: datetime
    open: float
    high: float
    low: float
    close: float
    tick_count: int = 0
