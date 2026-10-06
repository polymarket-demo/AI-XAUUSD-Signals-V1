import yfinance as yf

data = yf.download(
    "GC=F",
    period="5d",
    interval="5m",
    progress=False
)

if data.empty:
    print("ERRORE: nessun dato")
else:
    close = data["Close"]

    ema20 = close.ewm(span=20).mean().iloc[-1]
    ema50 = close.ewm(span=50).mean().iloc[-1]
    price = close.iloc[-1]

    if ema20 > ema50:
        trend = "BUY"
    elif ema20 < ema50:
        trend = "SELL"
    else:
        trend = "NEUTRAL"

    print("==============================")
    print("AI XAUUSD SIGNALS V1")
    print("TREND ENGINE")
    print("==============================")
    print("PRICE:", round(float(price), 2))
    print("EMA20:", round(float(ema20), 2))
    print("EMA50:", round(float(ema50), 2))
    print("TREND:", trend)
    print("==============================")
