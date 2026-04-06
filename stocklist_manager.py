#!/usr/bin/env python3
"""
TargetList 股票列表管理模块
支持从 CSV 或 PostgreSQL 读取股票列表
"""
from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import List, Optional

from db_config import get_db_config

try:
    import psycopg2
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

logger = logging.getLogger(__name__)


class StockListManager:
    """股票列表管理器"""
    
    def __init__(self, use_db: bool = True):
        """
        初始化管理器
        
        Args:
            use_db: 是否优先使用数据库
        """
        self.use_db = use_db and POSTGRES_AVAILABLE
        if use_db and not POSTGRES_AVAILABLE:
            logger.warning("PostgreSQL 不可用，将使用 CSV 文件")
    
    def get_stock_list(
        self,
        use_active_only: bool = True,
        csv_path: str = 'stocklist.csv'
    ) -> List[str]:
        """
        获取股票代码列表
        
        Args:
            use_active_only: 是否只获取启用的股票（数据库模式）
            csv_path: CSV 文件路径（CSV 模式）
        
        Returns:
            股票代码列表（ts_code 格式）
        """
        if self.use_db:
            try:
                return self._get_from_db(use_active_only)
            except Exception as e:
                logger.error(f"从数据库读取失败: {e}，回退到 CSV")
                return self._get_from_csv(csv_path)
        else:
            return self._get_from_csv(csv_path)
    
    def _get_from_db(self, use_active_only: bool = True) -> List[str]:
        """从数据库获取"""
        db_config = get_db_config()
        conn = psycopg2.connect(**db_config)
        
        try:
            with conn.cursor() as cur:
                if use_active_only:
                    cur.execute("SELECT ts_code FROM TargetList WHERE is_active = TRUE ORDER BY ts_code")
                else:
                    cur.execute("SELECT ts_code FROM TargetList ORDER BY ts_code")
                
                return [row[0] for row in cur.fetchall()]
        finally:
            conn.close()
    
    def _get_from_csv(self, csv_path: str = 'stocklist.csv') -> List[str]:
        """从 CSV 文件获取"""
        csv_file = Path(csv_path)
        if not csv_file.exists():
            logger.error(f"CSV 文件不存在: {csv_path}")
            return []
        
        codes = []
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                codes.append(row.get('ts_code', ''))
        
        return [c for c in codes if c]
    
    def import_from_csv(self, csv_path: str = 'stocklist.csv') -> int:
        """
        从 CSV 导入到数据库
        
        Args:
            csv_path: CSV 文件路径
        
        Returns:
            导入的记录数
        """
        if not POSTGRES_AVAILABLE:
            raise ImportError("PostgreSQL 不可用")
        
        csv_file = Path(csv_path)
        if not csv_file.exists():
            logger.error(f"CSV 文件不存在: {csv_path}")
            return 0
        
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
            logger.warning("CSV 文件为空")
            return 0
        
        db_config = get_db_config()
        conn = psycopg2.connect(**db_config)
        
        try:
            with conn.cursor() as cur:
                # 清空现有数据
                cur.execute("TRUNCATE TABLE TargetList RESTART IDENTITY")
                
                # 批量插入
                from psycopg2.extras import execute_values
                execute_values(
                    cur,
                    """INSERT INTO TargetList 
                        (ts_code, symbol, name, area, industry, is_active)
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
                
                logger.info(f"成功导入 {len(records)} 条记录")
                return len(records)
                
        finally:
            conn.close()
    
    def set_stock_status(self, ts_code: str, is_active: bool) -> bool:
        """
        设置股票启用状态
        
        Args:
            ts_code: 股票代码（带后缀）
            is_active: 是否启用
        
        Returns:
            是否成功
        """
        if not POSTGRES_AVAILABLE:
            raise ImportError("PostgreSQL 不可用")
        
        db_config = get_db_config()
        conn = psycopg2.connect(**db_config)
        
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE TargetList 
                       SET is_active = %s, updated_at = CURRENT_TIMESTAMP 
                       WHERE ts_code = %s""",
                    (is_active, ts_code)
                )
                conn.commit()
                return cur.rowcount > 0
        finally:
            conn.close()
    
    def get_stock_info(self, ts_code: str) -> Optional[dict]:
        """
        获取股票详细信息
        
        Args:
            ts_code: 股票代码（带后缀）
        
        Returns:
            股票信息字典
        """
        if not POSTGRES_AVAILABLE:
            return None
        
        db_config = get_db_config()
        conn = psycopg2.connect(**db_config)
        
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT ts_code, symbol, name, area, industry, is_active 
                       FROM TargetList WHERE ts_code = %s""",
                    (ts_code,)
                )
                row = cur.fetchone()
                if row:
                    return {
                        'ts_code': row[0],
                        'symbol': row[1],
                        'name': row[2],
                        'area': row[3],
                        'industry': row[4],
                        'is_active': row[5]
                    }
                return None
        finally:
            conn.close()


# 便捷函数
def get_stock_list(use_db: bool = True, csv_path: str = 'stocklist.csv') -> List[str]:
    """
    获取股票代码列表的便捷函数
    
    Args:
        use_db: 是否优先使用数据库
        csv_path: CSV 文件路径
    
    Returns:
        股票代码列表
    """
    manager = StockListManager(use_db=use_db)
    return manager.get_stock_list(csv_path=csv_path)


if __name__ == '__main__':
    # 测试
    logging.basicConfig(level=logging.INFO)
    
    manager = StockListManager(use_db=True)
    
    # 获取股票列表
    stocks = manager.get_stock_list()
    print(f"获取到 {len(stocks)} 只股票")
    print(f"前10只: {stocks[:10]}")
