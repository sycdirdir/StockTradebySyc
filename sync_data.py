"""
数据同步模块
从 Tushare 同步数据到 PostgreSQL
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import datetime, timedelta
from typing import List, Optional

import pandas as pd
import psycopg2
import tushare as ts
from psycopg2.extras import execute_values

from config import TUSHARE_TOKEN
from db_config import get_db_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)


class DataSyncer:
    """数据同步器"""
    
    def __init__(self):
        self.db_config = get_db_config()
        self.pro = ts.pro_api(TUSHARE_TOKEN)
    
    def _get_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(**self.db_config)
    
    def get_latest_date(self, table: str = 'daily') -> Optional[str]:
        """获取表中最新日期"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(f"SELECT MAX(trade_date) FROM {table}")
                result = cur.fetchone()
                return result[0] if result else None
        finally:
            conn.close()
    
    def get_stock_codes(self, list_status: str = 'L') -> List[str]:
        """获取股票代码列表"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT ts_code FROM stock_basic WHERE list_status = %s",
                    (list_status,)
                )
                return [row[0] for row in cur.fetchall()]
        finally:
            conn.close()
    
    def save_daily_data(self, df: pd.DataFrame, table_name: str = 'daily') -> int:
        """
        保存日线数据到数据库
        
        Args:
            df: Tushare 返回的数据框
            table_name: 目标表名
        
        Returns:
            保存的记录数
        """
        if df is None or df.empty:
            return 0
        
        df = df.fillna('')
        
        records = []
        for _, row in df.iterrows():
            records.append((
                row['ts_code'], row['trade_date'],
                row.get('open', ''), row.get('high', ''), row.get('low', ''),
                row.get('close', ''), row.get('pre_close', ''), row.get('change', ''),
                row.get('pct_chg', ''), row.get('vol', ''), row.get('amount', '')
            ))
        
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                execute_values(
                    cur,
                    f"""INSERT INTO {table_name} 
                        (ts_code, trade_date, open, high, low, close, 
                         pre_close, change, pct_chg, vol, amount) 
                       VALUES %s 
                       ON CONFLICT (ts_code, trade_date) DO UPDATE SET
                       open = EXCLUDED.open, high = EXCLUDED.high, low = EXCLUDED.low,
                       close = EXCLUDED.close, pre_close = EXCLUDED.pre_close,
                       change = EXCLUDED.change, pct_chg = EXCLUDED.pct_chg,
                       vol = EXCLUDED.vol, amount = EXCLUDED.amount, 
                       update_time = CURRENT_TIMESTAMP""",
                    records
                )
                conn.commit()
                return len(records)
        finally:
            conn.close()
    
    def sync_daily(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        batch_size: int = 100
    ) -> int:
        """
        同步日线数据
        
        Args:
            start_date: 开始日期，默认从数据库最新日期+1开始
            end_date: 结束日期，默认为今天
            batch_size: 每批处理的股票数量
        
        Returns:
            同步的记录总数
        """
        logger.info("=" * 60)
        logger.info("📥 同步日线数据")
        logger.info("=" * 60)
        
        # 获取最新日期
        latest = self.get_latest_date('daily')
        logger.info(f"当前最新日期: {latest}")
        
        # 计算目标日期
        if start_date is None:
            if latest:
                latest_dt = datetime.strptime(latest, '%Y%m%d')
                start_date = (latest_dt + timedelta(days=1)).strftime('%Y%m%d')
            else:
                start_date = '20240101'
        
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
        
        # 生成交易日列表
        target_dates = []
        curr = datetime.strptime(start_date, '%Y%m%d')
        end = datetime.strptime(end_date, '%Y%m%d')
        
        while curr <= end:
            if curr.weekday() < 5:  # 跳过周末
                target_dates.append(curr.strftime('%Y%m%d'))
            curr += timedelta(days=1)
        
        if not target_dates:
            logger.info("无需同步新数据")
            return 0
        
        logger.info(f"需要获取的日期: {target_dates}")
        
        # 获取股票列表
        stock_codes = self.get_stock_codes()
        logger.info(f"股票数量: {len(stock_codes)}")
        
        total_saved = 0
        
        for trade_date in target_dates:
            logger.info(f"\n📥 获取 {trade_date} 数据...")
            
            for i in range(0, len(stock_codes), batch_size):
                batch = stock_codes[i:i+batch_size]
                batch_str = ','.join(batch)
                
                try:
                    df = self.pro.daily(ts_code=batch_str, trade_date=trade_date)
                    if df is not None and not df.empty:
                        saved = self.save_daily_data(df)
                        total_saved += saved
                        logger.info(f"  批次 {i//batch_size + 1}: {saved} 条")
                    time.sleep(0.12)  # 限速
                except Exception as e:
                    logger.error(f"  错误: {e}")
                    time.sleep(1)
        
        logger.info(f"\n✅ 日线同步完成! 共新增 {total_saved} 条")
        return total_saved
    
    def sync_weekly_monthly(self) -> int:
        """同步周线和月线数据"""
        logger.info("\n📥 同步周线/月线数据...")
        
        latest = self.get_latest_date('daily')
        if not latest:
            logger.warning("没有日线数据，跳过周线/月线同步")
            return 0
        
        year = latest[:4]
        stock_codes = self.get_stock_codes()
        total_saved = 0
        
        # 同步周线
        logger.info("获取周线数据...")
        try:
            df_weekly = self.pro.weekly(
                ts_code=','.join(stock_codes[:500]),
                start_date=f"{year}0101",
                end_date=latest
            )
            if df_weekly is not None and not df_weekly.empty:
                saved = self.save_daily_data(df_weekly, 'stock_weekly')
                total_saved += saved
                logger.info(f"  周线: {saved} 条")
        except Exception as e:
            logger.error(f"周线同步错误: {e}")
        
        time.sleep(0.5)
        
        # 同步月线
        logger.info("获取月线数据...")
        try:
            df_monthly = self.pro.monthly(
                ts_code=','.join(stock_codes[:500]),
                start_date=f"{year}0101",
                end_date=latest
            )
            if df_monthly is not None and not df_monthly.empty:
                saved = self.save_daily_data(df_monthly, 'stock_monthly')
                total_saved += saved
                logger.info(f"  月线: {saved} 条")
        except Exception as e:
            logger.error(f"月线同步错误: {e}")
        
        logger.info(f"✅ 周线/月线同步完成! 共新增 {total_saved} 条")
        return total_saved


def main():
    parser = argparse.ArgumentParser(description='同步 Tushare 数据到 PostgreSQL')
    parser.add_argument('--start', help='开始日期 (YYYYMMDD)')
    parser.add_argument('--end', help='结束日期 (YYYYMMDD)')
    parser.add_argument('--daily', action='store_true', help='同步日线数据')
    parser.add_argument('--weekly-monthly', action='store_true', help='同步周线/月线数据')
    parser.add_argument('--all', action='store_true', help='同步所有数据')
    
    args = parser.parse_args()
    
    syncer = DataSyncer()
    
    if args.all or args.daily or (not args.daily and not args.weekly_monthly):
        syncer.sync_daily(args.start, args.end)
    
    if args.all or args.weekly_monthly:
        syncer.sync_weekly_monthly()
    
    # 最终统计
    latest = syncer.get_latest_date('daily')
    conn = syncer._get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM daily;")
            count = cur.fetchone()[0]
            logger.info(f"\n📊 最终状态: 最新日期 {latest}, 总记录 {count:,}")
    finally:
        conn.close()
    
    logger.info("\n✨ 全部完成!")


if __name__ == '__main__':
    main()
