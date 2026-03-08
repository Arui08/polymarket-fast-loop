#!/usr/bin/env python3
import json
import os
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SQUARE_API_URL = "https://www.binance.com/bapi/composite/v1/public/pgc/openApi/content/add"

COINS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "BNB": "binancecoin",
}


def fetch_market() -> dict:
    params = urlencode({
        "ids": ",".join(COINS.values()),
        "vs_currencies": "usd",
        "include_24hr_change": "true",
        "include_24hr_high": "true",
        "include_24hr_low": "true",
    })
    url = f"https://api.coingecko.com/api/v3/simple/price?{params}"
    req = Request(url, headers={"accept": "application/json"})
    with urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fmt_line(name: str, data: dict) -> str:
    last = float(data["usd"])
    high = float(data.get("usd_24h_high") or last)
    low = float(data.get("usd_24h_low") or last)
    chg = float(data.get("usd_24h_change") or 0)
    support = low
    resistance = high
    bias = "偏强" if chg > 2 else ("偏弱" if chg < -2 else "震荡")
    return (
        f"{name}：现价 {last:,.2f}，24h {chg:+.2f}%。"
        f"短线支撑先看 {support:,.2f}，上方阻力关注 {resistance:,.2f}，"
        f"当前结构 {bias}。"
    )


def build_post() -> str:
    market = fetch_market()
    btc = market[COINS["BTC"]]
    eth = market[COINS["ETH"]]
    bnb = market[COINS["BNB"]]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    overall = "市场偏风险偏好回升" if float(btc.get("usd_24h_change", 0)) > 1 and float(eth.get("usd_24h_change", 0)) > 1 else "市场分化，追高要控制节奏"

    content = (
        f"晚间行情观察｜{now}\n\n"
        f"市场总览：BTC {float(btc['usd']):,.2f} / ETH {float(eth['usd']):,.2f} / BNB {float(bnb['usd']):,.2f}。{overall}。\n\n"
        f"1. {fmt_line('BTC', btc)}\n"
        f"2. {fmt_line('ETH', eth)}\n"
        f"3. {fmt_line('BNB', bnb)}\n\n"
        f"我的看法：如果 BTC 站稳日内中枢并带动 ETH/BNB 共振，短线还有上冲机会；"
        f"如果冲高后量能跟不上，就更像区间震荡，适合分批止盈，不适合盲目追涨。\n\n"
        f"风险提示：meme 和山寨波动更大，主流币如果先走弱，题材币通常会更快回撤。"
    )
    return content


def post_to_square(api_key: str, content: str) -> dict:
    payload = json.dumps({"bodyTextOnly": content}).encode("utf-8")
    headers = {
        "X-Square-OpenAPI-Key": api_key,
        "Content-Type": "application/json",
        "clienttype": "binanceSkill",
    }
    req = Request(SQUARE_API_URL, data=payload, headers=headers, method="POST")
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    api_key = os.environ["SQUARE_OPENAPI_KEY"]
    content = build_post()
    resp = post_to_square(api_key, content)
    post_id = resp.get("data", {}).get("id")
    square_url = f"https://www.binance.com/square/post/{post_id}" if post_id else None
    print(json.dumps({"content": content, "response": resp, "square_url": square_url}, ensure_ascii=False, indent=2))
    code = resp.get("code")
    if code != "000000" or not post_id:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
