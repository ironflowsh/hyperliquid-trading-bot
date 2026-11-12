# Hyperliquid trading bot

A small Hyperliquid trading bot in Python, built on the official [Hyperliquid Python SDK](https://github.com/hyperliquid-dex/hyperliquid-python-sdk). It trades an Ironflow paper box: your own simulated Hyperliquid account with $10,000 and live prices. No signup, no key and no testnet faucet.

## Run

```bash
pip install -r requirements.txt
python bot.py
```

Or in one command with [uv](https://docs.astral.sh/uv/): `uv run bot.py`.

The first run creates a paper box, saves its URL in `.ironbox` and trades BTC every 15 minutes. It goes long when the 8-candle moving average of 15-minute closes is above the 21-candle average, and short when it is below. `python bot.py --once` runs one pass and exits.

```text
New paper box: Trial paper box, removed after 24 hours, or after 2 hours with no requests and no strategy running.
Paper wallet 0x7FAAb0Ce6631b692458760fe5a3e2afa43c940F5
sell 0.00279 BTC [{'filled': {'totalSz': '0.00279', 'avgPx': '71609.551971', 'oid': 3}}]
01:26:03 close 71,438.0  BTC -0.00279  equity $9,999.71
```

## How it works

- **Signals:** candles from Ironflow's data API, `GET https://api.ironflow.sh/v1/candles`, no key needed.
- **Orders:** the SDK's `Exchange` with `base_url` set to the box URL. The box fills against Hyperliquid's live book and charges Hyperliquid's fees and funding.
- **`skip_ws=True`:** a paper box has no WebSocket. Without `Info(base_url, skip_ws=True)`, the SDK waits on one forever.
- **Wallet:** a throwaway key derived from the box URL. A box binds to the first wallet that signs, so every run signs with the same one. Never put a funded key here.

To change the strategy, edit the settings at the top of `bot.py` (`COIN`, `INTERVAL`, `FAST`, `SLOW`, `SIZE_USD`) or replace `signal()`.

## Keep a box

A trial box ends after 24 hours, or after 2 hours with no requests. A free key from [ironflow.sh/key](https://ironflow.sh/key) makes a box that stays, and raises the data limits from 30 to 60 requests a minute:

```bash
export IRONFLOW_KEY=if_your_key
rm .ironbox && python bot.py
```

To use a box you already have: `IRONFLOW_BOX_URL=https://api.ironflow.sh/box/ibxs_... python bot.py`. The box URL works like a password.

## On Hyperliquid

The same code can later point at Hyperliquid's API with your own keys: change `base_url` and the wallet in `connect()`. Ironflow never trades real money.

This is an example, not trading advice.

## Links

- [Hyperliquid paper trading guide](https://ironflow.sh/guides/hyperliquid-paper-trading)
- [Ironflow API docs](https://docs.ironflow.sh)
- [Hyperliquid MCP server](https://docs.ironflow.sh/guides/ai-agents) for Claude, Cursor and other agents

## License

MIT
