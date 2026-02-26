#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同花顺风格条件选股引擎

支持多维度筛选条件：
- 基本面：价格区间、市值范围
- 技术面：RSI、均线排列、MACD、成交量倍率
- 竞价数据：竞价涨幅、竞价量比
- 市场分类：按板块、按市场筛选
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


class StockScreener:
    """同花顺风格条件选股引擎"""

    # 预置条件模板
    PRESET_TEMPLATES = {
        'low_price_breakout': {
            'name': '低价突破股',
            'description': '价格10元以下、竞价高开、技术面良好的低价弹性股',
            'conditions': {
                'price_min': 2.0,
                'price_max': 10.0,
                'auction_ratio_min': 0.5,
                'tech_score_min': 0.55,
                'confidence_levels': ['very_high', 'high'],
            }
        },
        'strong_momentum': {
            'name': '强势动量股',
            'description': '综合评分≥0.8、强烈推荐、竞价高开的强势标的',
            'conditions': {
                'total_score_min': 0.8,
                'auction_ratio_min': 1.0,
                'gap_types': ['gap_up'],
                'confidence_levels': ['very_high'],
            }
        },
        'value_pick': {
            'name': '价值精选',
            'description': '中等价位、技术面稳健、综合评分≥0.7的价值标的',
            'conditions': {
                'price_min': 10.0,
                'price_max': 100.0,
                'total_score_min': 0.7,
                'tech_score_min': 0.6,
            }
        },
        'oversold_rebound': {
            'name': '超跌反弹',
            'description': 'RSI偏低且有企稳迹象、竞价平开或微涨的超跌反弹机会',
            'conditions': {
                'rsi_max': 55.0,
                'auction_ratio_min': -0.5,
                'auction_ratio_max': 1.5,
                'total_score_min': 0.5,
            }
        },
        'small_cap_growth': {
            'name': '中小盘成长',
            'description': '市值200亿以下、创业板或中小板的成长型个股',
            'conditions': {
                'market_cap_max': 200.0,
                'markets': ['创业板', '中小板'],
                'total_score_min': 0.6,
            }
        },
    }

    def __init__(self):
        self.last_results = []

    def screen(self, stock_list, conditions):
        """
        根据条件对股票列表进行筛选

        @param {list} stock_list - 待筛选的股票字典列表
        @param {dict} conditions - 筛选条件字典
        @returns {list} 符合条件的股票列表，按 total_score 降序
        """
        results = []
        for stock in stock_list:
            if self._match(stock, conditions):
                results.append(stock)

        results.sort(key=lambda x: x.get('total_score', 0), reverse=True)
        self.last_results = results
        return results

    def screen_with_preset(self, stock_list, preset_key):
        """
        使用预置模板进行选股

        @param {list} stock_list - 待筛选的股票字典列表
        @param {str} preset_key - 预置模板 key
        @returns {list} 符合条件的股票列表
        """
        template = self.PRESET_TEMPLATES.get(preset_key)
        if not template:
            return []
        return self.screen(stock_list, template['conditions'])

    @classmethod
    def get_preset_list(cls):
        """
        获取所有预置模板的简要信息

        @returns {list[dict]} 模板列表
        """
        return [
            {
                'key': key,
                'name': tpl['name'],
                'description': tpl['description'],
                'conditions': tpl['conditions'],
            }
            for key, tpl in cls.PRESET_TEMPLATES.items()
        ]

    # ------------------------------------------------------------------
    # 内部匹配逻辑
    # ------------------------------------------------------------------

    def _match(self, stock, conditions):
        """逐项检查条件是否全部满足"""

        # --- 价格区间 ---
        price = stock.get('current_price', 0)
        if conditions.get('price_min') is not None and price < conditions['price_min']:
            return False
        if conditions.get('price_max') is not None and price > conditions['price_max']:
            return False

        # --- 综合评分 ---
        total_score = stock.get('total_score', 0)
        if conditions.get('total_score_min') is not None and total_score < conditions['total_score_min']:
            return False
        if conditions.get('total_score_max') is not None and total_score > conditions['total_score_max']:
            return False

        # --- 技术评分 ---
        tech_score = stock.get('tech_score', 0)
        if conditions.get('tech_score_min') is not None and tech_score < conditions['tech_score_min']:
            return False
        if conditions.get('tech_score_max') is not None and tech_score > conditions['tech_score_max']:
            return False

        # --- 竞价评分 ---
        auction_score = stock.get('auction_score', 0)
        if conditions.get('auction_score_min') is not None and auction_score < conditions['auction_score_min']:
            return False
        if conditions.get('auction_score_max') is not None and auction_score > conditions['auction_score_max']:
            return False

        # --- 竞价涨幅 ---
        auction_ratio = stock.get('auction_ratio', 0)
        if conditions.get('auction_ratio_min') is not None and auction_ratio < conditions['auction_ratio_min']:
            return False
        if conditions.get('auction_ratio_max') is not None and auction_ratio > conditions['auction_ratio_max']:
            return False

        # --- RSI ---
        rsi = stock.get('rsi', 50)
        if conditions.get('rsi_min') is not None and rsi < conditions['rsi_min']:
            return False
        if conditions.get('rsi_max') is not None and rsi > conditions['rsi_max']:
            return False

        # --- 市值范围 (亿) ---
        market_cap = stock.get('market_cap_billion', 0)
        if conditions.get('market_cap_min') is not None and market_cap < conditions['market_cap_min']:
            return False
        if conditions.get('market_cap_max') is not None and market_cap > conditions['market_cap_max']:
            return False

        # --- 跳空类型 ---
        gap_types = conditions.get('gap_types')
        if gap_types and stock.get('gap_type') not in gap_types:
            return False

        # --- 信心等级 ---
        confidence_levels = conditions.get('confidence_levels')
        if confidence_levels and stock.get('confidence') not in confidence_levels:
            return False

        # --- 市场/板块 ---
        markets = conditions.get('markets')
        if markets and stock.get('market') not in markets:
            return False

        # --- 关键词搜索（代码或名称） ---
        keyword = conditions.get('keyword', '').strip()
        if keyword:
            symbol = stock.get('symbol', '')
            name = stock.get('stock_name', '')
            if keyword not in symbol and keyword not in name:
                return False

        return True
