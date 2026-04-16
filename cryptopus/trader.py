import threading
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
        self._pnl_lock = threading.Lock()

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
            if amount > pos.amount:
                self.logger.log(
                    f"WARN: sell amount {amount:.6f} exceeds position {pos.amount:.6f} "
                    f"for {symbol}; clamping to position size."
                )
                amount = pos.amount
            realized = (price - pos.avg_price) * amount
            pos.realized_pnl += realized
            self._update_daily_pnl(realized)
            pos.amount -= amount
            if pos.amount < 1e-12:
                pos.amount = 0
                pos.avg_price = 0
        self.positions[symbol] = pos
        if self.store:
            self.store.save_position(pos)
        if self.events:
            self.events.emit("position_updated", pos)

    def reconcile_positions(self) -> None:
        """Sync local positions with actual exchange balances.

        Fetches real balances from the exchange and logs any discrepancies
        with locally tracked positions. Updates local state to match exchange.
        Only runs when exchange is connected (live or paper with API keys).
        """
        if self.data_engine.exchange is None:
            self.logger.log("Reconciliation skipped: no exchange connection.")
            return
        try:
            balance = self.data_engine.exchange.fetch_balance()
        except Exception as exc:
            self.logger.log(f"Reconciliation failed: could not fetch balance: {exc}")
            return

        # Build a map of exchange positions (non-zero balances)
        exchange_positions: Dict[str, float] = {}
        free = balance.get("free", {})
        for asset, amount in free.items():
            if isinstance(amount, (int, float)) and amount > 1e-12:
                exchange_positions[asset] = float(amount)

        # Compare with local positions
        discrepancies = 0
        for symbol, pos in self.positions.items():
            base = symbol.split("/")[0] if "/" in symbol else symbol
            exchange_amount = exchange_positions.get(base, 0.0)
            if abs(pos.amount - exchange_amount) > 1e-8:
                self.logger.log(
                    f"RECONCILE: {symbol} — local: {pos.amount:.8f}, "
                    f"exchange: {exchange_amount:.8f} (diff: {pos.amount - exchange_amount:+.8f})"
                )
                pos.amount = exchange_amount
                if pos.amount < 1e-12:
                    pos.amount = 0
                    pos.avg_price = 0
                self.positions[symbol] = pos
                if self.store:
                    self.store.save_position(pos)
                discrepancies += 1

        if discrepancies == 0:
            self.logger.log("Reconciliation complete: local positions match exchange.")
        else:
            self.logger.log(f"Reconciliation complete: corrected {discrepancies} position(s).")

    def get_realized_pnl_today(self) -> float:
        """Thread-safe read of today's realized P&L."""
        with self._pnl_lock:
            return self.realized_pnl_today

    def _update_daily_pnl(self, realized: float) -> None:
        with self._pnl_lock:
            day = datetime.now(timezone.utc).timetuple().tm_yday
            if self._pnl_day != day:
                self.realized_pnl_today = 0.0
                self._pnl_day = day
            self.realized_pnl_today += realized
            if self.store:
                today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                self.store.save_daily_pnl(today, self.realized_pnl_today)
