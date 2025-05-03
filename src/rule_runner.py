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
    _YAHOO_CHART_HASH = "#eyJsYXlvdXQiOnsiaW50ZXJ2YWwiOiJkYXkiLCJwZXJpb2RpY2l0eSI6MSwidGltZVVuaXQiOm51bGwsImNhbmRsZVdpZHRoIjoxOS4zMTc0NjAzMTc0NjAzMTYsImZsaXBwZWQiOmZhbHNlLCJ2b2x1bWVVbmRlcmxheSI6dHJ1ZSwiYWRqIjp0cnVlLCJjcm9zc2hhaXIiOnRydWUsImNoYXJ0VHlwZSI6ImNhbmRsZSIsImV4dGVuZGVkIjpmYWxzZSwibWFya2V0U2Vzc2lvbnMiOnt9LCJhZ2dyZWdhdGlvblR5cGUiOiJvaGxjIiwiY2hhcnRTY2FsZSI6ImxpbmVhciIsInN0dWRpZXMiOnsi4oCMdm9sIHVuZHLigIwiOnsidHlwZSI6InZvbCB1bmRyIiwiaW5wdXRzIjp7IlNlcmllcyI6InNlcmllcyIsImlkIjoi4oCMdm9sIHVuZHLigIwiLCJkaXNwbGF5Ijoi4oCMdm9sIHVuZHLigIwifSwib3V0cHV0cyI6eyJVcCBWb2x1bWUiOiIjMGRiZDZlZWUiLCJEb3duIFZvbHVtZSI6IiNmZjU1NDdlZSJ9LCJwYW5lbCI6ImNoYXJ0IiwicGFyYW1ldGVycyI6eyJjaGFydE5hbWUiOiJjaGFydCIsImVkaXRNb2RlIjp0cnVlLCJwYW5lbE5hbWUiOiJjaGFydCJ9LCJkaXNhYmxlZCI6ZmFsc2V9LCLigIxtYeKAjCAoMTAwLG1hLDApIjp7InR5cGUiOiJtYSIsImlucHV0cyI6eyJQZXJpb2QiOiIxMDAiLCJGaWVsZCI6ImZpZWxkIiwiVHlwZSI6Im1hIiwiT2Zmc2V0IjowLCJpZCI6IuKAjG1h4oCMICgxMDAsbWEsMCkiLCJkaXNwbGF5Ijoi4oCMbWHigIwgKDEwMCxtYSwwKSJ9LCJvdXRwdXRzIjp7Ik1BIjp7ImNvbG9yIjoiIzAwYWZlZCJ9fSwicGFuZWwiOiJjaGFydCIsInBhcmFtZXRlcnMiOnsiY2hhcnROYW1lIjoiY2hhcnQiLCJlZGl0TW9kZSI6dHJ1ZSwicGFuZWxOYW1lIjoiY2hhcnQifSwiZGlzYWJsZWQiOmZhbHNlfSwi4oCMbWHigIwgKDIwMCxtYSwwKSI6eyJ0eXBlIjoibWEiLCJpbnB1dHMiOnsiUGVyaW9kIjoiMjAwIiwiRmllbGQiOiJmaWVsZCIsIlR5cGUiOiJtYSIsIk9mZnNldCI6MCwiaWQiOiLigIxtYeKAjCAoMjAwLG1hLDApIiwiZGlzcGxheSI6IuKAjG1h4oCMICgyMDAsbWEsMCkifSwib3V0cHV0cyI6eyJNQSI6eyJjb2xvciI6IiMwMDcyMzgifX0sInBhbmVsIjoiY2hhcnQiLCJwYXJhbWV0ZXJzIjp7ImNoYXJ0TmFtZSI6ImNoYXJ0IiwiZWRpdE1vZGUiOnRydWUsInBhbmVsTmFtZSI6ImNoYXJ0In0sImRpc2FibGVkIjpmYWxzZX0sIuKAjG1h4oCMICg1MCxtYSwwKS0yIjp7InR5cGUiOiJtYSIsImlucHV0cyI6eyJQZXJpb2QiOjUwLCJGaWVsZCI6ImZpZWxkIiwiVHlwZSI6Im1hIiwiT2Zmc2V0IjowLCJpZCI6IuKAjG1h4oCMICg1MCxtYSwwKS0yIiwiZGlzcGxheSI6IuKAjG1h4oCMICg1MCxtYSwwKS0yIn0sIm91dHB1dHMiOnsiTUEiOiIjRkYwMDAwIn0sInBhbmVsIjoiY2hhcnQiLCJwYXJhbWV0ZXJzIjp7ImNoYXJ0TmFtZSI6ImNoYXJ0IiwiZWRpdE1vZGUiOnRydWUsInBhbmVsTmFtZSI6ImNoYXJ0In0sImRpc2FibGVkIjpmYWxzZX0sIuKAjHJzaeKAjCAoMTQpLTIiOnsidHlwZSI6InJzaSIsImlucHV0cyI6eyJQZXJpb2QiOjE0LCJGaWVsZCI6ImZpZWxkIiwiaWQiOiLigIxyc2nigIwgKDE0KS0yIiwiZGlzcGxheSI6IuKAjHJzaeKAjCAoMTQpLTIifSwib3V0cHV0cyI6eyJSU0kiOiJhdXRvIn0sInBhbmVsIjoi4oCMcnNp4oCMICgxNCktMiIsInBhcmFtZXRlcnMiOnsic3R1ZHlPdmVyWm9uZXNFbmFibGVkIjp0cnVlLCJzdHVkeU92ZXJCb3VnaHRWYWx1ZSI6ODAsInN0dWR5T3ZlckJvdWdodENvbG9yIjoiYXV0byIsInN0dWR5T3ZlclNvbGRWYWx1ZSI6MjAsInN0dWR5T3ZlclNvbGRDb2xvciI6ImF1dG8iLCJjaGFydE5hbWUiOiJjaGFydCIsImVkaXRNb2RlIjp0cnVlLCJwYW5lbE5hbWUiOiLigIxyc2nigIwgKDE0KS0yIn0sImRpc2FibGVkIjpmYWxzZX0sIuKAjG1h4oCMICgxMCxlbWEsMCkiOnsidHlwZSI6Im1hIiwiaW5wdXRzIjp7IlBlcmlvZCI6IjEwIiwiRmllbGQiOiJmaWVsZCIsIlR5cGUiOiJleHBvbmVudGlhbCIsIk9mZnNldCI6MCwiaWQiOiLigIxtYeKAjCAoMTAsZW1hLDApIiwiZGlzcGxheSI6IuKAjG1h4oCMICgxMCxlbWEsMCkifSwib3V0cHV0cyI6eyJNQSI6eyJjb2xvciI6IiM4NTYxYTcifX0sInBhbmVsIjoiY2hhcnQiLCJwYXJhbWV0ZXJzIjp7ImNoYXJ0TmFtZSI6ImNoYXJ0IiwiZWRpdE1vZGUiOnRydWV9LCJkaXNhYmxlZCI6ZmFsc2V9fSwicGFuZWxzIjp7ImNoYXJ0Ijp7InBlcmNlbnQiOjAuNzYxOTA0NzYxOTA0NzYyLCJkaXNwbGF5IjoiTlZTIiwiY2hhcnROYW1lIjoiY2hhcnQiLCJpbmRleCI6MCwieUF4aXMiOnsibmFtZSI6ImNoYXJ0IiwicG9zaXRpb24iOm51bGx9LCJ5YXhpc0xIUyI6W10sInlheGlzUkhTIjpbImNoYXJ0Iiwi4oCMdm9sIHVuZHLigIwiXX0sIuKAjHJzaeKAjCAoMTQpLTIiOnsicGVyY2VudCI6MC4yMzgwOTUyMzgwOTUyMzgwNSwiZGlzcGxheSI6IuKAjHJzaeKAjCAoMTQpLTIiLCJjaGFydE5hbWUiOiJjaGFydCIsImluZGV4IjoxLCJ5QXhpcyI6eyJuYW1lIjoi4oCMcnNp4oCMICgxNCktMiIsInBvc2l0aW9uIjpudWxsfSwieWF4aXNMSFMiOltdLCJ5YXhpc1JIUyI6WyLigIxyc2nigIwgKDE0KS0yIl19fSwic2V0U3BhbiI6eyJtdWx0aXBsaWVyIjozLCJiYXNlIjoibW9udGgiLCJwZXJpb2RpY2l0eSI6eyJwZXJpb2QiOjEsInRpbWVVbml0IjoiZGF5In0sInNob3dFdmVudHNRdW90ZSI6dHJ1ZSwiZm9yY2VMb2FkIjpmYWxzZSwidXNlRXhpc3RpbmdEYXRhIjp0cnVlfSwib3V0bGllcnMiOmZhbHNlLCJhbmltYXRpb24iOnRydWUsImhlYWRzVXAiOnsic3RhdGljIjp0cnVlLCJkeW5hbWljIjpmYWxzZSwiZmxvYXRpbmciOmZhbHNlfSwibGluZVdpZHRoIjoyLCJmdWxsU2NyZWVuIjp0cnVlLCJzdHJpcGVkQmFja2dyb3VuZCI6dHJ1ZSwiY29sb3IiOiIjMDA4MWYyIiwiY3Jvc3NoYWlyU3RpY2t5IjpmYWxzZSwiZG9udFNhdmVSYW5nZVRvTGF5b3V0Ijp0cnVlLCJzeW1ib2xzIjpbeyJzeW1ib2wiOiJOVlMiLCJzeW1ib2xPYmplY3QiOnsic3ltYm9sIjoiTlZTIiwicXVvdGVUeXBlIjoiRVFVSVRZIiwiZXhjaGFuZ2VUaW1lWm9uZSI6IkFtZXJpY2EvTmV3X1lvcmsiLCJwZXJpb2QxIjoxNjYzNjI0ODAwLCJwZXJpb2QyIjoxNzQ1ODcwNDAwfSwicGVyaW9kaWNpdHkiOjEsImludGVydmFsIjoiZGF5IiwidGltZVVuaXQiOm51bGwsInNldFNwYW4iOnsibXVsdGlwbGllciI6MywiYmFzZSI6Im1vbnRoIiwicGVyaW9kaWNpdHkiOnsicGVyaW9kIjoxLCJ0aW1lVW5pdCI6ImRheSJ9LCJzaG93RXZlbnRzUXVvdGUiOnRydWUsImZvcmNlTG9hZCI6ZmFsc2UsInVzZUV4aXN0aW5nRGF0YSI6dHJ1ZX19XX0sImV2ZW50cyI6eyJkaXZzIjp0cnVlLCJzcGxpdHMiOnRydWUsInRyYWRpbmdIb3Jpem9uIjoibm9uZSIsInNpZ0RldkV2ZW50cyI6W119LCJwcmVmZXJlbmNlcyI6e319"

    def __init__(self) -> None:
        super().__init__(self._NAME, self._DESCRIPTION)
        os.makedirs(self._DATA_DIR, exist_ok=True)

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--json", help="use the stock tickers from the JSON file")
        parser.add_argument("--sector", help="filter groups by sector name (case-insensitive)")

    def handle(self, args: argparse.Namespace) -> None:
        json_file = args.json
        sector_filter = args.sector.lower() if args.sector else None

        with open(json_file) as f:
            data = json.load(f)
            groups = [TickerGroup.from_dict(item) for item in data]

        if sector_filter:
            groups = [g for g in groups if g.sector.lower() == sector_filter]
            if not groups:
                console.print(f"[red]❌ No groups found for sector:[/red] '{args.sector}'")
                return

        html_sections = []
        for group in groups:
            results, invalids = self.screen_multiple_stocks(group.tickers)
            html_sections.append(self.generate_html_table(results, group.sector, group.subsector, invalids))

        full_html_body = "\n".join(html_sections)
        html = f"""
        <!DOCTYPE html>
        <html lang=\"en\">
        <head>
          <meta charset=\"UTF-8\">
          <title>Stock Screening Results</title>
          <script src=\"https://cdn.tailwindcss.com\"></script>
        </head>
        <body class=\"bg-gray-50 text-gray-900 p-8\">
          <div class=\"max-w-screen-2xl mx-auto\">
            <h1 class=\"text-3xl font-bold mb-6\">📊 Stock Screening Results</h1>
            {full_html_body}
          </div>
        </body>
        </html>
        """

        output_path = os.path.join("public", "index.html")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"✅ Styled HTML saved to: {output_path}")
        webbrowser.open(f"file://{os.path.abspath(output_path)}")

    def load_cached_data(self, ticker: str) -> pd.DataFrame | None:
        file_path = os.path.join(self._DATA_DIR, f"{ticker}.json")
        if not os.path.exists(file_path):
            return None

        with open(file_path, "r") as f:
            raw = json.load(f)
            timestamp = datetime.fromisoformat(raw["timestamp"])
            if datetime.now() - timestamp > timedelta(hours=1):
                return None
            df = pd.read_json(io.StringIO(raw["data"]), convert_dates=True)
            df.index = pd.to_datetime(df.index)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df

    def save_cached_data(self, ticker: str, df: pd.DataFrame) -> None:
        df_json = df.to_json(date_format="iso")
        file_path = os.path.join(self._DATA_DIR, f"{ticker}.json")
        with open(file_path, "w") as f:
            json.dump({"timestamp": datetime.now().isoformat(), "data": df_json}, f)

    def download_batch_data(self, tickers: List[str]) -> dict:
        data = {}
        fresh_tickers = []

        for ticker in tickers:
            cached = self.load_cached_data(ticker)
            if cached is not None:
                data[ticker] = cached
            else:
                fresh_tickers.append(ticker)

        if fresh_tickers:
            print(f"⬇️ Downloading data for tickers: {', '.join(fresh_tickers)}")
            df_all = yf.download(fresh_tickers, period="90d", interval="1d", group_by="ticker", auto_adjust=False)
            for ticker in fresh_tickers:
                try:
                    df = df_all[ticker]
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                    df.index = pd.to_datetime(df.index)
                    self.save_cached_data(ticker, df)
                    data[ticker] = df
                except Exception as e:
                    print(f"⚠️ Error loading data for {ticker}: {e}")

        return data

    def check_stock_criteria(self, ticker: str, df: pd.DataFrame) -> dict:
        if df.empty or len(df) < 60:
            return {"Ticker": ticker, "Error": "Not enough data", "Available Columns": ", ".join(df.columns)}

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

        core_criteria_count = sum(
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
            "Core Criteria Met": core_conditions_met,
            "Core Criteria Score": "🟩" * core_criteria_count + "⬜" * (5 - core_criteria_count),
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
        }

    def screen_multiple_stocks(self, tickers) -> tuple[list, list]:
        results = []
        invalid_tickers = []
        data_map = self.download_batch_data(tickers)

        for ticker in tickers:
            try:
                if ticker not in data_map or data_map[ticker].empty:
                    invalid_tickers.append(ticker)
                    continue
                result = self.check_stock_criteria(ticker, df=data_map[ticker])
                results.append(result)
            except Exception as e:
                print(f"⚠️ Error processing ticker {ticker}: {e}")
                invalid_tickers.append(ticker)  # Add to invalid_tickers if an exception occurs

        if invalid_tickers:
            print(f"⚠️ Invalid or no data for tickers: {', '.join(invalid_tickers)}")

        return results, invalid_tickers

    def generate_html_table(self, results: List[dict], sector: str, subsector: str, invalid_tickers: List[str]) -> str:
        if not results:
            return ""

        df = pd.DataFrame(results)

        if "Ticker" in df.columns:
            df["Ticker"] = df["Ticker"].apply(
                lambda t: f'<a href="https://finance.yahoo.com/quote/{t}" target="_blank" class="text-blue-600 underline">{t}</a>'
            )

        for col in df.columns:
            if df[col].dtype == bool:
                df[col] = df[col].map({True: "✅", False: "❌"})

        table_html = df.to_html(
            index=False,
            escape=False,
            border=0,
            classes="table-auto w-full text-sm text-gray-700",
            na_rep="–",
        ).replace("<table", '<table class="table-auto w-full border-collapse text-sm text-gray-700"')
        table_html = table_html.replace("<thead>", '<thead class="bg-gray-100 text-left font-semibold">')
        table_html = table_html.replace("<th>", '<th class="px-4 py-2 whitespace-nowrap border-b border-gray-200">')
        table_html = table_html.replace("<td>", '<td class="px-4 py-2 border-t border-gray-200 align-top">')

        section_heading_html = f"""
        <div class=\"mb-6\">
            <h2 class=\"text-2xl font-bold text-gray-800\">{sector}</h2>
            <h3 class=\"text-xl font-semibold text-gray-600\">{subsector}</h3>
        </div>
        """

        delisted_html = ""
        if invalid_tickers:
            delisted_html = f"""
            <div class=\"mt-4 bg-red-50 border border-red-200 text-red-800 p-4 rounded shadow\">
                <h4 class=\"font-semibold mb-1\">⚠️ Invalid or Missing Data for Tickers</h4>
                <ul class=\"list-disc list-inside text-sm\">
                    {''.join(f'<li>{ticker}</li>' for ticker in invalid_tickers)}
                </ul>
            </div>
            """

        return f"""
        <div class=\"mb-12\">
            {section_heading_html}
            <div class=\"overflow-auto rounded shadow bg-white p-4 border border-gray-200\">
                {table_html}
            </div>
            {delisted_html}
        </div>
        """
