# Dip Monitor

一个轻量、免费的股票**逢跌买入提醒**工具。跑在 GitHub Actions 上,当某只标的从近期高点回撤设定的百分比时,推送通知到你手机。

无需付费套餐、无需自己搭服务器、不涉及任何交易——它**只监测价格并提醒你**,买不买、买什么完全由你决定。

## 工作原理

对每个配置了阈值的标的:

1. 参考点 `ref` 跟随价格上行(每创新高就抬高)。
2. 当价格跌到 `ref × (1 − 阈值)` 时,触发一个**逢跌信号**。
3. 触发后 `ref` 重置到当前价——因此持续下跌会在每跌一档时继续触发("连跌连买")。

状态(滚动参考点 `ref` 和每月触发次数)保存在 `state.json` 中,每次运行后提交回仓库,因此工具能跨次运行"记住"。

```
GitHub Actions(定时)
      |
      v
   monitor.py  --->  拉取最新价格(stooq)
      |                 |
      |                 v
      |           更新 ref / 检测回撤
      |                 |
      v                 v
  state.json       通知(ntfy 推送 + 运行摘要)
```

## 特性

- **免费**——完全运行在 GitHub Actions 免费额度内
- **跟随高点逻辑**——按"从滚动高点回撤百分比"提醒,而非固定价格
- **连跌连买**——持续下跌时每跌一档继续触发
- **月度触发计数**——记录每只标的本月触发了几次
- **手机推送([ntfy](https://ntfy.sh))**——无需注册、无需 token
- **只提醒不下单**——绝不执行任何交易

## 安装步骤(约 10 分钟)

### 1. 使用本仓库
把以下文件 Fork 或复制到一个仓库中:
```
monitor.py
.github/workflows/monitor.yml
README.md
```

### 2. 配置你的标的
编辑 `monitor.py` 顶部的 `ASSETS`:
```python
ASSETS = {
    "VOO":  0.04,   # 标的 : 回撤阈值(4%)
    "QQQ":  0.06,
    "NVDA": 0.06,
    # 添加你自己的 ...
}
```

### 3.(可选)用 ntfy 推送到手机
不配置的话,结果只会写在 GitHub Actions 的运行摘要里。
想要手机推送:

1. 手机安装 **ntfy** App(App Store / Google Play)。
2. 订阅一个**随机、难猜的频道名**(例如 `dip-alert-yournamexxx`)。
   > ntfy 频道对任何知道名字的人公开——请起一个无法被猜到的名字。
3. 在仓库:**Settings -> Secrets and variables -> Actions -> New repository secret**
   - 名称(Name):`NTFY_TOPIC`
   - 值(Value):你的频道名

### 4. 启用 Actions
- 进入 **Actions** 标签页,如有提示则启用工作流。
- 手动运行一次:**Actions -> Dip Monitor -> Run workflow**。
- 之后会按 `monitor.yml` 里的定时计划自动运行。

## 调整运行频率

编辑 `.github/workflows/monitor.yml` 里的 `cron`(UTC 时间)。美股交易时段约为 UTC 14:30-21:00。每天多次检查的示例:
```yaml
schedule:
  - cron: "0 15 * * 1-5"
  - cron: "0 18 * * 1-5"
  - cron: "30 20 * * 1-5"
```

## 说明与限制

- **数据源([stooq](https://stooq.com))为收盘/延迟价**,非实时逐笔数据。适合波段/中长线建仓,不适合日内交易。
- **月度触发计数只记录、不强制**——如需"月度上限",请在据信号操作时自行执行。
- **OTC / 流动性差的标的**数据可能不全或延迟。
- GitHub Actions 免费额度对每个交易日运行几次绰绰有余。

## 免责声明

本项目仅用于**信息与教育目的**。它不执行任何交易,也**不构成投资建议**。市场有风险,你需对自己的决策负全部责任。作者不对其准确性、完整性或任何特定用途的适用性作任何担保。

## 许可证

MIT


# Dip Monitor

A lightweight, free stock **dip-buying alert** tool that runs on GitHub Actions and pushes a notification to your phone when a ticker drops a set percentage from its recent high.

No paid plan, no server to host, no trading involved — it only **watches prices and notifies you**. You stay in full control of what (if anything) you buy.

## How it works

For each ticker you configure with a threshold:

1. A reference point `ref` follows the price upward (it ratchets up on every new high).
2. When the price falls to `ref × (1 − threshold)`, a **dip signal** fires.
3. After firing, `ref` resets to the current price — so a sustained decline keeps firing at each further step down ("buy on each dip").

State (the rolling `ref` and a per-month trigger count) is stored in `state.json` and committed back each run, so the tool "remembers" across runs.

```
GitHub Actions (cron)
      |
      v
   monitor.py  --->  fetch latest prices (stooq)
      |                 |
      |                 v
      |           update ref / detect dip
      |                 |
      v                 v
  state.json       notify (ntfy push + run summary)
```

## Features

- **Free** — runs entirely on GitHub Actions' free tier
- **Trailing-high logic** — alerts on % drop from the rolling high, not a fixed price
- **Buy-on-each-dip** — keeps firing through a sustained decline
- **Monthly trigger count** — tracks how many times each ticker fired this month
- **Phone push via [ntfy](https://ntfy.sh)** — no account, no token
- **Notify-only** — never places trades

## Setup (~10 minutes)

### 1. Use this repo
Fork or copy these files into a repository:
```
monitor.py
.github/workflows/monitor.yml
README.md
```

### 2. Configure your tickers
Edit the `ASSETS` block at the top of `monitor.py`:
```python
ASSETS = {
    "VOO":  0.04,   # ticker : dip threshold (4%)
    "QQQ":  0.06,
    "NVDA": 0.06,
    # add your own ...
}
```

### 3. (Optional) Phone push with ntfy
Without this, results are written to the GitHub Actions run summary only.
To get phone pushes:

1. Install the **ntfy** app (App Store / Google Play).
2. Subscribe to a topic with a **random, hard-to-guess name** (e.g. `dip-alert-7h3k9x2`).
   > ntfy topics are public to anyone who knows the name — pick something unguessable.
3. In your repo: **Settings -> Secrets and variables -> Actions -> New repository secret**
   - Name: `NTFY_TOPIC`
   - Value: your topic name

### 4. Enable Actions
- Go to the **Actions** tab and enable workflows if prompted.
- Run it once manually: **Actions -> Dip Monitor -> Run workflow**.
- After that it runs automatically on the schedule in `monitor.yml`.

## Adjusting frequency

Edit the `cron` lines in `.github/workflows/monitor.yml` (UTC). US market hours are ~14:30-21:00 UTC. Example for a few checks per day:
```yaml
schedule:
  - cron: "0 15 * * 1-5"
  - cron: "0 18 * * 1-5"
  - cron: "30 20 * * 1-5"
```

## Notes & limitations

- **Data source ([stooq](https://stooq.com)) is end-of-day / delayed**, not real-time tick data. Fine for swing/position entries; not for intraday trading.
- The **monthly trigger count** is recorded, not enforced — if you want a monthly cap, apply it yourself when acting on alerts.
- **OTC / thinly traded tickers** may have incomplete or delayed data.
- GitHub Actions' free tier is more than enough for a few runs per weekday.

## Disclaimer

This project is for **informational and educational purposes only**. It does not place trades and is **not financial advice**. Markets involve risk; you are solely responsible for your own decisions. The authors provide no warranty of accuracy, completeness, or fitness for any purpose.

## License

MIT
