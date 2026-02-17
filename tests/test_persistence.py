"""Tests for TradeStore (SQLite persistence)."""
from datetime import datetime, timezone

from cryptopus.config import Order, Position
from cryptopus.persistence import TradeStore


def _make_store():
    """Create an in-memory TradeStore for testing."""
    return TradeStore(db_path=":memory:")


class TestTradeStore:
    def test_save_and_load_order(self):
        store = _make_store()
        order = Order(
            ts=datetime(2025, 1, 1, tzinfo=timezone.utc),
            side="buy",
            price=50000.0,
            amount=0.1,
            status="paper",
            symbol="BTC/USD",
        )
        store.save_order(order)
        orders = store.load_orders(limit=10)
        assert len(orders) == 1
        assert orders[0].symbol == "BTC/USD"
        assert orders[0].side == "buy"
        assert orders[0].price == 50000.0

    def test_load_orders_limit(self):
        store = _make_store()
        for i in range(10):
            store.save_order(Order(
                ts=datetime(2025, 1, 1, tzinfo=timezone.utc),
                side="buy", price=100.0 + i, amount=1.0, status="paper", symbol="BTC/USD",
            ))
        orders = store.load_orders(limit=5)
        assert len(orders) == 5

    def test_save_and_load_position(self):
        store = _make_store()
        pos = Position(symbol="ETH/USD", amount=10.0, avg_price=3000.0, realized_pnl=50.0)
        store.save_position(pos)
        positions = store.load_positions()
        assert "ETH/USD" in positions
        assert positions["ETH/USD"].amount == 10.0
        assert positions["ETH/USD"].avg_price == 3000.0

    def test_position_upsert(self):
        store = _make_store()
        store.save_position(Position(symbol="BTC/USD", amount=1.0, avg_price=50000.0, realized_pnl=0.0))
        store.save_position(Position(symbol="BTC/USD", amount=2.0, avg_price=55000.0, realized_pnl=100.0))
        positions = store.load_positions()
        assert positions["BTC/USD"].amount == 2.0
        assert positions["BTC/USD"].realized_pnl == 100.0

    def test_daily_pnl(self):
        store = _make_store()
        store.save_daily_pnl("2025-01-01", 150.0)
        assert store.load_daily_pnl("2025-01-01") == 150.0
        assert store.load_daily_pnl("2025-01-02") == 0.0

    def test_daily_pnl_upsert(self):
        store = _make_store()
        store.save_daily_pnl("2025-01-01", 100.0)
        store.save_daily_pnl("2025-01-01", 200.0)
        assert store.load_daily_pnl("2025-01-01") == 200.0
