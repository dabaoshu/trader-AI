#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析规则基类

所有行业/策略规则需继承此类并实现 evaluate 方法。
引擎通过 rules/ 目录自动发现并加载规则。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseAnalysisRule(ABC):
    """分析规则抽象基类"""

    @property
    @abstractmethod
    def rule_id(self) -> str:
        """唯一标识，如 'tech_sector'"""

    @property
    @abstractmethod
    def name(self) -> str:
        """中文名称，如 '科技板块规则'"""

    @property
    def description(self) -> str:
        return ''

    @property
    def weight(self) -> float:
        """该规则在综合评分中的默认权重 (0‑1)"""
        return 1.0

    @abstractmethod
    def evaluate(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估方法 — 必须实现

        @param ctx 包含:
            - price_data  : pd.DataFrame (OHLCV)
            - stock_code  : str
            - stock_name  : str
            - market      : str ('a_stock' | 'hk_stock' | 'us_stock')
            - technical   : dict (MA/RSI/MACD/BB 等)
            - fundamental : dict (基本面)
            - sentiment   : dict (舆情)
        @returns dict 必须含 'score' (0-100) 和 'details' (str)
        """
