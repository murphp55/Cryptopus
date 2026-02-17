import queue
from datetime import datetime, timezone


class Logger:
    def __init__(self, log_queue: queue.Queue) -> None:
        self.log_queue = log_queue

    def log(self, msg: str) -> None:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        self.log_queue.put(f"[{ts}] {msg}")
