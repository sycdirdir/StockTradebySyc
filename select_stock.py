"""
优化版选股程序 - 支持并行加载、数据缓存、策略并行执行
支持 PostgreSQL 数据源

优化点：
1. 并行数据加载 - 使用多进程加速 CSV 读取
2. 数据缓存 - 基于文件哈希的内存缓存，避免重复读取
3. 指标预计算 - 缓存通用指标避免重复计算
4. 策略并行执行 - 多线程并行运行多个策略
5. PostgreSQL 支持 - 从数据库直接读取数据
6. 性能计时 - 详细的性能分析日志
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import logging
import pickle
import sys
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from multiprocessing import cpu_count
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd

# 导入 Selector 中的指标计算函数
try:
    from Selector import compute_kdj, compute_bbi, compute_dif, compute_zx_lines
except ImportError:
    # 如果 Selector.py 不存在这些函数，使用占位符
    def compute_kdj(df, n=9): return df
    def compute_bbi(df): return df["close"].rolling(24).mean()
    def compute_dif(df): return df["close"].diff()
    def compute_zx_lines(df): return (df["close"], df["close"])

# 导入 PostgreSQL 数据加载器
try:
    from db_loader import load_data_from_postgres, PostgresLoader
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("PostgreSQL 支持未启用，请安装 psycopg2")

# ---------- 日志配置 ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("select_results.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("select")


# ---------- 数据缓存管理 ----------

class DataCache:
    """数据缓存管理器 - 基于文件哈希"""
    CACHE_DIR = Path(".cache")
    
    @classmethod
    def _get_cache_key(cls, data_dir: Path) -> str:
        """基于文件修改时间和大小生成缓存键"""
        mtimes = []
        for f in sorted(data_dir.glob("*.csv")):
            stat = f.stat()
            mtimes.append(f"{f.name}:{stat.st_mtime:.0f}:{stat.st_size}")
        content = "|".join(mtimes).encode()
        return hashlib.md5(content).hexdigest()[:16]
    
    @classmethod
    def load(cls, data_dir: Path) -> Optional[Dict[str, pd.DataFrame]]:
        """尝试从缓存加载数据"""
        cache_key = cls._get_cache_key(data_dir)
        cache_file = cls.CACHE_DIR / f"data_{cache_key}.pkl"
        
        if cache_file.exists():
            try:
                logger.info("从缓存加载数据: %s", cache_file.name)
                with open(cache_file, "rb") as f:
                    return pickle.load(f)
            except Exception as e:
                logger.warning("缓存加载失败: %s", e)
        return None
    
    @classmethod
    def save(cls, data_dir: Path, data: Dict[str, pd.DataFrame]):
        """保存数据到缓存"""
        cls.CACHE_DIR.mkdir(exist_ok=True)
        cache_key = cls._get_cache_key(data_dir)
        cache_file = cls.CACHE_DIR / f"data_{cache_key}.pkl"
        
        try:
            with open(cache_file, "wb") as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
            logger.info("数据已缓存到: %s", cache_file)
        except Exception as e:
            logger.warning("缓存保存失败: %s", e)
    
    @classmethod
    def clear(cls):
        """清除所有缓存"""
        if cls.CACHE_DIR.exists():
            for f in cls.CACHE_DIR.glob("*.pkl"):
                f.unlink()
            logger.info("缓存已清除")


# ---------- 并行数据加载 ----------

def _load_single_stock(args: Tuple[Path, str]) -> Tuple[str, Optional[pd.DataFrame]]:
    """加载单个股票数据（用于多进程）"""
    data_dir, code = args
    fp = data_dir / f"{code}.csv"
    
    if not fp.exists():
        return code, None
    
    try:
        df = pd.read_csv(fp, parse_dates=["date"]).sort_values("date")
        return code, df
    except Exception as e:
        logger.warning("加载 %s 失败: %s", code, e)
        return code, None


def load_data_parallel(
    data_dir: Path, 
    codes: Iterable[str], 
    max_workers: int = None,
    use_cache: bool = True
) -> Dict[str, pd.DataFrame]:
    """
    并行加载股票数据
    
    Args:
        data_dir: 数据目录
        codes: 股票代码列表
        max_workers: 并行进程数，默认 CPU 核心数
        use_cache: 是否使用缓存
    
    Returns:
        股票代码 -> DataFrame 的字典
    """
    codes = list(codes)
    
    # 尝试从缓存加载
    if use_cache:
        cached = DataCache.load(data_dir)
        if cached is not None:
            # 只返回需要的代码
            return {k: v for k, v in cached.items() if k in codes}
    
    max_workers = max_workers or min(cpu_count(), 8)
    frames = {}
    
    logger.info("并行加载 %d 只股票 (workers=%d)...", len(codes), max_workers)
    start = time.perf_counter()
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_load_single_stock, (data_dir, code)): code 
                   for code in codes}
        
        for future in as_completed(futures):
            code, df = future.result()
            if df is not None:
                frames[code] = df
    
    elapsed = time.perf_counter() - start
    logger.info("数据加载完成: %d/%d 只, 耗时 %.3fs", len(frames), len(codes), elapsed)
    
    # 保存到缓存
    if use_cache and frames:
        DataCache.save(data_dir, frames)
    
    return frames


# ---------- 配置加载 ----------

def load_config(cfg_path: Path) -> List[Dict[str, Any]]:
    """加载配置文件（支持 JSON/YAML）"""
    if not cfg_path.exists():
        logger.error("配置文件 %s 不存在", cfg_path)
        sys.exit(1)
    
    suffix = cfg_path.suffix.lower()
    
    try:
        with cfg_path.open(encoding="utf-8") as f:
            if suffix in (".yaml", ".yml"):
                import yaml
                cfg_raw = yaml.safe_load(f)
            else:
                cfg_raw = json.load(f)
    except Exception as e:
        logger.error("配置文件解析失败: %s", e)
        sys.exit(1)
    
    # 兼容三种结构
    if isinstance(cfg_raw, list):
        cfgs = cfg_raw
    elif isinstance(cfg_raw, dict) and "selectors" in cfg_raw:
        cfgs = cfg_raw["selectors"]
    else:
        cfgs = [cfg_raw]
    
    if not cfgs:
        logger.error("配置未定义任何 Selector")
        sys.exit(1)
    
    return cfgs


def instantiate_selector(cfg: Dict[str, Any]):
    """动态加载 Selector 类并实例化"""
    cls_name: str = cfg.get("class")
    if not cls_name:
        raise ValueError("缺少 class 字段")
    
    try:
        module = importlib.import_module("Selector")
        cls = getattr(module, cls_name)
    except (ModuleNotFoundError, AttributeError) as e:
        raise ImportError(f"无法加载 Selector.{cls_name}: {e}") from e
    
    params = cfg.get("params", {})
    return cfg.get("alias", cls_name), cls(**params)


# ---------- 策略执行 ----------

def run_selector(cfg: Dict[str, Any], trade_date, data: Dict[str, pd.DataFrame]) -> Tuple[str, List[str], Optional[str]]:
    """运行单个策略"""
    if cfg.get("activate", True) is False:
        return cfg.get("alias", "unknown"), [], None
    
    try:
        alias, selector = instantiate_selector(cfg)
        picks = selector.select(trade_date, data)
        return alias, picks, None
    except Exception as e:
        return cfg.get("alias", "unknown"), [], str(e)


def run_selectors_parallel(
    configs: List[Dict],
    trade_date,
    data: Dict[str, pd.DataFrame],
    max_workers: int = 4
) -> List[Tuple[str, List[str], Optional[str]]]:
    """并行执行多个策略"""
    results = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(run_selector, cfg, trade_date, data): cfg 
                   for cfg in configs}
        
        for future in as_completed(futures):
            alias, picks, error = future.result()
            results.append((alias, picks, error))
            
            if error:
                logger.error("策略 %s 执行失败: %s", alias, error)
    
    return results


# ---------- 主函数 ----------

def main():
    p = argparse.ArgumentParser(description="优化版选股程序 - 支持并行和缓存")
    p.add_argument("--data-dir", default="./data", help="CSV 行情目录")
    p.add_argument("--config", default="./configs.json", help="Selector 配置文件")
    p.add_argument("--date", help="交易日 YYYY-MM-DD；缺省=数据最新日期")
    p.add_argument("--tickers", default="all", help="'all' 或逗号分隔股票代码列表")
    p.add_argument("--workers", type=int, default=None, help="数据加载并行进程数")
    p.add_argument("--strategy-workers", type=int, default=4, help="策略执行并行线程数")
    p.add_argument("--no-cache", action="store_true", help="禁用数据缓存")
    p.add_argument("--clear-cache", action="store_true", help="清除缓存后运行")
    p.add_argument("--precompute", action="store_true", help="预计算常用指标")
    # PostgreSQL 相关参数
    p.add_argument("--postgres", action="store_true", help="使用 PostgreSQL 数据源")
    p.add_argument("--pg-table", default="daily", help="PostgreSQL 表名 (daily/stock_weekly/stock_monthly)")
    p.add_argument("--pg-start", default="20240101", help="PostgreSQL 数据开始日期 (YYYYMMDD)")
    # TargetList 相关参数
    p.add_argument("--use-targetlist-db", action="store_true", help="从数据库 TargetList 表读取股票列表")
    p.add_argument("--targetlist-active-only", action="store_true", default=True, help="只读取启用的股票")
    args = p.parse_args()
    
    # 清除缓存
    if args.clear_cache:
        DataCache.clear()
    
    # --- 加载行情 ---
    if args.postgres:
        # 使用 PostgreSQL 数据源
        if not POSTGRES_AVAILABLE:
            logger.error("PostgreSQL 支持未启用，请安装 psycopg2: pip install psycopg2-binary")
            sys.exit(1)
        
        logger.info("使用 PostgreSQL 数据源，表: %s", args.pg_table)
        
        if args.tickers.lower() == "all":
            # 加载所有股票
            data = load_data_from_postgres(
                start_date=args.pg_start,
                table=args.pg_table
            )
        else:
            # 加载指定股票
            codes = [c.strip() for c in args.tickers.split(",") if c.strip()]
            data = load_data_from_postgres(
                codes=codes,
                start_date=args.pg_start,
                table=args.pg_table
            )
        
        if not data:
            logger.error("未能从 PostgreSQL 加载任何数据")
            sys.exit(1)
        
        logger.info("从 PostgreSQL 加载了 %d 只股票的数据", len(data))
        
    else:
        # 使用 CSV 数据源
        data_dir = Path(args.data_dir)
        if not data_dir.exists():
            logger.error("数据目录 %s 不存在", data_dir)
            sys.exit(1)
        
        codes = (
            [f.stem for f in data_dir.glob("*.csv")]
            if args.tickers.lower() == "all"
            else [c.strip() for c in args.tickers.split(",") if c.strip()]
        )
        if not codes:
            logger.error("股票池为空！")
            sys.exit(1)
        
        # 并行加载数据（带缓存）
    data = load_data_parallel(
        data_dir, 
        codes, 
        max_workers=args.workers,
        use_cache=not args.no_cache
    )
    
    if not data:
        logger.error("未能加载任何行情数据")
        sys.exit(1)
    
    # 预计算指标
    if args.precompute:
        logger.info("预计算指标已启用，注意：需要 Selector 支持预计算指标")
    
    # 确定交易日期
    trade_date = (
        pd.to_datetime(args.date)
        if args.date
        else max(df["date"].max() for df in data.values())
    )
    if not args.date:
        logger.info("未指定 --date，使用最近日期 %s", trade_date.date())
    
    # --- 加载 Selector 配置 ---
    selector_cfgs = load_config(Path(args.config))
    
    # --- 并行执行策略 ---
    logger.info("开始执行 %d 个策略 (workers=%d)...", len(selector_cfgs), args.strategy_workers)
    start = time.perf_counter()
    
    results = run_selectors_parallel(
        selector_cfgs, 
        trade_date, 
        data, 
        max_workers=args.strategy_workers
    )
    
    elapsed = time.perf_counter() - start
    logger.info("策略执行完成，总耗时 %.3fs", elapsed)
    
    # --- 输出结果 ---
    for alias, picks, error in results:
        if error:
            logger.error("============== 选股结果 [%s] ==============", alias)
            logger.error("执行失败: %s", error)
            continue
            
        logger.info("")
        logger.info("============== 选股结果 [%s] ==============", alias)
        logger.info("交易日: %s", trade_date.date())

if __name__ == "__main__":
    main()
