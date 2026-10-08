
def ema(values, period):
    if not values or len(values) < period:
        return None

    multiplier = 2 / (period + 1)

    value = sum(values[:period]) / period

    for price in values[period:]:
        value = (price - value) * multiplier + value

    return value


def true_range(candle, previous_close=None):

    if previous_close is None:
        return candle.high - candle.low

    return max(
        candle.high - candle.low,
        abs(candle.high - previous_close),
        abs(candle.low - previous_close),
    )


def atr(candles, period):

    if len(candles) < period:
        return None

    ranges = []

    for i, candle in enumerate(candles):

        previous_close = (
            candles[i - 1].close
            if i > 0
            else None
        )

        ranges.append(
            true_range(
                candle,
                previous_close,
            )
        )

    return sum(ranges[-period:]) / period


def efficiency_ratio(candles, period):

    if len(candles) < period + 1:
        return None

    window = candles[-period:]

    direction = abs(
        window[-1].close - window[0].close
    )

    volatility = 0.0

    for i in range(1, len(window)):
        volatility += abs(
            window[i].close - window[i - 1].close
        )

    if volatility == 0:
        return 0.0

    return direction / volatility
