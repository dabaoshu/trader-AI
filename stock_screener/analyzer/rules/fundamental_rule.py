#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""基本面分析规则"""

from typing import Dict, Any
from stock_screener.analyzer.base_rule import BaseAnalysisRule


class FundamentalRule(BaseAnalysisRule):
    """通用基本面评估规则"""

    rule_id = 'fundamental'
    name = '基本面分析'
    description = '基于财务指标（ROE/PE/负债率/增长率）的基本面评分'
    weight = 0.40

    def evaluate(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        fund = ctx.get('fundamental', {})
        fi = fund.get('financial_indicators', {})
        score = 50
        details_parts = []

        if len(fi) >= 10:
            score += 15
            details_parts.append(f'获取{len(fi)}项指标(+15)')

        roe = fi.get('净资产收益率', 0) or fi.get('ROE', 0) or 0
        if roe > 15:
            score += 10
            details_parts.append(f'ROE={roe:.1f}%优秀(+10)')
        elif roe > 10:
            score += 5
            details_parts.append(f'ROE={roe:.1f}%良好(+5)')
        elif roe and roe < 5:
            score -= 5
            details_parts.append(f'ROE={roe:.1f}%偏低(-5)')

        pe = fi.get('市盈率', 0) or fi.get('PE_Ratio', 0) or 0
        if 0 < pe < 20:
            score += 10
            details_parts.append(f'PE={pe:.1f}合理(+10)')
        elif pe > 50:
            score -= 5
            details_parts.append(f'PE={pe:.1f}偏高(-5)')

        debt = fi.get('资产负债率', 50) or fi.get('debt_ratio', 50) or 50
        if debt < 30:
            score += 5
            details_parts.append(f'负债率{debt:.0f}%低(+5)')
        elif debt > 70:
            score -= 10
            details_parts.append(f'负债率{debt:.0f}%高(-10)')

        if fund.get('valuation'):
            score += 5
        if fund.get('performance_forecast'):
            score += 5

        score = max(0, min(100, score))
        return {'score': score, 'details': '；'.join(details_parts) or '基本面数据有限'}
