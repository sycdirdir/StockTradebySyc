"""
PostgreSQL 数据加载器
为选股程序提供从 PostgreSQL 读取数据的功能
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor

from db_config import get_db_config

logger = logging.getLogger(__name__)


class PostgresLoader:
    """PostgreSQL 数据加载器"""
    
    def __init__(self):
        self.db_config = get_db_config()
    
    def _get_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(**self.db_config)
    
    def load_stock_data(
        self,
        ts_codes: List[str],
        start_date: str,
        end_date: Optional[str] = None,
        table: str = 'daily'
    ) -> Dict[str, pd.DataFrame]:
        """
        从 PostgreSQL 加载股票数据
        
        Args:
            ts_codes: 股票代码列表（如 ['000001.SZ', '000002.SZ']）
            start_date: 开始日期（格式：YYYYMMDD）
            end_date: 结束日期，默认为今天
            table: 表名（daily/stock_weekly/stock_monthly）
        
        Returns:
            股票代码 -> DataFrame 的字典
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
        
        conn = self._get_connection()
        
        # 构建查询
        codes_str = ','.join([f"'{code}'" for code in ts_codes])
        
        query = f"""
        SELECT 
            ts_code,
            trade_date as date,
            open,
            high,
            low,
            close,
            vol as volume,
            amount,
            ah, al, nh, nl
        FROM {table}
        WHERE ts_code IN ({codes_str})
        AND trade_date >= %s AND trade_date <= %s
        ORDER BY ts_code, trade_date
        """
        
        try:
            # 读取数据
            df = pd.read_sql(query, conn, params=(start_date, end_date))
            
            # 转换日期格式
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
            
            # 按股票代码分组
            result = {}
            for ts_code in ts_codes:
                stock_df = df[df['ts_code'] == ts_code].copy()
                if not stock_df.empty:
                    # 移除 ts_code 列，与 CSV 格式保持一致
                    stock_df = stock_df.drop(columns=['ts_code'])
                    # 提取纯数字代码作为键
                    code = ts_code.split('.')[0]
                    result[code] = stock_df
            
            logger.info(f"从 {table} 加载了 {len(result)} 只股票的数据")
            return result
            
        finally:
            conn.close()
    
    def load_all_stocks(
        self,
        start_date: str,
        end_date: Optional[str] = None,
        table: str = 'daily',
        limit: Optional[int] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        加载所有股票数据
        
        Args:
            start_date: 开始日期（格式：YYYYMMDD）
            end_date: 结束日期
            table: 表名
            limit: 限制股票数量（用于测试）
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
        
        conn = self._get_connection()
        
        limit_clause = f"LIMIT {limit}" if limit else ""
        
        query = f"""
        SELECT DISTINCT ts_code FROM {table}
        WHERE trade_date >= %s
        {limit_clause}
        """
        
        try:
            codes_df = pd.read_sql(query, conn, params=(start_date,))
            ts_codes = codes_df['ts_code'].tolist()
            
            logger.info(f"发现 {len(ts_codes)} 只股票")
            
            return self.load_stock_data(ts_codes, start_date, end_date, table)
            
        finally:
            conn.close()
    
    def get_stock_list(self, list_status: str = 'L') -> List[str]:
        """
        获取股票列表
        
        Args:
            list_status: 'L' 上市, 'D' 退市, 'P' 暂停上市
        
        Returns:
            股票代码列表
        """
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
    
    def get_latest_date(self, table: str = 'daily') -> str:
        """获取最新数据日期"""
        conn = self._get_connection()
        
        try:
            with conn.cursor() as cur:
                cur.execute(f"SELECT MAX(trade_date) FROM {table}")
                result = cur.fetchone()
                return result[0] if result else None
        finally:
            conn.close()


def load_data_from_postgres(
    data_dir: Optional[str] = None,
    codes: Optional[List[str]] = None,
    start_date: str = '20240101',
    end_date: Optional[str] = None,
    table: str = 'daily',
    **kwargs
) -> Dict[str, pd.DataFrame]:
    """
    从 PostgreSQL 加载数据的便捷函数
    兼容 select_stock.py 的接口
    """
    loader = PostgresLoader()
    
    if codes:
        # 转换代码格式（添加后缀）
        ts_codes = []
        for code in codes:
            if '.' not in code:
                # 根据代码规则添加后缀
                if code.startswith('6'):
                    ts_codes.append(f"{code}.SH")
                else:
                    ts_codes.append(f"{code}.SZ")
            else:
                ts_codes.append(code)
        return loader.load_stock_data(ts_codes, start_date, end_date, table)
    else:
        return loader.load_all_stocks(start_date, end_date, table)


if __name__ == '__main__':
    # 测试加载
    logging.basicConfig(level=logging.INFO)
    
    loader = PostgresLoader()
    
    # 测试加载单只股票
    print("测试加载单只股票...")
    data = loader.load_stock_data(['000001.SZ'], '20240101', '20240331')
    for code, df in data.items():
        print(f"\n股票 {code}:")
        print(df.head())
        print(f"数据条数: {len(df)}")
