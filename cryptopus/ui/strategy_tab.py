from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

from cryptopus.strategies import STRATEGIES
from cryptopus.ui.tooltip import ToolTip

if TYPE_CHECKING:
    from cryptopus.ui import App

# Map strategy names to their description text
_STRATEGY_DESCRIPTIONS = {s.name: s.description for s in STRATEGIES}


def build_strategy(frame: ttk.Frame, app: App) -> None:
    ctk = app.ctk
    Frame = ctk.CTkFrame if ctk else ttk.Frame
    Label = ctk.CTkLabel if ctk else ttk.Label
    Button = ctk.CTkButton if ctk else ttk.Button
    Entry = ctk.CTkEntry if ctk else ttk.Entry
    OptionMenu = ctk.CTkOptionMenu if ctk else ttk.OptionMenu
    Group = ctk.CTkFrame if ctk else ttk.LabelFrame

    app.strategy_var = tk.StringVar(value=STRATEGIES[0].name)
    strategies = [s.name for s in STRATEGIES]

    # Strategy selection row
    sel_row = Frame(frame)
    sel_row.pack(pady=(12, 2), padx=20, fill="x")
    Label(sel_row, text="Active strategy", font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 8))
    if ctk:
        menu = OptionMenu(
            sel_row,
            values=strategies,
            variable=app.strategy_var,
            command=app._select_strategy,
        )
    else:
        menu = OptionMenu(sel_row, app.strategy_var, strategies[0], *strategies, command=app._select_strategy)
    menu.pack(side="left")

    # Strategy description box
    if ctk:
        desc_frame = Group(frame)
        Label(desc_frame, text="Strategy description", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=8, pady=(8, 2))
    else:
        desc_frame = Group(frame, text="Strategy description", padding=8)
    desc_frame.pack(pady=6, padx=20, fill="x")
    app._strategy_desc_label = Label(
        desc_frame,
        text=_STRATEGY_DESCRIPTIONS.get(STRATEGIES[0].name, ""),
        wraplength=500,
        font=("Segoe UI", 9),
    )
    app._strategy_desc_label.pack(anchor="w")

    # Update description when strategy changes
    _orig_select = app._select_strategy

    def _select_with_desc(selection: str) -> None:
        _orig_select(selection)
        app._strategy_desc_label.configure(text=_STRATEGY_DESCRIPTIONS.get(selection, ""))

    app._select_strategy = _select_with_desc  # type: ignore[assignment]
    menu.configure(command=_select_with_desc)

    # Separator
    if ctk:
        divider = ctk.CTkFrame(frame, height=1, fg_color="#3f3f46")
        divider.pack(fill="x", padx=20, pady=6)
    else:
        ttk.Separator(frame, orient="horizontal").pack(fill="x", padx=20, pady=6)

    # Trade size
    size_row = Frame(frame)
    size_row.pack(pady=2, padx=20, fill="x")
    lbl = Label(size_row, text="Trade size (base units)")
    lbl.pack(side="left")
    ToolTip(lbl, "How much of the asset to buy/sell per trade.\nExample: 0.001 BTC means each trade is ~$60-100 at current prices.")
    app.trade_size_var = tk.StringVar(value=str(app.config_state.trade_size))
    Entry(size_row, textvariable=app.trade_size_var, width=120 if ctk else 12).pack(side="left", padx=8)

    # ATR sizing
    atr_row = Frame(frame)
    atr_row.pack(pady=2, padx=20, fill="x")
    app.atr_sizing_var = tk.BooleanVar(value=app.config_state.use_atr_sizing)
    atr_cb = ctk.CTkCheckBox(atr_row, text="Use ATR-based position sizing", variable=app.atr_sizing_var) if ctk else ttk.Checkbutton(atr_row, text="Use ATR-based position sizing", variable=app.atr_sizing_var)
    atr_cb.pack(side="left")
    ToolTip(atr_cb, "Automatically sizes trades based on recent volatility (ATR-14).\nHigher volatility = smaller position to control risk.")

    # Risk per trade
    risk_row = Frame(frame)
    risk_row.pack(pady=2, padx=20, fill="x")
    rlbl = Label(risk_row, text="Risk per trade (% of equity)")
    rlbl.pack(side="left")
    ToolTip(rlbl, "Max percentage of your account value to risk on a single trade.\n1% is conservative. Only used when ATR sizing is enabled.")
    app.risk_pct_var = tk.StringVar(value=str(app.config_state.risk_per_trade_pct))
    Entry(risk_row, textvariable=app.risk_pct_var, width=80 if ctk else 8).pack(side="left", padx=8)

    button_row = Frame(frame)
    button_row.pack(pady=8, padx=20)
    Button(button_row, text="Update Strategy Settings", command=app._update_strategy_settings).pack(side="left", padx=6)
