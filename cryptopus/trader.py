import traceback
from datetime import datetime, timezone
from typing import Dict, List, Optional

from cryptopus.config import AppConfig, Order, Position
from cryptopus.data_engine import DataEngine
from cryptopus.events import EventBus
from cryptopus.logger import Logger
from cryptopus.persistence import TradeStore


class Trader:
    def __init__(self, config: AppConfig, data_engine: DataEngine, logger: Logger,
                 store: Optional[TradeStore] = None, events: Optional[EventBus] = None) -> None:
        self.config = config
        self.data_engine = data_engine
        self.logger = logger
        self.store = store
        self.events = events
        self.positions: Dict[str, Position] = {}
        self.orders: List[Order] = []
        self.realized_pnl_today: float = 0.0
        self._pnl_day: Optional[int] = None

        if self.store:
            self.positions = self.store.load_positions()
            self.orders = self.store.load_orders(limit=200)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            self.realized_pnl_today = self.store.load_daily_pnl(today)
            self._pnl_day = datetime.now(timezone.utc).timetuple().tm_yday
            if self.positions:
                self.logger.log(f"Loaded {len(self.positions)} positions from DB.")
            if self.orders:
                self.logger.log(f"Loaded {len(self.orders)} orders from DB.")

    def place_order(self, symbol: str, side: str, amount: float, price: float) -> Order:
        if self.config.live_trading and self.data_engine.exchange is not None:
            try:
                order = self.data_engine.exchange.create_order(
                    symbol=symbol,
                    type="market",
                    side=side,
                    amount=amount,
                )
                record = Order(
                    ts=datetime.now(timezone.utc),
                    side=side,
                    price=price,
                    amount=amount,
                    status=order.get("status", "submitted"),
                    symbol=symbol,
                    exchange_id=order.get("id"),
                )
                self.logger.log(f"Live order submitted: {side} {amount} {symbol}")
                self._apply_fill(symbol, side, amount, price)
                self.orders.append(record)
                if self.store:
                    self.store.save_order(record)
                if self.events:
                    self.events.emit("order_placed", record)
                return record
            except Exception as exc:
                self.logger.log(f"Live order FAILED: {exc}\n{traceback.format_exc()}")
                record = Order(
                    ts=datetime.now(timezone.utc),
                    side=side,
                    price=price,
                    amount=amount,
                    status="failed",
                    symbol=symbol,
                )
                self.orders.append(record)
                if self.store:
                    self.store.save_order(record)
                if self.events:
                    self.events.emit("order_placed", record)
                return record

        record = Order(
            ts=datetime.now(timezone.utc),
            side=side,
            price=price,
            amount=amount,
            status="paper",
            symbol=symbol,
        )
        self._apply_fill(symbol, side, amount, price)
        self.orders.append(record)
        if self.store:
            self.store.save_order(record)
        if self.events:
            self.events.emit("order_placed", record)
        self.logger.log(f"Paper order: {side} {amount} {symbol} @ {price:.2f}")
        return record

    def _apply_fill(self, symbol: str, side: str, amount: float, price: float) -> None:
        pos = self.positions.get(symbol, Position(symbol=symbol))
        if side == "buy":
            new_amount = pos.amount + amount
            if new_amount > 0:
                pos.avg_price = (pos.avg_price * pos.amount + price * amount) / new_amount
            pos.amount = new_amount
        else:
            realized = (price - pos.avg_price) * amount
            pos.realized_pnl += realized
            self._update_daily_pnl(realized)
            pos.amount -= amount
            if pos.amount < 0:
                pos.amount = 0
                pos.avg_price = 0
        self.positions[symbol] = pos
        if self.store:
            self.store.save_position(pos)
        if self.events:
            self.events.emit("position_updated", pos)

    def _update_daily_pnl(self, realized: float) -> None:
        day = datetime.now(timezone.utc).timetuple().tm_yday
        if self._pnl_day != day:
            self.realized_pnl_today = 0.0
            self._pnl_day = day
        self.realized_pnl_today += realized
        if self.store:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            self.store.save_daily_pnl(today, self.realized_pnl_today)
