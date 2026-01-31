import json
import queue
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Tuple

import tkinter as tk
from tkinter import ttk, messagebox

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # type: ignore
    from matplotlib.figure import Figure  # type: ignore
    from matplotlib import dates as mdates  # type: ignore
except Exception:
    FigureCanvasTkAgg = None
    Figure = None
    mdates = None

try:
    import ccxt  # type: ignore
except Exception:
    ccxt = None

try:
    import requests  # type: ignore
except Exception:
    requests = None

try:
    import websocket  # type: ignore
except Exception:
    websocket = None


APP_TITLE = "Cryptopus Trader"


@dataclass
class AppConfig:
    exchange: str = "coinbase"
    symbol: str = "BTC/USD"
    timeframe: str = "5m"
    live_trading: bool = False
    enable_websocket: bool = True
    trade_size: float = 0.001
    poll_seconds: int = 5
    max_daily_loss: float = 150.0
    cooldown_seconds: int = 90
    fee_rate: float = 0.001
    backtest_cash: float = 1000.0


@dataclass
class Order:
    ts: datetime
    side: str
    price: float
    amount: float
    status: str
    exchange_id: Optional[str] = None


@dataclass
class Position:
    symbol: str
    amount: float = 0.0
    avg_price: float = 0.0
    realized_pnl: float = 0.0


class Logger:
    def __init__(self, log_queue: queue.Queue):
        self.log_queue = log_queue

    def log(self, msg: str) -> None:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        self.log_queue.put(f"[{ts}] {msg}")


class WebSocketPriceFeed(threading.Thread):
    def __init__(self, symbol: str, logger: Logger, on_price: Callable[[str, float], None]):
        super().__init__(daemon=True)
        self.symbol = symbol
        self.logger = logger
        self.on_price = on_price
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        product_id = self.symbol.replace("/", "-")

        def on_open(ws):  # type: ignore
            sub = {"type": "subscribe", "product_ids": [product_id], "channels": ["ticker"]}
            ws.send(json.dumps(sub))
            self.logger.log(f"Websocket subscribed: {product_id}")

        def on_message(ws, message):  # type: ignore
            if self._stop_event.is_set():
                ws.close()
                return
            try:
                data = json.loads(message)
                if data.get("type") != "ticker":
                    return
                price = data.get("price")
                if price is None:
                    return
                self.on_price(self.symbol, float(price))
            except Exception as exc:
                self.logger.log(f"Websocket parse error: {exc}")

        def on_error(ws, error):  # type: ignore
            self.logger.log(f"Websocket error: {error}")

        def on_close(ws, *args):  # type: ignore
            self.logger.log("Websocket closed.")

        while not self._stop_event.is_set():
            try:
                ws_app = websocket.WebSocketApp(
                    "wss://ws-feed.exchange.coinbase.com",
                    on_open=on_open,
                    on_message=on_message,
                    on_error=on_error,
                    on_close=on_close,
                )
                ws_app.run_forever(ping_interval=20, ping_timeout=10)
            except Exception as exc:
                self.logger.log(f"Websocket connection error: {exc}")
            time.sleep(5)


class DataEngine:
    def __init__(self, config: AppConfig, logger: Logger, keys: Dict[str, Dict[str, str]]):
        self.config = config
        self.logger = logger
        self.keys = keys
        self.exchange = None
        self.latest_price: Dict[str, float] = {}
        self._ws_thread: Optional[WebSocketPriceFeed] = None

        if ccxt is not None:
            self.exchange = self._init_exchange()
        self._start_ws_if_needed()

    def _init_exchange(self):
        name = self.config.exchange
        if not hasattr(ccxt, name):
            self.logger.log(f"Exchange '{name}' not found in ccxt. Using public price only.")
            return None
        klass = getattr(ccxt, name)
        creds = self.keys.get(name, {})
        return klass({
            "apiKey": creds.get("apiKey", ""),
            "secret": creds.get("secret", ""),
            "password": creds.get("password", ""),
            "enableRateLimit": True,
        })

    def set_exchange(self, name: str) -> None:
        self.config.exchange = name
        if ccxt is not None:
            self.exchange = self._init_exchange()
        self._start_ws_if_needed()

    def fetch_ticker(self, symbol: str) -> Optional[Dict]:
        if symbol in self.latest_price:
            return {"last": self.latest_price[symbol], "symbol": symbol, "source": "websocket"}
        if self.exchange is not None:
            try:
                return self.exchange.fetch_ticker(symbol)
            except Exception as exc:
                self.logger.log(f"Ticker fetch failed: {exc}")
        return self._fetch_public_price(symbol)

    def _fetch_public_price(self, symbol: str) -> Optional[Dict]:
        if requests is None:
            return None
        base = symbol.split("/")[0].lower()
        try:
            resp = requests.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "bitcoin,ethereum,solana,cardano,avalanche-2", "vs_currencies": "usd"},
                timeout=5,
            )
            resp.raise_for_status()
            data = resp.json()
            mapping = {
                "btc": "bitcoin",
                "eth": "ethereum",
                "sol": "solana",
                "ada": "cardano",
                "avax": "avalanche-2",
            }
            key = mapping.get(base)
            if not key or key not in data:
                return None
            price = float(data[key]["usd"])
            return {"last": price, "symbol": symbol}
        except Exception as exc:
            self.logger.log(f"Public price fetch failed: {exc}")
            return None

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> Optional[List[List[float]]]:
        if self.exchange is None:
            return None
        try:
            return self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        except Exception as exc:
            self.logger.log(f"OHLCV fetch failed: {exc}")
            return None

    def _start_ws_if_needed(self) -> None:
        if self._ws_thread:
            self._ws_thread.stop()
            self._ws_thread = None
        if not self.config.enable_websocket:
            return
        if self.config.exchange != "coinbase":
            return
        if websocket is None:
            self.logger.log("websocket-client not installed; websocket feed disabled.")
            return
        self._ws_thread = WebSocketPriceFeed(
            symbol=self.config.symbol,
            logger=self.logger,
            on_price=self._update_price,
        )
        self._ws_thread.start()

    def _update_price(self, symbol: str, price: float) -> None:
        self.latest_price[symbol] = price


class Trader:
    def __init__(self, config: AppConfig, data_engine: DataEngine, logger: Logger):
        self.config = config
        self.data_engine = data_engine
        self.logger = logger
        self.positions: Dict[str, Position] = {}
        self.orders: List[Order] = []
        self.realized_pnl_today: float = 0.0
        self._pnl_day: Optional[int] = None

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
                    exchange_id=order.get("id"),
                )
                self.logger.log(f"Live order submitted: {side} {amount} {symbol}")
                self._apply_fill(symbol, side, amount, price)
                self.orders.append(record)
                return record
            except Exception as exc:
                self.logger.log(f"Live order failed: {exc}")

        record = Order(
            ts=datetime.now(timezone.utc),
            side=side,
            price=price,
            amount=amount,
            status="paper",
        )
        self._apply_fill(symbol, side, amount, price)
        self.orders.append(record)
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

    def _update_daily_pnl(self, realized: float) -> None:
        day = datetime.now(timezone.utc).timetuple().tm_yday
        if self._pnl_day != day:
            self.realized_pnl_today = 0.0
            self._pnl_day = day
        self.realized_pnl_today += realized


class StrategyBase:
    name = "Base"

    def evaluate(self, ohlcv: List[List[float]]) -> Optional[str]:
        raise NotImplementedError


class MomentumStrategy(StrategyBase):
    name = "Momentum"

    def evaluate(self, ohlcv: List[List[float]]) -> Optional[str]:
        closes = [c[4] for c in ohlcv][-5:]
        if len(closes) < 5:
            return None
        if closes[-1] > closes[0] * 1.002:
            return "buy"
        if closes[-1] < closes[0] * 0.998:
            return "sell"
        return None


class MeanReversionStrategy(StrategyBase):
    name = "Mean Reversion"

    def evaluate(self, ohlcv: List[List[float]]) -> Optional[str]:
        closes = [c[4] for c in ohlcv][-20:]
        if len(closes) < 20:
            return None
        mean = sum(closes) / len(closes)
        last = closes[-1]
        if last < mean * 0.99:
            return "buy"
        if last > mean * 1.01:
            return "sell"
        return None


class BreakoutStrategy(StrategyBase):
    name = "Breakout"

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


class ScalpingStrategy(StrategyBase):
    name = "Scalping"

    def evaluate(self, ohlcv: List[List[float]]) -> Optional[str]:
        closes = [c[4] for c in ohlcv][-10:]
        if len(closes) < 10:
            return None
        spread = max(closes) - min(closes)
        if spread == 0:
            return None
        last = closes[-1]
        if last <= min(closes) + spread * 0.1:
            return "buy"
        if last >= max(closes) - spread * 0.1:
            return "sell"
        return None


class ArbitrageStrategy(StrategyBase):
    name = "Arbitrage (Simulated)"

    def evaluate(self, ohlcv: List[List[float]]) -> Optional[str]:
        if len(ohlcv) < 2:
            return None
        last = ohlcv[-1][4]
        prev = ohlcv[-2][4]
        if last > prev * 1.003:
            return "sell"
        if last < prev * 0.997:
            return "buy"
        return None


STRATEGIES = [
    MomentumStrategy(),
    MeanReversionStrategy(),
    BreakoutStrategy(),
    ScalpingStrategy(),
    ArbitrageStrategy(),
]


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
    ):
        self.start_cash = start_cash
        self.end_cash = end_cash
        self.trades = trades
        self.wins = wins
        self.max_dd = max_dd
        self.equity_curve = equity_curve
        self.drawdowns = drawdowns
        self.timestamps = timestamps

    @property
    def return_pct(self) -> float:
        if self.start_cash == 0:
            return 0.0
        return (self.end_cash - self.start_cash) / self.start_cash * 100

    @property
    def win_rate(self) -> float:
        return (self.wins / self.trades * 100) if self.trades else 0.0


class BacktestEngine:
    def __init__(self, fee_rate: float):
        self.fee_rate = fee_rate

    def run(self, ohlcv: List[List[float]], strategy: StrategyBase, cash: float) -> BacktestResult:
        start_cash = cash
        position = 0.0
        entry_price = 0.0
        trades = 0
        wins = 0
        equity_curve: List[float] = []
        timestamps: List[datetime] = []
        drawdowns: List[float] = []
        peak = 0.0

        for idx in range(20, len(ohlcv)):
            window = ohlcv[: idx + 1]
            price = window[-1][4]
            signal = strategy.evaluate(window)
            if signal == "buy" and cash > 0:
                fee = cash * self.fee_rate
                position = (cash - fee) / price
                entry_price = price
                cash = 0
                trades += 1
            elif signal == "sell" and position > 0:
                proceeds = position * price
                fee = proceeds * self.fee_rate
                cash = proceeds - fee
                if price > entry_price:
                    wins += 1
                position = 0
                trades += 1
            equity = cash + position * price
            equity_curve.append(equity)
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
        )

    def _max_drawdown(self, equity: List[float]) -> float:
        peak = equity[0]
        max_dd = 0.0
        for val in equity:
            if val > peak:
                peak = val
            drawdown = (peak - val) / peak if peak else 0.0
            if drawdown > max_dd:
                max_dd = drawdown
        return max_dd * 100


class StrategyRunner(threading.Thread):
    def __init__(self, config: AppConfig, data_engine: DataEngine, trader: Trader, logger: Logger):
        super().__init__(daemon=True)
        self.config = config
        self.data_engine = data_engine
        self.trader = trader
        self.logger = logger
        self.active = False
        self.strategy: StrategyBase = STRATEGIES[0]
        self._last_trade_ts: Optional[float] = None

    def run(self) -> None:
        self.logger.log("Strategy runner started.")
        while True:
            if self.active:
                self._tick()
            time.sleep(self.config.poll_seconds)

    def _tick(self) -> None:
        ohlcv = self.data_engine.fetch_ohlcv(self.config.symbol, self.config.timeframe, limit=120)
        if not ohlcv:
            return
        if self._risk_blocked():
            return
        signal = self.strategy.evaluate(ohlcv)
        last_price = ohlcv[-1][4]
        if signal in ("buy", "sell"):
            self.trader.place_order(self.config.symbol, signal, self.config.trade_size, last_price)
            self.logger.log(f"{self.strategy.name} signal: {signal} @ {last_price:.2f}")
            self._last_trade_ts = time.time()

    def _risk_blocked(self) -> bool:
        if self.trader.realized_pnl_today <= -self.config.max_daily_loss:
            self.logger.log("Max daily loss hit; strategy paused.")
            return True
        if self._last_trade_ts is not None:
            if time.time() - self._last_trade_ts < self.config.cooldown_seconds:
                return True
        return False


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1100x700")

        self.log_queue: queue.Queue = queue.Queue()
        self.logger = Logger(self.log_queue)

        self.config_state = AppConfig()
        self.keys = self._load_keys()
        self.data_engine = DataEngine(self.config_state, self.logger, self.keys)
        self.trader = Trader(self.config_state, self.data_engine, self.logger)
        self.runner = StrategyRunner(self.config_state, self.data_engine, self.trader, self.logger)
        self.runner.start()
        self.compare_plot = {
            "equity": {"canvas": None, "fig": None, "ax": None, "info": None},
            "returns": {"canvas": None, "fig": None, "ax": None, "info": None},
        }

        self._build_ui()
        self._poll_logs()

    def _load_keys(self) -> Dict[str, Dict[str, str]]:
        try:
            with open("config.json", "r", encoding="utf-8") as handle:
                return json.load(handle).get("exchanges", {})
        except FileNotFoundError:
            return {}
        except Exception as exc:
            messagebox.showerror("Config Error", str(exc))
            return {}

    def _build_ui(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        self.tab_overview = ttk.Frame(notebook)
        self.tab_market = ttk.Frame(notebook)
        self.tab_strategy = ttk.Frame(notebook)
        self.tab_positions = ttk.Frame(notebook)
        self.tab_settings = ttk.Frame(notebook)
        self.tab_backtest = ttk.Frame(notebook)
        self.tab_logs = ttk.Frame(notebook)

        notebook.add(self.tab_overview, text="Overview")
        notebook.add(self.tab_market, text="Market")
        notebook.add(self.tab_strategy, text="Strategy")
        notebook.add(self.tab_positions, text="Positions")
        notebook.add(self.tab_settings, text="Settings")
        notebook.add(self.tab_backtest, text="Backtest")
        notebook.add(self.tab_logs, text="Logs")

        self._build_overview()
        self._build_market()
        self._build_strategy()
        self._build_positions()
        self._build_settings()
        self._build_backtest()
        self._build_logs()

    def _build_overview(self) -> None:
        frame = self.tab_overview
        self.overview_price = ttk.Label(frame, text="Last Price: --", font=("Segoe UI", 14))
        self.overview_price.pack(pady=4)

        self.overview_status = ttk.Label(frame, text="Strategy: stopped", font=("Segoe UI", 12))
        self.overview_status.pack(pady=4)

        button_row = ttk.Frame(frame)
        button_row.pack(pady=4)
        ttk.Button(button_row, text="Refresh Price", command=self._refresh_price).pack(side="left", padx=6)
        ttk.Button(button_row, text="Toggle Strategy", command=self._toggle_strategy).pack(side="left", padx=6)

    def _build_market(self) -> None:
        frame = self.tab_market
        self.market_tree = ttk.Treeview(frame, columns=("field", "value"), show="headings", height=12)
        self.market_tree.heading("field", text="Field")
        self.market_tree.heading("value", text="Value")
        self.market_tree.column("field", width=200)
        self.market_tree.column("value", width=400)
        self.market_tree.pack(padx=20, pady=6, fill="x")

        button_row = ttk.Frame(frame)
        button_row.pack(pady=4)
        ttk.Button(button_row, text="Fetch Ticker", command=self._refresh_price).pack(side="left", padx=6)

    def _build_strategy(self) -> None:
        frame = self.tab_strategy
        self.strategy_var = tk.StringVar(value=STRATEGIES[0].name)
        strategies = [s.name for s in STRATEGIES]
        ttk.Label(frame, text="Active strategy").pack(pady=2)
        ttk.OptionMenu(frame, self.strategy_var, strategies[0], *strategies, command=self._select_strategy).pack(pady=2)

        ttk.Label(frame, text="Trade size (base units)").pack(pady=2)
        self.trade_size_var = tk.StringVar(value=str(self.config_state.trade_size))
        ttk.Entry(frame, textvariable=self.trade_size_var, width=12).pack(pady=2)

        button_row = ttk.Frame(frame)
        button_row.pack(pady=4)
        ttk.Button(button_row, text="Update Strategy Settings", command=self._update_strategy_settings).pack(side="left", padx=6)

    def _build_positions(self) -> None:
        frame = self.tab_positions
        self.positions_tree = ttk.Treeview(frame, columns=("symbol", "amount", "avg_price"), show="headings", height=8)
        for col, text, width in [
            ("symbol", "Symbol", 120),
            ("amount", "Amount", 120),
            ("avg_price", "Avg Price", 120),
        ]:
            self.positions_tree.heading(col, text=text)
            self.positions_tree.column(col, width=width)
        self.positions_tree.pack(padx=20, pady=6, fill="x")

        self.orders_tree = ttk.Treeview(frame, columns=("time", "side", "price", "amount", "status"), show="headings", height=8)
        for col, text, width in [
            ("time", "Time", 160),
            ("side", "Side", 80),
            ("price", "Price", 120),
            ("amount", "Amount", 120),
            ("status", "Status", 100),
        ]:
            self.orders_tree.heading(col, text=text)
            self.orders_tree.column(col, width=width)
        self.orders_tree.pack(padx=20, pady=6, fill="x")

        button_row = ttk.Frame(frame)
        button_row.pack(pady=4)
        ttk.Button(button_row, text="Refresh Positions", command=self._refresh_positions).pack(side="left", padx=6)

    def _build_settings(self) -> None:
        frame = self.tab_settings
        self.exchange_var = tk.StringVar(value=self.config_state.exchange)
        exchange_options = ["coinbase", "kraken", "binance", "bybit", "alpaca"]
        ttk.Label(frame, text="Exchange").pack(pady=2)
        ttk.OptionMenu(frame, self.exchange_var, exchange_options[0], *exchange_options).pack(pady=2)

        self.symbol_var = tk.StringVar(value=self.config_state.symbol)
        ttk.Label(frame, text="Symbol").pack(pady=2)
        symbol_options = ["BTC/USD", "ETH/USD", "SOL/USD", "ADA/USD", "AVAX/USD"]
        ttk.OptionMenu(frame, self.symbol_var, symbol_options[0], *symbol_options).pack(pady=2)

        self.timeframe_var = tk.StringVar(value=self.config_state.timeframe)
        ttk.Label(frame, text="Timeframe").pack(pady=2)
        timeframe_options = ["1m", "5m", "15m", "1h", "4h"]
        ttk.OptionMenu(frame, self.timeframe_var, timeframe_options[1], *timeframe_options).pack(pady=2)

        self.poll_var = tk.StringVar(value=str(self.config_state.poll_seconds))
        ttk.Label(frame, text="Poll seconds").pack(pady=2)
        ttk.Entry(frame, textvariable=self.poll_var, width=6).pack(pady=2)

        self.live_var = tk.BooleanVar(value=self.config_state.live_trading)
        ttk.Checkbutton(frame, text="Live trading (uses API keys)", variable=self.live_var).pack(pady=2)

        self.ws_var = tk.BooleanVar(value=self.config_state.enable_websocket)
        ttk.Checkbutton(frame, text="Enable Coinbase Websocket", variable=self.ws_var).pack(pady=2)

        self.max_loss_var = tk.StringVar(value=str(self.config_state.max_daily_loss))
        ttk.Label(frame, text="Max daily loss (USD)").pack(pady=2)
        ttk.Entry(frame, textvariable=self.max_loss_var, width=10).pack(pady=2)

        self.cooldown_var = tk.StringVar(value=str(self.config_state.cooldown_seconds))
        ttk.Label(frame, text="Cooldown seconds").pack(pady=2)
        ttk.Entry(frame, textvariable=self.cooldown_var, width=10).pack(pady=2)

        button_row = ttk.Frame(frame)
        button_row.pack(pady=4)
        ttk.Button(button_row, text="Save Settings", command=self._save_settings).pack(side="left", padx=6)

    def _build_backtest(self) -> None:
        frame = self.tab_backtest
        sub_notebook = ttk.Notebook(frame)
        sub_notebook.pack(fill="both", expand=True, padx=6, pady=2)

        compare_tab = ttk.Frame(sub_notebook)
        sub_notebook.add(compare_tab, text="Compare")
        self._build_backtest_compare(compare_tab)

        compare_returns_tab = ttk.Frame(sub_notebook)
        sub_notebook.add(compare_returns_tab, text="Compare Returns")
        self._build_backtest_compare_returns(compare_returns_tab)

        for strat in STRATEGIES:
            tab = ttk.Frame(sub_notebook)
            sub_notebook.add(tab, text=strat.name)
            self._build_backtest_tab(tab, strat)

    def _build_backtest_tab(self, frame: ttk.Frame, strategy: StrategyBase) -> None:
        symbol_var = tk.StringVar(value=self.config_state.symbol)
        timeframe_var = tk.StringVar(value=self.config_state.timeframe)
        cash_var = tk.StringVar(value=str(self.config_state.backtest_cash))

        ttk.Label(frame, text=f"{strategy.name} backtest").pack(pady=4)

        input_row = ttk.Frame(frame)
        input_row.pack(pady=2)
        ttk.Label(input_row, text="Symbol").pack(side="left", padx=4)
        options = ["BTC/USD", "ETH/USD", "SOL/USD", "ADA/USD", "AVAX/USD"]
        ttk.OptionMenu(input_row, symbol_var, options[0], *options).pack(side="left", padx=4)
        ttk.Label(input_row, text="Timeframe").pack(side="left", padx=4)
        tf_options = ["1m", "5m", "15m", "1h", "4h"]
        ttk.OptionMenu(input_row, timeframe_var, tf_options[1], *tf_options).pack(side="left", padx=4)
        ttk.Label(input_row, text="Start USD").pack(side="left", padx=4)
        ttk.Entry(input_row, textvariable=cash_var, width=8).pack(side="left", padx=4)

        result_box = tk.Text(frame, height=5, wrap="word", state="disabled")
        result_box.pack(fill="x", padx=10, pady=4)

        plot_frame = ttk.Frame(frame)
        plot_frame.pack(fill="both", expand=True, padx=8, pady=4)

        canvas = None
        if FigureCanvasTkAgg and Figure:
            fig = Figure(figsize=(7.5, 5.2), dpi=100)
            ax_equity = fig.add_subplot(2, 1, 1)
            ax_dd = fig.add_subplot(2, 1, 2, sharex=ax_equity)
            ax_equity.set_title("Equity Curve")
            ax_equity.set_ylabel("USD")
            ax_dd.set_title("Drawdown")
            ax_dd.set_ylabel("%")
            ax_dd.set_xlabel("Time (UTC)")
            fig.tight_layout()
            canvas = FigureCanvasTkAgg(fig, master=plot_frame)
            canvas.get_tk_widget().pack(fill="both", expand=True)
        else:
            ttk.Label(plot_frame, text="matplotlib not installed; plots disabled.").pack(pady=6)

        def run_backtest() -> None:
            try:
                cash = float(cash_var.get())
            except ValueError:
                messagebox.showerror("Invalid Input", "Starting cash must be numeric.")
                return
            ohlcv = self.data_engine.fetch_ohlcv(symbol_var.get(), timeframe_var.get(), limit=500)
            if not ohlcv:
                messagebox.showerror("No Data", "Could not load OHLCV data.")
                return
            engine = BacktestEngine(self.config_state.fee_rate)
            result = engine.run(ohlcv, strategy, cash)
            result_box.configure(state="normal")
            result_box.delete("1.0", "end")
            result_box.insert(
                "end",
                (
                    f"Start: ${cash:.2f}\n"
                    f"End: ${result.end_cash:.2f}\n"
                    f"Return: {result.return_pct:.2f}%\n"
                    f"Trades: {result.trades}\n"
                    f"Win rate: {result.win_rate:.1f}%\n"
                    f"Max drawdown: {result.max_dd:.2f}%\n"
                ),
            )
            result_box.configure(state="disabled")
            if canvas and Figure:
                fig = canvas.figure
                ax_equity = fig.axes[0]
                ax_dd = fig.axes[1]
                ax_equity.clear()
                ax_dd.clear()
                ax_equity.set_title(f"Equity Curve ({symbol_var.get()} {timeframe_var.get()})")
                ax_equity.set_ylabel("USD")
                ax_dd.set_title("Drawdown")
                ax_dd.set_ylabel("%")
                ax_dd.set_xlabel("Time (UTC)")
                ax_equity.plot(result.timestamps, result.equity_curve, color="#2c7fb8")
                ax_dd.plot(result.timestamps, result.drawdowns, color="#d95f0e")
                if mdates:
                    locator = mdates.AutoDateLocator(minticks=3, maxticks=8)
                    formatter = mdates.ConciseDateFormatter(locator)
                    ax_equity.xaxis.set_major_locator(locator)
                    ax_equity.xaxis.set_major_formatter(formatter)
                    ax_dd.xaxis.set_major_locator(locator)
                    ax_dd.xaxis.set_major_formatter(formatter)
                for ax in (ax_equity, ax_dd):
                    for label in ax.get_xticklabels():
                        label.set_rotation(45)
                        label.set_ha("right")
                fig.tight_layout()
                canvas.draw()

        ttk.Button(input_row, text="Run Backtest", command=run_backtest).pack(side="left", padx=6)

    def _build_backtest_compare(self, frame: ttk.Frame) -> None:
        symbol_var = tk.StringVar(value=self.config_state.symbol)
        timeframe_var = tk.StringVar(value=self.config_state.timeframe)
        cash_var = tk.StringVar(value=str(self.config_state.backtest_cash))

        ttk.Label(frame, text="Compare strategies").pack(pady=4)

        input_row = ttk.Frame(frame)
        input_row.pack(pady=2)
        ttk.Label(input_row, text="Symbol").pack(side="left", padx=4)
        options = ["BTC/USD", "ETH/USD", "SOL/USD", "ADA/USD", "AVAX/USD"]
        ttk.OptionMenu(input_row, symbol_var, options[0], *options).pack(side="left", padx=4)
        ttk.Label(input_row, text="Timeframe").pack(side="left", padx=4)
        tf_options = ["1m", "5m", "15m", "1h", "4h"]
        ttk.OptionMenu(input_row, timeframe_var, tf_options[1], *tf_options).pack(side="left", padx=4)
        ttk.Label(input_row, text="Start USD").pack(side="left", padx=4)
        ttk.Entry(input_row, textvariable=cash_var, width=8).pack(side="left", padx=4)

        result_box = tk.Text(frame, height=3, wrap="word", state="disabled")
        result_box.pack(fill="x", padx=10, pady=4)

        metrics_tree = ttk.Treeview(
            frame,
            columns=("strategy", "return", "max_dd", "win_rate", "trades"),
            show="headings",
            height=3,
        )
        def _sort_tree(col: str, descending: bool) -> None:
            rows = []
            for item in metrics_tree.get_children(""):
                value = metrics_tree.set(item, col)
                try:
                    key = float(value)
                except ValueError:
                    key = value
                rows.append((key, item))
            rows.sort(reverse=descending, key=lambda x: x[0])
            for index, (_, item) in enumerate(rows):
                metrics_tree.move(item, "", index)
            metrics_tree.heading(col, command=lambda: _sort_tree(col, not descending))

        metrics_tree.heading("strategy", text="Strategy", command=lambda: _sort_tree("strategy", False))
        metrics_tree.heading("return", text="Return %", command=lambda: _sort_tree("return", True))
        metrics_tree.heading("max_dd", text="Max DD %", command=lambda: _sort_tree("max_dd", True))
        metrics_tree.heading("win_rate", text="Win %", command=lambda: _sort_tree("win_rate", True))
        metrics_tree.heading("trades", text="Trades", command=lambda: _sort_tree("trades", True))
        metrics_tree.column("strategy", width=180)
        metrics_tree.column("return", width=100)
        metrics_tree.column("max_dd", width=100)
        metrics_tree.column("win_rate", width=100)
        metrics_tree.column("trades", width=80)
        metrics_tree.pack(fill="x", padx=10, pady=4)

        def run_compare() -> None:
            try:
                cash = float(cash_var.get())
            except ValueError:
                messagebox.showerror("Invalid Input", "Starting cash must be numeric.")
                return
            ohlcv = self.data_engine.fetch_ohlcv(symbol_var.get(), timeframe_var.get(), limit=800)
            if not ohlcv:
                messagebox.showerror("No Data", "Could not load OHLCV data.")
                return
            engine = BacktestEngine(self.config_state.fee_rate)
            results = []
            for strat in STRATEGIES:
                results.append((strat.name, engine.run(ohlcv, strat, cash)))

            best_return = max(results, key=lambda item: item[1].return_pct)
            best_risk = max(
                results,
                key=lambda item: (item[1].return_pct / item[1].max_dd) if item[1].max_dd > 0 else item[1].return_pct,
            )
            result_box.configure(state="normal")
            result_box.delete("1.0", "end")
            result_box.insert(
                "end",
                f"Best return: {best_return[0]} ({best_return[1].return_pct:.2f}%)\n"
                f"Best risk-adjusted: {best_risk[0]} "
                f"({best_risk[1].return_pct:.2f}% / {best_risk[1].max_dd:.2f}%)\n"
                f"Compared {len(results)} strategies on {symbol_var.get()} {timeframe_var.get()}.\n",
            )
            result_box.configure(state="disabled")

            metrics_tree.delete(*metrics_tree.get_children())
            for name, result in results:
                metrics_tree.insert(
                    "",
                    "end",
                    values=(
                        name,
                        f"{result.return_pct:.2f}",
                        f"{result.max_dd:.2f}",
                        f"{result.win_rate:.1f}",
                        result.trades,
                    ),
                )

            self._update_compare_plot(results, symbol_var.get(), timeframe_var.get())

        ttk.Button(input_row, text="Run Comparison", command=run_compare).pack(side="left", padx=6)

        self._build_backtest_compare_equity(frame)

    def _build_logs(self) -> None:
        frame = self.tab_logs
        self.log_text = tk.Text(frame, height=24, wrap="word", state="disabled")
        self.log_text.pack(padx=12, pady=6, fill="both", expand=True)

    def _build_backtest_compare_equity(self, frame: ttk.Frame) -> None:
        info = ttk.Label(frame, text="Run a comparison to render plots.", font=("Segoe UI", 11))
        info.pack(pady=6)

        plot_frame = ttk.Frame(frame)
        plot_frame.pack(fill="both", expand=True, padx=8, pady=4)

        if FigureCanvasTkAgg and Figure:
            fig = Figure(figsize=(10.5, 7.5), dpi=100)
            ax = fig.add_subplot(1, 1, 1)
            ax.set_title("Equity Curve Comparison")
            ax.set_ylabel("USD")
            fig.tight_layout()
            canvas = FigureCanvasTkAgg(fig, master=plot_frame)
            canvas.get_tk_widget().pack(fill="both", expand=True)
            self.compare_plot["equity"].update({"canvas": canvas, "fig": fig, "ax": ax, "info": info})
        else:
            ttk.Label(plot_frame, text="matplotlib not installed; plots disabled.").pack(pady=6)

    def _build_backtest_compare_returns(self, frame: ttk.Frame) -> None:
        info = ttk.Label(frame, text="Run a comparison to render plots.", font=("Segoe UI", 11))
        info.pack(pady=6)

        plot_frame = ttk.Frame(frame)
        plot_frame.pack(fill="both", expand=True, padx=8, pady=4)

        if FigureCanvasTkAgg and Figure:
            fig = Figure(figsize=(10.5, 7.5), dpi=100)
            ax = fig.add_subplot(1, 1, 1)
            ax.set_title("Return vs Max Drawdown")
            ax.set_ylabel("%")
            fig.tight_layout()
            canvas = FigureCanvasTkAgg(fig, master=plot_frame)
            canvas.get_tk_widget().pack(fill="both", expand=True)
            self.compare_plot["returns"].update({"canvas": canvas, "fig": fig, "ax": ax, "info": info})
        else:
            ttk.Label(plot_frame, text="matplotlib not installed; plots disabled.").pack(pady=6)

    def _update_compare_plot(self, results: List[Tuple[str, BacktestResult]], symbol: str, timeframe: str) -> None:
        equity = self.compare_plot.get("equity", {})
        returns_plot = self.compare_plot.get("returns", {})

        # Equity plot
        eq_canvas = equity.get("canvas")
        eq_ax = equity.get("ax")
        eq_info = equity.get("info")
        if eq_canvas and eq_ax:
            eq_ax.clear()
            eq_ax.set_title(f"Equity Curve Comparison ({symbol} {timeframe})")
            eq_ax.set_ylabel("USD")

            colors = ["#2c7fb8", "#7fcdbb", "#fdae61", "#d95f0e", "#7b3294"]
            for idx, (name, result) in enumerate(results):
                color = colors[idx % len(colors)]
                eq_ax.plot(result.timestamps, result.equity_curve, label=name, color=color)

            eq_ax.legend(loc="best", fontsize=8)
            if results and mdates:
                locator = mdates.AutoDateLocator(minticks=3, maxticks=8)
                formatter = mdates.ConciseDateFormatter(locator)
                eq_ax.xaxis.set_major_locator(locator)
                eq_ax.xaxis.set_major_formatter(formatter)
            for label in eq_ax.get_xticklabels():
                label.set_rotation(45)
                label.set_ha("right")
            if eq_info:
                eq_info.config(text=f"Data: {symbol} {timeframe}, {len(results[0][1].timestamps)} candles (UTC)")
            equity["fig"].tight_layout()
            eq_canvas.draw()

        # Returns plot
        ret_canvas = returns_plot.get("canvas")
        ret_ax = returns_plot.get("ax")
        ret_info = returns_plot.get("info")
        if ret_canvas and ret_ax:
            ret_ax.clear()
            ret_ax.set_title("Return vs Max Drawdown")
            ret_ax.set_ylabel("%")

            names = []
            returns = []
            max_dds = []
            for name, result in results:
                names.append(name)
                returns.append(result.return_pct)
                max_dds.append(result.max_dd)

            x = range(len(names))
            ret_ax.bar([i - 0.2 for i in x], returns, width=0.4, label="Return", color="#2c7fb8")
            ret_ax.bar([i + 0.2 for i in x], max_dds, width=0.4, label="Max DD", color="#d95f0e")
            ret_ax.set_xticks(list(x))
            ret_ax.set_xticklabels(names, rotation=20, ha="right")
            ret_ax.legend(loc="upper right")
            for label in ret_ax.get_xticklabels():
                label.set_rotation(45)
                label.set_ha("right")
            if ret_info:
                ret_info.config(text=f"Data: {symbol} {timeframe}, {len(results[0][1].timestamps)} candles (UTC)")
            returns_plot["fig"].tight_layout()
            ret_canvas.draw()

    def _refresh_price(self) -> None:
        symbol = self.config_state.symbol
        ticker = self.data_engine.fetch_ticker(symbol)
        if not ticker:
            self.logger.log("No ticker available.")
            return
        price = ticker.get("last")
        if price is None:
            return
        source = ticker.get("source", "rest")
        self.overview_price.config(text=f"Last Price: {price:.2f} ({symbol}) [{source}]")

        self.market_tree.delete(*self.market_tree.get_children())
        for key, value in ticker.items():
            self.market_tree.insert("", "end", values=(key, value))

    def _select_strategy(self, selection: str) -> None:
        for strat in STRATEGIES:
            if strat.name == selection:
                self.runner.strategy = strat
                self.overview_status.config(text=f"Strategy: {strat.name}")
                self.logger.log(f"Selected strategy: {strat.name}")
                return

    def _update_strategy_settings(self) -> None:
        try:
            self.config_state.trade_size = float(self.trade_size_var.get())
            self.logger.log(f"Trade size set to {self.config_state.trade_size}")
        except ValueError:
            messagebox.showerror("Invalid Input", "Trade size must be a number.")

    def _toggle_strategy(self) -> None:
        self.runner.active = not self.runner.active
        status = "running" if self.runner.active else "stopped"
        self.overview_status.config(text=f"Strategy: {status}")
        self.logger.log(f"Strategy runner {status}.")

    def _refresh_positions(self) -> None:
        self.positions_tree.delete(*self.positions_tree.get_children())
        for pos in self.trader.positions.values():
            self.positions_tree.insert("", "end", values=(pos.symbol, pos.amount, f"{pos.avg_price:.2f}"))

        self.orders_tree.delete(*self.orders_tree.get_children())
        for order in self.trader.orders[-20:]:
            self.orders_tree.insert(
                "", "end",
                values=(
                    order.ts.strftime("%H:%M:%S"),
                    order.side,
                    f"{order.price:.2f}",
                    order.amount,
                    order.status,
                ),
            )

    def _save_settings(self) -> None:
        self.config_state.exchange = self.exchange_var.get()
        self.config_state.symbol = self.symbol_var.get()
        self.config_state.timeframe = self.timeframe_var.get()
        try:
            self.config_state.poll_seconds = int(self.poll_var.get())
        except ValueError:
            messagebox.showerror("Invalid Input", "Poll seconds must be an integer.")
            return
        self.config_state.live_trading = self.live_var.get()
        self.config_state.enable_websocket = self.ws_var.get()
        try:
            self.config_state.max_daily_loss = float(self.max_loss_var.get())
            self.config_state.cooldown_seconds = int(self.cooldown_var.get())
        except ValueError:
            messagebox.showerror("Invalid Input", "Max daily loss and cooldown must be numeric.")
            return
        self.data_engine.set_exchange(self.config_state.exchange)
        self.logger.log("Settings saved.")

    def _poll_logs(self) -> None:
        while not self.log_queue.empty():
            msg = self.log_queue.get()
            self.log_text.configure(state="normal")
            self.log_text.insert("end", msg + "\n")
            self.log_text.configure(state="disabled")
            self.log_text.see("end")
        self.after(500, self._poll_logs)


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
