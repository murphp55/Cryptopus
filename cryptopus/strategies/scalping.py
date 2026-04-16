from typing import List, Optional


class ScalpingStrategy:
    name = "Scalping"

    def __init__(self, band_pct: float = 10.0, window: int = 10) -> None:
        self.band_pct = band_pct
        self.window = window

    @property
    def description(self) -> str:
        return (
            f"Makes many small trades: buys near the bottom {self.band_pct}% of the "
            f"{self.window}-candle range, sells near the top {self.band_pct}%. "
            "Best in tight, low-volatility sideways markets."
        )

    def evaluate(self, ohlcv: List[List[float]]) -> Optional[str]:
        closes = [c[4] for c in ohlcv][-self.window:]
        if len(closes) < self.window:
            return None
        spread = max(closes) - min(closes)
        if spread == 0:
            return None
        last = closes[-1]
        band = self.band_pct / 100
        if last <= min(closes) + spread * band:
            return "buy"
        if last >= max(closes) - spread * band:
            return "sell"
        return None
