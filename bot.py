import os
import time
import traceback

from ai_xauusd.config import Config
from ai_xauusd.data import SiftingFeed
from ai_xauusd.candles import CandleBuilder
from ai_xauusd.pipeline import Pipeline


def print_candle(c):
    print(
        f"[M5 CLOSED] "
        f"{c.open_ts.isoformat()} -> {c.close_ts.isoformat()} | "
        f"O={c.open:.2f} "
        f"H={c.high:.2f} "
        f"L={c.low:.2f} "
        f"C={c.close:.2f} "
        f"ticks={c.tick_count}",
        flush=True
    )


def main():
    print("=" * 60, flush=True)
    print("AI-XAUUSD-SIGNALS-V1", flush=True)
    print("LIVE DATA -> TICK -> M5 -> CLOSED CANDLE -> SIGNAL", flush=True)
    print("NO AUTOMATIC ORDERS", flush=True)
    print("=" * 60, flush=True)

    api_key = os.getenv("SIFTING_API_KEY")

    if not api_key:
        raise RuntimeError(
            "SIFTING_API_KEY non configurata nelle Variables di Railway."
        )

    cfg = Config()

    builder = CandleBuilder()
    pipeline = Pipeline(cfg)

    feed = SiftingFeed(
        api_key=api_key,
        product="com",
        symbol="XAUUSD",
    )

    print("[START] Connessione al feed LIVE XAUUSD...", flush=True)

    ticks = 0
    candles = 0

    while True:
        try:
            for tick in feed:
                ticks += 1

                candle = builder.add_tick(tick)

                if candle is None:
                    continue

                candles += 1

                print_candle(candle)

                evaluation = pipeline.on_candle(
                    candle,
                    allow_signal=True,
                )

                if evaluation.signal:
                    s = evaluation.signal

                    print(
                        "\n"
                        "************** SIGNAL **************\n"
                        f"TIME   : {s.ts}\n"
                        f"DIRECTION: {s.direction}\n"
                        f"ENTRY  : {s.entry:.2f}\n"
                        f"SL     : {s.sl:.2f}\n"
                        f"TP     : {s.tp:.2f}\n"
                        f"SCORE  : {s.score:.2f}\n"
                        "************************************\n",
                        flush=True,
                    )
                else:
                    print(
                        f"[EVAL] reason={evaluation.reason}",
                        flush=True,
                    )

                if candles % 10 == 0:
                    print(
                        f"[STATUS] ticks={ticks} M5_closed={candles}",
                        flush=True,
                    )

        except KeyboardInterrupt:
            print("[STOP] Arresto manuale.", flush=True)
            break

        except Exception as exc:
            print(
                f"[ERROR] {type(exc).__name__}: {exc}",
                flush=True,
            )
            traceback.print_exc()

            print(
                "[RECONNECT] Nuovo tentativo tra 5 secondi...",
                flush=True,
            )

            time.sleep(5)

            try:
                feed = SiftingFeed(
                    api_key=api_key,
                    product="com",
                    symbol="XAUUSD",
                )
            except Exception as reconnect_error:
                print(
                    f"[RECONNECT ERROR] {reconnect_error}",
                    flush=True,
                )
                time.sleep(5)


if __name__ == "__main__":
    main()
