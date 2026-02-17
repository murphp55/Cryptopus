from typing import List, Optional


class BreakoutStrategy:
    name = "Breakout"
    description = (
        "Catches big moves: buys when price breaks above the 20-candle high, sells when "
        "it breaks below the 20-candle low. Best when volatility is expanding."
    )

    def evaluate(self, ohlcv: List[List[float]]) -> Optional[str]:
        highs = [c[2] for c in ohlcv][-20:]
        lows = [c[3] for c in ohlcv][-20:]
        if len(highs) < 20:
            return None
        last_close = ohlcv[-1][4]
        if last_close > max(highs[:-1]) * 1.001:
            return "buy"
        if last_close < min(lows[:-1]) * 0.999:
            return "sell"
        return None
