"""Tests for the BacktestEngine."""
from cryptopus.backtest import BacktestEngine, BacktestResult
from cryptopus.strategies import MomentumStrategy


def _make_candle(ts: float, o: float, h: float, l: float, c: float, v: float = 100.0):
    return [ts, o, h, l, c, v]


def _make_trending_candles(n: int, start_price: float = 100.0, trend: float = 0.5):
    """Generate n candles with a steady trend."""
    base_ts = 1_000_000_000_000
    candles = []
    for i in range(n):
        p = start_price + i * trend
        candles.append(_make_candle(base_ts + i * 60_000, p, p + 1.0, p - 1.0, p))
    return candles


class TestBacktestEngine:
    def test_basic_run(self):
        candles = _make_trending_candles(50)
        engine = BacktestEngine(fee_rate=0.001)
        result = engine.run(candles, MomentumStrategy(), 1000.0)
        assert isinstance(result, BacktestResult)
        assert result.start_cash == 1000.0
        assert len(result.equity_curve) == 30  # 50 - 20 window
        assert len(result.timestamps) == 30

    def test_return_pct(self):
        result = BacktestResult(
            start_cash=1000.0, end_cash=1100.0, trades=2, wins=1,
            max_dd=5.0, equity_curve=[], drawdowns=[], timestamps=[],
        )
        assert result.return_pct == 10.0

    def test_win_rate(self):
        result = BacktestResult(
            start_cash=1000.0, end_cash=1100.0, trades=4, wins=3,
            max_dd=5.0, equity_curve=[], drawdowns=[], timestamps=[],
        )
        assert result.win_rate == 75.0

    def test_win_rate_no_trades(self):
        result = BacktestResult(
            start_cash=1000.0, end_cash=1000.0, trades=0, wins=0,
            max_dd=0.0, equity_curve=[], drawdowns=[], timestamps=[],
        )
        assert result.win_rate == 0.0

    def test_slippage_reduces_returns(self):
        candles = _make_trending_candles(50)
        engine_no_slip = BacktestEngine(fee_rate=0.001, slippage_pct=0.0)
        engine_slip = BacktestEngine(fee_rate=0.001, slippage_pct=1.0)
        result_no_slip = engine_no_slip.run(candles, MomentumStrategy(), 1000.0)
        result_slip = engine_slip.run(candles, MomentumStrategy(), 1000.0)
        # Slippage should reduce or equal returns
        assert result_slip.end_cash <= result_no_slip.end_cash

    def test_stop_loss_triggers(self):
        # Create candles that go up then crash
        candles = _make_trending_candles(30, start_price=100.0, trend=1.0)
        # Add crash candles
        for i in range(25):
            p = 130.0 - i * 3.0
            candles.append(_make_candle(
                candles[-1][0] + 60_000, p, p + 1.0, p - 3.0, p
            ))
        engine = BacktestEngine(fee_rate=0.001, stop_loss_pct=5.0, take_profit_pct=0.0)
        result = engine.run(candles, MomentumStrategy(), 1000.0)
        assert result.trades > 0
