# Hyperliquid trading bot

A small Hyperliquid trading bot in Python. It reads candles and liquidations from [Ironflow](https://ironflow.sh), Hyperliquid market data from our own nodes, and trades through the official [Hyperliquid Python SDK](https://github.com/hyperliquid-dex/hyperliquid-python-sdk). It runs as a dry run by default, with no key and no wallet.

## Run

```bash
pip install -r requirements.txt
python bot.py --once
```

Or in one command with [uv](https://docs.astral.sh/uv/): `uv run bot.py --once`.

The first run prints the last hour of BTC liquidations, reads 15-minute BTC candles and prints the order it would send. It goes long when the 8-candle moving average of closes is above the 21-candle average, and short when it is below. Without `--once` it runs a pass every 15 minutes.

```text
Dry run on BTC: no orders are sent
BTC-PERP last hour: $123,456 longs and $7,890 shorts liquidated (12 liquidations)
dry run: would buy 0.00324 BTC at market
13:13:53 close 61,794.0  signal long  BTC +0.0
```

## Place orders

```bash
export HL_PRIVATE_KEY=0x...          # an API wallet key from app.hyperliquid.xyz/API
export HL_ACCOUNT_ADDRESS=0x...      # the account the API wallet trades for
python bot.py --trade testnet        # Hyperliquid testnet
python bot.py --trade mainnet        # real funds
```

Start on testnet. Use an API wallet, not your main private key: it can trade but cannot withdraw.

## How it works

- **Liquidations:** `GET https://api.ironflow.sh/v1/liquidations/summary?market=BTC-PERP&windows=1h`, long and short USD liquidated in the last hour.
- **Signals:** `GET https://api.ironflow.sh/v1/candles`, built from every Hyperliquid fill.
- **Orders:** the SDK's `Exchange.market_open`, one order to reach the target position.

To change the strategy, edit the settings at the top of `bot.py` (`COIN`, `INTERVAL`, `FAST`, `SLOW`, `SIZE_USD`) or replace `signal()`.

## Limits

Without a key: 30 requests a minute and 100 credits a day per IP, and 24 hours of history. A candle read costs 1 credit and the liquidation summary 5, so a pass every 15 minutes fits. A free key from [ironflow.sh/key](https://ironflow.sh/key) gives 1,000 credits a day and 14 days of history:

```bash
export IRONFLOW_KEY=if_your_key
```

Plans for more history and higher limits: Explorer $49, Builder $149 and Pro $499 a month.

This is an example, not trading advice.

## Links

- [Ironflow API docs](https://docs.ironflow.sh)
- [Liquidation alerts to Discord, Slack, Telegram or a webhook](https://docs.ironflow.sh/guides/liquidation-alerts)
- [Hyperliquid MCP server](https://docs.ironflow.sh/guides/ai-agents) for Claude, Cursor and other agents

## License

MIT
