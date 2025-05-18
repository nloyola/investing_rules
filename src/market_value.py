from datetime import date, datetime, timedelta
from jinja2 import Environment, FileSystemLoader
from rich.console import Console
import argparse
import os
import pandas as pd
import plotly.graph_objs as go
import yfinance as yf

from .config import Config
from .base_command import BaseCommand
from .ticker_group import TickerGroup

console = Console()


class MarketValueCommand(BaseCommand):
    _NAME = "market-value"
    _DESCRIPTION = "generates a graph in HTML display the daily value of a stock"

    _DATA_DIR = "stock_data"

    def __init__(self) -> None:
        super().__init__(self._NAME, self._DESCRIPTION)
        os.makedirs(self._DATA_DIR, exist_ok=True)

    # def add_arguments(self, parser: argparse.ArgumentParser) -> None:
    # parser.add_argument("--json", help="use the stock tickers from the JSON file")
    # parser.add_argument("--sector", help="filter groups by sector name (case-insensitive)")

    def handle(self, args: argparse.Namespace) -> None:
        holdings = {
            "XUS.TO": [
                {"date": "2025-04-10", "shares": 100},
                {"date": "2025-04-15", "shares": 100},
                {"date": "2025-05-13", "shares": 100},
                {"date": "2025-05-13", "shares": 200},
            ],
            "MSFT": [{"date": "2025-04-10", "shares": 3}, {"date": "2025-04-15", "shares": 2}],
        }

        start_date = "2025-04-10"
        end_date = date.today()
        all_prices = {}

        for symbol, purchases in holdings.items():
            # try:
            df = yf.download(symbol, start=start_date, end=end_date)
            df.columns = [f"{col}" for col, _ in df.columns]
            print(f"df: {df.columns}")
            if df.empty:
                print(f"❌ No data for {symbol}")
                continue

            # Build a time series of cumulative shares held
            shares_series = pd.Series(0, index=df.index)
            for purchase in purchases:
                purchase_date = pd.to_datetime(purchase["date"])
                if purchase_date in shares_series.index:
                    shares_series.loc[purchase_date] += purchase["shares"]
                else:
                    # If purchase date is not a trading day, add to next available date
                    next_idx = shares_series.index.searchsorted(purchase_date)
                    if next_idx < len(shares_series):
                        shares_series.iloc[next_idx] += purchase["shares"]
                    else:
                        print(f"⚠️ Purchase date {purchase['date']} for {symbol} is after available data.")

            df["SharesHeld"] = shares_series.cumsum()
            df["MarketValue"] = df["Close"] * df["SharesHeld"]
            all_prices[symbol] = df["MarketValue"].rename(symbol)
            print(f"✅ Loaded {symbol}")
        # except Exception as e:
        #     print(f"❌ Failed to load {symbol}: {e}")

        print(f"all_prices: {all_prices}")

        # Combine into one DataFrame
        if all_prices:
            combined = pd.concat(all_prices.values(), axis=1).fillna(0)
            combined["TotalValue"] = combined.sum(axis=1)
            combined.index.name = "Date"

            # Plot a separate graph for each ticker
            for symbol in holdings:
                if symbol in combined:
                    fig = go.Figure()
                    fig.add_trace(
                        go.Scatter(x=combined.index, y=combined[symbol], mode="lines", name=f"{symbol} Value")
                    )
                    fig.update_layout(
                        title=f"Daily Market Value of {symbol}",
                        xaxis_title="Date",
                        yaxis_title="Value",
                        template="plotly_white",
                    )
                    filename = f"public/market_value_{symbol.replace('.', '_')}.html"
                    fig.write_html(filename)
                    print(f"📊 Chart for {symbol} saved to: {filename}")

            # Optionally, keep the total portfolio chart as well
            fig_total = go.Figure()
            fig_total.add_trace(
                go.Scatter(x=combined.index, y=combined["TotalValue"], mode="lines", name="Total Portfolio Value")
            )
            fig_total.update_layout(
                title="Daily Market Value of Holdings",
                xaxis_title="Date",
                yaxis_title="Value",
                template="plotly_white",
            )
            fig_total.write_html("public/market_value.html")
            print("📊 Total portfolio chart saved to: market_value_chart_total.html")
        else:
            print("⚠️ No data was loaded. Check your symbols.")
