# Binance Futures Testnet Trading Bot

A Python CLI application for placing **Market**, **Limit**, and **Stop-Limit** orders on [Binance Futures Testnet](https://testnet.binancefuture.com) (USDT-M).

## Features

- **Three order types**: Market, Limit, and Stop-Limit (bonus)
- **Input validation**: Symbol, side, order type, quantity, and price are validated before submission
- **Rich CLI output**: Colour-coded tables for request summaries and API responses
- **Structured logging**: JSON-style file logs + concise console logs
- **Error handling**: Catches and explains API errors, network issues, and invalid input
- **Direct REST implementation**: Uses `httpx` with HMAC-SHA256 signing — no wrapper library needed

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py           # Package init
│   ├── client.py             # Binance REST client (signing, HTTP, error parsing)
│   ├── orders.py             # Order placement logic (validation → API → result)
│   ├── validators.py         # Input validation functions
│   └── logging_config.py     # Dual-handler logging setup
├── cli.py                    # CLI entry point (Typer + Rich)
├── logs/
│   └── trading_bot.log       # Auto-generated log file
├── .env.example              # API credential template
├── .gitignore
├── requirements.txt
└── README.md
```

## Setup

### Prerequisites

- Python 3.10 or later
- A [Binance Futures Testnet](https://testnet.binancefuture.com) account with API credentials

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd trading_bot

# Create a virtual environment (recommended)
python -m venv .venv

# Activate it
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your Binance Futures Testnet API credentials:
   ```
   BINANCE_TESTNET_API_KEY=your_api_key_here
   BINANCE_TESTNET_API_SECRET=your_api_secret_here
   ```

> **⚠️ Never commit your `.env` file.** It is already included in `.gitignore`.

## Usage

All commands are run from the `trading_bot/` directory.

### Place a Market Order

```bash
python cli.py order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

### Place a Limit Order

```bash
python cli.py order --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 100000
```

### Place a Stop-Limit Order (Bonus)

```bash
python cli.py order --symbol ETHUSDT --side BUY --type STOP_LIMIT \
    --quantity 0.01 --price 2500 --stop-price 2480
```

### View Help

```bash
python cli.py --help
python cli.py order --help
```

### Example Output

```
┏━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Parameter ┃ Value     ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━┩
│ Symbol    │ BTCUSDT   │
│ Side      │ BUY       │
│ Order Type│ MARKET    │
│ Quantity  │ 0.001     │
└───────────┴───────────┘

┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┓
┃ Field        ┃ Value           ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━┩
│ Order ID     │ 123456789       │
│ Symbol       │ BTCUSDT         │
│ Side         │ BUY             │
│ Type         │ MARKET          │
│ Status       │ FILLED          │
│ Executed Qty │ 0.001           │
│ Avg Price    │ 104523.50       │
└──────────────┴─────────────────┘

╭─── Success ───╮
│ ✅ Order placed successfully!             │
│ Order ID: 123456789  |  Status: FILLED    │
╰───────────────╯
```

## Logging

Logs are written to `logs/trading_bot.log` in structured JSON format:

```json
{"timestamp": "2026-06-11T12:00:00+00:00", "level": "INFO", "module": "orders", "message": "Placing MARKET BUY order: BTCUSDT qty=0.001"}
{"timestamp": "2026-06-11T12:00:01+00:00", "level": "DEBUG", "module": "client", "message": ">>> POST /fapi/v1/order params={...}"}
{"timestamp": "2026-06-11T12:00:01+00:00", "level": "DEBUG", "module": "client", "message": "<<< 200 {\"orderId\": 123456789, ...}"}
{"timestamp": "2026-06-11T12:00:01+00:00", "level": "INFO", "module": "orders", "message": "Order placed successfully — orderId=123456789 status=FILLED"}
```

## Assumptions

1. **Testnet only** — this application is designed for Binance Futures Testnet (`https://testnet.binancefuture.com`). Do **not** use it with production API credentials.
2. **USDT-M Futures** — all trading pairs are USDT-margined futures (e.g., BTCUSDT, ETHUSDT).
3. **No position management** — the bot places individual orders only. It does not track open positions, calculate PnL, or manage risk.
4. **GTC default** — Limit and Stop-Limit orders default to Good-Til-Cancelled time-in-force.
5. **System clock** — the machine running this bot must have a reasonably accurate system clock (within a few seconds of UTC) for API signature timestamps.

## Dependencies

| Package        | Purpose                        |
|----------------|--------------------------------|
| `httpx`        | HTTP client for REST API calls |
| `typer`        | CLI framework                  |
| `rich`         | Terminal formatting & tables   |
| `python-dotenv`| Load `.env` configuration      |

## License

This project is provided for evaluation purposes.
