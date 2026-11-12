# /// script
# requires-python = ">=3.9"
# dependencies = ["hyperliquid-python-sdk==0.24.0"]
# ///
"""A small Hyperliquid trading bot on a paper box.

Signals come from Ironflow candles. Orders go through the official Hyperliquid
Python SDK to an Ironflow paper box: a simulated Hyperliquid account with
$10,000 and live prices. No real order is ever placed.

    python bot.py          # trade every 15 minutes until Ctrl+C
    python bot.py --once   # one pass, then exit
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
import time
from pathlib import Path

import requests
from eth_account import Account
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils.error import ClientError

# Strategy: long when the fast moving average is above the slow one, short
# when it is below. Edit these, or replace signal().
COIN = "BTC"          # Hyperliquid coin name
INTERVAL = "15m"      # candle interval: 1m, 5m, 15m, 1h, 4h, 1d
FAST, SLOW = 8, 21    # moving average lengths, in candles
SIZE_USD = 200        # position size in USD
EVERY_S = 15 * 60     # seconds between passes

IRONFLOW = "https://api.ironflow.sh"
KEY = os.environ.get("IRONFLOW_KEY", "")  # optional, from https://ironflow.sh/key
HEADERS = {"User-Agent": os.environ.get("IRONFLOW_USER_AGENT", "hyperliquid-trading-bot/0.1")}
if KEY:
    HEADERS["Authorization"] = f"Bearer {KEY}"
BOX_FILE = Path(__file__).with_name(".ironbox")  # the box URL, kept between runs


def new_box() -> str:
    """Create a paper box. Without a key it is a 24-hour trial box."""
    r = requests.post(f"{IRONFLOW}/v1/ironbox", json={"name": "hyperliquid-trading-bot", "mode": "paper"},
                      headers=HEADERS, timeout=30)
    r.raise_for_status()
    box = r.json()
    print("New paper box:", box.get("message", box["id"]))
    BOX_FILE.write_text(box["base_url"])
    return box["base_url"]


def connect() -> tuple[Info, Exchange, str]:
    """The box from IRONFLOW_BOX_URL, the last run, or a new one."""
    url = os.environ.get("IRONFLOW_BOX_URL") or (BOX_FILE.read_text().strip() if BOX_FILE.exists() else "")
    try:
        info = Info(url, skip_ws=True) if url else None  # a paper box has no WebSocket
    except ClientError:
        info = None  # the box expired
    if info is None:
        url = new_box()
        info = Info(url, skip_ws=True)
    # A box binds to the first wallet that signs. This one is derived from the
    # box URL, so every run signs with the same throwaway wallet.
    wallet = Account.from_key(hashlib.sha256(url.encode()).digest())
    return info, Exchange(wallet, base_url=url), wallet.address


def closes() -> list[float]:
    """Closes of the last finished candles, oldest first, from Ironflow."""
    r = requests.get(f"{IRONFLOW}/v1/candles", headers=HEADERS, timeout=30,
                     params={"market": f"{COIN}-PERP", "interval": INTERVAL, "limit": SLOW + 1})
    r.raise_for_status()
    length_ms = int(INTERVAL[:-1]) * {"m": 60, "h": 3600, "d": 86400}[INTERVAL[-1]] * 1000
    now_ms = time.time() * 1000
    return [float(c["close"]) for c in r.json()["data"] if c["timestamp"] + length_ms <= now_ms]


def signal(prices: list[float]) -> int:
    """+1 for long, -1 for short."""
    fast = sum(prices[-FAST:]) / FAST
    slow = sum(prices[-SLOW:]) / SLOW
    return 1 if fast > slow else -1


def position(info: Info, address: str) -> float:
    for p in info.user_state(address)["assetPositions"]:
        if p["position"]["coin"] == COIN:
            return float(p["position"]["szi"])
    return 0.0


def market_order(exchange: Exchange, is_buy: bool, size: float) -> object:
    """A market order, tried again while the box's book is a few seconds old."""
    for _ in range(5):
        result = exchange.market_open(COIN, is_buy, size)
        statuses = result["response"]["data"]["statuses"] if result["status"] == "ok" else result
        if "unavailable" not in str(statuses):
            break
        time.sleep(2)
    return statuses


def step(info: Info, exchange: Exchange, address: str) -> None:
    prices = closes()
    if len(prices) < SLOW:
        print(f"only {len(prices)} candles, need {SLOW}")
        return
    want = signal(prices)
    held = position(info, address)
    if held * want <= 0:  # flat, or on the wrong side: one order to the target
        decimals = info.asset_to_sz_decimals[info.name_to_asset(COIN)]
        target = want * round(SIZE_USD / float(info.all_mids()[COIN]), decimals)
        size = round(abs(target - held), decimals)
        print("buy" if want > 0 else "sell", size, COIN, market_order(exchange, want > 0, size))
    state = info.user_state(address)
    print(f"{time.strftime('%H:%M:%S')} close {prices[-1]:,.1f}  {COIN} {position(info, address):+}  "
          f"equity ${float(state['marginSummary']['accountValue']):,.2f}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--once", action="store_true", help="one pass, then exit")
    args = parser.parse_args()
    info, exchange, address = connect()
    print(f"Paper wallet {address}")
    while True:
        try:
            step(info, exchange, address)
        except (requests.RequestException, ClientError, KeyError) as e:
            print("step failed:", e, file=sys.stderr)
        if args.once:
            return
        time.sleep(EVERY_S)


if __name__ == "__main__":
    main()
