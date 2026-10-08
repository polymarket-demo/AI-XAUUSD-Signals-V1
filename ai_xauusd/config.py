from dataclasses import dataclass, field


@dataclass
class Config:

    # DATA
    max_spread: float = 1.0
    max_price_jump: float = 15.0
    max_tick_gap_s: int = 120

    # COMPONENTI
    use_trend: bool = True
    use_momentum: bool = True
    use_fibonacci: bool = True
    use_pullback: bool = True
    use_confirmation: bool = True

    # TREND
    ema_fast: int = 20
    ema_slow: int = 50
    atr_period: int = 14
    strong_trend_atr: float = 0.5
    trend_require_strong: bool = False

    # MOMENTUM
    impulse_lookback: int = 30
    impulse_min_atr: float = 3.0
    impulse_max_bars: int = 10
    impulse_max_age: int = 15
    impulse_min_dir_ratio: float = 0.6

    # FIBONACCI
    fib_levels: tuple = (0.382, 0.5, 0.618)
    fib_tol_atr: float = 0.3
    fib_invalid: float = 0.786

    # PULLBACK
    pullback_min_bars: int = 2
    pullback_max_counter_atr: float = 1.5
    pullback_respect_ema_slow: bool = True

    # CONFIRMATION
    confirm_modes: tuple = (
        "breakout",
        "rejection",
        "engulfing",
    )
    confirm_min_hits: int = 1

    # REGIME
    er_period: int = 20
    er_trending: float = 0.30
    vol_lookback: int = 100
    vol_high: float = 1.2
    vol_low: float = 0.8

    # SCORING
    weights: dict = field(default_factory=lambda: {
        "trend": 20,
        "momentum": 20,
        "fibonacci": 15,
        "pullback": 20,
        "confirmation": 15,
        "regime": 10,
    })

    min_score: float = 0.0

    # RISK
    sl_mode: str = "swing"
    sl_atr_mult: float = 1.5
    sl_buffer_atr: float = 0.1
    rr: float = 2.0

    half_spread: float = 0.15
    min_risk_atr: float = 0.5
    max_risk_atr: float = 4.0

    # SIGNAL CONTROL
    cooldown_bars: int = 3
    max_trade_bars: int = 48
    max_gap_min: int = 60
    sl_slippage: float = 0.10

    # STATISTICS
    min_trades_verdict: int = 100
