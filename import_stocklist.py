#!/usr/bin/env python3
"""
导入 stocklist.csv 到 PostgreSQL TargetList 表
"""
import csv
import logging
import sys
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

from db_config import get_db_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def import_stocklist(csv_path: str = 'stocklist.csv'):
    """导入 stocklist.csv 到 TargetList 表"""
    
    # 读取 CSV 文件
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
                True  # is_active
            ))
    
    if not records:
        logger.warning("CSV 文件为空")
        return 0
    
    logger.info(f"读取到 {len(records)} 条记录")
    
    # 连接数据库
    db_config = get_db_config()
    conn = psycopg2.connect(**db_config)
    
    try:
        with conn.cursor() as cur:
            # 清空现有数据
            cur.execute("TRUNCATE TABLE TargetList RESTART IDENTITY")
            
            # 批量插入
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
            
            logger.info(f"成功导入 {len(records)} 条记录到 TargetList 表")
            
            # 显示统计
            cur.execute("SELECT COUNT(*) FROM TargetList WHERE is_active = TRUE")
            active_count = cur.fetchone()[0]
            logger.info(f"其中启用状态: {active_count} 条")
            
            return len(records)
            
    except Exception as e:
        logger.error(f"导入失败: {e}")
        conn.rollback()
        return 0
    finally:
        conn.close()


if __name__ == '__main__':
    csv_path = sys.argv[1] if len(sys.argv) > 1 else 'stocklist.csv'
    import_stocklist(csv_path)
