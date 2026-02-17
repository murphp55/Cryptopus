from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cryptopus.ui import App


def build_positions(frame: tk.Widget, app: App) -> None:
    ctk = app.ctk
    Frame = ctk.CTkFrame if ctk else ttk.Frame
    Button = ctk.CTkButton if ctk else ttk.Button

    app.positions_tree = ttk.Treeview(frame, columns=("symbol", "amount", "avg_price", "pnl"), show="headings", height=8)
    for col, text, width in [
        ("symbol", "Symbol", 120),
        ("amount", "Amount", 120),
        ("avg_price", "Avg Price", 120),
        ("pnl", "Realized PnL", 120),
    ]:
        app.positions_tree.heading(col, text=text)
        app.positions_tree.column(col, width=width)
    app.positions_tree.pack(padx=20, pady=6, fill="x")

    app.orders_tree = ttk.Treeview(frame, columns=("time", "symbol", "side", "price", "amount", "status"), show="headings", height=8)
    for col, text, width in [
        ("time", "Time", 160),
        ("symbol", "Symbol", 100),
        ("side", "Side", 80),
        ("price", "Price", 120),
        ("amount", "Amount", 120),
        ("status", "Status", 100),
    ]:
        app.orders_tree.heading(col, text=text)
        app.orders_tree.column(col, width=width)
    app.orders_tree.pack(padx=20, pady=6, fill="x")

    button_row = Frame(frame)
    button_row.pack(pady=4)
    Button(button_row, text="Refresh Positions", command=app._refresh_positions).pack(side="left", padx=6)
