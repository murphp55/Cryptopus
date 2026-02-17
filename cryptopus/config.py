from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional


@dataclass
class AppConfig:
    exchange: str = "coinbase"
    symbol: str = "BTC/USD"
    timeframe: str = "5m"
    live_trading: bool = False
    enable_websocket: bool = True
    trade_size: float = 0.001
    poll_seconds: int = 5
    max_daily_loss: float = 150.0
    cooldown_seconds: int = 90
    fee_rate: float = 0.001
    backtest_cash: float = 1000.0
    stop_loss_pct: float = 2.0
    take_profit_pct: float = 3.0
    use_atr_sizing: bool = False
    risk_per_trade_pct: float = 1.0
    backtest_slippage_pct: float = 0.05


@dataclass
class Order:
    ts: datetime
    side: str
    price: float
    amount: float
    status: str
    symbol: str = ""
    exchange_id: Optional[str] = None


@dataclass
class Position:
    symbol: str
    amount: float = 0.0
    avg_price: float = 0.0
    realized_pnl: float = 0.0


def validate_config(data: Any, log_fn: Callable[[str], None]) -> Dict[str, Dict[str, str]]:
    """Validate config.json structure, return exchanges dict."""
    if not isinstance(data, dict):
        log_fn("CONFIG WARNING: config.json root is not a dict.")
        return {}
    exchanges = data.get("exchanges")
    if exchanges is None:
        log_fn("CONFIG WARNING: missing 'exchanges' key in config.json.")
        return {}
    if not isinstance(exchanges, dict):
        log_fn("CONFIG WARNING: 'exchanges' is not a dict.")
        return {}
    for name, creds in exchanges.items():
        if not isinstance(creds, dict):
            log_fn(f"CONFIG WARNING: exchange '{name}' credentials are not a dict.")
            continue
        if not isinstance(creds.get("apiKey", ""), str):
            log_fn(f"CONFIG WARNING: exchange '{name}' apiKey is not a string.")
        if not isinstance(creds.get("secret", ""), str):
            log_fn(f"CONFIG WARNING: exchange '{name}' secret is not a string.")
    return exchanges
