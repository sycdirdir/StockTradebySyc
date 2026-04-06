#!/usr/bin/env python3
"""
select_stock.py 的补丁 - 添加 TargetList 数据库支持

使用方法：
1. 从数据库 TargetList 读取股票列表并运行选股
   python select_stock_v2.py --use-targetlist-db --postgres

2. 更新股票启用状态
   python select_stock_v2.py --set-status 000001.SZ:false
"""
import sys
from pathlib import Path

# 导入原始 select_stock 的功能
sys.path.insert(0, str(Path(__file__).parent))

# 导入 stocklist_manager
try:
    from stocklist_manager import StockListManager, get_stock_list
    TARGETLIST_AVAILABLE = True
except ImportError:
    TARGETLIST_AVAILABLE = False
    print("Warning: stocklist_manager not available")


def patch_main():
    """为 main 函数添加 TargetList 支持"""
    import argparse
    
    # 先解析参数
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--use-targetlist-db', action='store_true')
    parser.add_argument('--targetlist-active-only', action='store_true', default=True)
    parser.add_argument('--set-status', help='设置股票状态，格式: ts_code:true/false')
    parser.add_argument('--import-stocklist', action='store_true', help='从 CSV 导入到数据库')
    
    # 只解析我们关心的参数
    args, remaining = parser.parse_known_args()
    
    # 处理特殊命令
    if args.set_status:
        if not TARGETLIST_AVAILABLE:
            print("Error: stocklist_manager not available")
            sys.exit(1)
        
        parts = args.set_status.split(':')
        if len(parts) != 2:
            print("Error: --set-status format should be ts_code:true/false")
            sys.exit(1)
        
        ts_code, status = parts
        is_active = status.lower() in ('true', '1', 'yes')
        
        manager = StockListManager(use_db=True)
        success = manager.set_stock_status(ts_code, is_active)
        if success:
            print(f"Updated {ts_code} is_active={is_active}")
        else:
            print(f"Stock {ts_code} not found")
        return
    
    if args.import_stocklist:
        if not TARGETLIST_AVAILABLE:
            print("Error: stocklist_manager not available")
            sys.exit(1)
        
        manager = StockListManager(use_db=True)
        count = manager.import_from_csv('stocklist.csv')
        print(f"Imported {count} stocks")
        return
    
    # 如果启用了 TargetList 数据库模式，获取股票列表
    if args.use_targetlist_db:
        if not TARGETLIST_AVAILABLE:
            print("Error: stocklist_manager not available")
            sys.exit(1)
        
        print(f"Loading stock list from database (active_only={args.targetlist_active_only})...")
        manager = StockListManager(use_db=True)
        stocks = manager.get_stock_list(use_active_only=args.targetlist_active_only)
        
        if not stocks:
            print("No stocks found in database")
            sys.exit(1)
        
        print(f"Loaded {len(stocks)} stocks from database")
        
        # 将股票列表添加到参数中
        tickers_arg = '--tickers=' + ','.join(stocks[:100])  # 限制数量避免命令行过长
        remaining = [tickers_arg if arg.startswith('--tickers') or arg == '--tickers' else arg for arg in remaining]
        if not any(arg.startswith('--tickers') for arg in remaining):
            remaining.append(tickers_arg)
    
    # 调用原始的 select_stock.py
    import subprocess
    result = subprocess.run([sys.executable, 'select_stock.py'] + remaining)
    sys.exit(result.returncode)


if __name__ == '__main__':
    patch_main()
