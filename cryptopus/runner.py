import threading
import time
from typing import List, Optional

from cryptopus.config import AppConfig
from cryptopus.data_engine import DataEngine
from cryptopus.events import EventBus
from cryptopus.logger import Logger
from cryptopus.strategies import STRATEGIES, StrategyBase, compute_atr
from cryptopus.trader import Trader


class StrategyRunner(threading.Thread):
    def __init__(self, config: AppConfig, data_engine: DataEngine, trader: Trader,
                 logger: Logger, events: Optional[EventBus] = None) -> None:
        super().__init__(daemon=True)
        self.config = config
        self.data_engine = data_engine
        self.trader = trader
        self.logger = logger
        self.events = events
        self.active = False
        self.strategy: StrategyBase = STRATEGIES[0]
        self._last_trade_ts: Optional[float] = None

    def run(self) -> None:
        self.logger.log("Strategy runner started.")
        while True:
            if self.active:
                self._tick()
            time.sleep(self.config.poll_seconds)

    def _calculate_position_size(self, ohlcv: List[List[float]], price: float) -> float:
        if not self.config.use_atr_sizing:
            return self.config.trade_size
        atr = compute_atr(ohlcv)
        if atr <= 0:
            return self.config.trade_size
        equity = self.config.backtest_cash
        pos = self.trader.positions.get(self.config.symbol)
        if pos and pos.amount > 0:
            equity = pos.amount * price + pos.realized_pnl
        risk_amount = equity * self.config.risk_per_trade_pct / 100
        size = risk_amount / atr
        size = max(size, self.config.trade_size * 0.1)
        size = min(size, self.config.trade_size * 10)
        return size

    def _tick(self) -> None:
        ohlcv = self.data_engine.fetch_ohlcv(self.config.symbol, self.config.timeframe, limit=120)
        if not ohlcv:
            return
        last_price = ohlcv[-1][4]

        # Check SL/TP on open positions
        self._check_sl_tp(last_price)

        if self._risk_blocked():
            return
        signal = self.strategy.evaluate(ohlcv)
        if signal in ("buy", "sell"):
            amount = self._calculate_position_size(ohlcv, last_price)
            self.trader.place_order(self.config.symbol, signal, amount, last_price)
            self.logger.log(f"{self.strategy.name} signal: {signal} @ {last_price:.2f} (size: {amount:.6f})")
            self._last_trade_ts = time.time()
            if self.events:
                self.events.emit("strategy_signal", self.strategy.name, signal, last_price)

    def _check_sl_tp(self, current_price: float) -> None:
        pos = self.trader.positions.get(self.config.symbol)
        if not pos or pos.amount <= 0 or pos.avg_price <= 0:
            return
        sl_pct = self.config.stop_loss_pct
        tp_pct = self.config.take_profit_pct
        if sl_pct > 0:
            sl_price = pos.avg_price * (1 - sl_pct / 100)
            if current_price <= sl_price:
                self.logger.log(
                    f"STOP LOSS triggered: price {current_price:.2f} <= SL {sl_price:.2f} "
                    f"(entry {pos.avg_price:.2f}, -{sl_pct}%)"
                )
                self.trader.place_order(self.config.symbol, "sell", pos.amount, current_price)
                self._last_trade_ts = time.time()
                return
        if tp_pct > 0:
            tp_price = pos.avg_price * (1 + tp_pct / 100)
            if current_price >= tp_price:
                self.logger.log(
                    f"TAKE PROFIT triggered: price {current_price:.2f} >= TP {tp_price:.2f} "
                    f"(entry {pos.avg_price:.2f}, +{tp_pct}%)"
                )
                self.trader.place_order(self.config.symbol, "sell", pos.amount, current_price)
                self._last_trade_ts = time.time()

    def _risk_blocked(self) -> bool:
        if self.trader.realized_pnl_today <= -self.config.max_daily_loss:
            self.logger.log("Max daily loss hit; strategy paused.")
            return True
        if self._last_trade_ts is not None:
            if time.time() - self._last_trade_ts < self.config.cooldown_seconds:
                return True
        return False
