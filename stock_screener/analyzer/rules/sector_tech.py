#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""科技板块专用规则"""

from typing import Dict, Any
from stock_screener.analyzer.base_rule import BaseAnalysisRule


class TechSectorRule(BaseAnalysisRule):
    """科技/半导体/AI 行业板块规则"""

    rule_id = 'sector_tech'
    name = '科技板块加成'
    description = '对科技、半导体、AI、软件行业的额外评分维度'
    weight = 0.0

    TECH_KEYWORDS = [
        '科技', '半导体', '芯片', '电子', '软件', '信息', '通信',
        '互联网', '计算机', 'AI', '人工智能', '数据', '云', '智能',
        '创达', '讯飞', '东方财富', '京东方', '歌尔', '海康',
    ]

    def evaluate(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        name = ctx.get('stock_name', '')
        strategy = ''
        if ctx.get('fundamental'):
            strategy = str(ctx['fundamental'].get('industry_analysis', ''))

        hit = any(kw in name or kw in strategy for kw in self.TECH_KEYWORDS)
        if not hit:
            return {'score': 50, 'details': '非科技板块，不额外加分'}

        tech = ctx.get('technical', {})
        rsi = tech.get('rsi', 50)
        vol = tech.get('volume_status', '')

        score = 60
        details = ['科技板块识别']
        if '放量上涨' in vol:
            score += 15
            details.append('资金活跃(+15)')
        if rsi < 60:
            score += 10
            details.append('未超买(+10)')

        return {'score': min(100, score), 'details': '；'.join(details)}
