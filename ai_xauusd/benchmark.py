import random


def random_baseline(
    cfg,
    candles,
    runs=20,
    risk_atr=1.5,
    mode="random",
):
    if not candles:
        return {
            "runs": runs,
            "values": [],
            "p5": 0.0,
            "p50": 0.0,
            "p95": 0.0,
        }

    results = []

    for run in range(runs):

        rng = random.Random(run + 1)

        total_r = 0.0

        for i in range(1, len(candles)):

            current = candles[i]

            if mode == "trend":

                previous = candles[i - 1]

                if current.close > previous.close:
                    direction = "BUY"
                elif current.close < previous.close:
                    direction = "SELL"
                else:
                    continue

            else:

                direction = rng.choice(
                    ["BUY", "SELL"]
                )

            entry = current.close

            risk = risk_atr

            if direction == "BUY":

                sl = entry - risk
                tp = entry + risk * cfg.rr

                if current.low <= sl:
                    total_r -= 1.0

                elif current.high >= tp:
                    total_r += cfg.rr

            else:

                sl = entry + risk
                tp = entry - risk * cfg.rr

                if current.high >= sl:
                    total_r -= 1.0

                elif current.low <= tp:
                    total_r += cfg.rr

        results.append(total_r)

    values = sorted(results)

    def percentile(data, p):

        if not data:
            return 0.0

        index = int(
            (len(data) - 1) * p
        )

        return data[index]

    return {
        "runs": runs,
        "values": results,
        "p5": percentile(values, 0.05),
        "p50": percentile(values, 0.50),
        "p95": percentile(values, 0.95),
    }
