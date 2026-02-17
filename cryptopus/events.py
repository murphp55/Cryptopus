from typing import Any, Callable, Dict, List


class EventBus:
    """Simple callback-based event system."""

    def __init__(self) -> None:
        self._listeners: Dict[str, List[Callable[..., Any]]] = {}

    def on(self, event: str, callback: Callable[..., Any]) -> None:
        """Register a callback for an event."""
        self._listeners.setdefault(event, []).append(callback)

    def off(self, event: str, callback: Callable[..., Any]) -> None:
        """Remove a callback for an event."""
        listeners = self._listeners.get(event, [])
        if callback in listeners:
            listeners.remove(callback)

    def emit(self, event: str, *args: Any, **kwargs: Any) -> None:
        """Emit an event, calling all registered callbacks."""
        for cb in self._listeners.get(event, []):
            cb(*args, **kwargs)
