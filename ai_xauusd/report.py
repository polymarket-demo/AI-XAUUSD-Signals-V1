def print_metrics(name, metrics):
    print(f"\n=== {name} ===")
    print(f"Trades       : {metrics['trades']}")
    print(f"Wins         : {metrics['wins']}")
    print(f"Losses       : {metrics['losses']}")
    print(f"Win rate     : {metrics['win_rate']:.2%}")
    print(f"Profit factor: {metrics['profit_factor']:.3f}")
    print(f"Expectancy   : {metrics['expectancy']:.4f} R")
    print(f"Total R      : {metrics['total_r']:.2f}")


def print_validation(result):
    print("\n" + "=" * 60)
    print("VALIDATION REPORT")
    print("=" * 60)

    print_metrics(
        "TRAIN",
        result["train"],
    )

    print_metrics(
        "TEST",
        result["test"],
    )

    print("=" * 60)


def print_ablation(results):
    print("\n" + "=" * 60)
    print("ABLATION REPORT")
    print("=" * 60)

    for name, metrics in results.items():
        print_metrics(name, metrics)

    print("=" * 60)
