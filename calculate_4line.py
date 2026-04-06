"""
4Line 指标计算模块
计算 AH, AL, NH, NL 指标

公式:
N = 3
PT = REF(HIGH,1) - REF(LOW,1)
CDP = (HIGH + LOW + CLOSE) / 3
AH = MA(CDP + PT, N)
AL = MA(CDP - PT, N)
NH = MA(2*CDP - LOW, N)
NL = MA(2*CDP - HIGH, N)
"""
from __future__ import annotations

import argparse
import logging
import sys
from typing import List, Tuple

import psycopg2
from psycopg2.extras import execute_values

from db_config import get_db_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

N = 3  # 移动平均周期


class FourLineCalculator:
    """4Line 指标计算器"""
    
    def __init__(self):
        self.db_config = get_db_config()
    
    def _get_connection(self):
        return psycopg2.connect(**self.db_config)
    
    def calculate_sql_method(self, table_name: str, date_field: str = 'trade_date') -> int:
        """
        使用 SQL 窗口函数计算 4Line 指标
        效率最高，适合大数据量
        """
        conn = self._get_connection()
        
        try:
            with conn.cursor() as cur:
                # 检查是否需要计算
                cur.execute(f"""
                    SELECT COUNT(*) FROM {table_name} 
                    WHERE ah IS NULL OR al IS NULL OR nh IS NULL OR nl IS NULL
                    LIMIT 1
                """)
                if cur.fetchone()[0] == 0:
                    logger.info(f"  ✓ {table_name} 无需计算")
                    return 0
                
                # 使用窗口函数计算
                sql = f"""
                WITH base AS (
                    SELECT 
                        id,
                        ts_code,
                        {date_field} as trade_date,
                        high,
                        low,
                        close,
                        LAG(high, 1) OVER (PARTITION BY ts_code ORDER BY {date_field}) - 
                        LAG(low, 1) OVER (PARTITION BY ts_code ORDER BY {date_field}) as pt,
                        (high + low + close) / 3.0 as cdp
                    FROM {table_name}
                    WHERE high IS NOT NULL AND low IS NOT NULL AND close IS NOT NULL
                ),
                with_cdp AS (
                    SELECT 
                        id,
                        cdp,
                        COALESCE(pt, 0) as pt,
                        cdp + COALESCE(pt, 0) as cdp_pt,
                        cdp - COALESCE(pt, 0) as cdp_pt_minus,
                        2 * cdp - low as cdp2_low,
                        2 * cdp - high as cdp2_high
                    FROM base
                ),
                final AS (
                    SELECT 
                        id,
                        AVG(cdp_pt) OVER w as ah,
                        AVG(cdp_pt_minus) OVER w as al,
                        AVG(cdp2_low) OVER w as nh,
                        AVG(cdp2_high) OVER w as nl
                    FROM with_cdp
                    WINDOW w AS (PARTITION BY ts_code ORDER BY trade_date 
                                 ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)
                )
                UPDATE {table_name} d
                SET 
                    ah = ROUND(f.ah, 2),
                    al = ROUND(f.al, 2),
                    nh = ROUND(f.nh, 2),
                    nl = ROUND(f.nl, 2)
                FROM final f
                WHERE d.id = f.id
                AND (d.ah IS NULL OR d.al IS NULL OR d.nh IS NULL OR d.nl IS NULL)
                """
                
                cur.execute(sql)
                conn.commit()
                
                # 统计
                cur.execute(f"""
                    SELECT COUNT(*) FROM {table_name} 
                    WHERE ah IS NOT NULL AND al IS NOT NULL 
                    AND nh IS NOT NULL AND nl IS NOT NULL
                """)
                updated = cur.fetchone()[0]
                
                logger.info(f"  ✓ {table_name}: 已计算 {updated:,} 条记录")
                return updated
                
        except Exception as e:
            logger.error(f"  ❌ {table_name} SQL计算失败: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()
    
    def calculate_python_method(self, table_name: str, date_field: str = 'trade_date') -> int:
        """
        使用 Python 逐股计算 4Line 指标
        更稳定，适合 SQL 方法失败时回退
        """
        conn = self._get_connection()
        
        try:
            with conn.cursor() as cur:
                # 获取需要计算的股票
                cur.execute(f"""
                    SELECT DISTINCT ts_code FROM {table_name}
                    WHERE ah IS NULL OR al IS NULL OR nh IS NULL OR nl IS NULL
                    ORDER BY ts_code
                """)
                stocks = [row[0] for row in cur.fetchall()]
                
                if not stocks:
                    logger.info(f"  ✓ {table_name} 无需计算")
                    return 0
                
                logger.info(f"  {table_name}: 需计算 {len(stocks)} 只股票")
                
                total_updated = 0
                
                for ts_code in stocks:
                    # 获取该股票数据
                    cur.execute(f"""
                        SELECT id, high, low, close
                        FROM {table_name}
                        WHERE ts_code = %s
                        ORDER BY {date_field}
                    """, (ts_code,))
                    
                    rows = cur.fetchall()
                    if len(rows) < N:
                        continue
                    
                    # 计算指标
                    results = self._calculate_stock_4line(rows)
                    
                    if results:
                        execute_values(
                            cur,
                            f"""UPDATE {table_name} d SET
                                ah = v.ah, al = v.al, nh = v.nh, nl = v.nl
                            FROM (VALUES %s) AS v(id, ah, al, nh, nl)
                            WHERE d.id = v.id""",
                            results
                        )
                        conn.commit()
                        total_updated += len(results)
                
                logger.info(f"  ✓ {table_name}: 已更新 {total_updated:,} 条")
                return total_updated
                
        finally:
            conn.close()
    
    def _calculate_stock_4line(self, rows: List[Tuple]) -> List[Tuple]:
        """
        计算单只股票的 4Line 指标
        
        Args:
            rows: [(id, high, low, close), ...]
        
        Returns:
            [(id, ah, al, nh, nl), ...]
        """
        # 构建数据数组
        data = []
        for row in rows:
            data.append({
                'id': row[0],
                'high': float(row[1]) if row[1] else 0,
                'low': float(row[2]) if row[2] else 0,
                'close': float(row[3]) if row[3] else 0
            })
        
        results = []
        
        for i in range(len(data)):
            # PT = REF(HIGH,1) - REF(LOW,1)
            pt = data[i-1]['high'] - data[i-1]['low'] if i > 0 else 0
            
            # CDP = (HIGH + LOW + CLOSE) / 3
            cdp = (data[i]['high'] + data[i]['low'] + data[i]['close']) / 3
            
            # 取最近N个值计算平均
            start_idx = max(0, i - N + 1)
            
            cdp_pt_vals = []
            cdp_pt_minus_vals = []
            cdp2_low_vals = []
            cdp2_high_vals = []
            
            for j in range(start_idx, i + 1):
                pt_j = data[j-1]['high'] - data[j-1]['low'] if j > 0 else 0
                cdp_j = (data[j]['high'] + data[j]['low'] + data[j]['close']) / 3
                
                cdp_pt_vals.append(cdp_j + pt_j)
                cdp_pt_minus_vals.append(cdp_j - pt_j)
                cdp2_low_vals.append(2 * cdp_j - data[j]['low'])
                cdp2_high_vals.append(2 * cdp_j - data[j]['high'])
            
            ah = sum(cdp_pt_vals) / len(cdp_pt_vals)
            al = sum(cdp_pt_minus_vals) / len(cdp_pt_minus_vals)
            nh = sum(cdp2_low_vals) / len(cdp2_low_vals)
            nl = sum(cdp2_high_vals) / len(cdp2_high_vals)
            
            results.append((
                data[i]['id'],
                round(ah, 2),
                round(al, 2),
                round(nh, 2),
                round(nl, 2)
            ))
        
        return results
    
    def calculate_all(self, use_sql: bool = True):
        """计算所有表的 4Line 指标"""
        logger.info("=" * 60)
        logger.info("📊 计算 4Line 指标 (AH, AL, NH, NL)")
        logger.info("=" * 60)
        
        tables = [
            ('daily', 'trade_date'),
            ('stock_weekly', 'trade_date'),
            ('stock_monthly', 'trade_date')
        ]
        
        for table_name, date_field in tables:
            logger.info(f"\n处理 {table_name}...")
            
            if use_sql:
                updated = self.calculate_sql_method(table_name, date_field)
                # 如果 SQL 方法失败或没有更新，尝试 Python 方法
                if updated == 0:
                    updated = self.calculate_python_method(table_name, date_field)
            else:
                updated = self.calculate_python_method(table_name, date_field)
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ 4Line 指标计算完成!")
        logger.info("=" * 60)
        
        # 显示统计
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                for table, _ in tables:
                    cur.execute(f"SELECT COUNT(*) FROM {table} WHERE ah IS NOT NULL")
                    count = cur.fetchone()[0]
                    logger.info(f"  {table}: {count:,} 条已计算")
        finally:
            conn.close()


def main():
    parser = argparse.ArgumentParser(description='计算 4Line 指标')
    parser.add_argument('--table', help='指定表名（daily/stock_weekly/stock_monthly）')
    parser.add_argument('--python', action='store_true', help='使用 Python 计算方法')
    
    args = parser.parse_args()
    
    calculator = FourLineCalculator()
    
    if args.table:
        calculator.calculate_python_method(args.table) if args.python else calculator.calculate_sql_method(args.table)
    else:
        calculator.calculate_all(use_sql=not args.python)


if __name__ == '__main__':
    main()