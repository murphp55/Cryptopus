from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING, List
from datetime import datetime, timezone

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # type: ignore
    from matplotlib.figure import Figure  # type: ignore
    from matplotlib import dates as mdates  # type: ignore
except Exception:
    FigureCanvasTkAgg = None
    Figure = None
    mdates = None

if TYPE_CHECKING:
    from cryptopus.ui import App


def build_overview(frame: tk.Widget, app: App) -> None:
    ctk = app.ctk
    Label = ctk.CTkLabel if ctk else ttk.Label
    Frame = ctk.CTkFrame if ctk else ttk.Frame
    Button = ctk.CTkButton if ctk else ttk.Button
    Group = ctk.CTkFrame if ctk else ttk.LabelFrame

    app.overview_price = Label(frame, text="Last Price: --", font=("Segoe UI", 14))
    app.overview_price.pack(pady=4)

    app.overview_status = Label(frame, text="Strategy: stopped", font=("Segoe UI", 12))
    app.overview_status.pack(pady=4)

    button_row = Frame(frame)
    button_row.pack(pady=4)
    Button(button_row, text="Refresh Price", command=app._refresh_price).pack(side="left", padx=6)
    Button(button_row, text="Toggle Strategy", command=app._toggle_strategy).pack(side="left", padx=6)

    # Kill switch
    emergency_frame = Frame(frame)
    emergency_frame.pack(pady=8)
    if ctk:
        app._emergency_btn = ctk.CTkButton(
            emergency_frame,
            text="EMERGENCY STOP",
            command=app._emergency_stop,
            fg_color="#cc0000",
            hover_color="#a90000",
            font=("Segoe UI", 12, "bold"),
            width=220,
            height=38,
        )
    else:
        app._emergency_btn = tk.Button(
            emergency_frame,
            text="EMERGENCY STOP",
            command=app._emergency_stop,
            bg="#cc0000",
            fg="white",
            font=("Segoe UI", 12, "bold"),
            padx=20,
            pady=8,
        )
    app._emergency_btn.pack()

    # Real-time P&L chart
    if ctk:
        pnl_frame = Group(frame)
    else:
        pnl_frame = Group(frame, text="Session P&L", padding=4)
    pnl_frame.pack(fill="both", expand=True, padx=12, pady=(4, 8))
    if ctk:
        Label(pnl_frame, text="Session P&L", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=8, pady=(6, 2))

    app._pnl_label = Label(pnl_frame, text="Realized P&L today: $0.00", font=("Segoe UI", 10))
    app._pnl_label.pack(anchor="w", padx=4)

    # P&L data storage
    app._pnl_timestamps: List[datetime] = []
    app._pnl_values: List[float] = []

    if FigureCanvasTkAgg and Figure:
        fig = Figure(figsize=(8, 2.5), dpi=100)
        ax = fig.add_subplot(1, 1, 1)
        ax.set_ylabel("P&L ($)", fontsize=9)
        ax.axhline(y=0, color="#999999", linewidth=0.8, linestyle="--")
        ax.set_title("Realized P&L", fontsize=10)
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=pnl_frame)
        canvas.get_tk_widget().pack(fill="both", expand=True)
        app._pnl_canvas = canvas
        app._pnl_fig = fig
        app._pnl_ax = ax
    else:
        app._pnl_canvas = None
        app._pnl_fig = None
        app._pnl_ax = None
        Label(pnl_frame, text="Install matplotlib for live P&L chart.").pack(pady=6)

    # Start polling P&L updates
    _poll_pnl(app)


def _poll_pnl(app: App) -> None:
    """Update the P&L display every 2 seconds."""
    pnl = app.trader.realized_pnl_today
    color = "#006600" if pnl >= 0 else "#cc0000"
    if app.ctk:
        app._pnl_label.configure(text=f"Realized P&L today: ${pnl:+.2f}", text_color=color)
    else:
        app._pnl_label.configure(text=f"Realized P&L today: ${pnl:+.2f}", foreground=color)

    now = datetime.now(timezone.utc)
    app._pnl_timestamps.append(now)
    app._pnl_values.append(pnl)

    # Keep last 500 data points
    if len(app._pnl_timestamps) > 500:
        app._pnl_timestamps = app._pnl_timestamps[-500:]
        app._pnl_values = app._pnl_values[-500:]

    if app._pnl_canvas and app._pnl_ax and len(app._pnl_timestamps) > 1:
        ax = app._pnl_ax
        ax.clear()
        ax.set_ylabel("P&L ($)", fontsize=9)
        ax.set_title("Realized P&L", fontsize=10)
        ax.axhline(y=0, color="#999999", linewidth=0.8, linestyle="--")

        fill_color = "#4CAF50" if pnl >= 0 else "#F44336"
        ax.plot(app._pnl_timestamps, app._pnl_values, color=fill_color, linewidth=1.5)
        ax.fill_between(app._pnl_timestamps, app._pnl_values, 0, alpha=0.15, color=fill_color)

        if mdates:
            locator = mdates.AutoDateLocator(minticks=3, maxticks=6)
            formatter = mdates.ConciseDateFormatter(locator)
            ax.xaxis.set_major_locator(locator)
            ax.xaxis.set_major_formatter(formatter)

        app._pnl_fig.tight_layout()
        app._pnl_canvas.draw_idle()

    app.after(2000, lambda: _poll_pnl(app))
