#!/usr/bin/env python3
"""
使用 TargetList 数据库的示例脚本

功能：
1. 从数据库 TargetList 表读取股票列表
2. 从 PostgreSQL 加载这些股票的数据
3. 运行选股策略
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from db_loader import PostgresLoader
from Selector import BBIKDJSelector, SuperB1Selector


def main():
    print("=" * 60)
    print("TargetList 数据库使用示例")
    print("=" * 60)
    
    # 1. 创建加载器
    loader = PostgresLoader()
    
    # 2. 从 TargetList 获取股票列表
    print("\n[1] 从 TargetList 获取股票列表...")
    stocks = loader.get_target_list(use_active_only=True)
    print(f"获取到 {len(stocks)} 只启用的股票")
    print(f"前10只: {stocks[:10]}")
    
    # 3. 加载这些股票的数据（最近3个月）
    print("\n[2] 加载股票数据...")
    from datetime import datetime, timedelta
    
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')
    
    # 只取前50只作为示例
    sample_stocks = stocks[:50]
    data = loader.load_stock_data(
        ts_codes=sample_stocks,
        start_date=start_date,
        end_date=end_date,
        table='daily'
    )
    print(f"成功加载 {len(data)} 只股票的数据")
    
    # 4. 运行选股策略
    print("\n[3] 运行选股策略...")
    
    # 获取最新交易日期
    trade_date = max(df["date"].max() for df in data.values())
    print(f"分析日期: {trade_date.date()}")
    
    # KDJ 战法
    selector1 = BBIKDJSelector(
        j_threshold=15,
        bbi_min_window=20,
        max_window=120
    )
    picks1 = selector1.select(trade_date, data)
    print(f"\nKDJ战法选中: {len(picks1)} 只")
    print(f"股票: {', '.join(picks1) if picks1 else '无'}")
    
    # SuperB1 战法
    selector2 = SuperB1Selector(
        lookback_n=10,
        close_vol_pct=0.02
    )
    picks2 = selector2.select(trade_date, data)
    print(f"\nSuperB1战法选中: {len(picks2)} 只")
    print(f"股票: {', '.join(picks2) if picks2 else '无'}")
    
    print("\n" + "=" * 60)
    print("示例完成!")
    print("=" * 60)


if __name__ == '__main__':
    main()
