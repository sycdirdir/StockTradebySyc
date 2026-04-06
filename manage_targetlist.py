#!/usr/bin/env python3
"""
TargetList 管理工具

用法:
    # 从 CSV 导入到数据库
    python manage_targetlist.py import
    
    # 列出所有股票
    python manage_targetlist.py list
    
    # 列出启用的股票
    python manage_targetlist.py list --active
    
    # 启用/禁用股票
    python manage_targetlist.py enable 000001.SZ
    python manage_targetlist.py disable 000001.SZ
    
    # 搜索股票
    python manage_targetlist.py search 平安
    
    # 按行业筛选
    python manage_targetlist.py filter --industry 银行
"""
import argparse
import csv
import sys
from pathlib import Path

from db_config import get_db_config

try:
    import psycopg2
    from psycopg2.extras import execute_values
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    print("Error: psycopg2 not installed")
    sys.exit(1)


def get_connection():
    """获取数据库连接"""
    config = get_db_config()
    return psycopg2.connect(**config)


def cmd_import(csv_path: str = 'stocklist.csv'):
    """从 CSV 导入"""
    csv_file = Path(csv_path)
    if not csv_file.exists():
        print(f"Error: CSV file not found: {csv_path}")
        return 1
    
    records = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append((
                row.get('ts_code', ''),
                row.get('symbol', ''),
                row.get('name', ''),
                row.get('area', ''),
                row.get('industry', ''),
                True
            ))
    
    if not records:
        print("Error: CSV file is empty")
        return 1
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE TargetList RESTART IDENTITY")
            execute_values(
                cur,
                """INSERT INTO TargetList (ts_code, symbol, name, area, industry, is_active)
                   VALUES %s
                   ON CONFLICT (ts_code) DO UPDATE SET
                   symbol = EXCLUDED.symbol,
                   name = EXCLUDED.name,
                   area = EXCLUDED.area,
                   industry = EXCLUDED.industry,
                   is_active = EXCLUDED.is_active,
                   updated_at = CURRENT_TIMESTAMP""",
                records
            )
            conn.commit()
            print(f"Imported {len(records)} stocks")
            return 0
    finally:
        conn.close()


def cmd_list(active_only: bool = False, limit: int = 20):
    """列出股票"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if active_only:
                cur.execute("""
                    SELECT ts_code, symbol, name, industry, is_active 
                    FROM TargetList WHERE is_active = TRUE ORDER BY ts_code
                """)
            else:
                cur.execute("""
                    SELECT ts_code, symbol, name, industry, is_active 
                    FROM TargetList ORDER BY ts_code LIMIT %s
                """, (limit,))
            
            rows = cur.fetchall()
            
            print(f"\n{'TS Code':<15} {'Symbol':<10} {'Name':<20} {'Industry':<20} {'Active'}")
            print("-" * 80)
            for row in rows:
                print(f"{row[0]:<15} {row[1]:<10} {row[2]:<20} {row[3]:<20} {'Y' if row[4] else 'N'}")
            
            # 统计
            cur.execute("SELECT COUNT(*), SUM(CASE WHEN is_active THEN 1 ELSE 0 END) FROM TargetList")
            total, active = cur.fetchone()
            print(f"\nTotal: {total}, Active: {active}, Inactive: {total - active}")
            return 0
    finally:
        conn.close()


def cmd_enable(ts_code: str, enable: bool = True):
    """启用/禁用股票"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE TargetList SET is_active = %s WHERE ts_code = %s",
                (enable, ts_code)
            )
            conn.commit()
            if cur.rowcount > 0:
                print(f"{'Enabled' if enable else 'Disabled'} {ts_code}")
                return 0
            else:
                print(f"Stock not found: {ts_code}")
                return 1
    finally:
        conn.close()


def cmd_search(keyword: str):
    """搜索股票"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ts_code, symbol, name, industry, is_active 
                FROM TargetList 
                WHERE name LIKE %s OR ts_code LIKE %s OR symbol LIKE %s
                ORDER BY ts_code
            """, (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'))
            
            rows = cur.fetchall()
            
            if not rows:
                print(f"No results for: {keyword}")
                return 1
            
            print(f"\n{'TS Code':<15} {'Symbol':<10} {'Name':<20} {'Industry':<20} {'Active'}")
            print("-" * 80)
            for row in rows:
                print(f"{row[0]:<15} {row[1]:<10} {row[2]:<20} {row[3]:<20} {'Y' if row[4] else 'N'}")
            print(f"\nFound {len(rows)} results")
            return 0
    finally:
        conn.close()


def cmd_filter(industry: str = None, area: str = None):
    """按条件筛选"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if industry:
                cur.execute("""
                    SELECT ts_code, symbol, name, industry, is_active 
                    FROM TargetList WHERE industry = %s ORDER BY ts_code
                """, (industry,))
            elif area:
                cur.execute("""
                    SELECT ts_code, symbol, name, area, is_active 
                    FROM TargetList WHERE area = %s ORDER BY ts_code
                """, (area,))
            else:
                print("Error: Please specify --industry or --area")
                return 1
            
            rows = cur.fetchall()
            
            if not rows:
                print("No results found")
                return 1
            
            print(f"\n{'TS Code':<15} {'Symbol':<10} {'Name':<20} {'Industry/Area':<20} {'Active'}")
            print("-" * 80)
            for row in rows:
                print(f"{row[0]:<15} {row[1]:<10} {row[2]:<20} {row[3]:<20} {'Y' if row[4] else 'N'}")
            print(f"\nFound {len(rows)} results")
            return 0
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description='TargetList Management Tool')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # import
    import_parser = subparsers.add_parser('import', help='Import from CSV')
    import_parser.add_argument('--csv', default='stocklist.csv', help='CSV file path')
    
    # list
    list_parser = subparsers.add_parser('list', help='List stocks')
    list_parser.add_argument('--active', action='store_true', help='Only active stocks')
    list_parser.add_argument('--limit', type=int, default=20, help='Limit results')
    
    # enable/disable
    enable_parser = subparsers.add_parser('enable', help='Enable stock')
    enable_parser.add_argument('ts_code', help='Stock code (e.g., 000001.SZ)')
    
    disable_parser = subparsers.add_parser('disable', help='Disable stock')
    disable_parser.add_argument('ts_code', help='Stock code (e.g., 000001.SZ)')
    
    # search
    search_parser = subparsers.add_parser('search', help='Search stocks')
    search_parser.add_argument('keyword', help='Search keyword')
    
    # filter
    filter_parser = subparsers.add_parser('filter', help='Filter stocks')
    filter_parser.add_argument('--industry', help='Filter by industry')
    filter_parser.add_argument('--area', help='Filter by area')
    
    args = parser.parse_args()
    
    if args.command == 'import':
        return cmd_import(args.csv)
    elif args.command == 'list':
        return cmd_list(active_only=args.active, limit=args.limit)
    elif args.command == 'enable':
        return cmd_enable(args.ts_code, enable=True)
    elif args.command == 'disable':
        return cmd_enable(args.ts_code, enable=False)
    elif args.command == 'search':
        return cmd_search(args.keyword)
    elif args.command == 'filter':
        return cmd_filter(industry=args.industry, area=args.area)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
