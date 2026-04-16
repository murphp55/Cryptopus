from typing import List, Optional


class BreakoutStrategy:
    name = "Breakout"

    def __init__(self, buffer_pct: float = 0.1, window: int = 20) -> None:
        self.buffer_pct = buffer_pct
        self.window = window

    @property
    def description(self) -> str:
        return (
            f"Catches big moves: buys when price breaks >{self.buffer_pct}% above the "
            f"{self.window}-candle high, sells when it breaks >{self.buffer_pct}% below the "
            f"{self.window}-candle low. Best when volatility is expanding."
        )

    def evaluate(self, ohlcv: List[List[float]]) -> Optional[str]:
        highs = [c[2] for c in ohlcv][-self.window:]
        lows = [c[3] for c in ohlcv][-self.window:]
        if len(highs) < self.window:
            return None
        last_close = ohlcv[-1][4]
        up_buffer = 1 + self.buffer_pct / 100
        down_buffer = 1 - self.buffer_pct / 100
        if last_close > max(highs[:-1]) * up_buffer:
            return "buy"
        if last_close < min(lows[:-1]) * down_buffer:
            return "sell"
        return None
