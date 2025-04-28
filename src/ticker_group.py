from dataclasses import dataclass
from typing import List


@dataclass
class TickerGroup:
    sector: str
    subsector: str
    tickers: List[str]

    @staticmethod
    def from_dict(data: dict) -> "TickerGroup":
        # Split and strip each ticker symbol
        tickers = [ticker.strip() for ticker in data["Company Ticker Symbols"].split(",")]
        return TickerGroup(
            sector=data["Sector"],
            subsector=data["Subsector"],
            tickers=tickers,
        )
