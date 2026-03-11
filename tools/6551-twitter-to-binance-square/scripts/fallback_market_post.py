#!/usr/bin/env python3
import json
import os
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SQUARE_API_URL = "https://www.binance.com/bapi/composite/v1/public/pgc/openApi/content/add"
COINGECKO_SIMPLE_PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"
COINGECKO_TRENDING_URL = "https://api.coingecko.com/api/v3/search/trending"
COINGECKO_GLOBAL_URL = "https://api.coingecko.com/api/v3/global"
TWITTER_API_BASE = "https://ai.6551.io"

COINS = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "binancecoin": "BNB",
}


def get_json(url: str) -> dict:
    req = Request(url, headers={"accept": "application/json", "user-agent": "Mozilla/5.0"})
    with urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def post_json(url: str, headers: dict, payload: dict) -> dict:
    req = Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    with urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_market_snapshot() -> dict:
    params = urlencode({
        "ids": ",".join(COINS.keys()),
        "vs_currencies": "usd",
        "include_24hr_change": "true",
        "include_24hr_high": "true",
        "include_24hr_low": "true",
        "include_market_cap": "true",
        "include_24hr_vol": "true",
    })
    return get_json(f"{COINGECKO_SIMPLE_PRICE_URL}?{params}")


def fetch_trending() -> list[dict]:
    data = get_json(COINGECKO_TRENDING_URL)
    coins = []
    for item in data.get("coins", [])[:5]:
        coin = item.get("item", {})
        coins.append({
            "name": coin.get("name", ""),
            "symbol": coin.get("symbol", ""),
            "market_cap_rank": coin.get("market_cap_rank", "N/A"),
        })
    return coins


def fetch_global() -> dict:
    return get_json(COINGECKO_GLOBAL_URL).get("data", {})


def fetch_x_hot_topics() -> list[dict]:
    token = os.environ.get("TWITTER_TOKEN", "")
    if not token:
        return []
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "keywords": "(bitcoin OR btc OR ethereum OR eth OR solana OR sol OR bnb OR meme OR memecoin)",
        "maxResults": 8,
        "product": "Top",
    }
    try:
        data = post_json(f"{TWITTER_API_BASE}/open/twitter_search", headers, payload)
    except Exception:
        return []

    items = data.get("data", []) if isinstance(data, dict) else []
    if items is None:
        items = []
    if isinstance(items, dict):
        items = items.get("tweets", []) or items.get("results", []) or []
    if items is None:
        items = []

    hot = []
    for t in items[:4]:
        text = (t.get("text") or "").replace("\n", " ").strip()
        if not text:
            continue
        hot.append({
            "user": t.get("userScreenName") or t.get("screenName") or "unknown",
            "text": text[:120],
        })
    return hot


def fmt_num(value: float) -> str:
    if value >= 1_000_000_000:
        return f"{value/1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"{value/1_000_000:.2f}M"
    return f"{value:,.2f}"


def coin_bias(chg: float) -> str:
    if chg > 3:
        return "偏强"
    if chg < -3:
        return "偏弱"
    return "震荡"


def range_judgement(name: str, item: dict) -> str:
    last = float(item.get("usd", 0))
    high = float(item.get("usd_24h_high", last) or last)
    low = float(item.get("usd_24h_low", last) or last)
    if high == low:
        band = last * 0.015
        high = last + band
        low = max(0, last - band)
    mid = (high + low) / 2
    if last >= mid:
        return f"{name} 当前运行在日内上半区，短线判定偏多；只要不跌回 {mid:,.2f} 下方，就按强势震荡看待，上方先盯 {high:,.2f} 的突破确认。"
    return f"{name} 当前运行在日内下半区，短线判定偏空到震荡偏弱；若迟迟站不回 {mid:,.2f} 上方，就要防继续回踩 {low:,.2f} 附近。"


def smart_money_view(btc: dict, eth: dict, bnb: dict) -> str:
    btc_vol = float(btc.get("usd_24h_vol", 0) or 0)
    eth_vol = float(eth.get("usd_24h_vol", 0) or 0)
    bnb_vol = float(bnb.get("usd_24h_vol", 0) or 0)
    leader = max([("BTC", btc_vol), ("ETH", eth_vol), ("BNB", bnb_vol)], key=lambda x: x[1])
    return (
        f"从24h成交额看，当前主导资金更集中在 {leader[0]}，对应成交额约 {fmt_num(leader[1])} 美元。"
        f"如果主流币成交额继续放大而 meme 跟涨不跟量，说明资金仍偏防守，不适合重仓追高小票。"
    )


def build_hot_events(global_data: dict, btc: dict, eth: dict, bnb: dict) -> list[str]:
    market_cap_change = float(global_data.get("market_cap_change_percentage_24h_usd", 0) or 0)
    defi_mcap = float(global_data.get("defi_market_cap", 0) or 0)
    defi_vol = float(global_data.get("defi_24h_volume", 0) or 0)
    return [
        f"全球加密总市值24h变动 {market_cap_change:+.2f}% —— {'偏利多' if market_cap_change > 1 else ('偏利空' if market_cap_change < -1 else '中性')}。",
        f"DeFi 市值约 {fmt_num(defi_mcap)} 美元，24h成交约 {fmt_num(defi_vol)} 美元，说明链上风险偏好 {'回升' if defi_vol > 1_000_000_000 else '一般'}。",
        f"BTC 24h成交额约 {fmt_num(float(btc.get('usd_24h_vol', 0) or 0))}，ETH 约 {fmt_num(float(eth.get('usd_24h_vol', 0) or 0))}，资金是否继续留在主流是接下来观察重点。",
        f"BNB 24h涨跌 {float(bnb.get('usd_24h_change', 0) or 0):+.2f}% ，如果BNB持续强于ETH，通常说明交易型情绪更活跃。",
    ]


def build_meme_section(trending: list[dict], xhot: list[dict]) -> str:
    lines = []
    if trending:
        for coin in trending[:3]:
            lines.append(f"- 热门币：{coin['name']} ({coin['symbol']})，市值排名 {coin['market_cap_rank']}，说明关注度在升温，但仍要看链上流动性和接力强度。")
    if xhot:
        for item in xhot[:3]:
            lines.append(f"- X 热议 @{item['user']}：{item['text']}")
    if not lines:
        return "当前未取到明显的 meme/X 热点数据，策略上更适合先盯主流币给方向，再决定是否扩张到高波动题材。"
    return "\n".join(lines)


def build_post() -> str:
    data = fetch_market_snapshot()
    global_data = fetch_global()
    trending = fetch_trending()
    xhot = fetch_x_hot_topics()

    btc = data["bitcoin"]
    eth = data["ethereum"]
    bnb = data["binancecoin"]
    bjt = timezone(timedelta(hours=8))
    now = datetime.now(bjt).strftime("%Y-%m-%d %H:%M 北京时间")

    btc_last = float(btc.get("usd", 0) or 0)
    eth_last = float(eth.get("usd", 0) or 0)
    bnb_last = float(bnb.get("usd", 0) or 0)
    btc_chg = float(btc.get("usd_24h_change", 0) or 0)
    eth_chg = float(eth.get("usd_24h_change", 0) or 0)
    bnb_chg = float(bnb.get("usd_24h_change", 0) or 0)

    risk_pref = "主流币更强，市场风险偏好在回升" if btc_chg > 1 and eth_chg > 1 else "市场仍偏分化，追涨需要更谨慎"
    flow_style = "资金更偏主流" if float(btc.get("usd_24h_vol", 0) or 0) > float(eth.get("usd_24h_vol", 0) or 0) else "ETH活跃度提升，风险偏好略有扩张"
    market_bias = "偏多" if btc_chg > 1 and eth_chg > 0 else ("偏空" if btc_chg < -1 and eth_chg < -1 else "震荡偏谨慎")
    action_plan = (
        "我会继续拿主流强势仓位，回调只考虑低吸，不轻易追高冷门小票。"
        if market_bias == "偏多" else
        "我会先降杠杆、降仓位，优先处理弱势仓位，等待市场重新给出更清晰方向。"
        if market_bias == "偏空" else
        "我会保持中性偏谨慎，主流币只做关键位博弈，meme 只看最强龙头，不做弱跟风。"
    )
    hot_events = build_hot_events(global_data, btc, eth, bnb)

    content = (
        f"晚间深度行情｜{now}\n\n"
        f"一、市场总览\n"
        f"BTC {btc_last:,.2f}（24h {btc_chg:+.2f}%） / ETH {eth_last:,.2f}（24h {eth_chg:+.2f}%） / BNB {bnb_last:,.2f}（24h {bnb_chg:+.2f}%）。"
        f"当前看，{risk_pref}，{flow_style}。BTC/ETH/BNB 的24h成交额分别约 {fmt_num(float(btc.get('usd_24h_vol', 0) or 0))} / {fmt_num(float(eth.get('usd_24h_vol', 0) or 0))} / {fmt_num(float(bnb.get('usd_24h_vol', 0) or 0))} 美元。\n\n"
        f"二、关键价格区间判断\n"
        f"BTC：日内低点 {float(btc.get('usd_24h_low', btc_last) or btc_last):,.2f}，高点 {float(btc.get('usd_24h_high', btc_last) or btc_last):,.2f}，当前结构 {coin_bias(btc_chg)}。{range_judgement('BTC', btc)}\n"
        f"ETH：日内低点 {float(eth.get('usd_24h_low', eth_last) or eth_last):,.2f}，高点 {float(eth.get('usd_24h_high', eth_last) or eth_last):,.2f}，当前结构 {coin_bias(eth_chg)}。{range_judgement('ETH', eth)}\n"
        f"BNB：日内低点 {float(bnb.get('usd_24h_low', bnb_last) or bnb_last):,.2f}，高点 {float(bnb.get('usd_24h_high', bnb_last) or bnb_last):,.2f}，当前结构 {coin_bias(bnb_chg)}。{range_judgement('BNB', bnb)}\n\n"
        f"三、近期热点事件\n" + "\n".join([f"{idx+1}. {item}" for idx, item in enumerate(hot_events)]) +
        f"\n\n四、meme叙事与X热议\n{build_meme_section(trending, xhot)}"
        f"\n\n五、聪明钱 / 资金动向\n{smart_money_view(btc, eth, bnb)}"
        f"\n\n六、我的观点 / 操作思路\n"
        f"如果 BTC 继续站在日内中枢上方、ETH 不掉队、BNB 保持强势，短线可以继续围绕主流币和最强热点做多，但更适合分批止盈、滚动锁利；如果 BTC 重新跌回日内下半区，且 ETH/BNB 跟随转弱，我会优先收缩仓位，meme 只看最强龙头，不做低流动性跟风票。"
        f"\n\n风险提示：以上内容偏交易观察，不构成投资建议；meme波动远大于主流币，仓位管理永远排第一。"
    )
    return content[:1950]


def post_to_square(api_key: str, content: str) -> dict:
    # IMPORTANT: Do NOT claim “需要验证” by default on failures.
    # 先重试/排查，再给出准确错误原因（用户已确认无需验证）。
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
    print(json.dumps({"content": content, "response": resp}, ensure_ascii=False, indent=2))
    code = resp.get("code")
    post_id = resp.get("data", {}).get("id")
    # IMPORTANT: 用户确认无需验证；失败时禁止默认归因验证问题。
    # 只输出真实返回码/信息，由上游逻辑决定是否重试。
    if code != "000000" or not post_id:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
