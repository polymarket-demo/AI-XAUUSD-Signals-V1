
from .pipeline import Pipeline


class Runner:

    def __init__(self, cfg, name="RUNNER"):
        self.cfg = cfg
        self.name = name

        self.pipe = Pipeline(cfg)

        self.on_signal = None

        self.trades = []

        self.last_signal = None

    def warmup(self, candles):

        for candle in candles:
            self.pipe.on_candle(
                candle,
                allow_signal=False,
            )

        self.trades = []
        self.last_signal = None

    def on_candle(self, candle):

        evaluation = self.pipe.on_candle(
            candle,
            allow_signal=True,
        )

        if evaluation.signal is None:
            return evaluation

        signal = evaluation.signal

        self.last_signal = signal

        if self.on_signal is not None:
            self.on_signal(signal)

        return evaluation
