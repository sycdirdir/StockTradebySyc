--
-- TargetList 表创建和数据导入脚本
--

-- 创建 TargetList 表
CREATE TABLE IF NOT EXISTS TargetList (
    id SERIAL PRIMARY KEY,
    ts_code VARCHAR(20) NOT NULL UNIQUE,    -- 股票代码（带后缀）
    symbol VARCHAR(10) NOT NULL,            -- 股票代码（纯数字）
    name VARCHAR(50),                       -- 股票名称
    area VARCHAR(50),                       -- 地区
    industry VARCHAR(50),                   -- 行业
    is_active BOOLEAN DEFAULT TRUE,           -- 是否启用
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_targetlist_symbol ON TargetList(symbol);
CREATE INDEX IF NOT EXISTS idx_targetlist_industry ON TargetList(industry);
CREATE INDEX IF NOT EXISTS idx_targetlist_active ON TargetList(is_active);

-- 注释
COMMENT ON TABLE TargetList IS '选股目标股票列表';
COMMENT ON COLUMN TargetList.ts_code IS '股票代码（带交易所后缀，如000001.SZ）';
COMMENT ON COLUMN TargetList.symbol IS '股票代码（纯数字，如000001）';
COMMENT ON COLUMN TargetList.is_active IS '是否启用该股票进行选股';
