# Dip Monitor

跟随高点回撤的逢跌买入监测。免费跑在 GitHub Actions 上,触发时通知你。
逻辑:参考点 ref 跟随价格高点;价格跌破 `ref*(1-阈值)` 就触发买入信号;触发后 ref 重置(连跌连买)。

## 它做什么
- 每个交易日定时拉每只标的的最新价
- 跟踪每只的滚动高点 ref(存在 state.json,自动记忆)
- 跌破 next_buy 就触发,记本月第几次,发通知
- **只通知,不下单**——你收到后自己去 IBKR 挂限价单

## 安装步骤(约 10 分钟)

### 1. 建仓库
- 在 GitHub 新建一个仓库(Private 即可),名字随便(如 `dip-monitor`)
- 把这三个文件传上去(保持目录结构):
  - `monitor.py`
  - `.github/workflows/monitor.yml`
  - `README.md`

### 2. 改你的标的和阈值
编辑 `monitor.py` 顶部的 `ASSETS`:
```python
ASSETS = {
    "VOO":   0.04,
    "QQQ":   0.06,
    "NVDA":  0.06,
    "SNDK":  0.06,
    "AIPO":  0.06,
    "MRAAY": 0.06,
}
```

### 3.(可选)配 ntfy 手机推送
不配的话,触发结果会写在 GitHub Actions 的运行摘要里(要去 Actions 页面看)。
想直接推到手机,用 **ntfy**(免费、不用注册、不用密码):

1. 手机装 **ntfy** App(App Store / Google Play 搜 "ntfy")
2. App 里点 "+" 订阅一个频道,**频道名自己起一个别人猜不到的**(比如 `dip-alert-xq8f3k2`)——
   注意:ntfy 频道是公开的,谁知道名字谁能看到,所以**起个随机、难猜的名字**
3. GitHub 仓库 → Settings → Secrets and variables → Actions → New repository secret:
   - `NTFY_TOPIC` = 你起的那个频道名(如 `dip-alert-xq8f3k2`)

触发时,手机上的 ntfy App 就会**立刻弹推送**,标题 "Dip 买入信号"。

### 4. 启用 Actions
- 仓库 → Actions 标签 → 如提示则点 "I understand, enable"
- 第一次可手动跑:Actions → Dip Monitor → "Run workflow"
- 之后按 `monitor.yml` 里的 cron 定时自动跑

## 调整运行频率
编辑 `.github/workflows/monitor.yml` 的 cron(UTC 时间):
- 现状:周一到五,每天 UTC 20:30 跑一次
- 想盘中多次:加几行,如
  ```yaml
  - cron: "0 15 * * 1-5"
  - cron: "0 18 * * 1-5"
  - cron: "30 20 * * 1-5"
  ```
  (美股盘中约 14:30–21:00 UTC)

## 注意
- **数据源 stooq 是收盘/延迟价**,不是实时 tick;对"逢跌分批、持有数月"足够,但不是秒级实时。
- **月度计数**:state.json 里记了本月触发次数,你可以据此执行"月度上限"(到上限就忽略后续)。脚本只记录不强制停,执不执行由你。
- **MRAAY 是 OTC**,stooq 数据可能不全或延迟,留意。
- GitHub Actions 免费额度对每天几次的运行**绰绰有余**(私有仓库每月 2000 分钟,这个任务每次几十秒)。
