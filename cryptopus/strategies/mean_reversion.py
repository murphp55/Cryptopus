from typing import List, Optional


class MeanReversionStrategy:
    name = "Mean Reversion"

    def __init__(self, threshold_pct: float = 1.0, window: int = 20) -> None:
        self.threshold_pct = threshold_pct
        self.window = window

    @property
    def description(self) -> str:
        return (
            f"Bets that price returns to the average: buys when price drops >{self.threshold_pct}% "
            f"below the {self.window}-candle mean, sells when it rises >{self.threshold_pct}% above. "
            "Best in range-bound, choppy markets."
        )

    def evaluate(self, ohlcv: List[List[float]]) -> Optional[str]:
        closes = [c[4] for c in ohlcv][-self.window:]
        if len(closes) < self.window:
            return None
        mean = sum(closes) / len(closes)
        last = closes[-1]
        buy_thresh = 1 - self.threshold_pct / 100
        sell_thresh = 1 + self.threshold_pct / 100
        if last < mean * buy_thresh:
            return "buy"
        if last > mean * sell_thresh:
            return "sell"
        return None
