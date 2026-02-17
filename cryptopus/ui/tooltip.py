"""Hover tooltip widget for tkinter."""
from __future__ import annotations

import tkinter as tk


class ToolTip:
    """Show a tooltip when hovering over a widget."""

    def __init__(self, widget: tk.Widget, text: str, wrap_length: int = 300) -> None:
        self.widget = widget
        self.text = text
        self.wrap_length = wrap_length
        self._tip_window: tk.Toplevel | None = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        if self._tip_window:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self._tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw,
            text=self.text,
            justify="left",
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            wraplength=self.wrap_length,
            font=("Segoe UI", 9),
            padx=6,
            pady=4,
        )
        label.pack()

    def _hide(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        if self._tip_window:
            self._tip_window.destroy()
            self._tip_window = None

    def update_text(self, text: str) -> None:
        self.text = text
