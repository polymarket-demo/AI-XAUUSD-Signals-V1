
def verdict(results, min_trades=100):

    n = len(results)

    if n < min_trades:
        return {
            "trades": n,
            "win_rate": None,
            "profit_factor": None,
            "expectancy": None,
            "verdict": "NON LO SAPPIAMO",
        }

    wins = [r for r in results if r > 0]
    losses = [r for r in results if r < 0]

    win_rate = len(wins) / n

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    if gross_loss == 0:
        profit_factor = float("inf")
    else:
        profit_factor = gross_profit / gross_loss

    expectancy = sum(results) / n

    if expectancy > 0 and profit_factor > 1:
        decision = "POSSIBILE EDGE"
    else:
        decision = "NESSUNA EVIDENZA DI EDGE"

    return {
        "trades": n,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "expectancy": expectancy,
        "verdict": decision,
    }
