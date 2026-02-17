from typing import List, Optional

from cryptopus.strategies.momentum import MomentumStrategy
from cryptopus.strategies.mean_reversion import MeanReversionStrategy
from cryptopus.strategies.breakout import BreakoutStrategy
from cryptopus.strategies.scalping import ScalpingStrategy
from cryptopus.strategies.contra_momentum import ContraMomentumStrategy


class StrategyBase:
    name = "Base"

    def evaluate(self, ohlcv: List[List[float]]) -> Optional[str]:
        raise NotImplementedError


def compute_atr(ohlcv: List[List[float]], period: int = 14) -> float:
    if len(ohlcv) < period + 1:
        return 0.0
    true_ranges = []
    for i in range(1, len(ohlcv)):
        high = ohlcv[i][2]
        low = ohlcv[i][3]
        prev_close = ohlcv[i - 1][4]
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        true_ranges.append(tr)
    return sum(true_ranges[-period:]) / period


STRATEGIES = [
    MomentumStrategy(),
    MeanReversionStrategy(),
    BreakoutStrategy(),
    ScalpingStrategy(),
    ContraMomentumStrategy(),
]

__all__ = [
    "StrategyBase",
    "compute_atr",
    "STRATEGIES",
    "MomentumStrategy",
    "MeanReversionStrategy",
    "BreakoutStrategy",
    "ScalpingStrategy",
    "ContraMomentumStrategy",
]
