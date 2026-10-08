from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from ai_xauusd.models import Tick, Candle
from ai_xauusd.candles import CandleBuilder
from ai_xauusd.config import Config
from ai_xauusd.tracker import Tracker
from ai_xauusd.pipeline import Signal, Pipeline
from ai_xauusd.runner import Runner
from ai_xauusd import engines as E
from ai_xauusd.stats import verdict
from ai_xauusd.benchmark import random_baseline
from ai_xauusd.synth import make_candles

T0 = datetime(2025, 1, 6, 10, 0, tzinfo=timezone.utc)
M5 = timedelta(minutes=5)


def mk(i, o, h, l, c, t0=T0):
    return Candle(t0 + i * M5, t0 + (i + 1) * M5, o, h, l, c, 1)


def test_candle_no_lookahead():
    b = CandleBuilder()
    assert b.add_tick(Tick(T0, 99.9, 100.1)) is None
    assert b.add_tick(Tick(T0 + timedelta(minutes=4, seconds=59), 104.9, 105.1)) is None
    c = b.add_tick(Tick(T0 + timedelta(minutes=5), 101.9, 102.1))
    assert c and c.open == 100 and c.high == 105 and c.close == 105 and c.tick_count == 2


def mk_sig(d="BUY"):
    return Signal(T0, d, 100, 98 if d == "BUY" else 102, 104 if d == "BUY" else 96, 2, 4, 2, 80, "HIGH",
                  "BUY", "", "", "", "", "", dict(market="TRENDING", vol="NORMAL_VOL", session="LONDON"), "k", 1.0)


def test_tracker_sl_first_when_both():
    tr = Tracker(Config()); tr.open_trade(mk_sig())
    r = tr.on_candle(mk(1, 100, 105, 97, 101))
    assert r.outcome == "LOSS" and r.r < 0


def test_tracker_win_sell():
    tr = Tracker(Config()); tr.open_trade(mk_sig("SELL"))
    r = tr.on_candle(mk(1, 100, 100.5, 95, 96))
    assert r.outcome == "WIN" and r.r > 0


def test_tracker_gap_exit_at_open():
    tr = Tracker(Config()); tr.last_ts = T0; tr.open_trade(mk_sig())
    r = tr.on_candle(mk(1, 90, 91, 89, 90, t0=T0 + timedelta(days=3)))   # weekend gap sotto lo SL
    assert r.outcome == "GAP" and r.exit < 90.5 and r.r < -1


def _leg_window():
    w = [mk(i, 100, 100.2, 99.8, 100) for i in range(20)]
    for k in range(1, 6):
        w.append(mk(19 + k, 100 + 2 * (k - 1), 100 + 2 * k + .1, 100 + 2 * (k - 1) - .1, 100 + 2 * k))
    for k, cl in enumerate((108, 106.5, 105)):
        w.append(mk(25 + k, cl + .7, cl + .8, cl - .2, cl))
    return w


def test_engines_buy_setup():
    cfg, w = Config(), _leg_window()
    m = E.momentum_engine(w, 1.0, 1, cfg); assert m["valid"] and m["size_atr"] > 9
    f = E.fibonacci_engine(w[-1].close, m, 1.0, cfg); assert f["valid"] and abs(f["depth"] - 0.495) < 0.02
    p = E.pullback_engine(w, m, f["depth"], 100.0, 1.0, cfg); assert p["valid"] and p["type"] == "NORMAL"
    w[-1] = mk(27, 99.5, 99.6, 98.9, 99.0)                      # chiude sotto l'inizio dell'impulso
    f2 = E.fibonacci_engine(99.0, m, 1.0, cfg); assert not f2["valid"]
    p2 = E.pullback_engine(w, m, f2["depth"], 100.0, 1.0, cfg)
    assert not p2["valid"] and "BROKE_IMPULSE_START" in p2["type"]


def test_gap_resets_window():
    p = Pipeline(Config())
    for c in make_candles(60, 1): p.on_candle(c)
    last = p.candles[-1]
    p.on_candle(mk(0, 100, 101, 99, 100, t0=last.close_ts + timedelta(days=2)))
    assert len(p.candles) == 1


def test_pipeline_is_causal():
    cs = make_candles(6000, 3)
    a, b = Runner(Config(), "A"), Runner(Config(), "B")
    sa, sb = [], []
    a.on_signal = lambda s: sa.append((s.ts, s.entry, s.sl, s.tp))
    b.on_signal = lambda s: sb.append((s.ts, s.entry, s.sl, s.tp))
    for c in cs[:3000]: a.on_candle(c)
    for c in cs: b.on_candle(c)
    cut = cs[2999].close_ts
    assert sa == [x for x in sb if x[0] <= cut] and len(sa) > 0, "il futuro cambia il passato: look-ahead!"


def test_verdict():
    assert "NON LO SAPPIAMO" in verdict([1.0] * 10)["verdict"]
    assert "POSSIBILE EDGE" in verdict([1.0, -0.5] * 150)["verdict"]
    assert "NESSUNA" in verdict([1.0, -1.0] * 150)["verdict"]


def test_benchmark_runs():
    cs = make_candles(3000, 5)
    b = random_baseline(Config(), cs, 20, 1.5, "trend", runs=5)
    assert b["runs"] == 5 and b["p5"] <= b["p95"]




def test_sifting_parse():
    from ai_xauusd.data import SiftingFeed
    t = SiftingFeed.parse({"p": "2650.5", "t": 1736157600000, "b": 2650.4, "a": 2650.6}, 1736157600120)
    assert t.bid == 2650.4 and t.ask == 2650.6 and t.latency_ms == 120 and t.ts.year == 2025
    t2 = SiftingFeed.parse({"p": 2650.5, "t": 1736157600000})            # senza bid/ask
    assert t2.mid == 2650.5 and t2.spread == 0
    assert SiftingFeed.parse({"x": 1}) is None


def test_candles_persist_and_warmup():
    from ai_xauusd.logger import DbLogger
    log = DbLogger(":memory:")
    cs = make_candles(120, 2)
    for c in cs: log.candle(c)
    back = log.recent_candles(100)
    assert len(back) == 100 and back[-1].close == cs[-1].close and back[0].open_ts == cs[20].open_ts
    r = Runner(Config(), "W"); r.warmup(back)
    assert r.pipe.ema_s.value is not None and r.trades == [] and r.tracker.open is None


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"): f(); print("OK", n)
