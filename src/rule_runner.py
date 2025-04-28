import yfinance as yf
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD
import os
import json
import io
from datetime import datetime, timedelta
import webbrowser
import tempfile
import argparse
from src.base_command import BaseCommand
from rich.console import Console
from src.ticker_group import TickerGroup
from typing import List


console = Console()


class RuleRunnerCommand(BaseCommand):
    _NAME = "rule-runner"
    _DESCRIPTION = "runs the rules on ticker symbols in a JSON file"

    _DATA_DIR = "stock_data"

    def __init__(self) -> None:
        super().__init__(self._NAME, self._DESCRIPTION)
        os.makedirs(self._DATA_DIR, exist_ok=True)

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--json", help="use the stock tickers from the JSON file")

    def handle(self, args: argparse.Namespace) -> None:
        json_file = args.json
        with open(json_file) as f:
            data = json.load(f)
            groups = [TickerGroup.from_dict(item) for item in data]
            console.print(f"ticker groups {groups[0]}\n", style="orange1")
            self.screen_multiple_stocks(groups[0].tickers)

    def get_delisted_tickers(self, tickers: List[str]):
        delisted = []
        for ticker in tickers:
            try:
                df = yf.download(ticker, period="1d")
                if df.empty or "Close" not in df.columns:
                    delisted.append(ticker)
            except Exception:
                delisted.append(ticker)
        return delisted

    def load_or_download_data(self, ticker: str, max_age_days: int = 1) -> pd.DataFrame:
        file_path = os.path.join(self._DATA_DIR, f"{ticker}.json")

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

    def check_stock_criteria(self, ticker: str):
        df = self.load_or_download_data(ticker)
        if df.empty or len(df) < 60:
            return {
                "Ticker": ticker,
                "Error": "Not enough data",
                "Available Columns": ", ".join(df.columns),
            }

        df["50dma"] = df["Close"].rolling(window=50).mean()
        df["10ema"] = df["Close"].ewm(span=10).mean()
        df["volume_avg_20"] = df["Volume"].rolling(window=20).mean()
        df["max_20d"] = df["Close"].rolling(window=20).max()
        df["max_60d"] = df["Close"].rolling(window=60).max()
        df["max_vol_10d"] = df["Volume"].rolling(window=10).max()

        close_series = df["Close"].squeeze()
        rsi = RSIIndicator(close=close_series).rsi()
        macd_calc = MACD(close=close_series)
        macd_line = macd_calc.macd()
        signal_line = macd_calc.macd_signal()

        price = df["Close"].iloc[-1].item()
        volume = df["Volume"].iloc[-1].item()
        avg_vol = df["volume_avg_20"].iloc[-1].item()
        dma_50 = df["50dma"].iloc[-1].item()

        dma_50_prev = df["50dma"].iloc[-15] if len(df) >= 65 else float("nan")
        dma_50_early = df["50dma"].iloc[-25] if len(df) >= 75 else float("nan")

        ema_10 = df["10ema"].iloc[-1].item()
        high_20d = df["max_20d"].iloc[-2].item()
        high_60d = df["max_60d"].iloc[-2].item()
        high_vol_10d = df["max_vol_10d"].iloc[-2].item()
        rsi_val = rsi.iloc[-1].item()
        macd_val = macd_line.iloc[-1].item()
        signal_val = signal_line.iloc[-1].item()

        # Main breakout checks
        breakout_20d = price > high_20d
        breakout_60d = price > high_60d
        breakout_confirmed = volume >= 1.5 * avg_vol and volume >= high_vol_10d
        price_above_50dma = price > dma_50
        price_above_10ema = price > ema_10
        dma_slope_up = dma_50 > dma_50_prev and dma_50_prev > dma_50_early
        rsi_filter = 50 < rsi_val < 75
        macd_bullish = macd_val > signal_val

        core_conditions_met = all(
            [
                breakout_20d or breakout_60d,
                breakout_confirmed,
                price_above_50dma,
                price_above_10ema,
                dma_slope_up,
            ]
        )

        return {
            "Ticker": ticker,
            "Price": round(price, 2),
            "20d High": round(high_20d, 2),
            "60d High": round(high_60d, 2),
            "Volume": int(volume),
            "20d Avg Vol": int(avg_vol),
            "Max Vol (10d)": int(high_vol_10d),
            "50DMA": round(dma_50, 2),
            "10EMA": round(ema_10, 2),
            "50DMA Prev (15d)": round(dma_50_prev, 2) if pd.notna(dma_50_prev) else None,
            "50DMA (25d ago)": round(dma_50_early, 2) if pd.notna(dma_50_early) else None,
            "RSI": round(rsi_val, 2),
            "MACD": round(macd_val, 2),
            "Signal": round(signal_val, 2),
            "Breakout 20d": breakout_20d,
            "Breakout 60d": breakout_60d,
            "Breakout Confirmed": breakout_confirmed,
            "Price > 50DMA": price_above_50dma,
            "Price > 10EMA": price_above_10ema,
            "50DMA Rising": dma_slope_up,
            "RSI 50-75": rsi_filter,
            "MACD Bullish": macd_bullish,
            "Core Criteria Met": core_conditions_met,
        }

    def screen_multiple_stocks(self, tickers):
        results = []

        delisted = self.get_delisted_tickers(tickers)
        if delisted:
            print("⚠️ Delisted tickers excluded:", ", ".join(delisted))
        tickers = [t for t in tickers if t not in delisted]

        for ticker in tickers:
            try:
                result = self.check_stock_criteria(ticker)
                if not isinstance(result, dict):
                    result = {"Ticker": ticker, "Error": str(result)}
                results.append(result)
            except Exception as e:
                try:
                    df = self.load_or_download_data(ticker)
                    columns = ", ".join(df.columns)
                except Exception:
                    columns = "Unavailable"
                results.append({"Ticker": ticker, "Error": str(e), "Available Columns": columns})

        if not results:
            print("No results to display.")
            return

        df = pd.DataFrame(results)

        table_html = df.to_html(
            index=False,
            escape=False,
            border=0,
            classes="table-auto w-full text-sm text-gray-700",
        )

        # Inject Tailwind classes
        table_html = (
            table_html.replace("<table", '<table class="table-auto w-full border-collapse text-sm text-gray-700"')
            .replace("<thead>", '<thead class="bg-gray-100 text-left font-semibold">')
            .replace("<th>", '<th class="px-4 py-2 whitespace-nowrap border-b border-gray-200">')
            .replace("<td>", '<td class="px-4 py-2 border-t border-gray-200 align-top">')
        )

        html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Stock Screening Results</title>
      <script src="https://cdn.tailwindcss.com"></script>
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

        with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8") as f:
            f.write(html)
            temp_path = f.name

        print(f"✅ Styled HTML saved to: {temp_path}")
        webbrowser.open(f"file://{os.path.abspath(temp_path)}")
