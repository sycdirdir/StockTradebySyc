--
-- Tushare 数据库创建脚本
-- 用于创建 StockTradebySyc 项目所需的 PostgreSQL 数据库结构
--
-- 使用方法:
--   psql -U postgres -d tushare -f schema.sql
--

-- ============================================
-- 1. 股票基础信息表
-- ============================================
CREATE TABLE IF NOT EXISTS stock_basic (
    id SERIAL PRIMARY KEY,
    ts_code VARCHAR(20) NOT NULL UNIQUE,           -- 股票代码
    symbol VARCHAR(10) NOT NULL,                   -- 股票代码（不带后缀）
    name VARCHAR(50),                              -- 股票名称
    area VARCHAR(50),                              -- 地区
    industry VARCHAR(50),                          -- 行业
    fullname VARCHAR(100),                         -- 全名
    enname VARCHAR(100),                           -- 英文名
    cnspell VARCHAR(50),                           -- 拼音缩写
    market VARCHAR(10),                            -- 市场类型
    exchange VARCHAR(10),                          -- 交易所
    curr_type VARCHAR(10),                         -- 货币类型
    list_status VARCHAR(1) DEFAULT 'L',            -- 上市状态: L上市 D退市 P暂停
    list_date VARCHAR(8),                          -- 上市日期
    delist_date VARCHAR(8),                        -- 退市日期
    is_hs VARCHAR(1),                              -- 是否沪深港通
    act_name VARCHAR(50),                          -- 实控人名称
    act_ent_type VARCHAR(50),                       -- 实控人类型
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_stock_basic_ts_code ON stock_basic(ts_code);
CREATE INDEX IF NOT EXISTS idx_stock_basic_list_status ON stock_basic(list_status);

-- ============================================
-- 2. 日线数据表
-- ============================================
CREATE TABLE IF NOT EXISTS daily (
    id SERIAL PRIMARY KEY,
    ts_code VARCHAR(20) NOT NULL,                  -- 股票代码
    trade_date VARCHAR(8) NOT NULL,                -- 交易日期 YYYYMMDD
    open NUMERIC(10,2),                            -- 开盘价
    high NUMERIC(10,2),                            -- 最高价
    low NUMERIC(10,2),                             -- 最低价
    close NUMERIC(10,2),                           -- 收盘价
    pre_close NUMERIC(10,2),                       -- 昨收价
    change NUMERIC(10,2),                          -- 涨跌额
    pct_chg NUMERIC(10,4),                         -- 涨跌幅
    vol NUMERIC(20,2),                             -- 成交量（手）
    amount NUMERIC(20,2),                          -- 成交额（千元）
    ah NUMERIC(10,2),
    al NUMERIC(10,2),
    nh NUMERIC(10,2),
    nl NUMERIC(10,2),
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ts_code, trade_date)
);

CREATE INDEX IF NOT EXISTS idx_daily_ts_code ON daily(ts_code);
CREATE INDEX IF NOT EXISTS idx_daily_trade_date ON daily(trade_date);
CREATE INDEX IF NOT EXISTS idx_daily_composite ON daily(ts_code, trade_date);
CREATE INDEX IF NOT EXISTS idx_daily_indicator ON daily(trade_date, ts_code);

-- ============================================
-- 3. 周线数据表
-- ============================================
CREATE TABLE IF NOT EXISTS stock_weekly (
    id SERIAL PRIMARY KEY,
    ts_code VARCHAR(20) NOT NULL,
    trade_date VARCHAR(8) NOT NULL,
    open NUMERIC(10,2),
    high NUMERIC(10,2),
    low NUMERIC(10,2),
    close NUMERIC(10,2),
    pre_close NUMERIC(10,2),
    change NUMERIC(10,2),
    pct_chg NUMERIC(10,4),
    vol NUMERIC(20,2),
    amount NUMERIC(20,2),
    ah NUMERIC(10,2),
    al NUMERIC(10,2),
    nh NUMERIC(10,2),
    nl NUMERIC(10,2),
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ts_code, trade_date)
);

CREATE INDEX IF NOT EXISTS idx_weekly_ts_code ON stock_weekly(ts_code);
CREATE INDEX IF NOT EXISTS idx_weekly_trade_date ON stock_weekly(trade_date);

-- ============================================
-- 4. 月线数据表
-- ============================================
CREATE TABLE IF NOT EXISTS stock_monthly (
    id SERIAL PRIMARY KEY,
    ts_code VARCHAR(20) NOT NULL,
    trade_date VARCHAR(8) NOT NULL,
    open NUMERIC(10,2),
    high NUMERIC(10,2),
    low NUMERIC(10,2),
    close NUMERIC(10,2),
    pre_close NUMERIC(10,2),
    change NUMERIC(10,2),
    pct_chg NUMERIC(10,4),
    vol NUMERIC(20,2),
    amount NUMERIC(20,2),
    ah NUMERIC(10,2),
    al NUMERIC(10,2),
    nh NUMERIC(10,2),
    nl NUMERIC(10,2),
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ts_code, trade_date)
);

CREATE INDEX IF NOT EXISTS idx_monthly_ts_code ON stock_monthly(ts_code);
CREATE INDEX IF NOT EXISTS idx_monthly_trade_date ON stock_monthly(trade_date);

-- ============================================
-- 5. 分钟线数据表
-- ============================================
CREATE TABLE IF NOT EXISTS stock_1min (
    id BIGSERIAL PRIMARY KEY,
    ts_code VARCHAR(20) NOT NULL,
    trade_time TIMESTAMP NOT NULL,
    open NUMERIC(10,2),
    high NUMERIC(10,2),
    low NUMERIC(10,2),
    close NUMERIC(10,2),
    vol NUMERIC(20,2),
    amount NUMERIC(20,2),
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ts_code, trade_time)
);
CREATE INDEX IF NOT EXISTS idx_1min_ts_code ON stock_1min(ts_code);
CREATE INDEX IF NOT EXISTS idx_1min_trade_time ON stock_1min(trade_time);

CREATE TABLE IF NOT EXISTS stock_5min (
    id BIGSERIAL PRIMARY KEY,
    ts_code VARCHAR(20) NOT NULL,
    trade_time TIMESTAMP NOT NULL,
    open NUMERIC(10,2),
    high NUMERIC(10,2),
    low NUMERIC(10,2),
    close NUMERIC(10,2),
    vol NUMERIC(20,2),
    amount NUMERIC(20,2),
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ts_code, trade_time)
);
CREATE INDEX IF NOT EXISTS idx_5min_ts_code ON stock_5min(ts_code);
CREATE INDEX IF NOT EXISTS idx_5min_trade_time ON stock_5min(trade_time);

CREATE TABLE IF NOT EXISTS stock_30min (
    id BIGSERIAL PRIMARY KEY,
    ts_code VARCHAR(20) NOT NULL,
    trade_time TIMESTAMP NOT NULL,
    open NUMERIC(10,2),
    high NUMERIC(10,2),
    low NUMERIC(10,2),
    close NUMERIC(10,2),
    vol NUMERIC(20,2),
    amount NUMERIC(20,2),
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ts_code, trade_time)
);
CREATE INDEX IF NOT EXISTS idx_30min_ts_code ON stock_30min(ts_code);
CREATE INDEX IF NOT EXISTS idx_30min_trade_time ON stock_30min(trade_time);

CREATE TABLE IF NOT EXISTS stock_60min (
    id BIGSERIAL PRIMARY KEY,
    ts_code VARCHAR(20) NOT NULL,
    trade_time TIMESTAMP NOT NULL,
    open NUMERIC(10,2),
    high NUMERIC(10,2),
    low NUMERIC(10,2),
    close NUMERIC(10,2),
    vol NUMERIC(20,2),
    amount NUMERIC(20,2),
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ts_code, trade_time)
);
CREATE INDEX IF NOT EXISTS idx_60min_ts_code ON stock_60min(ts_code);
CREATE INDEX IF NOT EXISTS idx_60min_trade_time ON stock_60min(trade_time);

-- ============================================
-- 6. 指数基础信息表
-- ============================================
CREATE TABLE IF NOT EXISTS index_basic (
    id SERIAL PRIMARY KEY,
    ts_code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(50),
    fullname VARCHAR(100),
    market VARCHAR(10),
    publisher VARCHAR(50),
    category VARCHAR(20),
    base_date VARCHAR(8),
    base_point NUMERIC(10,2),
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 7. TargetList 选股目标表
-- ============================================
CREATE TABLE IF NOT EXISTS TargetList (
    id SERIAL PRIMARY KEY,
    ts_code VARCHAR(20) NOT NULL UNIQUE,
    symbol VARCHAR(10) NOT NULL,
    name VARCHAR(50),
    area VARCHAR(50),
    industry VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_targetlist_symbol ON TargetList(symbol);
CREATE INDEX IF NOT EXISTS idx_targetlist_industry ON TargetList(industry);
CREATE INDEX IF NOT EXISTS idx_targetlist_active ON TargetList(is_active);
