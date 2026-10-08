from .runner import Runner
from .tracker import Tracker


def run_backtest(candles, cfg, name="BACKTEST"):

    runner = Runner(
        cfg,
        name=name,
    )

    tracker = Tracker(cfg)

    signals = []
    results = []

    def on_signal(signal):

        signals.append(signal)

        if tracker.open is None:
            tracker.open_trade(signal)

    runner.on_signal = on_signal

    for candle in candles:

        evaluation = runner.on_candle(candle)

        result = tracker.on_candle(candle)

        if result is not None:
            results.append(result)

    return {
        "signals": signals,
        "results": results,
        "r_values": [
            result.r
            for result in results
        ],
    }
