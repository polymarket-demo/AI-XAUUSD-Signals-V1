
from dataclasses import dataclass


@dataclass
class TradeResult:
    outcome: str
    entry: float
    exit: float
    r: float
    bars: int


class Tracker:

    def __init__(self, cfg):
        self.cfg = cfg

        self.open = None
        self.last_ts = None

    def open_trade(self, signal):
        self.open = signal

    def on_candle(self, candle):

        if self.open is None:
            return None

        signal = self.open

        direction = signal.direction
        entry = signal.entry
        sl = signal.sl
        tp = signal.tp

        self.last_ts = candle.close_ts

        # BUY
        if direction == "BUY":

            # SL viene controllato prima del TP
            if candle.low <= sl:
                r = (sl - entry) / signal.risk

                result = TradeResult(
                    outcome="LOSS",
                    entry=entry,
                    exit=sl,
                    r=r,
                    bars=1,
                )

                self.open = None
                return result

            if candle.high >= tp:
                r = (tp - entry) / signal.risk

                result = TradeResult(
                    outcome="WIN",
                    entry=entry,
                    exit=tp,
                    r=r,
                    bars=1,
                )

                self.open = None
                return result

        # SELL
        elif direction == "SELL":

            # SL viene controllato prima del TP
            if candle.high >= sl:
                r = (entry - sl) / signal.risk

                result = TradeResult(
                    outcome="LOSS",
                    entry=entry,
                    exit=sl,
                    r=r,
                    bars=1,
                )

                self.open = None
                return result

            if candle.low <= tp:
                r = (entry - tp) / signal.risk

                result = TradeResult(
                    outcome="WIN",
                    entry=entry,
                    exit=tp,
                    r=r,
                    bars=1,
                )

                self.open = None
                return result

        return None
