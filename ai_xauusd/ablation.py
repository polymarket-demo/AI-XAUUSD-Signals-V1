from copy import deepcopy

from .backtest import run_backtest
from .metrics import calculate_metrics


def run_ablation(candles, cfg):
    results = {}

    baseline_cfg = deepcopy(cfg)

    baseline = run_backtest(
        candles,
        baseline_cfg,
        name="BASELINE",
    )

    results["BASELINE"] = calculate_metrics(
        baseline["results"]
    )

    components = [
        "use_trend",
        "use_momentum",
        "use_fibonacci",
        "use_pullback",
        "use_confirmation",
    ]

    for component in components:

        test_cfg = deepcopy(cfg)

        setattr(
            test_cfg,
            component,
            False,
        )

        result = run_backtest(
            candles,
            test_cfg,
            name=f"NO_{component.upper()}",
        )

        results[
            f"NO_{component.upper()}"
        ] = calculate_metrics(
            result["results"]
        )

    return results
