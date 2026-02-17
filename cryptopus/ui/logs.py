from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cryptopus.ui import App


def build_logs(frame: ttk.Frame, app: App) -> None:
    if app.ctk:
        app.log_text = app.ctk.CTkTextbox(frame, height=400, wrap="word")
        app.log_text.configure(state="disabled")
    else:
        app.log_text = tk.Text(frame, height=24, wrap="word", state="disabled")
    app.log_text.pack(padx=12, pady=6, fill="both", expand=True)
