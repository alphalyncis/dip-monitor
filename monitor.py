"""
Dip Monitor —— 跟随高点回撤监测
每次运行:拉最新价 → 更新每只标的的参考点(滚动高点)→ 判断是否跌破 next_buy → 触发就通知。
状态(参考点 ref)存在 state.json 里,GitHub Actions 每次运行会读写它,实现"记忆"。

逻辑与你回测一致:
  - ref 跟随价格上行(创新高就抬高)
  - 价格 <= ref*(1-th) 触发买入
  - 触发后 ref 重置到当前价(连跌连买)
"""

import json
import os
import sys
import urllib.request
import datetime

# ========== CONFIG:在这里改你的标的和阈值 ==========
ASSETS = {
    "VOO":   0.04,
    "QQQ":   0.0003,
    "NVDA":  0.06,
    "SNDK":  0.06,
    "AIPO":  0.06,
    "MRAAY": 0.06,
}
STATE_FILE = "state.json"
# ==================================================

YAHOO_QUOTE = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=5d"
YAHOO_HIST = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?period1={p1}&period2={p2}&interval=1d"

# 策略起点(和你回测一致)。脚本第一次见到某只标的时,
# 会拉"起点 -> 今天"的历史,完整跑一遍你的 ref 爬高逻辑来初始化 ref。
STRATEGY_START = "2025-07-25"


def fetch_price(symbol):
    """拉最新收盘价。返回 float 或 None。"""
    url = YAHOO_QUOTE.format(sym=symbol)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode("utf-8"))
        closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        for c in reversed(closes):
            if c is not None:
                return float(c)
        return None
    except Exception as e:
        print(f"  [WARN] price {symbol} failed: {e}")
        return None


def compute_ref(symbol, th):
    """
    复现你 Python 回测的逻辑来初始化 ref:
    拉 STRATEGY_START -> 今天 的每日收盘价, 从第一天开始让 ref 跟随价格爬高,
    跌破 ref*(1-th) 则触发并把 ref 重置到买入价(连跌连买)。
    返回跑完整段历史后的当前 ref。
    """
    p1 = int(datetime.datetime.strptime(STRATEGY_START, "%Y-%m-%d")
             .replace(tzinfo=datetime.timezone.utc).timestamp())
    p2 = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    url = YAHOO_HIST.format(sym=symbol, p1=p1, p2=p2)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode("utf-8"))
        closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        px = [c for c in closes if c is not None]
        if not px:
            return None
        # ===== 你 Python 原逻辑 =====
        ref = px[0]
        for p in px:
            if p > ref:
                ref = p
            if p <= ref * (1 - th):
                ref = p
        return float(ref)
    except Exception as e:
        print(f"  [WARN] hist {symbol} failed: {e}")
        return None


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def notify(messages):
    """发通知:写 GitHub 运行摘要 + ntfy 手机推送。"""
    body = "\n".join(messages)

    # 1) 写进 GitHub Actions 的运行摘要(在 Actions 页面能看到)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write("## 🔔 Dip 触发\n\n" + body + "\n")

    # 2) ntfy 手机推送(在环境变量 NTFY_TOPIC 里填你订阅的频道名)
    topic = os.environ.get("NTFY_TOPIC")
    if topic:
        try:
            url = f"https://ntfy.sh/{topic}"
            data = body.encode("utf-8")
            req = urllib.request.Request(
                url, data=data,
                headers={
                    # HTTP 头只能 latin-1, 所以 Title 用英文; 中文内容在 body(UTF-8)里
                    "Title": "Dip Buy Signal",
                    "Priority": "high",
                    "Tags": "chart_with_downwards_trend",
                },
            )
            urllib.request.urlopen(req, timeout=20)
            print("  [OK] ntfy push sent")
        except Exception as e:
            print(f"  [WARN] ntfy failed: {e}")


def main():
    state = load_state()
    triggered = []
    today = datetime.date.today().isoformat()

    print(f"=== Dip Monitor {today} ===")
    for sym, th in ASSETS.items():
        price = fetch_price(sym)
        if price is None:
            print(f"{sym}: no price, skip")
            continue

        st = state.get(sym, {})
        if "ref" in st:
            ref = st["ref"]                       # 已有历史,沿用记忆的 ref
            first_init = False
        else:
            # 第一次见到这只:用 STRATEGY_START -> 今天 的历史跑你的逻辑,得到当前 ref
            r = compute_ref(sym, th)
            ref = r if r is not None else price
            first_init = True
            print(f"  [INIT] {sym} ref from strategy replay: {ref:.2f}")
        month = st.get("month", today[:7])
        count = st.get("count", 0)

        # 月份切换 → 重置本月计数
        if month != today[:7]:
            month = today[:7]
            count = 0

        # 更新参考点:创新高则抬高
        if price > ref:
            ref = price

        next_buy = ref * (1 - th)
        fired = price <= next_buy

        if fired and not first_init:
            count += 1
            msg = (f"{sym}: 价格 {price:.2f} 跌破 next_buy {next_buy:.2f} "
                   f"(阈值{int(th*100)}%) → 买入信号 #{count}(本月第{count}次)")
            triggered.append(msg)
            print("  >>> " + msg)
            ref = price  # 触发后重置(连跌连买)
        elif fired and first_init:
            # 初始化当天恰好已在触发位:更新 ref,但不补报历史信号
            ref = price
            print(f"  [INIT] {sym} 当前已处于触发位,ref 重置为 {price:.2f}(首次运行不补报)")
        else:
            drop_needed = (next_buy / price - 1) * 100
            print(f"{sym}: {price:.2f} | next_buy {next_buy:.2f} "
                  f"(还需{drop_needed:+.1f}%) | ref {ref:.2f} | 本月已触发{count}次")

        state[sym] = {"ref": ref, "month": month, "count": count,
                      "last_price": price, "last_check": today}

    save_state(state)

    if triggered:
        notify(triggered)
        print(f"\n触发 {len(triggered)} 个,已通知。")
    else:
        print("\n本次无触发。")


if __name__ == "__main__":
    main()
