"""Tests for all trading strategies."""
import time

from cryptopus.strategies import (
    MomentumStrategy,
    MeanReversionStrategy,
    BreakoutStrategy,
    ScalpingStrategy,
    ContraMomentumStrategy,
    compute_atr,
)


def _make_candle(ts: float, o: float, h: float, l: float, c: float, v: float = 100.0):
    return [ts, o, h, l, c, v]


def _make_flat_candles(n: int, price: float = 100.0):
    """Generate n flat candles at a fixed price."""
    base_ts = 1_000_000_000_000
    return [_make_candle(base_ts + i * 60_000, price, price + 0.01, price - 0.01, price) for i in range(n)]


class TestMomentumStrategy:
    def test_buy_signal(self):
        strat = MomentumStrategy()
        candles = _make_flat_candles(10, price=100.0)
        # Make last 5 candles trend up >0.2%
        for i in range(5):
            candles[-(5 - i)][4] = 100.0 + i * 0.1  # close prices: 100.0, 100.1, 100.2, 100.3, 100.4
        assert strat.evaluate(candles) == "buy"

    def test_sell_signal(self):
        strat = MomentumStrategy()
        candles = _make_flat_candles(10, price=100.0)
        for i in range(5):
            candles[-(5 - i)][4] = 100.0 - i * 0.1
        assert strat.evaluate(candles) == "sell"

    def test_no_signal_flat(self):
        strat = MomentumStrategy()
        candles = _make_flat_candles(10, price=100.0)
        assert strat.evaluate(candles) is None

    def test_insufficient_data(self):
        strat = MomentumStrategy()
        candles = _make_flat_candles(3)
        assert strat.evaluate(candles) is None


class TestMeanReversionStrategy:
    def test_buy_below_mean(self):
        strat = MeanReversionStrategy()
        candles = _make_flat_candles(25, price=100.0)
        # Set last candle well below mean
        candles[-1][4] = 98.0
        assert strat.evaluate(candles) == "buy"

    def test_sell_above_mean(self):
        strat = MeanReversionStrategy()
        candles = _make_flat_candles(25, price=100.0)
        candles[-1][4] = 102.0
        assert strat.evaluate(candles) == "sell"

    def test_no_signal_at_mean(self):
        strat = MeanReversionStrategy()
        candles = _make_flat_candles(25, price=100.0)
        assert strat.evaluate(candles) is None

    def test_insufficient_data(self):
        strat = MeanReversionStrategy()
        candles = _make_flat_candles(10)
        assert strat.evaluate(candles) is None


class TestBreakoutStrategy:
    def test_buy_above_high(self):
        strat = BreakoutStrategy()
        candles = _make_flat_candles(25, price=100.0)
        # Set close above prior highs
        candles[-1][4] = 101.0
        assert strat.evaluate(candles) == "buy"

    def test_sell_below_low(self):
        strat = BreakoutStrategy()
        candles = _make_flat_candles(25, price=100.0)
        candles[-1][4] = 99.0
        assert strat.evaluate(candles) == "sell"

    def test_no_signal_in_range(self):
        strat = BreakoutStrategy()
        candles = _make_flat_candles(25, price=100.0)
        assert strat.evaluate(candles) is None


class TestScalpingStrategy:
    def test_buy_at_range_low(self):
        strat = ScalpingStrategy()
        # Create candles with a spread
        candles = _make_flat_candles(15, price=100.0)
        for i in range(10):
            candles[-(10 - i)][4] = 100.0 + i  # 100..109
        candles[-1][4] = 100.0  # last at bottom of range
        assert strat.evaluate(candles) == "buy"

    def test_sell_at_range_high(self):
        strat = ScalpingStrategy()
        candles = _make_flat_candles(15, price=100.0)
        for i in range(10):
            candles[-(10 - i)][4] = 100.0 + i
        candles[-1][4] = 109.0  # last at top of range
        assert strat.evaluate(candles) == "sell"

    def test_no_signal_zero_spread(self):
        strat = ScalpingStrategy()
        candles = _make_flat_candles(15, price=100.0)
        assert strat.evaluate(candles) is None


class TestContraMomentumStrategy:
    def test_sell_on_rise(self):
        strat = ContraMomentumStrategy()
        candles = _make_flat_candles(5, price=100.0)
        candles[-2][4] = 100.0
        candles[-1][4] = 100.5  # >0.3% up
        assert strat.evaluate(candles) == "sell"

    def test_buy_on_drop(self):
        strat = ContraMomentumStrategy()
        candles = _make_flat_candles(5, price=100.0)
        candles[-2][4] = 100.0
        candles[-1][4] = 99.5  # >0.3% down
        assert strat.evaluate(candles) == "buy"

    def test_no_signal_small_move(self):
        strat = ContraMomentumStrategy()
        candles = _make_flat_candles(5, price=100.0)
        assert strat.evaluate(candles) is None


class TestComputeATR:
    def test_basic_atr(self):
        candles = _make_flat_candles(20, price=100.0)
        # Inject some volatility
        for i in range(1, 20):
            candles[i][2] = 101.0  # high
            candles[i][3] = 99.0   # low
        atr = compute_atr(candles, period=14)
        assert atr > 0

    def test_insufficient_data(self):
        candles = _make_flat_candles(5)
        assert compute_atr(candles, period=14) == 0.0
