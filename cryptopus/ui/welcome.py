"""Getting Started wizard shown on first launch."""
from __future__ import annotations

import os
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cryptopus.ui import App

_FLAG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".welcome_shown")

_STEPS = [
    {
        "title": "Welcome to Cryptopus Trader!",
        "body": (
            "This app lets you backtest and run crypto trading strategies.\n\n"
            "You can start safely - the app runs in PAPER TRADING mode by default, "
            "meaning no real money is used until you explicitly enable live trading.\n\n"
            "Let's walk through the basics."
        ),
    },
    {
        "title": "Step 1: Pick a Strategy",
        "body": (
            "Go to the STRATEGY tab and choose from 5 built-in strategies:\n\n"
            "  Momentum - rides trends\n"
            "  Mean Reversion - buys dips, sells rallies\n"
            "  Breakout - catches big price moves\n"
            "  Scalping - many small trades in tight ranges\n"
            "  Contra-Momentum - fades sharp moves\n\n"
            "Each strategy has a description explaining how it works. "
            "Start with Momentum or Mean Reversion - they are the easiest to understand."
        ),
    },
    {
        "title": "Step 2: Backtest First",
        "body": (
            "Before risking anything, go to the BACKTEST tab.\n\n"
            "Each strategy has its own sub-tab where you can:\n"
            "  - Choose a symbol (e.g. BTC/USD)\n"
            "  - Set starting cash (e.g. $1,000)\n"
            "  - Click 'Run Backtest' to simulate\n\n"
            "You'll see the return %, win rate, equity curve, and drawdown chart. "
            "The 'Compare' tab runs ALL strategies side-by-side so you can see which "
            "performs best.\n\n"
            "A buy-and-hold benchmark line shows what would happen if you just bought "
            "and held the asset - your strategy should aim to beat it."
        ),
    },
    {
        "title": "Step 3: Configure Risk",
        "body": (
            "Go to the SETTINGS tab to adjust risk controls:\n\n"
            "  BASIC settings (start here):\n"
            "    - Exchange & Symbol: which market to trade\n"
            "    - Timeframe: candle size (5m = 5-minute candles)\n\n"
            "  RISK settings (important!):\n"
            "    - Stop Loss %: auto-sell if price drops this far (e.g. 2%)\n"
            "    - Take Profit %: auto-sell if price rises this far (e.g. 3%)\n"
            "    - Max Daily Loss: stop trading if you lose this much in a day\n\n"
            "Hover over any field for an explanation."
        ),
    },
    {
        "title": "Step 4: Paper Trade",
        "body": (
            "Once you're happy with a strategy and settings:\n\n"
            "  1. Go to OVERVIEW tab\n"
            "  2. Click 'Toggle Strategy' to start\n"
            "  3. Watch the POSITIONS tab for trades\n"
            "  4. Watch the LOGS tab for activity\n"
            "  5. Check the P&L chart on the Overview tab\n\n"
            "The strategy runs automatically. Use the red EMERGENCY STOP button "
            "if you need to halt everything immediately.\n\n"
            "When you're confident, you can enable live trading in Settings "
            "(requires exchange API keys in config.json)."
        ),
    },
]


def should_show_welcome() -> bool:
    return not os.path.exists(_FLAG_FILE)


def mark_welcome_shown() -> None:
    try:
        with open(_FLAG_FILE, "w") as f:
            f.write("1")
    except OSError:
        pass


def show_welcome(app: App) -> None:
    """Show the Getting Started wizard dialog."""
    dialog = tk.Toplevel(app)
    dialog.title("Getting Started")
    dialog.geometry("560x420")
    dialog.resizable(False, False)
    dialog.transient(app)
    dialog.grab_set()

    # Center on parent
    dialog.update_idletasks()
    x = app.winfo_x() + (app.winfo_width() - 560) // 2
    y = app.winfo_y() + (app.winfo_height() - 420) // 2
    dialog.geometry(f"+{x}+{y}")

    step_idx = [0]

    # Title
    title_label = ttk.Label(dialog, text=_STEPS[0]["title"], font=("Segoe UI", 14, "bold"))
    title_label.pack(pady=(16, 8), padx=20)

    # Body
    body_text = tk.Text(
        dialog, wrap="word", height=14, font=("Segoe UI", 10),
        relief="flat", bg=dialog.cget("bg"), padx=10, pady=4,
    )
    body_text.pack(fill="both", expand=True, padx=20)
    body_text.insert("1.0", _STEPS[0]["body"])
    body_text.configure(state="disabled")

    # Progress indicator
    progress_label = ttk.Label(dialog, text=f"1 / {len(_STEPS)}", font=("Segoe UI", 9))
    progress_label.pack(pady=(4, 0))

    # Buttons
    btn_frame = ttk.Frame(dialog)
    btn_frame.pack(pady=(4, 16), padx=20, fill="x")

    dont_show = tk.BooleanVar(value=True)
    ttk.Checkbutton(btn_frame, text="Don't show again", variable=dont_show).pack(side="left")

    def _close() -> None:
        if dont_show.get():
            mark_welcome_shown()
        dialog.destroy()

    def _update_step() -> None:
        step = _STEPS[step_idx[0]]
        title_label.config(text=step["title"])
        body_text.configure(state="normal")
        body_text.delete("1.0", "end")
        body_text.insert("1.0", step["body"])
        body_text.configure(state="disabled")
        progress_label.config(text=f"{step_idx[0] + 1} / {len(_STEPS)}")
        back_btn.config(state="normal" if step_idx[0] > 0 else "disabled")
        if step_idx[0] == len(_STEPS) - 1:
            next_btn.config(text="Get Started!")
        else:
            next_btn.config(text="Next")

    def _next() -> None:
        if step_idx[0] >= len(_STEPS) - 1:
            _close()
        else:
            step_idx[0] += 1
            _update_step()

    def _back() -> None:
        if step_idx[0] > 0:
            step_idx[0] -= 1
            _update_step()

    back_btn = ttk.Button(btn_frame, text="Back", command=_back, state="disabled")
    back_btn.pack(side="right", padx=(6, 0))
    next_btn = ttk.Button(btn_frame, text="Next", command=_next)
    next_btn.pack(side="right")
    skip_btn = ttk.Button(btn_frame, text="Skip", command=_close)
    skip_btn.pack(side="right", padx=(0, 6))
