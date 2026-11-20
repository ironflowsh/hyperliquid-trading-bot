# AGENTS.md

A Hyperliquid trading bot template. Signals come from Ironflow's Hyperliquid data API; orders go through the official Hyperliquid Python SDK. By default it is a dry run and places nothing.

## Run and test

- Install: `pip install -r requirements.txt` (Python 3.9+), or `uv run bot.py`.
- Test with `python bot.py --once`: one dry-run pass, then exit. Without `--once` it loops every 15 minutes.
- No key needed for data. `IRONFLOW_KEY` (optional, free from https://ironflow.sh/key) raises the limits.
- `--trade testnet` or `--trade mainnet` sends real orders and needs `HL_PRIVATE_KEY` (an API wallet key) and, for an API wallet, `HL_ACCOUNT_ADDRESS`. Never print, log or commit the key. Default to testnet.

## Data calls

- `GET https://api.ironflow.sh/v1/liquidations/summary?market=BTC-PERP&windows=1h` once at start (5 credits).
- `GET https://api.ironflow.sh/v1/candles?market=BTC-PERP&interval=15m&limit=22` once per pass (1 credit).
- Keyless: 30 requests a minute, 100 credits a day per IP, 24 hours of history. A pass every 15 minutes is about 96 credits a day.
- On a 402 or 429 the error message says what ran out and when it comes back; `ironflow()` raises it as `IronflowError`.

## Changing the bot

- Strategy settings are at the top of `bot.py`. `signal(prices)` returns +1 (long) or -1 (short), and `step()` sends one market order to reach that position.
- More data for signals: liquidation rows (`/v1/liquidations`), the live liquidation stream (`/v1/liquidations/stream`), the liquidation map (`/v1/liquidations/map?market=`), funding (`/v1/funding`) and open interest (`/v1/open-interest`).

## Reference

- API docs: https://docs.ironflow.sh, OpenAPI: https://api.ironflow.sh/openapi.yaml, summary: https://ironflow.sh/llms.txt
- MCP server for agents: https://mcp.ironflow.sh/mcp
