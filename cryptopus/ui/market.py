from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cryptopus.ui import App


def build_market(frame: tk.Widget, app: App) -> None:
    ctk = app.ctk
    Frame = ctk.CTkFrame if ctk else ttk.Frame
    Button = ctk.CTkButton if ctk else ttk.Button

    app.market_tree = ttk.Treeview(frame, columns=("field", "value"), show="headings", height=12)
    app.market_tree.heading("field", text="Field")
    app.market_tree.heading("value", text="Value")
    app.market_tree.column("field", width=200)
    app.market_tree.column("value", width=400)
    app.market_tree.pack(padx=20, pady=6, fill="x")

    button_row = Frame(frame)
    button_row.pack(pady=4)
    Button(button_row, text="Fetch Ticker", command=app._refresh_price).pack(side="left", padx=6)
