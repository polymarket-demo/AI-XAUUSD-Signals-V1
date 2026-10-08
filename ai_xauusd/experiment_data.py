from .synth import make_candles


def load_synthetic_data(
    candles=6000,
    seed=1,
):
    return make_candles(
        n=candles,
        seed=seed,
    )


def load_train_test_data(
    candles=6000,
    seed=1,
):
    data = load_synthetic_data(
        candles=candles,
        seed=seed,
    )

    cut = int(len(data) * 0.8)

    return (
        data[:cut],
        data[cut:],
    )
