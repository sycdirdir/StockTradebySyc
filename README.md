# QuantView Pro - 量化交易看盘系统

基于 Vue3 + ECharts + Flask 的量化交易看盘平台，对接 PostgreSQL 数据库。

## 项目结构

```
├── backend/                # Flask 后端
│   ├── app.py             # API 主文件（所有接口）
│   ├── db_config.py       # 数据库配置
│   ├── requirements.txt   # Python 依赖
│   └── .env.example       # 环境变量模板
│
├── frontend/              # Vue3 前端
│   ├── src/
│   │   ├── App.vue        # 根组件（总调度）
│   │   ├── main.js        # 入口
│   │   ├── api/
│   │   │   └── index.js   # API 请求封装
│   │   ├── composables/
│   │   │   └── useData.js # 数据逻辑 hooks
│   │   ├── components/
│   │   │   ├── KlineChart.vue    # ECharts K 线图（核心）
│   │   │   ├── TopBar.vue        # 顶部导航栏
│   │   │   ├── StockInfoBar.vue  # 股票实时信息栏
│   │   │   ├── ChartToolbar.vue  # 工具栏（周期/策略/指标）
│   │   │   ├── LegendBar.vue     # 图例栏
│   │   │   ├── SidePanel.vue     # 右侧信息面板
│   │   │   └── BottomBar.vue     # 底部状态栏
│   │   └── styles/
│   │       └── main.css   # 全局样式（设计令牌系统）
│   ├── index.html
│   ├── package.json
│   └── vite.config.js     # Vite 配置（含 API 代理）
│
└── quant-trading-view.html  # 原始单文件版本（设计参考）
```

## 快速开始

### 1. 后端（Flask）

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填入你的 PostgreSQL 连接信息
python app.py   # 启动在 http://localhost:5001
```

后端 API 接口：

| 接口 | 说明 |
|------|------|
| `GET /api/health` | 健康检查 |
| `GET /api/stocks?keyword=茅台&page=1&page_size=50` | 股票搜索 |
| `GET /api/stocks/{ts_code}` | 股票详情 |
| `GET /api/kline/{ts_code}?period=day&indicators=ma,boll,kdj` | K线+指标+信号 |
| `GET /api/strategies` | 策略列表 |
| `GET /api/stats?ts_code=600519.SH&period=day` | 交易统计 |

### 2. 前端（Vue3 + Vite）

```bash
cd frontend
npm install
npm run dev   # 启动在 http://localhost:3000
```

开发模式下前端自动代理 `/api/*` 到后端 5001 端口。

### 3. 生产构建

```bash
cd frontend && npm run build   # 输出到 dist/
```

## 数据库

对接 StockTradebySyc 项目的 PostgreSQL 数据库：
- `stock_basic` — 股票基本信息
- `daily` — 日线（含 AH/AL/NH/NL）
- `stock_weekly` / `stock_monthly` — 周/月线
- `stock_1min` ~ `stock_60min` — 分钟线

## 技术栈

- **前端**: Vue 3 (Composition API) + ECharts 5 + Vite + Axios
- **后端**: Flask 3 + Flask-CORS + psycopg2 + pandas + numpy
- **数据库**: PostgreSQL
- **样式**: CSS Design Token（深色交易主题，红涨绿跌）

## 功能特点

- K 线图（MA/BOLL/KDJ 指标切换）
- 买入/卖出信号标注
- 持仓区间高亮（盈亏色彩区分）
- 股票实时搜索
- 周期切换（1分/5分/15分/30分/60分/日/周/月）
- 策略表现统计面板
- 交易记录列表
- 响应式布局
