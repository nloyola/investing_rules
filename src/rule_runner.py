import yfinance as yf
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD
import json
from datetime import datetime, timedelta
from src.ticker_group import TickerGroup
from typing import List, Callable


class RuleRunner:
    def __init__(self) -> None:
        pass

    def do_work(self, callback: Callable[[str], None]) -> str:
        self.callback = callback
        json_file = "output.json"
        # sector_filter = "energy"
        sector_filter = "health care"

        with open(json_file) as f:
            data = json.load(f)
            groups = [TickerGroup.from_dict(item) for item in data]

        if sector_filter:
            groups = [g for g in groups if g.sector.lower() == sector_filter]
            if not groups:
                callback(f"❌ No groups found for sector: '{sector_filter}'")
                return ""

        html_sections = []
        for group in groups:
            html_sections.append(self.screen_multiple_stocks(group.tickers, group.sector, group.subsector))

        return "".join(html_sections)

    def load_data_batch(self, tickers: List[str]) -> dict:
        data = {}
        self.callback(f"⬇️ Downloading data for {len(tickers)} tickers...")
        df_all = yf.download(tickers, period="90d", interval="1d", group_by="ticker", progress=False)

        print("Downloaded columns:", df_all.columns)
        if isinstance(df_all.columns, pd.MultiIndex):
            print("Downloaded tickers:", df_all.columns.levels[0])
        else:
            print("Downloaded tickers: Not multi-indexed")

        for ticker in tickers:
            try:
                if isinstance(df_all.columns, pd.MultiIndex):
                    if ticker not in df_all.columns.levels[0]:
                        print(f"⚠️ {ticker} not in downloaded data")
                        continue
                    df = df_all[ticker].copy()
                    df.columns = df.columns.get_level_values(0)
                else:
                    df = df_all.copy()
                    if ticker != tickers[0] or "Close" not in df.columns:
                        print(f"⚠️ Skipping {ticker} due to unexpected structure")
                        continue

                if df.empty or "Close" not in df.columns:
                    print(f"⚠️ No data for {ticker}")
                    continue

                data[ticker] = df
            except Exception as e:
                print(f"❌ Error loading {ticker}: {e}")
                continue

        return data

    def check_stock_criteria_from_df(self, ticker: str, df: pd.DataFrame):
        if df.empty or len(df) < 60:
            return {"Ticker": ticker, "Error": "Not enough data"}

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

        try:
            price = df["Close"].iloc[-1]
            volume = df["Volume"].iloc[-1]
            avg_vol = df["volume_avg_20"].iloc[-1]
            dma_50 = df["50dma"].iloc[-1]
            dma_50_prev = df["50dma"].iloc[-15] if len(df) >= 65 else float("nan")
            dma_50_early = df["50dma"].iloc[-25] if len(df) >= 75 else float("nan")
            ema_10 = df["10ema"].iloc[-1]
            high_20d = df["max_20d"].iloc[-2]
            high_60d = df["max_60d"].iloc[-2]
            high_vol_10d = df["max_vol_10d"].iloc[-2]
            rsi_val = rsi.iloc[-1]
            macd_val = macd_line.iloc[-1]
            signal_val = signal_line.iloc[-1]
        except Exception:
            return {"Ticker": ticker, "Error": "Data error during calculation"}

        breakout_20d = bool(price > high_20d)
        breakout_60d = bool(price > high_60d)
        breakout_confirmed = bool(volume >= 1.5 * avg_vol and volume >= high_vol_10d)
        price_above_50dma = bool(price > dma_50)
        price_above_10ema = bool(price > ema_10)
        dma_slope_up = bool(dma_50 > dma_50_prev > dma_50_early)
        rsi_filter = bool(50 < rsi_val < 75)
        macd_bullish = bool(macd_val > signal_val)

        core_criteria = [
            breakout_20d or breakout_60d,
            breakout_confirmed,
            price_above_50dma,
            price_above_10ema,
            dma_slope_up,
        ]

        core_criteria_count = sum(core_criteria)

        return {
            "Ticker": ticker,
            "Price": round(price, 2),
            "Core Criteria Met": all(core_criteria),
            "Core Criteria Score": core_criteria_count,
            "20d High": round(high_20d, 2),
            "60d High": round(high_60d, 2),
            "Volume": int(volume),
            "20d Avg Vol": int(avg_vol),
            "Max Vol (10d)": int(high_vol_10d),
            "50DMA": round(dma_50, 2),
            "10EMA": round(ema_10, 2),
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
        }

    def screen_multiple_stocks(self, tickers, sector, subsector):
        results = []
        data_by_ticker = self.load_data_batch(tickers)
        valid_tickers = data_by_ticker.keys()
        invalid_tickers = []

        for ticker in tickers:
            if ticker not in valid_tickers:
                # results.append({"Ticker": ticker, "Error": "Delisted or no data returned"})
                invalid_tickers.append(ticker)
                continue
            try:
                df = data_by_ticker[ticker]
                result = self.check_stock_criteria_from_df(ticker, df)
                results.append(result)
            except Exception as e:
                # result = {"Ticker": ticker, "Error": str(e)}
                invalid_tickers.append(ticker)

        return json.dumps(results, indent=2)
