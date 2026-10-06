import os
import time
import logging

import pandas as pd
import yfinance as yf


# ============================================================
# AI XAUUSD SIGNALS V1
# MODULE 1 - TREND ENGINE
# ============================================================

SYMBOL = os.getenv("YF_SYMBOL", "GC=F")
INTERVAL = "5m"
PERIOD = "5d"

EMA_FAST = 20
EMA_SLOW = 50
ATR_PERIOD = 14

# Forza minima del trend, misurata rispetto all'ATR.
MIN_TREND_STRENGTH = 0.10

logging.basicConfig(
level=logging.INFO,
format="%(asctime)s | %(levelname)s | %(message)s"
)


def download_data():
logging.info(f"Download dati: {SYMBOL} | {INTERVAL} | {PERIOD}")

data = yf.download(
SYMBOL,
period=PERIOD,
interval=INTERVAL,
auto_adjust=False,
progress=False
)

if data is None or data.empty:
raise RuntimeError("Nessun dato ricevuto da Yahoo Finance.")

# Gestione delle colonne MultiIndex di yfinance
if isinstance(data.columns, pd.MultiIndex):
data.columns = data.columns.get_level_values(0)

required = ["Open", "High", "Low", "Close"]

for column in required:
if column not in data.columns:
raise RuntimeError(f"Colonna mancante: {column}")

return data.dropna(subset=required).copy()


def calculate_indicators(data):
data["EMA20"] = data["Close"].ewm(
span=EMA_FAST,
adjust=False
).mean()

data["EMA50"] = data["Close"].ewm(
span=EMA_SLOW,
adjust=False
).mean()

previous_close = data["Close"].shift(1)

true_range = pd.concat(
[
data["High"] - data["Low"],
(data["High"] - previous_close).abs(),
(data["Low"] - previous_close).abs()
],
axis=1
).max(axis=1)

data["ATR14"] = true_range.rolling(ATR_PERIOD).mean()

data["EMA20_Slope"] = data["EMA20"].diff()

# Distanza tra EMA20 ed EMA50 rapportata alla volatilità
data["TrendStrength"] = (
(data["EMA20"] - data["EMA50"]).abs()
/ data["ATR14"]
)

return data


def evaluate_trend(row):
if pd.isna(row["EMA20"]) or pd.isna(row["EMA50"]):
return "NEUTRAL", "INSUFFICIENT_DATA"

if pd.isna(row["ATR14"]) or row["ATR14"] <= 0:
return "NEUTRAL", "INVALID_ATR"

strength = row["TrendStrength"]
slope = row["EMA20_Slope"]

if row["EMA20"] > row["EMA50"]:
if strength < MIN_TREND_STRENGTH:
return "NEUTRAL", "BUY_TOO_WEAK"

if slope < 0:
return "BUY_WEAKENING", "EMA20_SLOPE_DOWN"

return "BUY", "TREND_UP"

if row["EMA20"] < row["EMA50"]:
if strength < MIN_TREND_STRENGTH:
return "NEUTRAL", "SELL_TOO_WEAK"

if slope > 0:
return "SELL_WEAKENING", "EMA20_SLOPE_UP"

return "SELL", "TREND_DOWN"

return "NEUTRAL", "EMA_EQUAL"


def main():
data = download_data()
data = calculate_indicators(data)

latest = data.iloc[-1]

trend, reason = evaluate_trend(latest)

print()
print("=" * 60)
print("AI XAUUSD SIGNALS V1")
print("MODULE 1 - TREND ENGINE")
print("=" * 60)

print(f"Symbol : {SYMBOL}")
print(f"Timeframe : {INTERVAL}")
print(f"Price : {latest['Close']:.2f}")
print(f"EMA20 : {latest['EMA20']:.2f}")
print(f"EMA50 : {latest['EMA50']:.2f}")
print(f"ATR14 : {latest['ATR14']:.2f}")
print(f"TrendStrength: {latest['TrendStrength']:.3f}")
print(f"TREND : {trend}")
print(f"REASON : {reason}")

print("=" * 60)

print()
print("ULTIME 5 CANDLE")
print("-" * 60)

columns = [
"Close",
"EMA20",
"EMA50",
"ATR14",
"TrendStrength",
"EMA20_Slope"
]

print(data[columns].tail(5).round(3).to_string())

print()
print("Nessun trade viene eseguito.")
print("Questo modulo serve solo a leggere il trend.")
print()

# Mantiene il processo vivo su Railway.
# Aggiorna il risultato ogni 5 minuti circa.
time.sleep(300)


if __name__ == "__main__":
while True:
try:
main()
except Exception as error:
logging.exception(f"ERRORE: {error}")
time.sleep(60)
