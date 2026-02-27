#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""金融板块专用规则"""

from typing import Dict, Any
from stock_screener.analyzer.base_rule import BaseAnalysisRule


class FinanceSectorRule(BaseAnalysisRule):
    """银行/保险/券商 行业板块规则"""

    rule_id = 'sector_finance'
    name = '金融板块加成'
    description = '对银行、保险、券商行业的额外评分维度，侧重估值和股息'
    weight = 0.0

    FINANCE_KEYWORDS = [
        '银行', '保险', '证券', '券商', '金融', '信托', '期货',
        '招商', '平安', '浦发', '兴业', '工商', '建设', '农业',
    ]

    def evaluate(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        name = ctx.get('stock_name', '')
        hit = any(kw in name for kw in self.FINANCE_KEYWORDS)
        if not hit:
            return {'score': 50, 'details': '非金融板块'}

        fi = ctx.get('fundamental', {}).get('financial_indicators', {})
        score = 55
        details = ['金融板块识别']

        pe = fi.get('市盈率', 0) or fi.get('PE_Ratio', 0)
        if 0 < pe < 10:
            score += 15
            details.append(f'低PE={pe:.1f}(+15)')
        elif 0 < pe < 15:
            score += 8
            details.append(f'PE={pe:.1f}合理(+8)')

        div_yield = fi.get('股息收益率', 0) or fi.get('Dividend_Yield', 0)
        if div_yield > 4:
            score += 15
            details.append(f'高股息{div_yield:.1f}%(+15)')
        elif div_yield > 2:
            score += 8
            details.append(f'股息{div_yield:.1f}%(+8)')

        return {'score': min(100, score), 'details': '；'.join(details)}
