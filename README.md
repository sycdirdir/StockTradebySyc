# Z哥战法的 Python 实现(更新版)

> **更新时间:2025-12-26** -
>
> 新增 **BigBullishVolumeSelector(暴力K战法)**:用于捕捉放量启动、贴近短线均值的强势阳线;

---

## 目录

* [项目简介](#项目简介)
* [快速上手](#快速上手)

  * [环境与依赖](#环境与依赖)
  * [准备 Tushare Token](#准备-tushare-token)
  * [准备 stocklist.csv](#准备-stocklistcsv)
  * [下载历史 K 线(qfq,多周期)](#下载历史-k-线qfq多周期)
  * [运行选股](#运行选股)
* [参数说明](#参数说明)

  * [`fetch_kline.py`](#fetch_klinepy)
  * [`select_stock.py`](#select_stockpy)
* [统一当日过滤 & 知行约束](#统一当日过滤--知行约束)
* [内置策略(Selector)](#内置策略selector)

  * [1. BBIKDJSelector(kdj战法)](#1-bbikdjselectorkdj战法)
  * [2. SuperB1Selector(SuperB1战法)](#2-superb1selectorsuperb1战法)
  * [3. BBIShortLongSelector(补票战法)](#3-bbishortlongselector补票战法)
  * [4. PeakKDJSelector(填坑战法)](#4-peakkdjselector填坑战法)
  * [5. MA60CrossVolumeWaveSelector(上穿60放量战法)](#5-ma60crossvolumewaveselector上穿60放量战法)
  * [6. BigBullishVolumeSelector(暴力K战法)](#6-bigbullishvolumeselector暴力k战法)

* [项目结构](#项目结构)
* [常见问题](#常见问题)
* [免责声明](#免责声明)

---

## 项目简介

| 名称                    | 功能简介

---

## 快速上手

### 环境与依赖

```bash
# Python 3.11/3.12 均可,示例以 3.12
conda create -n stock python=3.12 -y
conda activate stock

# 进入你的项目目录
cd /path/to/your/project

# 安装依赖
pip install -r requirements.txt
```

> 关键依赖:`pandas`, `tqdm`, `tushare`, `numpy`, `scipy`。

### 准备配置文件

项目使用 `.env` 文件管理敏感配置(API Token、Webhook Key 等)。

1. 复制配置模板:

```bash
cp .env.example .env
```

2. 编辑 `.env` 文件,填入你的实际配置:

```bash
# Tushare Token(从 https://tushare.pro/ 获取)
TUSHARE_TOKEN=your_tushare_token_here

# 企业微信机器人 Webhook Key(可选)
QYWX_WEBHOOK_KEY=your_qywx_webhook_key_here
```

> **注意**:`.env` 文件已被添加到 `.gitignore`,不会被提交到 Git,请放心使用。

**替代方案**:你也可以直接设置环境变量:

```bash
# macOS / Linux (bash)
export TUSHARE_TOKEN=your_token
export QYWX_WEBHOOK_KEY=your_key

# Windows (PowerShell)
$env:TUSHARE_TOKEN="your_token"
$env:QYWX_WEBHOOK_KEY="your_key"
```

### 下载历史 K 线(qfq,多周期)

```bash
python fetch_kline.py \
  --start 20240101 \
  --end today \
  --freq 30min \
  --stocklist ./stocklist.csv \
  --exclude-boards gem star bj \
  --out ./data \
  --workers 6
```

* **数据源固定**:Tushare K 线,**前复权 qfq**;支持周期:`D/W/M/1min/5min/15min/30min/60min`。
* **保存策略**:每只股票**全量覆盖写入** `./data/<freq>/XXXXXX.csv`(如 `./data/30min/000001.csv`)。
* **并发抓取**:默认 6 线程;支持封禁冷却(命中「访问频繁/429/403...」将睡眠约 600s 并重试,最多 3 次)。

### 运行选股

```bash
python select_stock.py \
  --data-dir ./data/30min \
  --config ./configs.json \
  --date 2025-09-10
```

> `--date` 可省略,默认取数据中的最后交易日。
>
> 若抓取日线(`--freq D`),通常使用 `--data-dir ./data/d`。

---

## 参数说明

### `fetch_kline.py`

| 参数                 | 默认值               | 说明                                                                         |
| ------------------ | ----------------- | -------------------------------------------------------------------------- |
| `--start`          | `20190101`        | 起始日期,格式 `YYYYMMDD` 或 `today`                                               |
| `--end`            | `today`           | 结束日期,格式同上                                                                  |
| `--freq`           | `D`               | K线周期:`D/W/M/1min/5min/15min/30min/60min`                                     |
| `--stocklist`      | `./stocklist.csv` | 股票清单 CSV 路径(含 `ts_code` 或 `symbol`)                                        |
| `--exclude-boards` | `[]`              | 排除板块,枚举:`gem`(创业板 300/301) / `star`(科创板 688) / `bj`(北交所 .BJ / 4/8 开头)。可多选。 |
| `--out`            | `./data`          | 输出根目录(自动创建 `./data/<freq>/` 子目录)                                      |
| `--workers`        | `6`               | 并发线程数                                                                      |

**输出 CSV 列**:`date, open, close, high, low, volume`(按日期升序)。

**抓取与重试**:每支股票最多 3 次尝试;疑似限流/封禁触发 **600s 冷却**;其它异常采用递进式短等候重试(15s×尝试次数)。

### `select_stock.py`

| 参数           | 默认值              | 说明       |
| ------------ | ---------------- | -------- |
| `--data-dir` | `./data`         | CSV 行情目录 |
| `--config`   | `./configs.json` | 选择器配置    |
| `--date`     | 数据最后交易日          | 选股交易日    |

---

## 内置策略(Selector)

> **提示**:文中"窗口"均指交易日数量。实际实现均已替换为最新代码逻辑。

### 1. BBIKDJSelector(KDJ战法)

核心逻辑:

* **价格波动约束**:最近 `max_window` 根收盘价的波动(`high/low-1`)≤ `price_range_pct`;
* **BBI 上升**:`bbi_deriv_uptrend`,允许一阶差分在 `bbi_q_threshold` 分位内为负(容忍回撤);
* **KDJ 低位**:当日 J 值 **< `j_threshold`** 或 **≤ 最近 `max_window` 的 `j_q_threshold` 分位**;
* **MACD**:`DIF > 0`;
* **MA60 条件**:当日 `close ≥ MA60` 且最近 `max_window` 内存在"**有效上穿 MA60**";
* **知行当日约束**:**收盘 > 长期线** 且 **短期线 > 长期线**。

`configs.json` 预设(与示例一致):

```json
{
  "class": "BBIKDJSelector",
  "alias": "KDJ战法",
  "activate": true,
  "params": {
    "j_threshold": 15,
    "bbi_min_window": 20,
    "max_window": 120,
    "price_range_pct": 1,
    "bbi_q_threshold": 0.2,
    "j_q_threshold": 0.10
  }
}
```

### 2. SuperB1Selector(SuperB1战法)

核心逻辑:

1. 在 `lookback_n` 窗内,存在某日 `t_m` **满足 BBIKDJSelector**;
2. 区间 `[t_m, 当日前一日]` 收盘价波动率 ≤ `close_vol_pct`;
3. 当日相对前一日 **下跌 ≥ `price_drop_pct`**;
4. 当日 J **< `j_threshold`** 或 **≤ `j_q_threshold` 分位**;
5. **知行约束**:

   * 在 `t_m` 当日:**收盘 > 长期线** 且 **短期线 > 长期线**;
   * 在 **当日**:只需 **短期线 > 长期线**。

`configs.json` 预设:

```json
{
  "class": "SuperB1Selector",
  "alias": "SuperB1战法",
  "activate": true,
  "params": {
    "lookback_n": 10,
    "close_vol_pct": 0.02,
    "price_drop_pct": 0.02,
    "j_threshold": 10,
    "j_q_threshold": 0.10,
    "B1_params": {
      "j_threshold": 15,
      "bbi_min_window": 20,
      "max_window": 120,
      "price_range_pct": 1,
      "bbi_q_threshold": 0.3,
      "j_q_threshold": 0.10
    }
  }
}
```

### 3. BBIShortLongSelector(补票战法)

核心逻辑:

* **BBI 上升**(容忍回撤);
* 最近 `m` 日内:

  * 长 RSV(`n_long`)**全 ≥ `upper_rsv_threshold`**;
  * 短 RSV(`n_short`)出现"**先 ≥ upper,再 < lower**"的序列结构;
  * 当日短 RSV **≥ upper**;
* **MACD**:`DIF > 0`;
* **知行当日约束**:**收盘 > 长期线** 且 **短期线 > 长期线**。

`configs.json` 预设:

```json
{
  "class": "BBIShortLongSelector",
  "alias": "补票战法",
  "activate": true,
  "params": {
    "n_short": 5,
    "n_long": 21,
    "m": 5,
    "bbi_min_window": 2,
    "max_window": 120,
    "bbi_q_threshold": 0.2,
    "upper_rsv_threshold": 75,
    "lower_rsv_threshold": 25
  }
}
```

### 4. PeakKDJSelector(填坑战法)

核心逻辑:

* 基于 `open/close` 的 `oc_max` 寻找峰值(`scipy.signal.find_peaks`);
* 选择最新峰 `peak_t` 与其前方**有效参照峰** `peak_(t-n)`:要求 `oc_t > oc_(t-n)`,并确保区间内其它峰不"抬高门槛";且 `oc_(t-n)` 必须 **高于区间最低收盘价 `gap_threshold`**;
* 当日收盘与 `peak_(t-n)` 的波动率 ≤ `fluc_threshold`;
* 当日 J **< `j_threshold`** 或 **≤ `j_q_threshold` 分位**;
* **知行当日约束**:**收盘 > 长期线** 且 **短期线 > 长期线**。

`configs.json` 预设:

```json
{
  "class": "PeakKDJSelector",
  "alias": "填坑战法",
  "activate": true,
  "params": {
    "j_threshold": 10,
    "max_window": 120,
    "fluc_threshold": 0.03,
    "j_q_threshold": 0.10,
    "gap_threshold": 0.2
  }
}
```

### 5. MA60CrossVolumeWaveSelector(上穿60放量战法)

核心逻辑:

1. 当日 J **< `j_threshold`** 或 **≤ `j_q_threshold` 分位**;
2. 最近 `lookback_n` 内存在**有效上穿 MA60**;
3. 以上穿日 `T` 到当日区间内 **High 最大日** 作为 `Tmax`,定义上涨波段 `[T, Tmax]`,其 **平均成交量 ≥ `vol_multiple` × 上穿前等长或截断窗口的平均量**;
4. `MA60` 的最近 `ma60_slope_days` 日 **回归斜率 > 0**;
5. **知行当日约束**:**收盘 > 长期线** 且 **短期线 > 长期线**。

`configs.json` 预设:

```json
{
  "class": "MA60CrossVolumeWaveSelector",
  "alias": "上穿60放量战法",
  "activate": true,
  "params": {
    "lookback_n": 25,
    "vol_multiple": 1.8,
    "j_threshold": 15,
    "j_q_threshold": 0.10,
    "ma60_slope_days": 5,
    "max_window": 120
  }
}
```

> **已移除**:`BreakoutVolumeKDJSelector(TePu 战法)`。

### 6. BigBullishVolumeSelector(暴力K战法)

核心逻辑:

1. **当日为长阳**:
   当日涨幅 `(close / prev_close - 1)` **大于 `up_pct_threshold`**;

2. **上影线短**:
   上影线比例
   \[
   \frac{High - \max(Open, Close)}{\max(Open, Close)}
   \]
   **小于 `upper_wick_pct_max`**,用于过滤冲高回落型假阳线;

3. **放量突破**:
   当日成交量
   \[
   Volume_{today} \ge vol\_multiple \times \text{前 } n \text{ 日均量}
   \]

4. **贴近知行短线(不过热)**:
   计算 `ZXDQ = EMA(EMA(C,10),10)`,要求
   \[
   Close < ZXDQ \times close\_lt\_zxdq\_mult
   \]
   用于过滤已经明显脱离短线均值、过度加速的股票。

5. (可选)**收阳约束**:`close ≥ open`。

该策略意在捕捉:
> **"刚刚放量启动的强势阳线,但尚未远离短期均线、仍具延续空间的个股"。**

---

`configs.json` 预设:

```json
{
  "class": "BigBullishVolumeSelector",
  "alias": "暴力K战法",
  "activate": true,
  "params": {
    "up_pct_threshold": 0.06,
    "upper_wick_pct_max": 0.02,
    "require_bullish_close": true,
    "close_lt_zxdq_mult": 1.15,
    "vol_lookback_n": 20,
    "vol_multiple": 2.5
  }
}


---

## 使用方法

### 完整使用流程

#### 1. 环境准备

```bash
# 克隆仓库
git clone git@github.com:sycdirdir/StockTradebySyc.git
cd StockTradebySyc

# 创建虚拟环境
conda create -n stock python=3.12 -y
conda activate stock

# 安装依赖
pip install -r requirements.txt
```

#### 2. 配置 API 密钥

```bash
# 复制配置模板
cp .env.example .env

# 编辑 .env 文件,填入你的 Tushare Token
# TUSHARE_TOKEN=your_token_here
vim .env
```

#### 3. 准备股票池

创建 `stocklist.csv` 文件,格式如下:

```csv
ts_code,symbol,name
000001.SZ,000001,平安银行
000002.SZ,000002,万科A
600000.SH,600000,浦发银行
```

或使用简单格式:

```csv
symbol
000001
000002
600000
```

#### 4. 下载历史数据

```bash
# 下载日线数据(默认周期)
python fetch_kline.py --start 20240101 --end today

# 下载30分钟线数据
python fetch_kline.py --start 20240101 --freq 30min --workers 8

# 下载数据并排除创业板、科创板、北交所
python fetch_kline.py --start 20240101 --exclude-boards gem star bj
```

#### 5. 运行选股

```bash
# 使用默认配置运行选股(分析最近一个交易日)
python select_stock.py --data-dir ./data/d

# 指定日期运行选股
python select_stock.py --data-dir ./data/30min --date 2025-09-10

# 使用自定义配置文件
python select_stock.py --data-dir ./data/d --config ./my_configs.json
```

#### 6. 发送企业微信通知(可选)

```bash
# 在 .env 中配置 QYWX_WEBHOOK_KEY 后,可以在选股脚本中集成通知
# 或在其他脚本中调用:
python -c "
from send_qywx import send_wechat_message
send_wechat_message('选股完成,发现3只符合条件的股票', mentioned_list=['@all'])
"
```

### 配置策略参数

编辑 `configs.json` 调整各战法的参数:

```json
{
  "selectors": [
    {
      "class": "BBIKDJSelector",
      "alias": "KDJ战法",
      "activate": true,      // 设为 false 可禁用该策略
      "params": {
        "j_threshold": 15,   // 调整 J 值阈值
        "max_window": 120    // 调整分析窗口
      }
    }
  ]
}
```

### 自动化运行(Linux/macOS)

创建定时任务(crontab):

```bash
# 编辑 crontab
crontab -e

# 添加定时任务(示例:每个交易日15:30运行选股)
30 15 * * 1-5 cd /path/to/StockTradebySyc && conda activate stock && python select_stock.py --data-dir ./data/d >> ./cron.log 2>&1
```

---

## 项目结构

```
.
├── .env                     # 环境变量配置文件(敏感信息,不提交Git)
├── .env.example             # 配置模板(可提交Git)
├── config.py                # 配置管理模块
├── configs.json             # 选择器参数(示例见上文)
├── configs.yaml             # YAML 格式配置示例
├── fetch_kline.py           # 从 stocklist.csv 读取并抓取 Tushare K 线(qfq,多周期)
├── fetch_min_klinepy        # 分钟级数据抓取
├── select_stock.py          # 批量选股入口(支持 CSV 和 PostgreSQL)
├── Selector.py              # 策略实现(含公共指标/过滤)
├── send_qywx.py             # 企业微信通知模块
├── benchmark.py             # 性能测试脚本
├── config.py                # 配置管理模块
├── db_config.py             # 数据库配置
├── db_loader.py             # PostgreSQL 数据加载器
├── sync_data.py             # 数据同步到 PostgreSQL
├── calculate_4line.py       # 4Line 指标计算
├── daily_job.py             # 每日自动同步任务
├── stocklist.csv            # 你的股票池(示例列:ts_code/symbol/...)
├── data/                    # 行情 CSV 输出根目录(按周期分子目录:d/5min/30min...)
├── database/                # 数据库脚本目录
│   ├── schema.sql           # 数据库创建脚本
│   ├── backup.sh            # 数据库备份脚本
│   ├── restore.sh           # 数据库恢复脚本
│   └── backups/             # 备份文件存放目录
├── .cache/                  # 数据缓存目录
├── fetch.log                # 抓取日志
└── select_results.log       # 选股日志
```

---

## 常见问题

**Q1：如何获取 Tushare Token？**
访问 [Tushare Pro](https://tushare.pro/) 注册账号，在个人中心获取 API Token。免费版有积分限制，建议根据需求选择合适的套餐。

**Q2：如何获取企业微信 Webhook Key？**
在企业微信群中，点击右上角「...」→「群机器人」→「添加机器人」→ 复制 Webhook 地址中的 `key` 参数值。

**Q3：为什么抓取会"卡住很久"？**
可能命中 Tushare 频控或网络封禁。脚本检测到典型关键字（如"访问频繁/429/403"）时，会进入**长冷却（默认 600s）**再重试。

**Q4：为什么不做增量合并？**
考虑采用增量更新会遇到前复权的问题，本版选择**每次全量覆盖写入**。

**Q5：创业板/科创板/北交所如何排除？**
运行时使用 `--exclude-boards gem star bj`，或按需选择其一/其二。

**Q6：配置不生效怎么办？**
1. 检查 `.env` 文件是否存在且格式正确（`KEY=VALUE`，无引号）
2. 检查 `.env` 文件是否在项目根目录
3. 尝试直接设置环境变量测试：`export TUSHARE_TOKEN=your_token`
4. 检查 `config.py` 是否能正常导入：
   ```bash
   python -c "from config import TUSHARE_TOKEN; print('Token loaded:', bool(TUSHARE_TOKEN))"
   ```

---

## PostgreSQL 数据源支持

项目现已支持直接从 PostgreSQL 数据库读取数据，无需下载 CSV 文件。

### 新增功能

| 文件 | 功能 |
|------|------|
| `db_config.py` | 数据库配置管理 |
| `db_loader.py` | PostgreSQL 数据加载器 |
| `sync_data.py` | 从 Tushare 同步数据到 PostgreSQL |
| `calculate_4line.py` | 计算 4Line 指标 (AH/AL/NH/NL) |
| `daily_job.py` | 每日自动同步任务 |

### 使用方法

#### 1. 从 PostgreSQL 运行选股

```bash
# 使用 PostgreSQL 数据源（日线）
python select_stock.py --postgres --pg-table daily --pg-start 20240101

# 使用周线数据
python select_stock.py --postgres --pg-table stock_weekly

# 指定股票代码
python select_stock.py --postgres --tickers 000001,000002,600000
```

#### 2. 同步数据到 PostgreSQL

```bash
# 同步日线数据
python sync_data.py --daily

# 同步周线/月线数据
python sync_data.py --weekly-monthly

# 同步所有数据
python sync_data.py --all
```

#### 3. 计算 4Line 指标

```bash
# 计算所有表的 4Line 指标
python calculate_4line.py

# 使用 SQL 窗口函数（更快）
python calculate_4line.py

# 使用 Python 逐股计算（更稳定）
python calculate_4line.py --python
```

#### 4. 每日自动任务

```bash
# 手动运行
python daily_job.py

# 添加到 crontab（每个交易日 17:00 运行）
0 17 * * 1-5 cd /path/to/project && python daily_job.py >> /var/log/daily_job.log 2>&1
```

#### 5. 数据库管理

```bash
# 创建数据库（首次使用）
cd database
psql -U postgres -f schema.sql

# 备份数据库
./backup.sh                    # 备份到默认目录
./backup.sh /path/to/backup    # 备份到指定目录

# 恢复数据库
./restore.sh backups/tushare_backup_20260406_213011.sql.gz
```

### 数据库配置

编辑 `.env` 文件配置数据库连接：

```bash
# PostgreSQL 配置（可选，默认使用本地 socket）
PGHOST=/var/run/postgresql
PGPORT=12335
PGDATABASE=tushare
PGUSER=postgres
PGPASSWORD=your_password
```

---

## 数据库说明

### 表结构

| 表名 | 说明 | 字段 |
|------|------|------|
| `stock_basic` | 股票基础信息 | ts_code, symbol, name, industry, list_date... |
| `daily` | 日线数据 | ts_code, trade_date, open/high/low/close, vol, amount, ah/al/nh/nl... |
| `stock_weekly` | 周线数据 | 同上 |
| `stock_monthly` | 月线数据 | 同上 |
| `stock_1min/5min/30min/60min` | 分钟线数据 | ts_code, trade_time, open/high/low/close... |
| `index_basic` | 指数基础信息 | ts_code, name, market... |
| `index_daily/week/month` | 指数数据 | ts_code, trade_date, close... |

### 4Line 指标字段

- `ah` - AH: 最高突破价 (Average High)
- `al` - AL: 最低支撑价 (Average Low)
- `nh` - NH: 近高突破价 (Near High)
- `nl` - NL: 近低支撑价 (Near Low)

计算公式：
```
N = 3
PT = REF(HIGH,1) - REF(LOW,1)
CDP = (HIGH + LOW + CLOSE) / 3
AH = MA(CDP + PT, N)
AL = MA(CDP - PT, N)
NH = MA(2*CDP - LOW, N)
NL = MA(2*CDP - HIGH, N)
```

---

## 免责声明

* 本仓库仅供学习与技术研究之用,**不构成任何投资建议**。股市有风险,入市需谨慎。
* 数据来源与接口可能随平台策略调整而变化,请合法合规使用。
* 致谢 **@Zettaranc** 在 Bilibili 的无私分享:[https://b23.tv/JxIOaNE](https://b23.tv/JxIOaNE)
