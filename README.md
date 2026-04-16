# Cryptopus Trader

A desktop-based Python cryptocurrency trading application with paper and live trading modes, multiple strategies, real-time price feeds, and comprehensive backtesting. Built with CustomTkinter GUI, CCXT exchange integration, and event-driven architecture.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Language** | Python 3.8+ |
| **GUI** | CustomTkinter (modern Tkinter wrapper) |
| **Exchange API** | CCXT (multi-exchange abstraction) |
| **Price Feed** | WebSocket (Coinbase), REST (OHLCV), CoinGecko (fallback) |
| **Persistence** | SQLite |
| **Visualization** | Matplotlib |
| **Architecture** | Event-driven with EventBus |
| **Testing** | pytest (47 tests across 6 modules) |

## Project Overview

Cryptopus is a **feature-complete crypto trading bot** with sophisticated risk management, multiple trading strategies, and paper/live trading modes. It supports five distinct strategies with full backtesting, position tracking, and P&L monitoring.

**Current Status**: Version 0.2.0, Phase 2 complete, Phase 3 pending (real-time equity curve, web UI)

## Key Features

### Trading Strategies (5 Total)
| Strategy | Description |
|----------|-------------|
| **Momentum** | Follows price trends with entry on breakout highs |
| **Mean Reversion** | Buys dips and sells rallies using RSI/volatility |
| **Breakout** | Enters on resistance/support breakouts with volume confirmation |
| **Scalping** | Short-term trades on intraday micro-movements |
| **Contra-Momentum** | Counter-trend strategy betting on reversals |

### Risk Management
- Stop Loss / Take Profit orders (per position)
- Max daily loss limit (kill-switch)
- Position size based on ATR (Average True Range)
- Emergency stop for rapid market shocks
- Cooldown periods between trades
- Per-trade risk/reward ratio enforcement

### Trading Modes
- **Paper Trading** (default): Risk-free simulation with realistic fills
- **Live Trading**: Real money execution via CCXT
- **Supported Exchanges**: Coinbase, Kraken, Binance, Bybit, Alpaca
- **Spot Trading Only**: No margin or futures

### Data & Analysis
- **Real-Time Prices**: WebSocket from Coinbase (BTC, ETH, etc.)
- **Historical OHLCV**: REST endpoints (1m, 5m, 1h, 1d timeframes)
- **CoinGecko Fallback**: Free tier data source if exchange unavailable
- **Backtesting Engine**: Compare all 5 strategies on historical data with fee/slippage modeling
- **SQLite Persistence**: Order history, position tracking, daily P&L

### GUI (CustomTkinter)
- **7 Main Tabs**: Overview | Market | Strategy | Positions | Settings | Backtest | Logs
- **Overview Tab**: Account balance, portfolio composition, daily P&L
- **Market Tab**: Real-time price charts, order book simulation
- **Strategy Tab**: Select strategy, adjust parameters, view signals
- **Positions Tab**: Open positions, entry price, unrealized P&L, close buttons
- **Settings Tab**: Exchange selection, API key entry, paper/live toggle, risk parameters
- **Backtest Tab**: Run historical comparison, chart performance, export results
- **Logs Tab**: Live application logging with timestamps and severity

## Project Structure

```
cryptopus/
├── app.py                              # Main entry point, CustomTkinter GUI
├── requirements.txt                    # Python dependencies
├── config.example.json                 # Template for exchange credentials
├── config.json                         # Local credentials (git-ignored)
│
├── cryptopus/
│   ├── __init__.py
│   ├── config.py                       # Configuration loading & validation
│   ├── runner.py                       # Trade execution engine
│   ├── backtest.py                     # Historical backtesting with fee modeling
│   ├── data_engine.py                  # OHLCV fetching & caching
│   ├── events.py                       # Event definitions
│   ├── logger.py                       # Structured logging
│   ├── persistence.py                  # SQLite database operations
│   ├── rate_limiter.py                 # Exchange rate limiting
│   │
│   └── strategies/
│       ├── __init__.py
│       ├── momentum.py                 # Momentum strategy (RSI, moving average)
│       ├── mean_reversion.py           # Mean reversion (Bollinger Bands)
│       ├── breakout.py                 # Breakout detection
│       ├── scalping.py                 # Micro-movement trading
│       └── contra_momentum.py          # Counter-trend strategy
│
└── tests/
    ├── test_runner.py                  # 12 tests
    ├── test_backtest.py                # 8 tests
    ├── test_data_engine.py             # 9 tests
    ├── test_events.py                  # 6 tests
    ├── test_persistence.py             # 7 tests
    └── test_strategies.py              # 5 tests
```

## Key Files to Know

| File | Lines | Purpose |
|------|-------|---------|
| `app.py` | ~400 | CustomTkinter GUI, event loop, tab management |
| `cryptopus/runner.py` | ~250 | Trade execution, order placement, position management |
| `cryptopus/backtest.py` | ~200 | Historical simulation with fee/slippage modeling |
| `cryptopus/data_engine.py` | ~150 | OHLCV fetching from exchanges & CoinGecko |
| `cryptopus/strategies/momentum.py` | ~80 | Momentum entry/exit logic |
| `cryptopus/persistence.py` | ~100 | SQLite schema and CRUD operations |

## How to Build & Run

### Prerequisites
- Python 3.8+
- pip (Python package manager)
- SQLite3 (usually included with Python)
- Git

### Setup

```bash
# Clone or navigate to project
cd cryptopus

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

```bash
# Copy example config
cp config.example.json config.json

# Edit config.json with your exchange API keys
# (Only needed for live trading; paper trading works without keys)
```

### Run Application

```bash
# Start the GUI
python app.py
```

The application will launch a CustomTkinter window with tabs for market data, strategies, positions, backtesting, and more.

### Building for Distribution

```bash
# Create standalone executable (Windows)
pip install pyinstaller
pyinstaller --onefile --windowed app.py

# Executable will be in dist/ folder
```

## Dependencies

```
ccxt                   # Multi-exchange trading
requests               # HTTP client for REST APIs
websocket-client       # WebSocket connection (Coinbase)
matplotlib             # Charting for backtests
customtkinter          # Modern GUI toolkit
sqlite3                # Built into Python
```

Install all with:
```bash
pip install -r requirements.txt
```

## Configuration

### API Keys (config.json)
```json
{
  "exchanges": {
    "coinbase": {
      "apiKey": "your_api_key",
      "secret": "your_api_secret",
      "passphrase": "your_passphrase"
    },
    "kraken": {
      "apiKey": "...",
      "secret": "..."
    }
  },
  "paper_mode": true,
  "default_exchange": "coinbase"
}
```

### Strategy Parameters (Adjustable in Settings Tab)
```
Momentum:
  - RSI period: 14
  - RSI threshold: 70 (overbought)
  - Moving avg period: 20

Mean Reversion:
  - Bollinger Band period: 20
  - Std dev: 2
  - RSI period: 14

Breakout:
  - Lookback period: 20
  - Volume threshold: 1.2x average
  - Breakout percent: 1.5%

Scalping:
  - Timeframe: 1m
  - Min move: 0.5%
  - Position size: Small

Contra-Momentum:
  - RSI threshold: 30 (oversold)
  - Reversal confirmation: 3 candles
```

## Development State

**Status**: Beta (Version 0.2.0)

**Completed** (Phase 1 & 2):
- Core trading engine with all 5 strategies
- Paper and live trading modes
- WebSocket and REST price feeds
- Backtesting with fee/slippage modeling
- SQLite persistence (orders, positions, P&L)
- Risk management (SL/TP, max daily loss, position sizing)
- CustomTkinter GUI with 7 tabs
- 47 comprehensive unit tests

**Current Limitations**:
- No real-time equity curve (recalculated on demand)
- GUI not responsive to live WebSocket updates (polls instead)
- No web UI (Tkinter desktop only)
- Backtesting doesn't account for slippage variance
- No multi-pair trading (single symbol at a time)
- No API key encryption in config file
- Limited error recovery on exchange outages

**Planned** (Phase 3):
- [ ] Real-time equity curve calculation
- [ ] Web UI (Flask/React) alongside desktop app
- [ ] Multi-symbol portfolio management
- [ ] Encrypted config file storage
- [ ] Email/Slack notifications for trades
- [ ] Advanced charting with TradingView integration
- [ ] Machine learning-based strategy optimization

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=cryptopus

# Run specific test module
pytest tests/test_runner.py -v

# Run single test
pytest tests/test_runner.py::test_place_limit_order -v
```

**Test Coverage**:
- runner.py: Order placement, position tracking, P&L calculation
- backtest.py: Strategy comparison, fee modeling, equity curves
- data_engine.py: OHLCV fetching, caching, fallback sources
- events.py: Event creation and dispatch
- persistence.py: Database operations
- strategies: Each strategy's signal generation

## Architecture Notes

### Event-Driven Design
The application uses an `EventBus` for loose coupling:
```
User Input (GUI) → Event → Bus → Handler → State Update
Price Feed → PriceUpdate Event → Strategy → Signal → Trade
```

### Strategy Interface
All strategies implement:
```python
class Strategy:
    def analyze(self, ohlcv_data) -> Signal:
        # Returns BUY, SELL, or HOLD signal
        
    def on_trade(self, trade) -> None:
        # Called after order execution
```

### Data Flow
```
1. Data Engine fetches OHLCV
2. Strategy receives data, generates signals
3. Runner evaluates signals against risk checks
4. Orders placed on exchange (live) or simulated (paper)
5. Fills tracked in database
6. GUI updated via event callbacks
```

## Risk Management Details

### Position Sizing
- Base size determined by account equity
- Adjusted by ATR (volatility)
- Max position = 2% of account per trade
- Formula: `position_size = account_equity * 0.02 / stop_loss_distance`

### Stop Loss / Take Profit
- Auto-set based on entry price
- SL: Entry - (2 × ATR)
- TP: Entry + (4 × ATR)
- Customizable ratio in settings

### Daily Loss Limit
- Tracks P&L since market open
- Closes all positions if loss exceeds 5% of account
- Prevents cascade failures

### Emergency Stop
- Triggered if single trade loss > 2% of account
- Immediately closes position and pauses trading
- Requires user acknowledgment to resume

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| WebSocket disconnects | App auto-reconnects; check internet connection |
| Exchange API rate limited | Use rate limiter class; add delays between calls |
| Config file not found | Run `cp config.example.json config.json` |
| Backtest data gaps | Download manually or use CoinGecko fallback |
| GUI freezes during backtest | Backtest runs in separate thread; UI should remain responsive |
| Paper mode not working | Check "Paper Mode" toggle in Settings tab |

## Debugging

```bash
# Enable debug logging
# Edit cryptopus/logger.py and set level to DEBUG

# View logs in application Logs tab
# Or check console output

# Check database
sqlite3 trading.db "SELECT * FROM orders LIMIT 10;"
```

## Performance Tips

1. **Reduce Backtest Timeframe**: Use 1h instead of 1m for faster historical analysis
2. **Limit History**: Request last 500 candles instead of 5000
3. **Cache OHLCV**: data_engine.py caches; reuse cached data when possible
4. **Paper Trading First**: Always test strategies in paper mode before going live
5. **Monitor Logs**: Watch for rate limit warnings; adjust API call frequency if needed

## Tips for Developers

1. **Adding a Strategy**: Create new file in `cryptopus/strategies/`, inherit from Strategy, implement `analyze()`
2. **Modifying GUI**: Edit `app.py` tab classes; use CustomTkinter widgets for modern look
3. **Testing Strategies**: Use backtest.py to compare against historical data
4. **Exchange Integration**: CCXT handles API differences; add new exchanges in config
5. **Logging**: Use `cryptopus.logger` for structured output with timestamps

## Notes for AI Assistants

When opening this project in a new session:
- **Entry Point**: `app.py` launches the GUI
- **Config Required**: Copy `config.example.json` to `config.json` (even for paper mode)
- **Paper Mode Default**: No real money at risk; good for testing
- **Five Strategies**: Each one can be tested individually or compared in backtest tab
- **Event-Driven**: Use EventBus for communication between components
- **Database**: SQLite at `trading.db`; schema created on first run
- **Testing**: Run `pytest` to verify system integrity
- **Safety**: Always test in paper mode first; real API keys required for live trading

## Compliance & Disclaimers

**This is educational software**. It is not financial advice, and Cryptopus is not production-ready for real money trading without significant additional hardening:
- No guarantees of uptime or accuracy
- Exchange API changes may break functionality
- Market gaps and slippage not fully modeled
- Use small position sizes for initial live trading
- Test thoroughly in paper mode first
- Monitor positions actively; do not leave unattended

**Use at your own risk.**

## Roadmap

### Short-term (v0.3)
- Real-time equity curve
- Web UI (Flask) alongside desktop app
- Encrypted API key storage

### Medium-term (v1.0)
- Multi-pair portfolio
- Advanced charting
- ML strategy optimization
- Email/Slack notifications

### Long-term (v2.0)
- Margin trading
- Futures contracts
- Options strategies
- Community signal sharing

## License

Proprietary—Patrick Murphy
