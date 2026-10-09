
from .indicators import atr, ema


def trend_engine(candles, cfg):
    if len(candles) < cfg.ema_slow:
        return {
            "valid": False,
            "direction": "",
            "ema_fast": None,
            "ema_slow": None,
            "atr": None,
        }

    closes = [c.close for c in candles]

    fast = ema(closes, cfg.ema_fast)
    slow = ema(closes, cfg.ema_slow)
    current_atr = atr(candles, cfg.atr_period)

    if fast is None or slow is None or current_atr is None:
        return {
            "valid": False,
            "direction": "",
            "ema_fast": fast,
            "ema_slow": slow,
            "atr": current_atr,
        }

    if fast > slow:
        direction = "BUY"
    elif fast < slow:
        direction = "SELL"
    else:
        direction = ""

    return {
        "valid": bool(direction),
        "direction": direction,
        "ema_fast": fast,
        "ema_slow": slow,
        "atr": current_atr,
    }


def momentum_engine(candles, current_atr, cfg):
    if len(candles) < cfg.impulse_lookback + 1:
        return {
            "valid": False,
            "direction": "",
            "size": 0.0,
            "size_atr": 0.0,
            "start": None,
            "end": None,
            "impulse_low": None,
            "impulse_high": None,
            "age": 0,
            "dir_ratio": 0.0,
        }

    if current_atr is None or current_atr <= 0:
        return {
            "valid": False,
            "direction": "",
            "size": 0.0,
            "size_atr": 0.0,
            "start": None,
            "end": None,
            "impulse_low": None,
            "impulse_high": None,
            "age": 0,
            "dir_ratio": 0.0,
        }

    window = candles[-cfg.impulse_lookback:]

    start = window[0].close
    end = window[-1].close

    move = end - start
    size = abs(move)
    size_atr = size / current_atr

    if move > 0:
        direction = "BUY"
    elif move < 0:
        direction = "SELL"
    else:
        direction = ""

    directional_bars = 0

    for i in range(1, len(window)):
        delta = window[i].close - window[i - 1].close

        if direction == "BUY" and delta > 0:
            directional_bars += 1
        elif direction == "SELL" and delta < 0:
            directional_bars += 1

    dir_ratio = directional_bars / max(1, len(window) - 1)

    valid = (
        bool(direction)
        and size_atr >= cfg.impulse_min_atr
        and dir_ratio >= cfg.impulse_min_dir_ratio
    )

    return {
        "valid": valid,
        "direction": direction,
        "size": size,
        "size_atr": size_atr,
        "start": start,
        "end": end,
        "impulse_low": min(c.low for c in window),
        "impulse_high": max(c.high for c in window),
        "age": 0,
        "dir_ratio": dir_ratio,
    }


def fibonacci_engine(price, momentum, current_atr, cfg):
    if not momentum.get("valid"):
        return {
            "valid": False,
            "level": None,
            "depth": None,
            "distance": None,
        }

    impulse_low = momentum.get("impulse_low")
    impulse_high = momentum.get("impulse_high")
    direction = momentum.get("direction")

    if (
        impulse_low is None
        or impulse_high is None
        or direction not in ("BUY", "SELL")
    ):
        return {
            "valid": False,
            "level": None,
            "depth": None,
            "distance": None,
        }

    size = impulse_high - impulse_low

    if size <= 0:
        return {
            "valid": False,
            "level": None,
            "depth": None,
            "distance": None,
        }

    if direction == "BUY":
        depth = (impulse_high - price) / size
    else:
        depth = (price - impulse_low) / size

    nearest = min(
        cfg.fib_levels,
        key=lambda level: abs(level - depth),
    )

    distance = abs(depth - nearest)

    if current_atr is not None and current_atr > 0:
        price_tolerance = cfg.fib_tol_atr * current_atr / size
    else:
        price_tolerance = cfg.fib_tol_atr

    valid = (
        depth >= min(cfg.fib_levels) - price_tolerance
        and depth <= cfg.fib_invalid
    )

    return {
        "valid": valid,
        "level": nearest,
        "depth": depth,
        "distance": distance,
    }


def pullback_engine(
    candles,
    momentum,
    fib_depth,
    ema_slow_value,
    current_atr,
    cfg,
):
    if not momentum.get("valid"):
        return {
            "valid": False,
            "type": "NO_MOMENTUM",
            "bars": 0,
            "counter_move": 0.0,
        }

    if fib_depth is None:
        return {
            "valid": False,
            "type": "NO_FIB",
            "bars": 0,
            "counter_move": 0.0,
        }

    if len(candles) < cfg.pullback_min_bars:
        return {
            "valid": False,
            "type": "NOT_ENOUGH_BARS",
            "bars": len(candles),
            "counter_move": 0.0,
        }

    direction = momentum["direction"]

    recent = candles[-cfg.pullback_min_bars:]

    if direction == "BUY":
        counter_move = max(
            0.0,
            momentum["end"] - min(c.low for c in recent),
        )
    else:
        counter_move = max(
            0.0,
            max(c.high for c in recent) - momentum["end"],
        )

    if current_atr is None or current_atr <= 0:
        return {
            "valid": False,
            "type": "NO_ATR",
            "bars": len(recent),
            "counter_move": counter_move,
        }

    counter_atr = counter_move / current_atr

    if counter_atr > cfg.pullback_max_counter_atr:
        return {
            "valid": False,
            "type": "DEEP_PULLBACK",
            "bars": len(recent),
            "counter_move": counter_move,
        }

    if cfg.pullback_respect_ema_slow and ema_slow_value is not None:
        last_close = candles[-1].close

        if direction == "BUY" and last_close < ema_slow_value:
            return {
                "valid": False,
                "type": "BROKE_EMA_SLOW",
                "bars": len(recent),
                "counter_move": counter_move,
            }

        if direction == "SELL" and last_close > ema_slow_value:
            return {
                "valid": False,
                "type": "BROKE_EMA_SLOW",
                "bars": len(recent),
                "counter_move": counter_move,
            }

    return {
        "valid": True,
        "type": "NORMAL",
        "bars": len(recent),
        "counter_move": counter_move,
        "counter_atr": counter_atr,
    }


def confirmation_engine(candles, direction, cfg):
    if len(candles) < 3:
        return {
            "valid": False,
            "hits": 0,
            "mode": "",
        }

    current = candles[-1]
    previous = candles[-2]

    hits = 0
    modes = []

    if direction == "BUY":
        if current.close > previous.high:
            hits += 1
            modes.append("breakout")

        if (
            current.low < previous.low
            and current.close > current.open
            and current.close > previous.close
        ):
            hits += 1
            modes.append("rejection")

        if (
            current.close > current.open
            and previous.close < previous.open
            and current.open <= previous.close
            and current.close >= previous.open
        ):
            hits += 1
            modes.append("engulfing")

    elif direction == "SELL":
        if current.close < previous.low:
            hits += 1
            modes.append("breakout")

        if (
            current.high > previous.high
            and current.close < current.open
            and current.close < previous.close
        ):
            hits += 1
            modes.append("rejection")

        if (
            current.close < current.open
            and previous.close > previous.open
            and current.open >= previous.close
            and current.close <= previous.open
        ):
            hits += 1
            modes.append("engulfing")

    allowed = set(cfg.confirm_modes)
    hits = sum(1 for mode in modes if mode in allowed)

    return {
        "valid": hits >= cfg.confirm_min_hits,
        "hits": hits,
        "mode": ",".join(modes),
    }


def regime_engine(candles, current_atr, cfg):
    if len(candles) < cfg.er_period + 1:
        return {
            "valid": False,
            "market": "UNKNOWN",
            "vol": "UNKNOWN",
            "er": None,
        }

    window = candles[-cfg.er_period:]

    direction_move = abs(
        window[-1].close - window[0].close
    )

    path = 0.0

    for i in range(1, len(window)):
        path += abs(
            window[i].close - window[i - 1].close
        )

    er = direction_move / path if path > 0 else 0.0

    if er >= cfg.er_trending:
        market = "TRENDING"
    else:
        market = "RANGING"

    atr_values = []

    for i in range(
        cfg.atr_period,
        len(candles) + 1,
    ):
        value = atr(
            candles[:i],
            cfg.atr_period,
        )

        if value is not None:
            atr_values.append(value)

    if not atr_values or current_atr is None:
        vol = "UNKNOWN"
    else:
        baseline = sum(
            atr_values[-cfg.vol_lookback:]
        ) / min(
            len(atr_values),
            cfg.vol_lookback,
        )

        ratio = current_atr / baseline if baseline > 0 else 1.0

        if ratio >= cfg.vol_high:
            vol = "HIGH_VOL"
        elif ratio <= cfg.vol_low:
            vol = "LOW_VOL"
        else:
            vol = "NORMAL_VOL"

    return {
        "valid": True,
        "market": market,
        "vol": vol,
        "er": er,
    }
