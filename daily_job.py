"""
每日数据同步任务
整合数据同步 + 4Line指标计算

运行方式:
    python daily_job.py
    
或添加到 crontab:
    0 17 * * 1-5 cd /path/to/project && python daily_job.py >> /var/log/daily_job.log 2>&1
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime

from sync_data import DataSyncer
from calculate_4line import FourLineCalculator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/daily_job.log', encoding='utf-8'),
    ]
)
logger = logging.getLogger(__name__)


def is_trading_day(date: datetime = None) -> bool:
    """检查是否为交易日（排除周末和节假日）"""
    if date is None:
        date = datetime.now()
    
    # 周末
    if date.weekday() >= 5:
        return False
    
    # 主要节假日（简化版）
    month_day = (date.month, date.day)
    holidays = [
        (1, 1),   # 元旦
        (5, 1), (5, 2), (5, 3), (5, 4), (5, 5),  # 劳动节
        (10, 1), (10, 2), (10, 3), (10, 4), (10, 5), (10, 6), (10, 7),  # 国庆
    ]
    
    if month_day in holidays:
        return False
    
    return True


def main():
    logger.info("=" * 60)
    logger.info("🚀 每日数据同步任务")
    logger.info("=" * 60)
    
    today = datetime.now()
    logger.info(f"当前时间: {today.strftime('%Y-%m-%d %H:%M')}")
    
    # 检查交易日
    if not is_trading_day(today):
        logger.info("⚠️ 今天是非交易日，跳过同步")
        return
    
    logger.info("✓ 今天是交易日，开始同步...")
    
    try:
        # 1. 同步日线数据
        syncer = DataSyncer()
        syncer.sync_daily()
        
        # 2. 同步周线/月线数据
        syncer.sync_weekly_monthly()
        
        # 3. 计算 4Line 指标
        calculator = FourLineCalculator()
        calculator.calculate_all()
        
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
        
    except Exception as e:
        logger.error(f"❌ 任务失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    main()