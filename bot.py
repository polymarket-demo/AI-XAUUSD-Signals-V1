# ============================================================
# PULLBACK ENGINE V1.1
# Uses candle HIGH/LOW to detect Fibonacci touch
# ============================================================

def check_pullback(trend, fib):

    if fib is None:

        return False, None

    candle = prices[-1]

    candle_high = candle["high"]
    candle_low = candle["low"]
    candle_close = candle["close"]

    levels = [
        ("38.2", fib["fib382"]),
        ("50.0", fib["fib500"]),
        ("61.8", fib["fib618"])
    ]

    closest_name = None
    closest_distance = None
    closest_level = None
    pullback = False

    for name, level in levels:

        # BUY:
        # price must pull back DOWN into Fibonacci zone
        if trend == "BUY":

            distance = abs(
                candle_low - level
            )

            touched = (
                candle_low
                <= level + FIB_TOLERANCE
                and
                candle_high
                >= level - FIB_TOLERANCE
            )

        # SELL:
        # price must pull back UP into Fibonacci zone
        elif trend == "SELL":

            distance = abs(
                candle_high - level
            )

            touched = (
                candle_high
                >= level - FIB_TOLERANCE
                and
                candle_low
                <= level + FIB_TOLERANCE
            )

        else:

            continue

        if (
            closest_distance is None
            or distance < closest_distance
        ):

            closest_distance = distance
            closest_name = name
            closest_level = level

        if touched:

            pullback = True

    print("")
    print("----------------------------------------")
    print("PULLBACK DEBUG")
    print(
        "CANDLE HIGH:",
        round(candle_high, 4)
    )
    print(
        "CANDLE LOW :",
        round(candle_low, 4)
    )
    print(
        "CANDLE CLOSE:",
        round(candle_close, 4)
    )

    if closest_level is not None:

        print(
            "NEAREST FIB:",
            closest_name,
            round(closest_level, 4)
        )

        print(
            "DISTANCE:",
            round(closest_distance, 4)
        )

    print(
        "FIB TOUCHED:",
        "YES" if pullback else "NO"
    )

    print("----------------------------------------")

    return pullback, (
        closest_name,
        closest_level
    )
