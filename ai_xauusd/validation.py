from .backtest import run_backtest
from .metrics import calculate_metrics


def split_data(candles, train_ratio=0.8):
    if not candles:
        return [], []

    cut = int(len(candles) * train_ratio)

    return (
        candles[:cut],
        candles[cut:],
    )


def validate(candles, cfg):
    train, test = split_data(candles)

    train_result = run_backtest(
        train,
        cfg,
        name="TRAIN",
    )

    test_result = run_backtest(
        test,
        cfg,
        name="TEST",
    )

    return {
        "train": calculate_metrics(
            train_result["results"]
        ),
        "test": calculate_metrics(
            test_result["results"]
        ),
        "train_trades": train_result["results"],
        "test_trades": test_result["results"],
    }
