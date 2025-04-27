import yfinance as yf
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD
import os
import json
import io
from datetime import datetime, timedelta
import sys
import webbrowser
import tempfile

DATA_DIR = "stock_data"
os.makedirs(DATA_DIR, exist_ok=True)


def load_tickers_from_file(filename="tickers.txt"):
    with open(filename, "r") as f:
        tickers = [line.strip() for line in f if line.strip()]
    return tickers


def get_delisted_tickers(tickers):
    delisted = []
    for ticker in tickers:
        try:
            df = yf.download(ticker, period="1d")
            if df.empty or "Close" not in df.columns:
                delisted.append(ticker)
        except Exception:
            delisted.append(ticker)
    return delisted


def load_or_download_data(ticker: str, max_age_days: int = 1) -> pd.DataFrame:
    file_path = os.path.join(DATA_DIR, f"{ticker}.json")

    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            raw = json.load(f)
            timestamp = datetime.fromisoformat(raw["timestamp"])
            if datetime.now() - timestamp < timedelta(days=max_age_days):
                print(f"📦 Using cached data for {ticker}")
                df = pd.read_json(io.StringIO(raw["data"]), convert_dates=True)
                df.index = pd.to_datetime(df.index)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                return df

    print(f"⬇️  Downloading new data for {ticker}")
    df = yf.download(ticker, period="90d", interval="1d")
    if df.empty or "Close" not in df.columns:
        raise ValueError(f"No valid price data found for {ticker}")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df_json = df.to_json(date_format="iso")
    with open(file_path, "w") as f:
        json.dump({"timestamp": datetime.now().isoformat(), "data": df_json}, f)
    return df


def check_stock_criteria(ticker: str):
    df = load_or_download_data(ticker)
    if df.empty or len(df) < 60:
        return {
            "Ticker": ticker,
            "Error": "Not enough data",
            "Available Columns": ", ".join(df.columns),
        }

    df["50dma"] = df["Close"].rolling(window=50).mean()
    df["volume_avg_20"] = df["Volume"].rolling(window=20).mean()

    close_series = df["Close"].squeeze()

    rsi = RSIIndicator(close=close_series).rsi()
    macd_calc = MACD(close=close_series)
    macd_line = macd_calc.macd()
    signal_line = macd_calc.macd_signal()

    price = df["Close"].iloc[-1].item()
    volume = df["Volume"].iloc[-1].item()
    avg_vol = df["volume_avg_20"].iloc[-1].item()
    dma_50 = df["50dma"].iloc[-1].item()
    dma_50_prev = df["50dma"].iloc[-15].item()
    recent_high = df["Close"].rolling(window=60).max().iloc[-2].item()
    rsi_val = rsi.iloc[-1].item()
    macd_val = macd_line.iloc[-1].item()
    signal_val = signal_line.iloc[-1].item()

    is_breakout = price > recent_high
    breakout_volume_confirmed = volume > 1.5 * avg_vol
    price_above_50dma = price > dma_50
    dma_slope = dma_50 > dma_50_prev
    rsi_good = 50 < rsi_val < 70
    macd_bullish = macd_val > signal_val

    core_conditions_met = all(
        [is_breakout, breakout_volume_confirmed, price_above_50dma, dma_slope]
    )

    return {
        "Ticker": ticker,
        "Price": round(price, 2),
        "60d High": round(recent_high, 2),
        "Volume": int(volume),
        "20d Avg Vol": int(avg_vol),
        "50DMA": round(dma_50, 2),
        "50DMA Prev (15d ago)": round(dma_50_prev, 2),
        "RSI": round(rsi_val, 2),
        "MACD": round(macd_val, 2),
        "Signal": round(signal_val, 2),
        "Breakout": is_breakout,
        "Vol Spike": breakout_volume_confirmed,
        "Price > 50DMA": price_above_50dma,
        "50DMA Up": dma_slope,
        "RSI 50-70": rsi_good,
        "MACD Bullish": macd_bullish,
        "Core Criteria Met": core_conditions_met,
    }


def screen_multiple_stocks(tickers):
    results = []

    delisted = get_delisted_tickers(tickers)
    if delisted:
        print("⚠️ Delisted tickers excluded:", ", ".join(delisted))
    tickers = [t for t in tickers if t not in delisted]

    for ticker in tickers:
        try:
            result = check_stock_criteria(ticker)
            if not isinstance(result, dict):
                result = {"Ticker": ticker, "Error": str(result)}
            results.append(result)
        except Exception as e:
            try:
                df = load_or_download_data(ticker)
                columns = ", ".join(df.columns)
            except Exception:
                columns = "Unavailable"
            results.append(
                {"Ticker": ticker, "Error": str(e), "Available Columns": columns}
            )

    if not results:
        print("No results to display.")
        return

    preferred_columns = [
        "Ticker",
        "Price",
        "60d High",
        "Volume",
        "20d Avg Vol",
        "50DMA",
        "50DMA Prev (15d ago)",
        "RSI",
        "MACD",
        "Signal",
        "Breakout",
        "Vol Spike",
        "Price > 50DMA",
        "50DMA Up",
        "RSI 50-70",
        "MACD Bullish",
        "Core Criteria Met",
    ]

    df = pd.DataFrame(results)

    for col in preferred_columns:
        if col not in df.columns:
            df[col] = ""

    all_columns = preferred_columns + [
        col for col in df.columns if col not in preferred_columns
    ]
    df = df[all_columns]

    table_html = df.to_html(
        index=False,
        escape=False,
        border=0,
        classes="table-auto w-full text-sm text-gray-700",
    )

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Stock Screening Results</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    thead th {{
      @apply text-left font-semibold text-gray-700 bg-gray-100 px-4 py-2;
    }}
    tbody td {{
      @apply px-4 py-2 align-top border-t;
    }}
    table {{
      @apply border-collapse w-full;
    }}
  </style>
</head>
<body class="bg-gray-50 text-gray-900 p-8">
  <div class="max-w-screen-2xl mx-auto">
    <h1 class="text-3xl font-bold mb-6">📊 Stock Screening Results</h1>
    <div class="overflow-auto rounded shadow bg-white p-4 border border-gray-200">
      {table_html}
    </div>
  </div>
</body>
</html>
"""

    with tempfile.NamedTemporaryFile(
        delete=False, suffix=".html", mode="w", encoding="utf-8"
    ) as f:
        f.write(html)
        temp_path = f.name

    print(f"✅ Styled HTML saved to: {temp_path}")
    webbrowser.open(f"file://{os.path.abspath(temp_path)}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script_name.py <ticker_file.txt>")
        sys.exit(1)

    ticker_file = sys.argv[1]
    tickers = load_tickers_from_file(ticker_file)
    screen_multiple_stocks(tickers)
