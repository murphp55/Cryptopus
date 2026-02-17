from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import TYPE_CHECKING, List, Tuple

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # type: ignore
    from matplotlib.figure import Figure  # type: ignore
    from matplotlib import dates as mdates  # type: ignore
except Exception:
    FigureCanvasTkAgg = None
    Figure = None
    mdates = None

from cryptopus.backtest import BacktestEngine, BacktestResult
from cryptopus.strategies import STRATEGIES

if TYPE_CHECKING:
    from cryptopus.ui import App


def build_backtest(frame: tk.Widget, app: App) -> None:
    ctk = app.ctk
    if ctk:
        sub_tabs = ctk.CTkTabview(frame)
        sub_tabs.pack(fill="both", expand=True, padx=6, pady=2)
        sub_tabs.add("Compare")
        sub_tabs.add("Compare Returns")
        _build_compare(sub_tabs.tab("Compare"), app)
        _build_compare_returns(sub_tabs.tab("Compare Returns"), app)
        for strat in STRATEGIES:
            sub_tabs.add(strat.name)
            _build_single(sub_tabs.tab(strat.name), strat, app)
        return

    sub_notebook = ttk.Notebook(frame)
    sub_notebook.pack(fill="both", expand=True, padx=6, pady=2)
    compare_tab = ttk.Frame(sub_notebook)
    sub_notebook.add(compare_tab, text="Compare")
    _build_compare(compare_tab, app)
    compare_returns_tab = ttk.Frame(sub_notebook)
    sub_notebook.add(compare_returns_tab, text="Compare Returns")
    _build_compare_returns(compare_returns_tab, app)
    for strat in STRATEGIES:
        tab = ttk.Frame(sub_notebook)
        sub_notebook.add(tab, text=strat.name)
        _build_single(tab, strat, app)


def _build_single(frame: tk.Widget, strategy, app: App) -> None:  # type: ignore
    ctk = app.ctk
    Label = ctk.CTkLabel if ctk else ttk.Label
    Frame = ctk.CTkFrame if ctk else ttk.Frame
    Entry = ctk.CTkEntry if ctk else ttk.Entry
    OptionMenu = ctk.CTkOptionMenu if ctk else ttk.OptionMenu
    Button = ctk.CTkButton if ctk else ttk.Button

    symbol_var = tk.StringVar(value=app.config_state.symbol)
    timeframe_var = tk.StringVar(value=app.config_state.timeframe)
    cash_var = tk.StringVar(value=str(app.config_state.backtest_cash))
    slippage_var = tk.StringVar(value=str(app.config_state.backtest_slippage_pct))

    Label(frame, text=f"{strategy.name} backtest").pack(pady=4)

    input_row = Frame(frame)
    input_row.pack(pady=2)
    Label(input_row, text="Symbol").pack(side="left", padx=4)
    options = ["BTC/USD", "ETH/USD", "SOL/USD", "ADA/USD", "AVAX/USD"]
    if ctk:
        OptionMenu(input_row, values=options, variable=symbol_var).pack(side="left", padx=4)
    else:
        OptionMenu(input_row, symbol_var, options[0], *options).pack(side="left", padx=4)
    Label(input_row, text="Timeframe").pack(side="left", padx=4)
    tf_options = ["1m", "5m", "15m", "1h", "4h"]
    if ctk:
        OptionMenu(input_row, values=tf_options, variable=timeframe_var).pack(side="left", padx=4)
    else:
        OptionMenu(input_row, timeframe_var, tf_options[1], *tf_options).pack(side="left", padx=4)
    Label(input_row, text="Start USD").pack(side="left", padx=4)
    Entry(input_row, textvariable=cash_var, width=80 if ctk else 8).pack(side="left", padx=4)
    Label(input_row, text="Slippage %").pack(side="left", padx=4)
    Entry(input_row, textvariable=slippage_var, width=70 if ctk else 6).pack(side="left", padx=4)

    if ctk:
        result_box = ctk.CTkTextbox(frame, height=95, wrap="word")
        result_box.configure(state="disabled")
    else:
        result_box = tk.Text(frame, height=5, wrap="word", state="disabled")
    result_box.pack(fill="x", padx=10, pady=4)

    plot_frame = Frame(frame)
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
        Label(plot_frame, text="matplotlib not installed; plots disabled.").pack(pady=6)

    def run_backtest() -> None:
        try:
            cash = float(cash_var.get())
        except ValueError:
            messagebox.showerror("Invalid Input", "Starting cash must be numeric.")
            return
        try:
            slippage = float(slippage_var.get())
        except ValueError:
            slippage = 0.0
        ohlcv = app.data_engine.fetch_ohlcv(symbol_var.get(), timeframe_var.get(), limit=500)
        if not ohlcv:
            messagebox.showerror("No Data", "Could not load OHLCV data.")
            return
        engine = BacktestEngine(
            app.config_state.fee_rate,
            slippage_pct=slippage,
            stop_loss_pct=app.config_state.stop_loss_pct,
            take_profit_pct=app.config_state.take_profit_pct,
        )
        result = engine.run(ohlcv, strategy, cash)
        result_box.configure(state="normal")
        result_box.delete("1.0", "end")
        bh_return = 0.0
        if result.buy_hold_curve and result.buy_hold_curve[0]:
            bh_return = (result.buy_hold_curve[-1] - result.buy_hold_curve[0]) / result.buy_hold_curve[0] * 100
        beat_bh = result.return_pct - bh_return
        result_box.insert(
            "end",
            (
                f"Start: ${cash:.2f}  |  End: ${result.end_cash:.2f}\n"
                f"Strategy return: {result.return_pct:.2f}%  |  Buy & Hold: {bh_return:.2f}%  |  "
                f"{'Beats' if beat_bh >= 0 else 'Trails'} B&H by {abs(beat_bh):.2f}%\n"
                f"Trades: {result.trades}  |  Win rate: {result.win_rate:.1f}%  |  "
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
            ax_equity.plot(result.timestamps, result.equity_curve, color="#2c7fb8", label=strategy.name)
            if result.buy_hold_curve:
                ax_equity.plot(result.timestamps, result.buy_hold_curve, color="#999999", linestyle="--", label="Buy & Hold")
                bh_ret = (result.buy_hold_curve[-1] - result.buy_hold_curve[0]) / result.buy_hold_curve[0] * 100 if result.buy_hold_curve[0] else 0
                ax_equity.legend(loc="best", fontsize=8)
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

    Button(input_row, text="Run Backtest", command=run_backtest).pack(side="left", padx=6)


def _build_compare(frame: tk.Widget, app: App) -> None:
    ctk = app.ctk
    Label = ctk.CTkLabel if ctk else ttk.Label
    Frame = ctk.CTkFrame if ctk else ttk.Frame
    Entry = ctk.CTkEntry if ctk else ttk.Entry
    OptionMenu = ctk.CTkOptionMenu if ctk else ttk.OptionMenu
    Button = ctk.CTkButton if ctk else ttk.Button

    symbol_var = tk.StringVar(value=app.config_state.symbol)
    timeframe_var = tk.StringVar(value=app.config_state.timeframe)
    cash_var = tk.StringVar(value=str(app.config_state.backtest_cash))
    slippage_var = tk.StringVar(value=str(app.config_state.backtest_slippage_pct))

    Label(frame, text="Compare strategies").pack(pady=4)

    input_row = Frame(frame)
    input_row.pack(pady=2)
    Label(input_row, text="Symbol").pack(side="left", padx=4)
    options = ["BTC/USD", "ETH/USD", "SOL/USD", "ADA/USD", "AVAX/USD"]
    if ctk:
        OptionMenu(input_row, values=options, variable=symbol_var).pack(side="left", padx=4)
    else:
        OptionMenu(input_row, symbol_var, options[0], *options).pack(side="left", padx=4)
    Label(input_row, text="Timeframe").pack(side="left", padx=4)
    tf_options = ["1m", "5m", "15m", "1h", "4h"]
    if ctk:
        OptionMenu(input_row, values=tf_options, variable=timeframe_var).pack(side="left", padx=4)
    else:
        OptionMenu(input_row, timeframe_var, tf_options[1], *tf_options).pack(side="left", padx=4)
    Label(input_row, text="Start USD").pack(side="left", padx=4)
    Entry(input_row, textvariable=cash_var, width=80 if ctk else 8).pack(side="left", padx=4)
    Label(input_row, text="Slippage %").pack(side="left", padx=4)
    Entry(input_row, textvariable=slippage_var, width=70 if ctk else 6).pack(side="left", padx=4)

    if ctk:
        result_box = ctk.CTkTextbox(frame, height=65, wrap="word")
        result_box.configure(state="disabled")
    else:
        result_box = tk.Text(frame, height=3, wrap="word", state="disabled")
    result_box.pack(fill="x", padx=10, pady=4)

    metrics_tree = ttk.Treeview(
        frame,
        columns=("strategy", "return", "bh_return", "vs_bh", "max_dd", "win_rate", "trades"),
        show="headings",
        height=4,
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
    metrics_tree.heading("bh_return", text="B&H %", command=lambda: _sort_tree("bh_return", True))
    metrics_tree.heading("vs_bh", text="vs B&H", command=lambda: _sort_tree("vs_bh", True))
    metrics_tree.heading("max_dd", text="Max DD %", command=lambda: _sort_tree("max_dd", True))
    metrics_tree.heading("win_rate", text="Win %", command=lambda: _sort_tree("win_rate", True))
    metrics_tree.heading("trades", text="Trades", command=lambda: _sort_tree("trades", True))
    metrics_tree.column("strategy", width=140)
    metrics_tree.column("return", width=80)
    metrics_tree.column("bh_return", width=70)
    metrics_tree.column("vs_bh", width=70)
    metrics_tree.column("max_dd", width=80)
    metrics_tree.column("win_rate", width=70)
    metrics_tree.column("trades", width=60)
    metrics_tree.pack(fill="x", padx=10, pady=4)

    def run_compare() -> None:
        try:
            cash = float(cash_var.get())
        except ValueError:
            messagebox.showerror("Invalid Input", "Starting cash must be numeric.")
            return
        try:
            slippage = float(slippage_var.get())
        except ValueError:
            slippage = 0.0
        ohlcv = app.data_engine.fetch_ohlcv(symbol_var.get(), timeframe_var.get(), limit=800)
        if not ohlcv:
            messagebox.showerror("No Data", "Could not load OHLCV data.")
            return
        engine = BacktestEngine(
            app.config_state.fee_rate,
            slippage_pct=slippage,
            stop_loss_pct=app.config_state.stop_loss_pct,
            take_profit_pct=app.config_state.take_profit_pct,
        )
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
            bh_ret = 0.0
            if result.buy_hold_curve and result.buy_hold_curve[0]:
                bh_ret = (result.buy_hold_curve[-1] - result.buy_hold_curve[0]) / result.buy_hold_curve[0] * 100
            vs_bh = result.return_pct - bh_ret
            metrics_tree.insert(
                "",
                "end",
                values=(
                    name,
                    f"{result.return_pct:.2f}",
                    f"{bh_ret:.2f}",
                    f"{vs_bh:+.2f}",
                    f"{result.max_dd:.2f}",
                    f"{result.win_rate:.1f}",
                    result.trades,
                ),
            )

        _update_compare_plot(app, results, symbol_var.get(), timeframe_var.get())

    Button(input_row, text="Run Comparison", command=run_compare).pack(side="left", padx=6)

    _build_compare_equity(frame, app)


def _build_compare_equity(frame: tk.Widget, app: App) -> None:
    Label = app.ctk.CTkLabel if app.ctk else ttk.Label
    Frame = app.ctk.CTkFrame if app.ctk else ttk.Frame
    info = Label(frame, text="Run a comparison to render plots.", font=("Segoe UI", 11))
    info.pack(pady=6)

    plot_frame = Frame(frame)
    plot_frame.pack(fill="both", expand=True, padx=8, pady=4)

    if FigureCanvasTkAgg and Figure:
        fig = Figure(figsize=(10.5, 7.5), dpi=100)
        ax = fig.add_subplot(1, 1, 1)
        ax.set_title("Equity Curve Comparison")
        ax.set_ylabel("USD")
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=plot_frame)
        canvas.get_tk_widget().pack(fill="both", expand=True)
        app.compare_plot["equity"].update({"canvas": canvas, "fig": fig, "ax": ax, "info": info})
    else:
        Label(plot_frame, text="matplotlib not installed; plots disabled.").pack(pady=6)


def _build_compare_returns(frame: tk.Widget, app: App) -> None:
    Label = app.ctk.CTkLabel if app.ctk else ttk.Label
    Frame = app.ctk.CTkFrame if app.ctk else ttk.Frame
    info = Label(frame, text="Run a comparison to render plots.", font=("Segoe UI", 11))
    info.pack(pady=6)

    plot_frame = Frame(frame)
    plot_frame.pack(fill="both", expand=True, padx=8, pady=4)

    if FigureCanvasTkAgg and Figure:
        fig = Figure(figsize=(10.5, 7.5), dpi=100)
        ax = fig.add_subplot(1, 1, 1)
        ax.set_title("Return vs Max Drawdown")
        ax.set_ylabel("%")
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=plot_frame)
        canvas.get_tk_widget().pack(fill="both", expand=True)
        app.compare_plot["returns"].update({"canvas": canvas, "fig": fig, "ax": ax, "info": info})
    else:
        Label(plot_frame, text="matplotlib not installed; plots disabled.").pack(pady=6)


def _update_compare_plot(app: App, results: List[Tuple[str, BacktestResult]], symbol: str, timeframe: str) -> None:
    equity = app.compare_plot.get("equity", {})
    returns_plot = app.compare_plot.get("returns", {})

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

        # Add buy-and-hold benchmark (from first result since data is the same)
        if results and results[0][1].buy_hold_curve:
            eq_ax.plot(
                results[0][1].timestamps, results[0][1].buy_hold_curve,
                color="#999999", linestyle="--", linewidth=2, label="Buy & Hold",
            )

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
            eq_info.configure(text=f"Data: {symbol} {timeframe}, {len(results[0][1].timestamps)} candles (UTC)")
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
            ret_info.configure(text=f"Data: {symbol} {timeframe}, {len(results[0][1].timestamps)} candles (UTC)")
        returns_plot["fig"].tight_layout()
        ret_canvas.draw()
