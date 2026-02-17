from typing import List, Optional


class MomentumStrategy:
    name = "Momentum"
    description = (
        "Follows the trend: buys when price rises >0.2% over the last 5 candles, "
        "sells when it drops >0.2%. Best in trending markets with clear direction."
    )

    def evaluate(self, ohlcv: List[List[float]]) -> Optional[str]:
        closes = [c[4] for c in ohlcv][-5:]
        if len(closes) < 5:
            return None
        if closes[-1] > closes[0] * 1.002:
            return "buy"
        if closes[-1] < closes[0] * 0.998:
            return "sell"
        return None
