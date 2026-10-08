
from dataclasses import dataclass

from . import engines


@dataclass
class Signal:
    ts: object
    direction: str
    entry: float
    sl: float
    tp: float
    risk: float
    reward: float
    rr: float
    score: float
    confidence: str
    trend: str
    momentum: str
    fibonacci: str
    pullback: str
    confirmation: str
    regime: dict
    reason: str
    setup_key: str
    atr: float


@dataclass
class Evaluation:
    signal: Signal | None
    reason: str


class Pipeline:

    def __init__(self, cfg):
        self.cfg = cfg
        self.candles = []
        self.last_signal_ts = None

    def on_candle(self, candle, allow_signal=True):

        self.candles.append(candle)

        max_history = max(
            self.cfg.ema_slow * 3,
            self.cfg.impulse_lookback * 3,
            self.cfg.vol_lookback + self.cfg.atr_period + 20,
        )

        if len(self.candles) > max_history:
            self.candles = self.candles[-max_history:]

        minimum = max(
            self.cfg.ema_slow,
            self.cfg.impulse_lookback + 1,
            self.cfg.atr_period + 1,
            self.cfg.er_period + 1,
        )

        if len(self.candles) < minimum:
            return Evaluation(
                signal=None,
                reason="WARMUP",
            )

        if not allow_signal:
            return Evaluation(
                signal=None,
                reason="SIGNALS_DISABLED",
            )

        return self._evaluate()

    def _evaluate(self):

        candles = self.candles

        trend = engines.trend_engine(
            candles,
            self.cfg,
        )

        if not trend["valid"]:
            return Evaluation(
                signal=None,
                reason="NO_TREND",
            )

        current_atr = trend["atr"]

        momentum = engines.momentum_engine(
            candles,
            current_atr,
            self.cfg,
        )

        if self.cfg.use_momentum and not momentum["valid"]:
            return Evaluation(
                signal=None,
                reason="NO_MOMENTUM",
            )

        if not momentum["valid"]:
            return Evaluation(
                signal=None,
                reason="NO_MOMENTUM",
            )

        direction = trend["direction"]

        if direction != momentum["direction"]:
            return Evaluation(
                signal=None,
                reason="TREND_MOMENTUM_CONFLICT",
            )

        price = candles[-1].close

        fib = engines.fibonacci_engine(
            price,
            momentum,
            current_atr,
            self.cfg,
        )

        if self.cfg.use_fibonacci and not fib["valid"]:
            return Evaluation(
                signal=None,
                reason="NO_FIBONACCI",
            )

        if not fib["valid"]:
            return Evaluation(
                signal=None,
                reason="NO_FIBONACCI",
            )

        pullback = engines.pullback_engine(
            candles,
            momentum,
            fib["depth"],
            trend["ema_slow"],
            current_atr,
            self.cfg,
        )

        if self.cfg.use_pullback and not pullback["valid"]:
            return Evaluation(
                signal=None,
                reason=f"NO_PULLBACK:{pullback['type']}",
            )

        confirmation = engines.confirmation_engine(
            candles,
            direction,
            self.cfg,
        )

        if self.cfg.use_confirmation and not confirmation["valid"]:
            return Evaluation(
                signal=None,
                reason="NO_CONFIRMATION",
            )

        regime = engines.regime_engine(
            candles,
            current_atr,
            self.cfg,
        )

        score = self._score(
            trend,
            momentum,
            fib,
            pullback,
            confirmation,
            regime,
        )

        if score < self.cfg.min_score:
            return Evaluation(
                signal=None,
                reason="LOW_SCORE",
            )

        entry = price

        sl = self._stop_loss(
            direction,
            candles,
            current_atr,
            self.cfg,
        )

        if direction == "BUY":
            risk = entry - sl
        else:
            risk = sl - entry

        if risk <= 0:
            return Evaluation(
                signal=None,
                reason="INVALID_RISK",
            )

        risk_atr = risk / current_atr

        if risk_atr < self.cfg.min_risk_atr:
            return Evaluation(
                signal=None,
                reason="RISK_TOO_SMALL",
            )

        if risk_atr > self.cfg.max_risk_atr:
            return Evaluation(
                signal=None,
                reason="RISK_TOO_LARGE",
            )

        if direction == "BUY":
            tp = entry + risk * self.cfg.rr
        else:
            tp = entry - risk * self.cfg.rr

        if self.last_signal_ts is not None:

            elapsed = (
                candles[-1].close_ts
                - self.last_signal_ts
            ).total_seconds()

            cooldown = (
                self.cfg.cooldown_bars * 5 * 60
            )

            if elapsed < cooldown:
                return Evaluation(
                    signal=None,
                    reason="COOLDOWN",
                )

        confidence = self._confidence(score)

        setup_key = (
            f"{direction}|"
            f"{round(fib['depth'], 3)}|"
            f"{confirmation['mode']}"
        )

        signal = Signal(
            ts=candles[-1].close_ts,
            direction=direction,
            entry=entry,
            sl=sl,
            tp=tp,
            risk=risk,
            reward=risk * self.cfg.rr,
            rr=self.cfg.rr,
            score=score,
            confidence=confidence,
            trend=direction,
            momentum=momentum["direction"],
            fibonacci=str(round(fib["depth"], 3)),
            pullback=pullback["type"],
            confirmation=confirmation["mode"],
            regime={
                "market": regime["market"],
                "vol": regime["vol"],
            },
            reason="ALL_COMPONENTS_CONFIRMED",
            setup_key=setup_key,
            atr=current_atr,
        )

        self.last_signal_ts = candles[-1].close_ts

        return Evaluation(
            signal=signal,
            reason="SIGNAL",
        )

    def _score(
        self,
        trend,
        momentum,
        fib,
        pullback,
        confirmation,
        regime,
    ):

        score = 0.0
        weights = self.cfg.weights

        if trend["valid"]:
            score += weights.get("trend", 0)

        if momentum["valid"]:
            score += weights.get("momentum", 0)

        if fib["valid"]:
            score += weights.get("fibonacci", 0)

        if pullback["valid"]:
            score += weights.get("pullback", 0)

        if confirmation["valid"]:
            score += weights.get("confirmation", 0)

        if regime["valid"]:
            score += weights.get("regime", 0)

        return score

    def _confidence(self, score):

        if score >= 80:
            return "HIGH"

        if score >= 60:
            return "MEDIUM"

        return "LOW"

    def _stop_loss(
        self,
        direction,
        candles,
        current_atr,
        cfg,
    ):

        recent = candles[-cfg.impulse_lookback:]

        if direction == "BUY":
            swing = min(c.low for c in recent)

            return (
                swing
                - current_atr * cfg.sl_buffer_atr
            )

        swing = max(c.high for c in recent)

        return (
            swing
            + current_atr * cfg.sl_buffer_atr
        )
