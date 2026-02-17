import time
import traceback
from typing import Dict, List, Optional, Tuple

try:
    import ccxt  # type: ignore
except Exception:
    ccxt = None

try:
    import requests  # type: ignore
except Exception:
    requests = None

try:
    import websocket as _ws_module  # type: ignore
except Exception:
    _ws_module = None

from cryptopus.config import AppConfig
from cryptopus.events import EventBus
from cryptopus.logger import Logger
from cryptopus.rate_limiter import RateLimiter
from cryptopus.websocket_feed import WebSocketPriceFeed


class DataEngine:
    def __init__(self, config: AppConfig, logger: Logger, keys: Dict[str, Dict[str, str]],
                 events: Optional[EventBus] = None) -> None:
        self.config = config
        self.logger = logger
        self.keys = keys
        self.events = events
        self.exchange = None
        self.latest_price: Dict[str, float] = {}
        self._ws_thread: Optional[WebSocketPriceFeed] = None
        self._ohlcv_cache: Dict[Tuple[str, str], Tuple[float, List[List[float]]]] = {}
        self._rate_limiter = RateLimiter(max_calls=10, period_seconds=60.0)

        if ccxt is not None:
            self.exchange = self._init_exchange()
        self._start_ws_if_needed()

    def _init_exchange(self):  # type: ignore
        name = self.config.exchange
        if not hasattr(ccxt, name):
            self.logger.log(f"Exchange '{name}' not found in ccxt. Using public price only.")
            return None
        klass = getattr(ccxt, name)
        creds = self.keys.get(name, {})
        return klass({
            "apiKey": creds.get("apiKey", ""),
            "secret": creds.get("secret", ""),
            "password": creds.get("password", ""),
            "enableRateLimit": True,
        })

    def set_exchange(self, name: str) -> None:
        self.config.exchange = name
        if ccxt is not None:
            self.exchange = self._init_exchange()
        self._start_ws_if_needed()

    def fetch_ticker(self, symbol: str) -> Optional[Dict]:
        if symbol in self.latest_price:
            return {"last": self.latest_price[symbol], "symbol": symbol, "source": "websocket"}
        if not self._rate_limiter.acquire():
            self.logger.log("Rate limited: skipping ticker fetch.")
            return None
        if self.exchange is not None:
            try:
                return self.exchange.fetch_ticker(symbol)
            except Exception as exc:
                self.logger.log(f"Ticker fetch failed: {exc}\n{traceback.format_exc()}")
        return self._fetch_public_price(symbol)

    def _fetch_public_price(self, symbol: str) -> Optional[Dict]:
        if requests is None:
            return None
        base = symbol.split("/")[0].lower()
        try:
            resp = requests.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "bitcoin,ethereum,solana,cardano,avalanche-2", "vs_currencies": "usd"},
                timeout=5,
            )
            resp.raise_for_status()
            data = resp.json()
            mapping = {
                "btc": "bitcoin",
                "eth": "ethereum",
                "sol": "solana",
                "ada": "cardano",
                "avax": "avalanche-2",
            }
            key = mapping.get(base)
            if not key or key not in data:
                return None
            price = float(data[key]["usd"])
            return {"last": price, "symbol": symbol}
        except Exception as exc:
            self.logger.log(f"Public price fetch failed: {exc}\n{traceback.format_exc()}")
            return None

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> Optional[List[List[float]]]:
        if self.exchange is None:
            return None
        cache_key = (symbol, timeframe)
        cached = self._ohlcv_cache.get(cache_key)
        if cached is not None:
            ts, data = cached
            if time.time() - ts < self.config.poll_seconds:
                return data
        if not self._rate_limiter.acquire():
            self.logger.log("Rate limited: skipping OHLCV fetch.")
            return cached[1] if cached else None
        try:
            data = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            self._ohlcv_cache[cache_key] = (time.time(), data)
            return data
        except Exception as exc:
            self.logger.log(f"OHLCV fetch failed: {exc}\n{traceback.format_exc()}")
            return None

    def _start_ws_if_needed(self) -> None:
        if self._ws_thread:
            self._ws_thread.stop()
            self._ws_thread = None
        if not self.config.enable_websocket:
            return
        if self.config.exchange != "coinbase":
            return
        if _ws_module is None:
            self.logger.log("websocket-client not installed; websocket feed disabled.")
            return
        self._ws_thread = WebSocketPriceFeed(
            symbol=self.config.symbol,
            logger=self.logger,
            on_price=self._update_price,
        )
        self._ws_thread.start()

    def _update_price(self, symbol: str, price: float) -> None:
        self.latest_price[symbol] = price
        if self.events:
            self.events.emit("price_updated", symbol, price)
