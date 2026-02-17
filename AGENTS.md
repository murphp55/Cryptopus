# Cryptopus Agents

## TODO
- Add perps and futures support (exchange selection, margin settings, funding-rate data, and risk controls).

## Phase 1: Trading Bot Improvements (COMPLETED)
- [x] Stop-loss / take-profit orders — auto-exit at SL/TP thresholds, in both live runner and backtests
- [x] SQLite persistence — orders, positions, daily PnL saved to `cryptopus.db` across restarts
- [x] ATR-based position sizing — volatility-aware sizing with configurable risk % per trade
- [x] Kill switch — red EMERGENCY STOP button on Overview, halts strategy and flattens positions
- [x] Application-level rate limiting — token bucket (10 calls/60s) on ticker and OHLCV fetches
- [x] WebSocket exponential backoff — 1s→60s backoff on disconnect, health tracking
- [x] Slippage modeling in backtests — configurable slippage % field in all backtest tabs
- [x] OHLCV data caching — in-memory cache keyed by (symbol, timeframe), TTL = poll_seconds
- [x] Renamed Arbitrage → Contra-Momentum — honest naming for the momentum-flip strategy
- [x] Config validation — validates config.json structure, logs warnings for malformed entries
- [x] Improved error handling — traceback logging, failed orders return proper Order records

## Phase 2: Reorganize Structure (COMPLETED)
- [x] Split monolith into `cryptopus/` package (was 1,554-line app.py → 20+ focused modules)
- [x] `cryptopus/config.py` — AppConfig, Order, Position dataclasses, validate_config()
- [x] `cryptopus/logger.py` — Logger class
- [x] `cryptopus/events.py` — Simple callback-based EventBus (on/off/emit)
- [x] `cryptopus/persistence.py` — TradeStore (SQLite)
- [x] `cryptopus/rate_limiter.py` — Token bucket RateLimiter
- [x] `cryptopus/websocket_feed.py` — WebSocketPriceFeed with exponential backoff
- [x] `cryptopus/data_engine.py` — DataEngine with caching and rate limiting
- [x] `cryptopus/trader.py` — Trader with persistence and event emission
- [x] `cryptopus/strategies/` — StrategyBase + 5 strategies in separate files + compute_atr()
- [x] `cryptopus/backtest.py` — BacktestEngine, BacktestResult
- [x] `cryptopus/runner.py` — StrategyRunner with SL/TP, ATR sizing, events
- [x] `cryptopus/ui/` — App class + 7 tab builder modules (overview, market, strategy, positions, settings, backtest, logs)
- [x] `app.py` — Thin entry point (10 lines)
- [x] EventBus wired into Trader, DataEngine, StrategyRunner (order_placed, position_updated, price_updated, strategy_signal, emergency_stop)
- [x] 47 pytest tests across 6 test files — all passing (strategies, backtest, trader, persistence, rate_limiter, config)
- [x] Full type hints on all public methods

## Phase 3: Improve the UI (PENDING)
- Add real-time P&L chart during paper/live trading
- Modernize GUI (CustomTkinter or web-based Dash/Streamlit)
