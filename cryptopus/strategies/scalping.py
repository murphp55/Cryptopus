from typing import List, Optional


class ScalpingStrategy:
    name = "Scalping"
    description = (
        "Makes many small trades: buys near the bottom 10% of the 10-candle range, "
        "sells near the top 10%. Best in tight, low-volatility sideways markets."
    )

    def evaluate(self, ohlcv: List[List[float]]) -> Optional[str]:
        closes = [c[4] for c in ohlcv][-10:]
        if len(closes) < 10:
            return None
        spread = max(closes) - min(closes)
        if spread == 0:
            return None
        last = closes[-1]
        if last <= min(closes) + spread * 0.1:
            return "buy"
        if last >= max(closes) - spread * 0.1:
            return "sell"
        return None
