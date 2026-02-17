import json
import queue
from tkinter import ttk, messagebox
from typing import Dict

import tkinter as tk

try:
    import customtkinter as ctk
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    _CTK_BASE = ctk.CTk
except ImportError:
    ctk = None  # type: ignore[assignment]
    _CTK_BASE = tk.Tk  # type: ignore[misc,assignment]

from cryptopus import APP_TITLE
from cryptopus.config import AppConfig, validate_config
from cryptopus.data_engine import DataEngine
from cryptopus.events import EventBus
from cryptopus.logger import Logger
from cryptopus.persistence import TradeStore
from cryptopus.runner import StrategyRunner
from cryptopus.strategies import STRATEGIES
from cryptopus.trader import Trader

from cryptopus.ui.overview import build_overview
from cryptopus.ui.market import build_market
from cryptopus.ui.strategy_tab import build_strategy
from cryptopus.ui.positions import build_positions
from cryptopus.ui.settings import build_settings
from cryptopus.ui.backtest_tab import build_backtest
from cryptopus.ui.logs import build_logs
from cryptopus.ui.welcome import should_show_welcome, show_welcome


class App(_CTK_BASE):  # type: ignore[misc]
    def __init__(self) -> None:
        super().__init__()
        self.ctk = ctk
        self.title(APP_TITLE)
        self.geometry("1200x780")

        self.log_queue: queue.Queue = queue.Queue()
        self.logger = Logger(self.log_queue)
        self.events = EventBus()

        self.config_state = AppConfig()
        self.store = TradeStore()
        self.keys = self._load_keys()
        self.data_engine = DataEngine(self.config_state, self.logger, self.keys, self.events)
        self.trader = Trader(self.config_state, self.data_engine, self.logger, self.store, self.events)
        self.runner = StrategyRunner(self.config_state, self.data_engine, self.trader, self.logger, self.events)
        self.runner.start()
        self.compare_plot: Dict = {
            "equity": {"canvas": None, "fig": None, "ax": None, "info": None},
            "returns": {"canvas": None, "fig": None, "ax": None, "info": None},
        }

        self._build_ui()
        self._poll_logs()

        if should_show_welcome():
            self.after(300, lambda: show_welcome(self))

    def _load_keys(self) -> Dict[str, Dict[str, str]]:
        try:
            with open("config.json", "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return validate_config(data, self.logger.log)
        except FileNotFoundError:
            self.logger.log("config.json not found; running without exchange API keys.")
            return {}
        except json.JSONDecodeError as exc:
            messagebox.showerror("Config Error", f"config.json is not valid JSON:\n{exc}")
            return {}
        except Exception as exc:
            messagebox.showerror("Config Error", str(exc))
            return {}

    def _build_ui(self) -> None:
        # Apply dark-friendly ttk styles for Treeview and other ttk widgets
        style = ttk.Style(self)
        style.theme_use("clam")
        if ctk and ctk.get_appearance_mode() == "Dark":
            style.configure("Treeview", background="#2b2b2b", foreground="#dcdcdc",
                            fieldbackground="#2b2b2b", rowheight=24)
            style.configure("Treeview.Heading", background="#3b3b3b", foreground="#ffffff",
                            font=("Segoe UI", 9, "bold"))
            style.map("Treeview", background=[("selected", "#1f6aa5")])

        if ctk:
            self._build_ctk_tabs()
        else:
            self._build_ttk_tabs()

    def _build_ctk_tabs(self) -> None:
        tabview = ctk.CTkTabview(self, segmented_button_selected_color="#1f6aa5")
        tabview.pack(fill="both", expand=True, padx=8, pady=8)

        tabview.add("Overview")
        tabview.add("Market")
        tabview.add("Strategy")
        tabview.add("Positions")
        tabview.add("Settings")
        tabview.add("Backtest")
        tabview.add("Logs")

        self.tab_overview = tabview.tab("Overview")
        self.tab_market = tabview.tab("Market")
        self.tab_strategy = tabview.tab("Strategy")
        self.tab_positions = tabview.tab("Positions")
        self.tab_settings = tabview.tab("Settings")
        self.tab_backtest = tabview.tab("Backtest")
        self.tab_logs = tabview.tab("Logs")

        build_overview(self.tab_overview, self)
        build_market(self.tab_market, self)
        build_strategy(self.tab_strategy, self)
        build_positions(self.tab_positions, self)
        build_settings(self.tab_settings, self)
        build_backtest(self.tab_backtest, self)
        build_logs(self.tab_logs, self)

    def _build_ttk_tabs(self) -> None:
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

        build_overview(self.tab_overview, self)
        build_market(self.tab_market, self)
        build_strategy(self.tab_strategy, self)
        build_positions(self.tab_positions, self)
        build_settings(self.tab_settings, self)
        build_backtest(self.tab_backtest, self)
        build_logs(self.tab_logs, self)

    # ---- Action handlers (called by tab builders) ----

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
        self.overview_price.configure(text=f"Last Price: {price:.2f} ({symbol}) [{source}]")

        self.market_tree.delete(*self.market_tree.get_children())
        for key, value in ticker.items():
            self.market_tree.insert("", "end", values=(key, value))

    def _select_strategy(self, selection: str) -> None:
        for strat in STRATEGIES:
            if strat.name == selection:
                self.runner.strategy = strat
                self.overview_status.configure(text=f"Strategy: {strat.name}")
                self.logger.log(f"Selected strategy: {strat.name}")
                return

    def _update_strategy_settings(self) -> None:
        try:
            self.config_state.trade_size = float(self.trade_size_var.get())
            self.config_state.use_atr_sizing = self.atr_sizing_var.get()
            self.config_state.risk_per_trade_pct = float(self.risk_pct_var.get())
            self.logger.log(
                f"Strategy settings updated: size={self.config_state.trade_size}, "
                f"ATR sizing={'on' if self.config_state.use_atr_sizing else 'off'}, "
                f"risk/trade={self.config_state.risk_per_trade_pct}%"
            )
        except ValueError:
            messagebox.showerror("Invalid Input", "Trade size and risk % must be numbers.")

    def _toggle_strategy(self) -> None:
        self.runner.active = not self.runner.active
        status = "running" if self.runner.active else "stopped"
        self.overview_status.configure(text=f"Strategy: {status}")
        self.logger.log(f"Strategy runner {status}.")

    def _emergency_stop(self) -> None:
        if not messagebox.askyesno("Emergency Stop", "This will STOP the strategy and SELL all open positions.\n\nProceed?"):
            return
        self.runner.active = False
        self.overview_status.configure(text="Strategy: EMERGENCY STOPPED")
        self.logger.log("EMERGENCY STOP activated.")
        self.events.emit("emergency_stop")
        for symbol, pos in list(self.trader.positions.items()):
            if pos.amount > 0:
                ticker = self.data_engine.fetch_ticker(symbol)
                price = ticker.get("last", 0) if ticker else 0
                if price > 0:
                    self.trader.place_order(symbol, "sell", pos.amount, price)
                    self.logger.log(f"EMERGENCY: sold {pos.amount} {symbol} @ {price:.2f}")
                else:
                    self.logger.log(f"EMERGENCY: could not get price for {symbol}, position NOT closed.")

    def _refresh_positions(self) -> None:
        self.positions_tree.delete(*self.positions_tree.get_children())
        for pos in self.trader.positions.values():
            self.positions_tree.insert(
                "", "end",
                values=(pos.symbol, pos.amount, f"{pos.avg_price:.2f}", f"{pos.realized_pnl:.2f}"),
            )

        self.orders_tree.delete(*self.orders_tree.get_children())
        for order in self.trader.orders[-50:]:
            self.orders_tree.insert(
                "", "end",
                values=(
                    order.ts.strftime("%Y-%m-%d %H:%M:%S"),
                    order.symbol,
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
            self.config_state.stop_loss_pct = float(self.sl_var.get())
            self.config_state.take_profit_pct = float(self.tp_var.get())
        except ValueError:
            messagebox.showerror("Invalid Input", "Max daily loss, cooldown, SL, and TP must be numeric.")
            return
        self.data_engine.set_exchange(self.config_state.exchange)
        self.logger.log(
            f"Settings saved. SL={self.config_state.stop_loss_pct}%, TP={self.config_state.take_profit_pct}%"
        )

    def _poll_logs(self) -> None:
        while not self.log_queue.empty():
            msg = self.log_queue.get()
            self.log_text.configure(state="normal")
            self.log_text.insert("end", msg + "\n")
            self.log_text.configure(state="disabled")
            self.log_text.see("end")
        self.after(500, self._poll_logs)
