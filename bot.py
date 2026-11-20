# /// script
# requires-python = ">=3.9"
# dependencies = ["hyperliquid-python-sdk==0.24.0"]
# ///
"""A small Hyperliquid trading bot on Ironflow data and the official SDK.

Signals come from Ironflow candles, and each run starts with the last hour of
liquidations. By default it is a dry run: it prints the order it would send
and places nothing. With --trade testnet (or mainnet) and HL_PRIVATE_KEY set,
it sends that order through the official Hyperliquid Python SDK.

    python bot.py                   # dry run every 15 minutes until Ctrl+C
    python bot.py --once            # one dry-run pass, then exit
    python bot.py --trade testnet   # place orders on Hyperliquid testnet
"""
from __future__ import annotations

import argparse
import os
import sys
import time

import requests
from eth_account import Account
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils import constants
from hyperliquid.utils.error import ClientError

# Strategy: long when the fast moving average is above the slow one, short
# when it is below. Edit these, or replace signal().
COIN = "BTC"          # Hyperliquid coin name
INTERVAL = "15m"      # candle interval: 1m, 5m, 15m, 1h, 4h, 1d
FAST, SLOW = 8, 21    # moving average lengths, in candles
SIZE_USD = 200        # position size in USD
EVERY_S = 15 * 60     # seconds between passes

IRONFLOW = "https://api.ironflow.sh"
KEY = os.environ.get("IRONFLOW_KEY", "")  # optional, free from https://ironflow.sh/key
HEADERS = {"User-Agent": os.environ.get("IRONFLOW_USER_AGENT", "hyperliquid-trading-bot/0.2")}
if KEY:
    HEADERS["Authorization"] = f"Bearer {KEY}"

NETWORKS = {"testnet": constants.TESTNET_API_URL, "mainnet": constants.MAINNET_API_URL}


class IronflowError(Exception):
    """An Ironflow answer that is not 2xx, with the API's own message."""


def ironflow(path: str, **params: object) -> dict:
    r = requests.get(f"{IRONFLOW}{path}", headers=HEADERS, params=params, timeout=30)
    if not r.ok:
        try:
            message = r.json()["error"]["message"]
        except (ValueError, KeyError, TypeError):
            message = r.text[:300]
        raise IronflowError(f"{r.status_code} {path}: {message}")
    return r.json()


def liquidations_last_hour() -> str:
    """Long and short USD liquidated on the coin's perp in the last hour."""
    body = ironflow("/v1/liquidations/summary", market=f"{COIN}-PERP", windows="1h")
    total = body["windows"][0]["total"]
    return (f"{COIN}-PERP last hour: ${total['long_usd']:,.0f} longs and ${total['short_usd']:,.0f} shorts "
            f"liquidated ({total['liquidations']} liquidations)")


def closes() -> list[float]:
    """Closes of the last finished candles, oldest first, from Ironflow."""
    body = ironflow("/v1/candles", market=f"{COIN}-PERP", interval=INTERVAL, limit=SLOW + 1)
    length_ms = int(INTERVAL[:-1]) * {"m": 60, "h": 3600, "d": 86400}[INTERVAL[-1]] * 1000
    now_ms = time.time() * 1000
    return [float(c["close"]) for c in body["data"] if c["timestamp"] + length_ms <= now_ms]


def signal(prices: list[float]) -> int:
    """+1 for long, -1 for short."""
    fast = sum(prices[-FAST:]) / FAST
    slow = sum(prices[-SLOW:]) / SLOW
    return 1 if fast > slow else -1


def position(info: Info, address: str | None) -> float:
    if address is None:  # dry run: start flat
        return 0.0
    for p in info.user_state(address)["assetPositions"]:
        if p["position"]["coin"] == COIN:
            return float(p["position"]["szi"])
    return 0.0


def order_size(info: Info, want: int, held: float, price: float) -> float:
    """Size of the one market order that takes the position from held to the target."""
    decimals = info.asset_to_sz_decimals[info.name_to_asset(COIN)]
    target = want * round(SIZE_USD / price, decimals)
    return round(abs(target - held), decimals)


def step(info: Info, exchange: Exchange | None, address: str | None) -> None:
    prices = closes()
    if len(prices) < SLOW:
        print(f"only {len(prices)} candles, need {SLOW}")
        return
    want = signal(prices)
    held = position(info, address)
    side = "buy" if want > 0 else "sell"
    if held * want <= 0:  # flat, or on the wrong side: one order to the target
        size = order_size(info, want, held, prices[-1])
        if exchange is None:
            print(f"dry run: would {side} {size} {COIN} at market")
        else:
            result = exchange.market_open(COIN, want > 0, size)
            print(side, size, COIN, result["response"]["data"]["statuses"] if result["status"] == "ok" else result)
    print(f"{time.strftime('%H:%M:%S')} close {prices[-1]:,.1f}  signal {'long' if want > 0 else 'short'}  "
          f"{COIN} {position(info, address):+}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--once", action="store_true", help="one pass, then exit")
    parser.add_argument("--trade", choices=sorted(NETWORKS), help="place orders on this network (needs HL_PRIVATE_KEY)")
    args = parser.parse_args()

    exchange = address = None
    info = Info(NETWORKS[args.trade or "mainnet"], skip_ws=True)
    if args.trade:
        secret = os.environ.get("HL_PRIVATE_KEY")
        if not secret:
            sys.exit("--trade needs HL_PRIVATE_KEY, an API wallet key from https://app.hyperliquid.xyz/API")
        wallet = Account.from_key(secret)
        # With an API wallet, HL_ACCOUNT_ADDRESS is the main account it trades for.
        address = os.environ.get("HL_ACCOUNT_ADDRESS") or wallet.address
        exchange = Exchange(wallet, base_url=NETWORKS[args.trade], account_address=address)
        print(f"Trading {COIN} on Hyperliquid {args.trade} as {address}")
    else:
        print(f"Dry run on {COIN}: no orders are sent")

    try:
        print(liquidations_last_hour())
    except (requests.RequestException, IronflowError, KeyError, IndexError) as e:
        print("liquidations:", e, file=sys.stderr)

    while True:
        try:
            step(info, exchange, address)
        except (requests.RequestException, IronflowError, ClientError, KeyError) as e:
            print("step failed:", e, file=sys.stderr)
        if args.once:
            return
        time.sleep(EVERY_S)


if __name__ == "__main__":
    main()
