"""Tests for the Trader class."""
import queue
from unittest.mock import MagicMock

from cryptopus.config import AppConfig
from cryptopus.data_engine import DataEngine
from cryptopus.logger import Logger
from cryptopus.trader import Trader


def _make_trader(store=None, events=None):
    config = AppConfig(live_trading=False)
    log_queue = queue.Queue()
    logger = Logger(log_queue)
    # Mock data engine to avoid exchange connections
    data_engine = MagicMock(spec=DataEngine)
    data_engine.exchange = None
    return Trader(config, data_engine, logger, store=store, events=events)


class TestTrader:
    def test_paper_buy_order(self):
        trader = _make_trader()
        order = trader.place_order("BTC/USD", "buy", 0.1, 50000.0)
        assert order.status == "paper"
        assert order.side == "buy"
        assert order.symbol == "BTC/USD"
        assert "BTC/USD" in trader.positions
        assert trader.positions["BTC/USD"].amount == 0.1
        assert trader.positions["BTC/USD"].avg_price == 50000.0

    def test_paper_sell_order_pnl(self):
        trader = _make_trader()
        trader.place_order("BTC/USD", "buy", 0.1, 50000.0)
        trader.place_order("BTC/USD", "sell", 0.1, 55000.0)
        pos = trader.positions["BTC/USD"]
        assert pos.amount == 0.0
        # Realized PnL: (55000 - 50000) * 0.1 = 500
        assert pos.realized_pnl == 500.0

    def test_multiple_buys_avg_price(self):
        trader = _make_trader()
        trader.place_order("BTC/USD", "buy", 0.1, 50000.0)
        trader.place_order("BTC/USD", "buy", 0.1, 60000.0)
        pos = trader.positions["BTC/USD"]
        assert pos.amount == 0.2
        assert pos.avg_price == 55000.0  # weighted average

    def test_daily_pnl_tracking(self):
        trader = _make_trader()
        trader.place_order("BTC/USD", "buy", 1.0, 100.0)
        trader.place_order("BTC/USD", "sell", 1.0, 110.0)
        assert trader.realized_pnl_today == 10.0

    def test_orders_list_grows(self):
        trader = _make_trader()
        trader.place_order("BTC/USD", "buy", 0.1, 50000.0)
        trader.place_order("ETH/USD", "buy", 1.0, 3000.0)
        assert len(trader.orders) == 2

    def test_events_emitted(self):
        from cryptopus.events import EventBus
        events = EventBus()
        orders_received = []
        events.on("order_placed", lambda o: orders_received.append(o))
        trader = _make_trader(events=events)
        trader.place_order("BTC/USD", "buy", 0.1, 50000.0)
        assert len(orders_received) == 1
        assert orders_received[0].side == "buy"
