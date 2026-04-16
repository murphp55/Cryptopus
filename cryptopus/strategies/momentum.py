from typing import List, Optional


class MomentumStrategy:
    name = "Momentum"

    def __init__(self, threshold_pct: float = 0.2, window: int = 5) -> None:
        self.threshold_pct = threshold_pct
        self.window = window

    @property
    def description(self) -> str:
        return (
            f"Follows the trend: buys when price rises >{self.threshold_pct}% over the "
            f"last {self.window} candles, sells when it drops >{self.threshold_pct}%. "
            "Best in trending markets with clear direction."
        )

    def evaluate(self, ohlcv: List[List[float]]) -> Optional[str]:
        closes = [c[4] for c in ohlcv][-self.window:]
        if len(closes) < self.window:
            return None
        up = 1 + self.threshold_pct / 100
        down = 1 - self.threshold_pct / 100
        if closes[-1] > closes[0] * up:
            return "buy"
        if closes[-1] < closes[0] * down:
            return "sell"
        return None
