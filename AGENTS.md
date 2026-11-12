# AGENTS.md

A Hyperliquid trading bot template. It uses the official Hyperliquid Python SDK against an Ironflow paper box, a simulated Hyperliquid account with $10,000 and live prices. Nothing here places a real order.

## Run and test

- Install: `pip install -r requirements.txt` (Python 3.9+), or `uv run bot.py`.
- Test with `python bot.py --once`: one pass, then exit. Without `--once` it loops every 15 minutes.
- No key needed. The first run creates a 24-hour trial box with `POST https://api.ironflow.sh/v1/ironbox` and saves its URL in `.ironbox` (gitignored). That URL is a credential: do not print, log or commit it.
- `IRONFLOW_KEY` (optional, free from https://ironflow.sh/key) keeps the box and raises data limits. `IRONFLOW_BOX_URL` uses an existing box.

## Paper box rules

- Always `Info(base_url, skip_ws=True)`. A box has no WebSocket, and the SDK waits on one forever without `skip_ws`.
- One wallet per box: the first signed action binds it. Keep the wallet derived in `connect()`. A new `Account.create()` on the same box is refused.
- The SDK signs for testnet when `base_url` is not `https://api.hyperliquid.xyz`. A box accepts that.
- `/info` on a box answers: meta, spotMeta, allMids, l2Book, metaAndAssetCtxs, clearinghouseState, openOrders, frontendOpenOrders, orderStatus, userFills, userFillsByTime, userFunding.
- `/exchange` on a box takes: order, cancel, cancelByCloid, modify, batchModify. Main perps, cross margin.
- A box has no `candleSnapshot`. Read candles from `https://api.ironflow.sh/v1/candles?market=BTC-PERP&interval=15m&limit=50`.
- An order can come back with `Paper market data unavailable.` when the box's book is a few seconds old. Retry after 2 seconds, as `market_order()` does.

## Changing the bot

- Strategy settings are at the top of `bot.py`. `signal(prices)` returns +1 (long) or -1 (short), and `step()` sends one market order to reach that position.
- Keyless data limits: 30 requests a minute, 300 a day, 24 hours of history. One pass makes one data call: at 15 minutes that is about 100 a day.
- Keep the bot on the paper box with the throwaway wallet. Never add a funded private key.

## Reference

- Paper trading guide: https://ironflow.sh/guides/hyperliquid-paper-trading
- API docs: https://docs.ironflow.sh, OpenAPI: https://api.ironflow.sh/openapi.yaml, summary: https://ironflow.sh/llms.txt
- MCP server for agents: https://mcp.ironflow.sh/mcp
