from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

from cryptopus.ui.tooltip import ToolTip

if TYPE_CHECKING:
    from cryptopus.ui import App


def build_settings(frame: ttk.Frame, app: App) -> None:
    ctk = app.ctk
    Frame = ctk.CTkFrame if ctk else ttk.Frame
    Label = ctk.CTkLabel if ctk else ttk.Label
    Group = ctk.CTkFrame if ctk else ttk.LabelFrame
    Entry = ctk.CTkEntry if ctk else ttk.Entry
    OptionMenu = ctk.CTkOptionMenu if ctk else ttk.OptionMenu
    Button = ctk.CTkButton if ctk else ttk.Button

    if ctk:
        inner = ctk.CTkScrollableFrame(frame)
        inner.pack(fill="both", expand=True, padx=4, pady=4)
    else:
        # Scrollable canvas for long settings
        canvas = tk.Canvas(frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    # --- BASIC SETTINGS ---
    if ctk:
        basic = Group(inner)
        Label(basic, text="Basic Settings", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=10, pady=(8, 4))
    else:
        basic = Group(inner, text="Basic Settings", padding=10)
    basic.pack(pady=(12, 6), padx=20, fill="x")

    # Exchange
    row = Frame(basic)
    row.pack(fill="x", pady=2)
    lbl = Label(row, text="Exchange")
    lbl.pack(side="left")
    ToolTip(lbl, "Which crypto exchange to connect to.\nRequires API keys in config.json for live trading.")
    app.exchange_var = tk.StringVar(value=app.config_state.exchange)
    exchange_options = ["coinbase", "kraken", "binance", "bybit", "alpaca"]
    if ctk:
        OptionMenu(row, values=exchange_options, variable=app.exchange_var).pack(side="left", padx=8)
    else:
        OptionMenu(row, app.exchange_var, exchange_options[0], *exchange_options).pack(side="left", padx=8)

    # Symbol
    row = Frame(basic)
    row.pack(fill="x", pady=2)
    lbl = Label(row, text="Symbol")
    lbl.pack(side="left")
    ToolTip(lbl, "The trading pair to watch and trade.\nBTC/USD = Bitcoin priced in US dollars.")
    app.symbol_var = tk.StringVar(value=app.config_state.symbol)
    symbol_options = ["BTC/USD", "ETH/USD", "SOL/USD", "ADA/USD", "AVAX/USD"]
    if ctk:
        OptionMenu(row, values=symbol_options, variable=app.symbol_var).pack(side="left", padx=8)
    else:
        OptionMenu(row, app.symbol_var, symbol_options[0], *symbol_options).pack(side="left", padx=8)

    # Timeframe
    row = Frame(basic)
    row.pack(fill="x", pady=2)
    lbl = Label(row, text="Timeframe")
    lbl.pack(side="left")
    ToolTip(lbl, "Size of each candle used by the strategy.\n1m = 1 minute, 5m = 5 minutes, 1h = 1 hour.\nSmaller = more trades but more noise.")
    app.timeframe_var = tk.StringVar(value=app.config_state.timeframe)
    timeframe_options = ["1m", "5m", "15m", "1h", "4h"]
    if ctk:
        OptionMenu(row, values=timeframe_options, variable=app.timeframe_var).pack(side="left", padx=8)
    else:
        OptionMenu(row, app.timeframe_var, timeframe_options[1], *timeframe_options).pack(side="left", padx=8)

    # Poll seconds
    row = Frame(basic)
    row.pack(fill="x", pady=2)
    lbl = Label(row, text="Poll seconds")
    lbl.pack(side="left")
    ToolTip(lbl, "How often the strategy checks for new data (in seconds).\nLower = more responsive but uses more API calls.")
    app.poll_var = tk.StringVar(value=str(app.config_state.poll_seconds))
    Entry(row, textvariable=app.poll_var, width=80 if ctk else 6).pack(side="left", padx=8)

    # --- CONNECTION SETTINGS ---
    if ctk:
        conn = Group(inner)
        Label(conn, text="Connection", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=10, pady=(8, 4))
    else:
        conn = Group(inner, text="Connection", padding=10)
    conn.pack(pady=6, padx=20, fill="x")

    app.live_var = tk.BooleanVar(value=app.config_state.live_trading)
    cb = ctk.CTkCheckBox(conn, text="Live trading (uses real money via API keys)", variable=app.live_var) if ctk else ttk.Checkbutton(conn, text="Live trading (uses real money via API keys)", variable=app.live_var)
    cb.pack(anchor="w", pady=2)
    ToolTip(cb, "OFF = paper trading (simulated, no real money).\nON = real orders sent to the exchange. Requires valid API keys.")

    app.ws_var = tk.BooleanVar(value=app.config_state.enable_websocket)
    cb = ctk.CTkCheckBox(conn, text="Enable Coinbase WebSocket (real-time prices)", variable=app.ws_var) if ctk else ttk.Checkbutton(conn, text="Enable Coinbase WebSocket (real-time prices)", variable=app.ws_var)
    cb.pack(anchor="w", pady=2)
    ToolTip(cb, "Get price updates in real-time via WebSocket instead of polling.\nOnly works with Coinbase. Falls back to REST if disabled.")

    # --- RISK SETTINGS ---
    if ctk:
        risk = Group(inner)
        Label(risk, text="Risk Controls", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=10, pady=(8, 4))
    else:
        risk = Group(inner, text="Risk Controls", padding=10)
    risk.pack(pady=6, padx=20, fill="x")

    # Stop loss
    row = Frame(risk)
    row.pack(fill="x", pady=2)
    lbl = Label(row, text="Stop loss (%)")
    lbl.pack(side="left")
    ToolTip(lbl, "Automatically sell if price drops this % below your entry price.\n2% means: bought at $100, auto-sell at $98.\nProtects against large losses.")
    app.sl_var = tk.StringVar(value=str(app.config_state.stop_loss_pct))
    Entry(row, textvariable=app.sl_var, width=100 if ctk else 10).pack(side="left", padx=8)

    # Take profit
    row = Frame(risk)
    row.pack(fill="x", pady=2)
    lbl = Label(row, text="Take profit (%)")
    lbl.pack(side="left")
    ToolTip(lbl, "Automatically sell if price rises this % above your entry price.\n3% means: bought at $100, auto-sell at $103.\nLocks in gains.")
    app.tp_var = tk.StringVar(value=str(app.config_state.take_profit_pct))
    Entry(row, textvariable=app.tp_var, width=100 if ctk else 10).pack(side="left", padx=8)

    # Max daily loss
    row = Frame(risk)
    row.pack(fill="x", pady=2)
    lbl = Label(row, text="Max daily loss (USD)")
    lbl.pack(side="left")
    ToolTip(lbl, "Stop all trading for the day if total losses exceed this amount.\nPrevents catastrophic drawdowns from bad market conditions.")
    app.max_loss_var = tk.StringVar(value=str(app.config_state.max_daily_loss))
    Entry(row, textvariable=app.max_loss_var, width=100 if ctk else 10).pack(side="left", padx=8)

    # Cooldown
    row = Frame(risk)
    row.pack(fill="x", pady=2)
    lbl = Label(row, text="Cooldown seconds")
    lbl.pack(side="left")
    ToolTip(lbl, "Minimum seconds to wait between trades.\nPrevents rapid-fire trading after a signal.\n90s is a safe default.")
    app.cooldown_var = tk.StringVar(value=str(app.config_state.cooldown_seconds))
    Entry(row, textvariable=app.cooldown_var, width=100 if ctk else 10).pack(side="left", padx=8)

    # Save button
    btn_row = Frame(inner)
    btn_row.pack(pady=12, padx=20)
    Button(btn_row, text="Save Settings", command=app._save_settings).pack(side="left", padx=6)
