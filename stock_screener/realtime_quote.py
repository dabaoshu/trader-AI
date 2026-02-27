#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时行情查询模块

通过 akshare 批量获取 A 股实时行情数据（当前价/涨跌幅/市盈率/市净率/成交量等）。
内置简单缓存，避免短时间内重复请求。
"""

import time
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

_cache: Dict[str, Any] = {}
_cache_ts: float = 0
_CACHE_TTL = 3


def fetch_realtime_quotes(symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    批量获取实时行情

    @param symbols  股票代码列表，如 ['sh.600036', 'sz.000001']
    @returns { symbol: { current_price, change_pct, pe_ratio, pb_ratio, ... } }
    """
    global _cache, _cache_ts
    now = time.time()
    if now - _cache_ts < _CACHE_TTL and _cache:
        hit = {s: _cache[s] for s in symbols if s in _cache}
        if len(hit) == len(symbols):
            return hit

    try:
        all_quotes = _fetch_a_stock_spot()
        _cache = all_quotes
        _cache_ts = time.time()
    except Exception as e:
        logger.warning(f"获取实时行情失败: {e}")
        all_quotes = _cache

    return {s: all_quotes.get(s, _empty_quote(s)) for s in symbols}


def _fetch_a_stock_spot() -> Dict[str, Dict[str, Any]]:
    """从 akshare 获取全市场 A 股实时行情快照"""
    import akshare as ak

    df = ak.stock_zh_a_spot_em()
    if df is None or df.empty:
        return {}

    result: Dict[str, Dict[str, Any]] = {}
    for _, row in df.iterrows():
        code = str(row.get('代码', ''))
        if not code:
            continue

        if code.startswith('6') or code.startswith('9'):
            full_code = f"sh.{code}"
        else:
            full_code = f"sz.{code}"

        def sf(v, d=0.0):
            try:
                v = float(v)
                if v != v:
                    return d
                return v
            except Exception:
                return d

        result[full_code] = {
            'symbol': full_code,
            'name': str(row.get('名称', '')),
            'current_price': sf(row.get('最新价')),
            'change_pct': sf(row.get('涨跌幅')),
            'change_amount': sf(row.get('涨跌额')),
            'volume': sf(row.get('成交量')),
            'turnover': sf(row.get('成交额')),
            'amplitude': sf(row.get('振幅')),
            'high': sf(row.get('最高')),
            'low': sf(row.get('最低')),
            'open': sf(row.get('今开')),
            'prev_close': sf(row.get('昨收')),
            'volume_ratio': sf(row.get('量比')),
            'turnover_rate': sf(row.get('换手率')),
            'pe_ratio': sf(row.get('市盈率-动态')),
            'pb_ratio': sf(row.get('市净率')),
            'total_market_cap': sf(row.get('总市值')),
            'circulating_market_cap': sf(row.get('流通市值')),
            'speed_60d': sf(row.get('60日涨跌幅')),
            'year_to_date': sf(row.get('年初至今涨跌幅')),
            'updated_at': datetime.now().strftime('%H:%M:%S'),
        }

    logger.info(f"实时行情快照: {len(result)} 只股票")
    return result


def _empty_quote(symbol: str) -> Dict[str, Any]:
    return {
        'symbol': symbol,
        'name': '',
        'current_price': 0,
        'change_pct': 0,
        'change_amount': 0,
        'pe_ratio': 0,
        'pb_ratio': 0,
        'volume': 0,
        'turnover': 0,
        'turnover_rate': 0,
        'volume_ratio': 0,
        'high': 0,
        'low': 0,
        'open': 0,
        'prev_close': 0,
        'total_market_cap': 0,
        'circulating_market_cap': 0,
        'updated_at': '',
    }
