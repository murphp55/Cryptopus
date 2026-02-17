from typing import List, Optional


class MeanReversionStrategy:
    name = "Mean Reversion"
    description = (
        "Bets that price returns to the average: buys when price drops >1% below the "
        "20-candle mean, sells when it rises >1% above. Best in range-bound, choppy markets."
    )

    def evaluate(self, ohlcv: List[List[float]]) -> Optional[str]:
        closes = [c[4] for c in ohlcv][-20:]
        if len(closes) < 20:
            return None
        mean = sum(closes) / len(closes)
        last = closes[-1]
        if last < mean * 0.99:
            return "buy"
        if last > mean * 1.01:
            return "sell"
        return None
