from datetime import datetime, timezone
from typing import List, Optional


class BacktestResult:
    def __init__(
        self,
        start_cash: float,
        end_cash: float,
        trades: int,
        wins: int,
        max_dd: float,
        equity_curve: List[float],
        drawdowns: List[float],
        timestamps: List[datetime],
        buy_hold_curve: Optional[List[float]] = None,
    ) -> None:
        self.start_cash = start_cash
        self.end_cash = end_cash
        self.trades = trades
        self.wins = wins
        self.max_dd = max_dd
        self.equity_curve = equity_curve
        self.drawdowns = drawdowns
        self.timestamps = timestamps
        self.buy_hold_curve = buy_hold_curve or []

    @property
    def return_pct(self) -> float:
        if self.start_cash == 0:
            return 0.0
        return (self.end_cash - self.start_cash) / self.start_cash * 100

    @property
    def win_rate(self) -> float:
        return (self.wins / self.trades * 100) if self.trades else 0.0


class BacktestEngine:
    def __init__(self, fee_rate: float, slippage_pct: float = 0.0,
                 stop_loss_pct: float = 0.0, take_profit_pct: float = 0.0) -> None:
        self.fee_rate = fee_rate
        self.slippage_pct = slippage_pct
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct

    def run(self, ohlcv: List[List[float]], strategy, cash: float) -> BacktestResult:  # type: ignore[override]
        start_cash = cash
        position = 0.0
        entry_price = 0.0
        trades = 0
        wins = 0
        equity_curve: List[float] = []
        buy_hold_curve: List[float] = []
        timestamps: List[datetime] = []
        drawdowns: List[float] = []
        peak = 0.0
        bh_start_price = ohlcv[20][4] if len(ohlcv) > 20 else ohlcv[0][4]

        for idx in range(20, len(ohlcv)):
            window = ohlcv[: idx + 1]
            price = window[-1][4]
            high = window[-1][2]
            low = window[-1][3]

            # Check SL/TP on open positions
            if position > 0 and entry_price > 0 and (self.stop_loss_pct > 0 or self.take_profit_pct > 0):
                sl_price = entry_price * (1 - self.stop_loss_pct / 100) if self.stop_loss_pct > 0 else 0
                tp_price = entry_price * (1 + self.take_profit_pct / 100) if self.take_profit_pct > 0 else float("inf")
                if sl_price > 0 and low <= sl_price:
                    sell_price = sl_price * (1 - self.slippage_pct / 100)
                    proceeds = position * sell_price
                    fee = proceeds * self.fee_rate
                    cash = proceeds - fee
                    if sl_price > entry_price:
                        wins += 1
                    position = 0
                    trades += 1
                elif high >= tp_price:
                    sell_price = tp_price * (1 - self.slippage_pct / 100)
                    proceeds = position * sell_price
                    fee = proceeds * self.fee_rate
                    cash = proceeds - fee
                    wins += 1
                    position = 0
                    trades += 1

            signal = strategy.evaluate(window)
            if signal == "buy" and cash > 0 and position == 0:
                buy_price = price * (1 + self.slippage_pct / 100)
                fee = cash * self.fee_rate
                position = (cash - fee) / buy_price
                entry_price = buy_price
                cash = 0
                trades += 1
            elif signal == "sell" and position > 0:
                sell_price = price * (1 - self.slippage_pct / 100)
                proceeds = position * sell_price
                fee = proceeds * self.fee_rate
                cash = proceeds - fee
                if sell_price > entry_price:
                    wins += 1
                position = 0
                trades += 1

            equity = cash + position * price
            equity_curve.append(equity)
            bh_equity = start_cash * (price / bh_start_price) if bh_start_price else start_cash
            buy_hold_curve.append(bh_equity)
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak * 100 if peak else 0.0
            drawdowns.append(drawdown)
            ts = datetime.fromtimestamp(window[-1][0] / 1000, tz=timezone.utc)
            timestamps.append(ts)

        end_cash = cash + position * ohlcv[-1][4]
        max_dd = max(drawdowns) if drawdowns else 0.0
        return BacktestResult(
            start_cash=start_cash,
            end_cash=end_cash,
            trades=trades,
            wins=wins,
            max_dd=max_dd,
            equity_curve=equity_curve,
            drawdowns=drawdowns,
            timestamps=timestamps,
            buy_hold_curve=buy_hold_curve,
        )
