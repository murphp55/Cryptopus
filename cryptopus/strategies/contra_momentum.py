from typing import List, Optional


class ContraMomentumStrategy:
    name = "Contra-Momentum"

    def __init__(self, threshold_pct: float = 0.3) -> None:
        self.threshold_pct = threshold_pct

    @property
    def description(self) -> str:
        return (
            f"Fades sharp moves: sells after a >{self.threshold_pct}% spike, buys after a "
            f">{self.threshold_pct}% dip. Bets on mean reversion over a single candle. "
            "Risky in strong trends."
        )

    def evaluate(self, ohlcv: List[List[float]]) -> Optional[str]:
        if len(ohlcv) < 2:
            return None
        last = ohlcv[-1][4]
        prev = ohlcv[-2][4]
        up = 1 + self.threshold_pct / 100
        down = 1 - self.threshold_pct / 100
        if last > prev * up:
            return "sell"
        if last < prev * down:
            return "buy"
        return None
