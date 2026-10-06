import yfinance as yf
import pandas as pd

# ==============================
# AI XAUUSD SIGNALS V1
# ==============================

data = yf.download(
    "GC=F",
    period="5d",
    interval="5m",
    progress=False
)

if data.empty:
    print("ERRORE: nessun dato")
    exit()

# ==============================
# DATI OHLC
# ==============================

if hasattr(data.columns, "levels"):
    close = data["Close"].iloc[:, 0]
    high = data["High"].iloc[:, 0]
    low = data["Low"].iloc[:, 0]
else:
    close = data["Close"]
    high = data["High"]
    low = data["Low"]

close = pd.to_numeric(close)
high = pd.to_numeric(high)
low = pd.to_numeric(low)

# ==============================
# INDICATORI
# ==============================

ema20 = close.ewm(span=20, adjust=False).mean()
ema50 = close.ewm(span=50, adjust=False).mean()

previous_close = close.shift(1)

tr1 = high - low
tr2 = (high - previous_close).abs()
tr3 = (low - previous_close).abs()

true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
atr14 = true_range.rolling(14).mean()

# ==============================
# VALORI ATTUALI
# ==============================

price = float(close.iloc[-1])
e20 = float(ema20.iloc[-1])
e50 = float(ema50.iloc[-1])
atr = float(atr14.iloc[-1])

ema_distance = abs(e20 - e50)

if atr > 0:
    trend_strength = ema_distance / atr
else:
    trend_strength = 0

ema20_slope = float(ema20.iloc[-1] - ema20.iloc[-4])

# ==============================
# TREND
# ==============================

if e20 > e50:
    trend = "BUY"
elif e20 < e50:
    trend = "SELL"
else:
    trend = "NEUTRAL"

# ==============================
# FORZA TREND
# ==============================

if trend_strength < 0.10:
    strength = "VERY WEAK"
elif trend_strength < 0.25:
    strength = "WEAK"
elif trend_strength < 0.50:
    strength = "MEDIUM"
else:
    strength = "STRONG"

# ==============================
# FINE TREND
# ==============================

trend_status = trend

if trend == "BUY" and ema20_slope < 0:
    trend_status = "BUY_WEAKENING"

elif trend == "SELL" and ema20_slope > 0:
    trend_status = "SELL_WEAKENING"

# ==============================
# IMPULSO
# ==============================

lookback = 3

move = price - float(close.iloc[-1 - lookback])

if atr > 0:
    impulse_strength = abs(move) / atr
else:
    impulse_strength = 0

if move > 0:
    impulse = "BUY"
elif move < 0:
    impulse = "SELL"
else:
    impulse = "NEUTRAL"

# ==============================
# SWING
# ==============================

swing_window = 12

recent_high = float(high.iloc[-swing_window:].max())
recent_low = float(low.iloc[-swing_window:].min())

swing_range = recent_high - recent_low

# ==============================
# FIBONACCI
# ==============================

if trend == "BUY":
    fib_382 = recent_high - swing_range * 0.382
    fib_500 = recent_high - swing_range * 0.500
    fib_618 = recent_high - swing_range * 0.618

    fib_position = (
        (recent_high - price) / swing_range
        if swing_range > 0 else 0
    )

else:
    fib_382 = recent_low + swing_range * 0.382
    fib_500 = recent_low + swing_range * 0.500
    fib_618 = recent_low + swing_range * 0.618

    fib_position = (
        (price - recent_low) / swing_range
        if swing_range > 0 else 0
    )

# ==============================
# PULLBACK
# ==============================

pullback = False

if trend == "BUY":
    if fib_382 <= price <= recent_high:
        pullback = True

elif trend == "SELL":
    if recent_low <= price <= fib_382:
        pullback = True

# ==============================
# CONFERMA CANDLE
# ==============================

last_open = float(
    data["Open"].iloc[-1, 0]
    if hasattr(data["Open"], "iloc") and len(data["Open"].shape) > 1
    else data["Open"].iloc[-1]
)

last_close = price

if last_close > last_open:
    candle_direction = "BUY"
elif last_close < last_open:
    candle_direction = "SELL"
else:
    candle_direction = "NEUTRAL"

confirmation = False

if trend == "BUY" and candle_direction == "BUY":
    confirmation = True

elif trend == "SELL" and candle_direction == "SELL":
    confirmation = True

# ==============================
# SIGNAL
# ==============================

signal = "NO SIGNAL"
reason = "Conditions not complete"

if trend_status in ["BUY", "SELL"]:
    
    if strength in ["MEDIUM", "STRONG"]:
        
        if impulse == trend:
            
            if pullback:
                
                if confirmation:
                    signal = trend
                    reason = "Trend + Impulse + Pullback + Confirmation"

# ==============================
# ENTRY / SL / TP
# ==============================

entry = price
sl = None
tp = None

if signal == "BUY":

    structure_sl = recent_low
    atr_sl = entry - atr * 1.0

    sl = min(structure_sl, atr_sl)

    risk = entry - sl

    if risk > 0:
        tp = entry + risk * 2.0

elif signal == "SELL":

    structure_sl = recent_high
    atr_sl = entry + atr * 1.0

    sl = max(structure_sl, atr_sl)

    risk = sl - entry

    if risk > 0:
        tp = entry - risk * 2.0

# ==============================
# OUTPUT
# ==============================

print("")
print("==============================")
print("AI XAUUSD SIGNALS V1")
print("==============================")

print("PRICE:", round(price, 2))
print("EMA20:", round(e20, 2))
print("EMA50:", round(e50, 2))
print("ATR14:", round(atr, 2))

print("------------------------------")

print("TREND:", trend)
print("TREND STRENGTH:", strength)
print("STRENGTH VALUE:", round(trend_strength, 3))
print("TREND STATUS:", trend_status)

print("------------------------------")

print("IMPULSE:", impulse)
print("IMPULSE STRENGTH:", round(impulse_strength, 3))

print("------------------------------")

print("SWING HIGH:", round(recent_high, 2))
print("SWING LOW:", round(recent_low, 2))

print("FIB 38.2:", round(fib_382, 2))
print("FIB 50.0:", round(fib_500, 2))
print("FIB 61.8:", round(fib_618, 2))

print("PULLBACK:", pullback)

print("------------------------------")

print("CANDLE:", candle_direction)
print("CONFIRMATION:", confirmation)

print("------------------------------")

print("SIGNAL:", signal)
print("REASON:", reason)

if sl is not None:
    print("ENTRY:", round(entry, 2))
    print("SL:", round(sl, 2))
    print("TP:", round(tp, 2))

print("==============================")
