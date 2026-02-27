#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""消费板块专用规则"""

from typing import Dict, Any
from stock_screener.analyzer.base_rule import BaseAnalysisRule


class ConsumerSectorRule(BaseAnalysisRule):
    """食品饮料/消费/医药 行业板块规则"""

    rule_id = 'sector_consumer'
    name = '消费板块加成'
    description = '对食品饮料、消费品、医药行业的额外评分维度，侧重品牌壁垒和盈利能力'
    weight = 0.0

    CONSUMER_KEYWORDS = [
        '白酒', '消费', '食品', '饮料', '医药', '医疗', '生物',
        '茅台', '五粮液', '洋河', '伊利', '美的', '海尔',
        '爱尔', '智飞', '沃森', '恒瑞',
    ]

    def evaluate(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        name = ctx.get('stock_name', '')
        hit = any(kw in name for kw in self.CONSUMER_KEYWORDS)
        if not hit:
            return {'score': 50, 'details': '非消费板块'}

        fi = ctx.get('fundamental', {}).get('financial_indicators', {})
        score = 55
        details = ['消费板块识别']

        gross_margin = fi.get('毛利率', 0)
        if gross_margin > 50:
            score += 15
            details.append(f'高毛利{gross_margin:.0f}%(+15)')
        elif gross_margin > 30:
            score += 8
            details.append(f'毛利{gross_margin:.0f}%(+8)')

        roe = fi.get('净资产收益率', 0) or fi.get('ROE', 0)
        if roe > 20:
            score += 10
            details.append(f'ROE={roe:.0f}%优秀(+10)')

        return {'score': min(100, score), 'details': '；'.join(details)}
