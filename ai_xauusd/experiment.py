from .ablation import run_ablation
from .report import print_ablation
from .validation import validate
from .report import print_validation


def run_experiment(candles, cfg):
    print("\n" + "=" * 60)
    print("AI-XAUUSD-SIGNALS-V1 EXPERIMENT")
    print("=" * 60)

    print("\n[1] TRAIN / TEST VALIDATION")

    validation_result = validate(
        candles,
        cfg,
    )

    print_validation(
        validation_result,
    )

    print("\n[2] ABLATION")

    ablation_result = run_ablation(
        candles,
        cfg,
    )

    print_ablation(
        ablation_result,
    )

    return {
        "validation": validation_result,
        "ablation": ablation_result,
    }
