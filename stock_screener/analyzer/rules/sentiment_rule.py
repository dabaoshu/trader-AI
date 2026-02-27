#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""市场情绪分析规则"""

from typing import Dict, Any
from stock_screener.analyzer.base_rule import BaseAnalysisRule


class SentimentRule(BaseAnalysisRule):
    """市场情绪/舆情评估规则"""

    rule_id = 'sentiment'
    name = '市场情绪分析'
    description = '基于新闻、公告、研报的情绪得分'
    weight = 0.20

    def evaluate(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        sent = ctx.get('sentiment', {})
        overall = sent.get('overall_sentiment', 0)
        confidence = sent.get('confidence_score', 0)
        total = sent.get('total_analyzed', 0)

        base = (overall + 1) * 50
        adjust = confidence * 10 + min(total / 100, 1.0) * 10
        score = max(0, min(100, base + adjust))

        trend = sent.get('sentiment_trend', '中性')
        return {
            'score': round(score, 1),
            'details': f'情绪趋势: {trend}，分析{total}条新闻，置信度{confidence:.0%}',
        }
