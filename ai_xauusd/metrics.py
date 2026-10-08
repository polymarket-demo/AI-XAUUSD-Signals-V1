def calculate_metrics(results):
    if not results:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "expectancy": 0.0,
            "total_r": 0.0,
        }

    r_values = [
        r.r if hasattr(r, "r") else float(r)
        for r in results
    ]

    wins = [r for r in r_values if r > 0]
    losses = [r for r in r_values if r < 0]

    trades = len(r_values)

    win_rate = (
        len(wins) / trades
        if trades > 0
        else 0.0
    )

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = float("inf")
    else:
        profit_factor = 0.0

    expectancy = (
        sum(r_values) / trades
        if trades > 0
        else 0.0
    )

    return {
        "trades": trades,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "expectancy": expectancy,
        "total_r": sum(r_values),
    }
