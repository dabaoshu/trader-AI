#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""技术面分析规则"""

from typing import Dict, Any
from stock_screener.analyzer.base_rule import BaseAnalysisRule


class TechnicalRule(BaseAnalysisRule):
    """通用技术面评估规则"""

    rule_id = 'technical'
    name = '技术面分析'
    description = '基于均线、RSI、MACD、布林带、成交量的综合技术评分'
    weight = 0.40

    def evaluate(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        tech = ctx.get('technical', {})
        score = 50
        details_parts = []

        ma_trend = tech.get('ma_trend', '')
        if ma_trend == '多头排列':
            score += 20
            details_parts.append('均线多头排列(+20)')
        elif ma_trend == '空头排列':
            score -= 20
            details_parts.append('均线空头排列(-20)')
        else:
            details_parts.append('均线震荡整理')

        rsi = tech.get('rsi', 50)
        if 30 <= rsi <= 70:
            score += 10
            details_parts.append(f'RSI={rsi:.0f} 正常区(+10)')
        elif rsi < 30:
            score += 5
            details_parts.append(f'RSI={rsi:.0f} 超卖(+5)')
        elif rsi > 70:
            score -= 5
            details_parts.append(f'RSI={rsi:.0f} 超买(-5)')

        macd = tech.get('macd_signal', '')
        if macd == '金叉向上':
            score += 15
            details_parts.append('MACD金叉(+15)')
        elif macd == '死叉向下':
            score -= 15
            details_parts.append('MACD死叉(-15)')

        bb = tech.get('bb_position', 0.5)
        if bb < 0.2:
            score += 10
            details_parts.append('布林带下轨附近(+10)')
        elif bb > 0.8:
            score -= 5
            details_parts.append('布林带上轨附近(-5)')

        vol = tech.get('volume_status', '')
        if '放量上涨' in vol:
            score += 10
            details_parts.append('放量上涨(+10)')
        elif '放量下跌' in vol:
            score -= 10
            details_parts.append('放量下跌(-10)')

        score = max(0, min(100, score))
        return {'score': score, 'details': '；'.join(details_parts)}
