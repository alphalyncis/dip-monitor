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
    "QQQ":   0.06,
    "NVDA":  0.06,
    "SNDK":  0.06,
    "AIPO":  0.06,
    "MRAAY": 0.06,
}
STATE_FILE = "state.json"
# ==================================================

STOOQ_URL = "https://stooq.com/q/d/l/?s={sym}.us&i=d"
YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=5d"


def fetch_from_stooq(symbol):
    url = STOOQ_URL.format(sym=symbol.lower())
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        text = r.read().decode("utf-8").strip()
    lines = text.splitlines()
    if len(lines) < 2:
        return None
    close = lines[-1].split(",")[4]
    if close in ("N/D", "", None):
        return None
    return float(close)


def fetch_from_yahoo(symbol):
    url = YAHOO_URL.format(sym=symbol)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read().decode("utf-8"))
    result = data["chart"]["result"][0]
    closes = result["indicators"]["quote"][0]["close"]
    # 取最后一个非空收盘价
    for c in reversed(closes):
        if c is not None:
            return float(c)
    return None


def fetch_price(symbol):
    """先试 stooq,失败再试 Yahoo。返回 float 或 None。"""
    for name, fn in [("stooq", fetch_from_stooq), ("yahoo", fetch_from_yahoo)]:
        try:
            p = fn(symbol)
            if p is not None:
                return p
        except Exception as e:
            print(f"  [WARN] {name} {symbol} failed: {e}")
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
                    "Title": "Dip 买入信号",
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
        ref = st.get("ref", price)        # 没有历史就用当前价初始化
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

        if fired:
            count += 1
            msg = (f"{sym}: 价格 {price:.2f} 跌破 next_buy {next_buy:.2f} "
                   f"(阈值{int(th*100)}%) → 买入信号 #{count}(本月第{count}次)")
            triggered.append(msg)
            print("  >>> " + msg)
            ref = price  # 触发后重置(连跌连买)
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
