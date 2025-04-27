import yfinance as yf
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD


def check_stock_criteria(ticker: str):
    # Download historical daily data
    df = yf.download(ticker, period="90d", interval="1d")
    if df.empty or len(df) < 60:
        return f"Not enough data for {ticker}"

    # Calculate moving averages and average volume
    df["50dma"] = df["Close"].rolling(window=50).mean()
    df["volume_avg_20"] = df["Volume"].rolling(window=20).mean()

    # Ensure close is a proper 1D Series
    close_series = df["Close"].squeeze()

    # Technical Indicators
    rsi = RSIIndicator(close=close_series).rsi()
    macd_calc = MACD(close=close_series)
    macd_line = macd_calc.macd()
    signal_line = macd_calc.macd_signal()

    # Extract latest values and convert to float to avoid format issues
    price = df["Close"].iloc[-1].item()
    volume = df["Volume"].iloc[-1].item()
    avg_vol = df["volume_avg_20"].iloc[-1].item()
    dma_50 = float(df["50dma"].iloc[-1])
    dma_50_prev = float(df["50dma"].iloc[-15])
    recent_high = df["Close"].rolling(window=60).max().iloc[-2].item()
    rsi_val = float(rsi.iloc[-1])
    macd_val = float(macd_line.iloc[-1])
    signal_val = float(signal_line.iloc[-1])

    # Check conditions
    is_breakout = price > recent_high
    breakout_volume_confirmed = volume > 1.5 * avg_vol
    price_above_50dma = price > dma_50
    dma_slope = dma_50 > dma_50_prev
    rsi_good = 50 < rsi_val < 70
    macd_bullish = macd_val > signal_val

    # Print results
    print(f"\n📈 {ticker} Analysis")
    print(f"Price: {price:.2f} | 60-day High: {recent_high:.2f}")
    print(f"Volume: {volume:.0f} | 20-day Avg Volume: {avg_vol:.0f}")
    print(f"50DMA: {dma_50:.2f} (was {dma_50_prev:.2f} 15 days ago)")
    print(f"RSI: {rsi_val:.2f} | MACD: {macd_val:.2f} vs Signal: {signal_val:.2f}\n")

    print("🧪 Checklist:")
    print(f"✔️ Breakout Above High: {is_breakout}")
    print(f"✔️ Volume Spike: {breakout_volume_confirmed}")
    print(f"✔️ Price > 50DMA: {price_above_50dma}")
    print(f"✔️ 50DMA Sloping Up: {dma_slope}")
    print(f"✔️ RSI in 50–70 Range: {rsi_good}")
    print(f"✔️ MACD Bullish: {macd_bullish}")

    # Final decision
    core = [is_breakout, breakout_volume_confirmed, price_above_50dma, dma_slope]
    if all(core):
        return f"\n✅ {ticker} meets core buy criteria!"
    else:
        return f"\n❌ {ticker} does not meet all core criteria."


# Test the function
if __name__ == "__main__":
    print(check_stock_criteria("GOOG"))
