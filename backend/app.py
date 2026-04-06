"""量化交易看盘系统 - Flask 后端 API

提供 K 线数据、股票列表、买卖信号、技术指标等 RESTful 接口。
对接 PostgreSQL 数据库（schema 与 StockTradebySyc 项目一致）。
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import psycopg2
import psycopg2.extras
from flask import Flask, jsonify, request
from flask_cors import CORS

from db_config import get_db_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# ---------------------------------------------------------------------------
# 数据库工具
# ---------------------------------------------------------------------------

_db_config = get_db_config()


def get_conn():
    """获取数据库连接"""
    return psycopg2.connect(**_db_config)


def query_df(sql: str, params=None) -> pd.DataFrame:
    """执行 SQL 并返回 DataFrame"""
    conn = get_conn()
    try:
        df = pd.read_sql_query(sql, conn, params=params)
        return df
    finally:
        conn.close()


def query_one(sql: str, params=None) -> dict | None:
    """执行 SQL 并返回单条记录"""
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def query_list(sql: str, params=None) -> list[dict]:
    """执行 SQL 并返回记录列表"""
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 技术指标计算
# ---------------------------------------------------------------------------

def calc_ma(series: pd.Series, period: int) -> list:
    """计算移动平均线"""
    result = series.rolling(window=period).mean()
    return [None if math.isnan(v) else round(float(v), 2) for v in result]


def calc_boll(series: pd.Series, period: int = 20, mult: float = 2.0) -> tuple:
    """计算布林带"""
    mid = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = mid + mult * std
    lower = mid - mult * std

    def _clean(s):
        return [None if math.isnan(v) else round(float(v), 2) for v in s]

    return _clean(upper), _clean(mid), _clean(lower)


def calc_kdj(df: pd.DataFrame, n: int = 9, m1: int = 3, m2: int = 3) -> tuple:
    """计算 KDJ 指标"""
    low_list = df['low'].rolling(window=n, min_periods=1).min()
    high_list = df['high'].rolling(window=n, min_periods=1).max()
    rsv = (df['close'] - low_list) / (high_list - low_list) * 100
    rsv = rsv.fillna(50)

    k = pd.Series([50.0] * len(df), index=df.index)
    d = pd.Series([50.0] * len(df), index=df.index)
    j = pd.Series([50.0] * len(df), index=df.index)

    for i in range(1, len(df)):
        k.iloc[i] = (2 / 3) * k.iloc[i - 1] + (1 / 3) * rsv.iloc[i]
        d.iloc[i] = (2 / 3) * d.iloc[i - 1] + (1 / 3) * k.iloc[i]
        j.iloc[i] = 3 * k.iloc[i] - 2 * d.iloc[i]

    def _clean(s):
        return [round(float(v), 2) for v in s]

    return _clean(k), _clean(d), _clean(j)


# ---------------------------------------------------------------------------
# 模拟买卖信号
# ---------------------------------------------------------------------------

def generate_mock_signals(dates: list, closes: list) -> dict:
    """根据简单策略生成模拟买卖信号"""
    buy_signals = []
    sell_signals = []
    hold_periods = []
    i = 5
    while i < len(dates) - 5:
        # 连续下跌后反弹买入
        if (closes[i] > closes[i - 1]
                and closes[i - 1] < closes[i - 2]
                and closes[i - 2] < closes[i - 3]):
            buy_signals.append({
                'date': dates[i],
                'price': closes[i],
            })
            hold_days = 5 + int((i * 7 + 3) % 15)
            sell_idx = min(i + hold_days, len(dates) - 1)
            sell_price = closes[sell_idx]
            pnl = round((sell_price - closes[i]) / closes[i] * 100, 2)
            is_profit = sell_price > closes[i]
            sell_signals.append({
                'date': dates[sell_idx],
                'price': sell_price,
                'pnl': pnl,
                'is_profit': is_profit,
            })
            hold_periods.append({
                'start': dates[i],
                'end': dates[sell_idx],
                'is_profit': is_profit,
                'pnl': pnl,
            })
            i = sell_idx + 1
            continue
        i += 1
    return {
        'buy_signals': buy_signals,
        'sell_signals': sell_signals,
        'hold_periods': hold_periods,
    }


# ---------------------------------------------------------------------------
# API 路由
# ---------------------------------------------------------------------------

@app.route('/api/health')
def health():
    """健康检查"""
    try:
        query_one("SELECT 1")
        db_status = 'ok'
    except Exception:
        db_status = 'error'
    return jsonify({
        'status': 'ok',
        'db': db_status,
        'time': datetime.now().isoformat(),
    })


@app.route('/api/stocks')
def list_stocks():
    """获取股票列表（分页 + 搜索）"""
    keyword = request.args.get('keyword', '').strip()
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 50, type=int)

    where = "WHERE list_status = 'L'"
    params = []
    if keyword:
        if keyword.isdigit():
            where += " AND (symbol LIKE %s OR ts_code LIKE %s)"
            params.extend([f'%{keyword}%', f'%{keyword}%'])
        else:
            where += " AND name LIKE %s"
            params.append(f'%{keyword}%')

    offset = (page - 1) * page_size
    count_sql = f"SELECT COUNT(*) FROM stock_basic {where}"
    total = query_one(count_sql, params or None)['count']

    sql = f"""
        SELECT ts_code, symbol, name, area, industry, market, list_date
        FROM stock_basic {where}
        ORDER BY ts_code
        LIMIT %s OFFSET %s
    """
    rows = query_list(sql, (*params, page_size, offset))

    return jsonify({
        'total': total,
        'page': page,
        'page_size': page_size,
        'data': rows,
    })


@app.route('/api/stocks/<ts_code>')
def stock_detail(ts_code: str):
    """获取单只股票基本信息"""
    sql = "SELECT * FROM stock_basic WHERE ts_code = %s"
    row = query_one(sql, (ts_code,))
    if not row:
        return jsonify({'error': 'Stock not found'}), 404
    return jsonify(row)


@app.route('/api/kline/<ts_code>')
def kline_data(ts_code: str):
    """获取 K 线数据

    Query params:
      - period: day | week | month | 1min | 5min | 30min | 60min (default: day)
      - start_date: YYYYMMDD
      - end_date: YYYYMMDD
      - indicators: ma,boll,kdj (comma separated, default: ma,boll)
    """
    period = request.args.get('period', 'day')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    indicators = request.args.get('indicators', 'ma,boll').split(',')

    table_map = {
        'day': 'daily',
        'week': 'stock_weekly',
        'month': 'stock_monthly',
        '1min': 'stock_1min',
        '5min': 'stock_5min',
        '30min': 'stock_30min',
        '60min': 'stock_60min',
    }
    table = table_map.get(period, 'daily')
    date_col = 'trade_time' if period in ('1min', '5min', '30min', '60min') else 'trade_date'

    where_conditions = ["ts_code = %s"]
    params: list = [ts_code]

    if start_date:
        where_conditions.append(f"{date_col} >= %s")
        params.append(start_date)
    if end_date:
        where_conditions.append(f"{date_col} <= %s")
        params.append(end_date)

    where_clause = " AND ".join(where_conditions)
    sql = f"""
        SELECT {date_col} as date, open, high, low, close, pre_close,
               change, pct_chg, vol, amount
        FROM {table}
        WHERE {where_clause}
        ORDER BY {date_col} ASC
    """
    df = query_df(sql, params)

    if df.empty:
        return jsonify({
            'ts_code': ts_code,
            'period': period,
            'dates': [],
            'kline': [],
            'signals': {'buy_signals': [], 'sell_signals': [], 'hold_periods': []},
            'indicators': {},
            'latest': None,
        })

    df['open'] = df['open'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['close'] = df['close'].astype(float)

    dates = df['date'].tolist()
    closes = df['close'].tolist()

    kline = []
    for _, row in df.iterrows():
        kline.append([
            float(row['open']),
            float(row['close']),
            float(row['low']),
            float(row['high']),
            float(row['vol']),
        ])

    ind_data = {}
    if 'ma' in indicators:
        ind_data['ma5'] = calc_ma(df['close'], 5)
        ind_data['ma10'] = calc_ma(df['close'], 10)
        ind_data['ma20'] = calc_ma(df['close'], 20)
    if 'boll' in indicators:
        upper, mid, lower = calc_boll(df['close'])
        ind_data['boll_upper'] = upper
        ind_data['boll_mid'] = mid
        ind_data['boll_lower'] = lower
    if 'kdj' in indicators:
        k_val, d_val, j_val = calc_kdj(df)
        ind_data['k'] = k_val
        ind_data['d'] = d_val
        ind_data['j'] = j_val

    signals = generate_mock_signals(dates, closes)

    last = df.iloc[-1]
    pre_close = float(last.get('pre_close', 0))
    close_price = float(last['close'])
    price_change = close_price - pre_close if pre_close else 0
    pct_chg_val = (price_change / pre_close * 100) if pre_close else 0

    latest = {
        'date': str(last['date']),
        'open': float(last['open']),
        'high': float(last['high']),
        'low': float(last['low']),
        'close': close_price,
        'pre_close': pre_close,
        'change': round(price_change, 2),
        'pct_chg': round(pct_chg_val, 2),
        'vol': float(last['vol']),
        'amount': float(last.get('amount', 0)),
    }

    return jsonify({
        'ts_code': ts_code,
        'period': period,
        'count': len(dates),
        'dates': dates,
        'kline': kline,
        'signals': signals,
        'indicators': ind_data,
        'latest': latest,
    })


@app.route('/api/strategies')
def list_strategies():
    """获取策略列表"""
    strategies = [
        {
            'id': 'bbikdj',
            'name': 'KDJ战法',
            'alias': 'BBIKDJSelector',
            'description': 'BBI导数上升趋势 + KDJ低位金叉 + MACD辅助确认',
        },
        {
            'id': 'superb1',
            'name': 'SuperB1战法',
            'alias': 'SuperB1Selector',
            'description': 'BBIKDJ增强版，叠加历史匹配、盘整区间、当日回调',
        },
        {
            'id': 'bbishortlong',
            'name': '补票战法',
            'alias': 'BBIShortLongSelector',
            'description': 'BBI趋势 + 短/长周期RSV组合 + DIF>0',
        },
        {
            'id': 'peakkdj',
            'name': '填坑战法',
            'alias': 'PeakKDJSelector',
            'description': '价格峰值识别 -> 回调后KDJ低位金叉',
        },
        {
            'id': 'ma60cross',
            'name': '上穿60放量战法',
            'alias': 'MA60CrossVolumeWaveSelector',
            'description': '价格上穿MA60 + 放量确认 + J值条件',
        },
        {
            'id': 'bigbullish',
            'name': '暴力K战法',
            'alias': 'BigBullishVolumeSelector',
            'description': '放量长阳线(涨幅>6%,上影线短,成交量放大)',
        },
    ]
    return jsonify(strategies)


@app.route('/api/stats')
def trade_stats():
    """获取交易统计概览"""
    ts_code = request.args.get('ts_code', '')
    period = request.args.get('period', 'day')

    if not ts_code:
        return jsonify({
            'total_return': 0, 'max_drawdown': 0, 'trade_count': 0,
            'win_rate': 0, 'profit_loss_ratio': 0, 'sharpe_ratio': 0,
            'hold_days': 0, 'avg_hold_days': 0,
        })

    table_map = {
        'day': 'daily',
        'week': 'stock_weekly',
        'month': 'stock_monthly',
    }
    table = table_map.get(period, 'daily')
    sql = f"""
        SELECT trade_date as date, close
        FROM {table}
        WHERE ts_code = %s
        ORDER BY trade_date ASC
    """
    df = query_df(sql, (ts_code,))

    if df.empty:
        return jsonify({
            'total_return': 0, 'max_drawdown': 0, 'trade_count': 0,
            'win_rate': 0, 'profit_loss_ratio': 0, 'sharpe_ratio': 0,
            'hold_days': 0, 'avg_hold_days': 0,
        })

    df['close'] = df['close'].astype(float)
    dates = df['date'].tolist()
    closes = df['close'].tolist()

    signals = generate_mock_signals(dates, closes)

    if not signals['buy_signals']:
        return jsonify({
            'total_return': 0, 'max_drawdown': 0, 'trade_count': 0,
            'win_rate': 0, 'profit_loss_ratio': 0, 'sharpe_ratio': 0,
            'hold_days': 0, 'avg_hold_days': 0,
        })

    pnls = [s['pnl'] for s in signals['sell_signals']]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    total_return = round(sum(pnls), 2)
    max_drawdown = round(min(pnls + [0]), 2)
    trade_count = len(pnls)
    win_rate = round(len(wins) / trade_count * 100, 1) if trade_count else 0

    avg_profit = sum(wins) / len(wins) if wins else 0
    avg_loss = abs(sum(losses) / len(losses)) if losses else 1
    profit_loss_ratio = round(avg_profit / avg_loss, 2) if avg_loss else 0

    if len(pnls) > 1:
        sharpe = round(np.mean(pnls) / (np.std(pnls) or 1), 2)
    else:
        sharpe = 0

    avg_hold_days = 10.6  # 简化

    return jsonify({
        'total_return': total_return,
        'max_drawdown': max_drawdown,
        'trade_count': trade_count,
        'win_rate': win_rate,
        'profit_loss_ratio': profit_loss_ratio,
        'sharpe_ratio': sharpe,
        'hold_days': 0,
        'avg_hold_days': avg_hold_days,
    })


if __name__ == '__main__':
    logger.info('QuantView API Server starting on http://localhost:5001')
    app.run(host='0.0.0.0', port=5001, debug=True)
