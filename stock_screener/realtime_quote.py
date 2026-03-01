#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时行情查询模块

通过 data_provider 批量获取 A 股实时行情数据（当前价/涨跌幅/市盈率/市净率/成交量等）。
内置简单缓存，避免短时间内重复请求。
"""

import time
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from data_provider import DataFetcherManager
from data_provider.base import normalize_stock_code

logger = logging.getLogger(__name__)

_cache: Dict[str, Any] = {}
_cache_ts: float = 0
_CACHE_TTL = 3


def _sf(v: Any, d: float = 0.0) -> float:
    """安全转 float，NaN 或异常时返回默认值"""
    try:
        x = float(v)
        return d if (x != x) else x
    except (TypeError, ValueError):
        return d


def _quote_to_dict(quote: Any, symbol: str) -> Dict[str, Any]:
    """将 UnifiedRealtimeQuote 转为模块对外 dict 结构"""
    if quote is None:
        return _empty_quote(symbol)
    return {
        'symbol': symbol,
        'name': getattr(quote, 'name', '') or '',
        'current_price': _sf(getattr(quote, 'price', None)),
        'change_pct': _sf(getattr(quote, 'change_pct', None)),
        'change_amount': _sf(getattr(quote, 'change_amount', None)),
        'volume': int(_sf(getattr(quote, 'volume', None))) if getattr(quote, 'volume', None) is not None else 0,
        'turnover': _sf(getattr(quote, 'amount', None)),
        'amplitude': _sf(getattr(quote, 'amplitude', None)),
        'high': _sf(getattr(quote, 'high', None)),
        'low': _sf(getattr(quote, 'low', None)),
        'open': _sf(getattr(quote, 'open_price', None)),
        'prev_close': _sf(getattr(quote, 'pre_close', None)),
        'volume_ratio': _sf(getattr(quote, 'volume_ratio', None)),
        'turnover_rate': _sf(getattr(quote, 'turnover_rate', None)),
        'pe_ratio': _sf(getattr(quote, 'pe_ratio', None)),
        'pb_ratio': _sf(getattr(quote, 'pb_ratio', None)),
        'total_market_cap': _sf(getattr(quote, 'total_mv', None)),
        'circulating_market_cap': _sf(getattr(quote, 'circ_mv', None)),
        'speed_60d': _sf(getattr(quote, 'change_60d', None)),
        'year_to_date': 0.0,
        'updated_at': datetime.now().strftime('%H:%M:%S'),
    }


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
        manager = DataFetcherManager()
        if symbols:
            manager.prefetch_realtime_quotes([normalize_stock_code(s) for s in symbols])
        result: Dict[str, Dict[str, Any]] = {}
        for s in symbols:
            code = normalize_stock_code(s)
            quote = manager.get_realtime_quote(code)
            result[s] = _quote_to_dict(quote, s)
        _cache = result
        _cache_ts = time.time()
        logger.info(f"实时行情: 已获取 {len(result)} 只")
        return result
    except Exception as e:
        logger.warning(f"获取实时行情失败: {e}")
        return {s: _cache.get(s, _empty_quote(s)) for s in symbols}


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
