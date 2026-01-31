# Cryptopus Trader

Tkinter-based US-focused crypto trading app with multiple strategies, exchange connectors via CCXT, websocket price feed (Coinbase), and paper/live modes.

## Quick start

1. Create a virtualenv and install deps:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2. Copy `config.example.json` to `config.json` and add your exchange keys if using live trading.
3. Run the app:

```bash
python app.py
```

## Notes

- Default mode is paper trading.
- Live trading uses CCXT and your keys from `config.json`.
- Coinbase is the default exchange for US-only spot trading.
- The strategy runner polls OHLCV; make sure the symbol and timeframe are supported by the exchange.
- A Backtest tab runs each strategy on recent OHLCV data.

## Safety

This is a starter project. It is not financial advice and not production-ready. Use small sizes and test thoroughly before using live keys.
