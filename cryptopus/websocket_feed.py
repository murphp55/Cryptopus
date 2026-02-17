import json
import threading
import time
import traceback
from typing import Callable

try:
    import websocket  # type: ignore
except Exception:
    websocket = None

from cryptopus.logger import Logger


class WebSocketPriceFeed(threading.Thread):
    def __init__(self, symbol: str, logger: Logger, on_price: Callable[[str, float], None]) -> None:
        super().__init__(daemon=True)
        self.symbol = symbol
        self.logger = logger
        self.on_price = on_price
        self._stop_event = threading.Event()
        self.last_message_time: float = 0.0

    def stop(self) -> None:
        self._stop_event.set()

    def is_healthy(self) -> bool:
        return (time.time() - self.last_message_time) < 30.0 if self.last_message_time else False

    def run(self) -> None:
        product_id = self.symbol.replace("/", "-")
        backoff = 1.0

        def on_open(ws):  # type: ignore
            nonlocal backoff
            sub = {"type": "subscribe", "product_ids": [product_id], "channels": ["ticker"]}
            ws.send(json.dumps(sub))
            self.logger.log(f"Websocket subscribed: {product_id}")
            backoff = 1.0

        def on_message(ws, message):  # type: ignore
            if self._stop_event.is_set():
                ws.close()
                return
            try:
                data = json.loads(message)
                if data.get("type") != "ticker":
                    return
                price = data.get("price")
                if price is None:
                    return
                self.last_message_time = time.time()
                self.on_price(self.symbol, float(price))
            except Exception as exc:
                self.logger.log(f"Websocket parse error: {exc}")

        def on_error(ws, error):  # type: ignore
            self.logger.log(f"Websocket error: {error}")

        def on_close(ws, *args):  # type: ignore
            self.logger.log("Websocket closed.")

        while not self._stop_event.is_set():
            try:
                ws_app = websocket.WebSocketApp(
                    "wss://ws-feed.exchange.coinbase.com",
                    on_open=on_open,
                    on_message=on_message,
                    on_error=on_error,
                    on_close=on_close,
                )
                ws_app.run_forever(ping_interval=20, ping_timeout=10)
            except Exception as exc:
                self.logger.log(f"Websocket connection error: {exc}\n{traceback.format_exc()}")
            if not self._stop_event.is_set():
                self.logger.log(f"Websocket reconnecting in {backoff:.0f}s...")
                time.sleep(backoff)
                backoff = min(backoff * 2, 60.0)
