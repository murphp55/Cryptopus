# Cryptopus — Agent Notes

## One-liner
Desktop crypto trading bot in Python (CustomTkinter GUI, CCXT, SQLite) with 7 strategies, backtesting, and a grid-search optimizer.

## Run it
```
py -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
py app.py                                        # GUI
py prefetch_binance.py --update --include-5m     # refresh cached OHLCV
py optimize.py --exchange binanceus --local-only --candles 2000
pytest                                           # tests
```

## Where we are right now
- Last touched: 2026-04-16
- Working on: Latest commit "Fix bugs, improve security, and add configurability". Heavy uncommitted state — README.md modified, many strategy/UI files modified, and several new files untracked (`optimize.py`, `prefetch_binance.py`, `backtest_cli.py`, `cryptopus/strategies/{bollinger,macd,rsi,vwap}.py`, `cryptopus/ui/simple_mode.py`, plus `cache/` and `logs/`). Treat repo as in flux.
- Known broken: `INJ` is still in symbol lists despite being unavailable on Binance.US — it gets skipped but wastes a slot. `trader.py` uses market orders only (always pays taker fees). GUI polls instead of reacting to WebSocket updates.

*This section goes stale fast. Check `git log -5` and `git status` before trusting it.*

## Gotchas
- Windows + Python Launcher: use `py`, not `python`. Activate venv with `.venv\Scripts\activate`.
- Default exchange is `binanceus` (user is US-based). `binance.com` is geo-blocked. Symbol format differs: Binance uses `/USDT`, Coinbase uses `/USD`.
- `prefetch_binance.py` only fetches 5m candles and downsamples to 15m (3:1) and 1h (12:1) locally — do NOT add separate 15m/1h API fetches, it wastes ~1,300 calls.
- Backtests must include fees (0.1%) and slippage (0.05%) — already wired via `config.py` defaults (`fee_rate=0.001`, `backtest_slippage_pct=0.05`). Changing these invalidates optimizer comparisons.
- SQLite DB at `cryptopus.db` (root). README mentions `trading.db` in one debug example — that's stale, ignore it.
- `config.json` is git-ignored; copy from `config.example.json`. Paper mode is default and needs no keys.
- Many `cryptopus/strategies/*.py` and `cryptopus/ui/*.py` files are uncommitted — verify with `git status` before assuming what's tracked.

## Non-obvious conventions
- Event-driven via `cryptopus/events.py` EventBus (`on/off/emit`). Components emit `order_placed`, `position_updated`, `price_updated`, `strategy_signal`, `emergency_stop` — wire new features through these, don't bypass.
- Strategies inherit `StrategyBase` and live one-per-file in `cryptopus/strategies/`. Adding one: drop file in that dir and register in `strategies/__init__.py`.
- Optimizer logs go to `logs/optimize_YYYYMMDD_HHMMSS.json` plus a `_validation.json` sibling — VWAP @ 1h is the current winner (see README optimization section).

See README.md for project description, tech stack, strategy list, optimization results, and feature inventory.
