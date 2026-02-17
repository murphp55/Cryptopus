from typing import List, Optional


class ContraMomentumStrategy:
    name = "Contra-Momentum"
    description = (
        "Fades sharp moves: sells after a >0.3% spike, buys after a >0.3% dip. "
        "Bets on mean reversion over a single candle. Risky in strong trends."
    )

    def evaluate(self, ohlcv: List[List[float]]) -> Optional[str]:
        if len(ohlcv) < 2:
            return None
        last = ohlcv[-1][4]
        prev = ohlcv[-2][4]
        if last > prev * 1.003:
            return "sell"
        if last < prev * 0.997:
            return "buy"
        return None
