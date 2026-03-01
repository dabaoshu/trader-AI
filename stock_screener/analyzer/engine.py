#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票分析引擎

可动态加载 rules/ 目录下的分析规则，对不同行业板块应用不同策略。
参考 stock-scanner 项目设计：多市场支持 + 技术/基本面/情绪三维评分。
"""

import os
import re
import sys
import importlib
import inspect
import logging
import math
import warnings
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

import pandas as pd
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
warnings.filterwarnings('ignore')

from stock_screener.analyzer.base_rule import BaseAnalysisRule
from data_provider import DataFetcherManager
from data_provider.base import normalize_stock_code

logger = logging.getLogger(__name__)


class StockAnalysisEngine:
    """
    股票分析引擎 — 支持动态规则加载

    使用方式:
        engine = StockAnalysisEngine()
        engine.load_rules()                          # 加载全部内置规则
        engine.set_active_rules(['technical', 'fundamental', 'sentiment'])
        report = engine.analyze('000001')             # 分析平安银行
    """

    # 市场自动检测
    MARKET_PATTERNS = {
        'a_stock': re.compile(r'^\d{6}$'),
        'hk_stock': re.compile(r'^(HK)?\d{4,5}$', re.I),
        'us_stock': re.compile(r'^[A-Za-z]{1,5}$'),
    }

    MARKET_META = {
        'a_stock': {'label': 'A股', 'currency': 'CNY'},
        'hk_stock': {'label': '港股', 'currency': 'HKD'},
        'us_stock': {'label': '美股', 'currency': 'USD'},
    }

    def __init__(self):
        self._rules: Dict[str, BaseAnalysisRule] = {}
        self._active_rule_ids: Optional[List[str]] = None

    # ------------------------------------------------------------------
    # 规则管理
    # ------------------------------------------------------------------

    def load_rules(self, extra_dirs: Optional[List[str]] = None):
        """
        从 rules/ 目录（及额外目录）自动发现并加载规则

        @param extra_dirs 额外规则目录列表
        """
        dirs = [os.path.join(os.path.dirname(__file__), 'rules')]
        if extra_dirs:
            dirs.extend(extra_dirs)

        for d in dirs:
            if not os.path.isdir(d):
                continue
            for fname in os.listdir(d):
                if not fname.endswith('.py') or fname.startswith('_'):
                    continue
                module_path = os.path.join(d, fname)
                self._load_rule_file(module_path, fname)

        logger.info(f"已加载 {len(self._rules)} 条分析规则: {list(self._rules.keys())}")

    def _load_rule_file(self, filepath: str, filename: str):
        module_name = f"_rule_{filename[:-3]}"
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        if spec is None or spec.loader is None:
            return
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception as e:
            logger.warning(f"加载规则文件失败 {filename}: {e}")
            return

        for _, obj in inspect.getmembers(mod, inspect.isclass):
            if issubclass(obj, BaseAnalysisRule) and obj is not BaseAnalysisRule:
                try:
                    instance = obj()
                    self._rules[instance.rule_id] = instance
                except Exception as e:
                    logger.warning(f"实例化规则失败 {obj.__name__}: {e}")

    def register_rule(self, rule: BaseAnalysisRule):
        """手动注册一条规则"""
        self._rules[rule.rule_id] = rule

    def get_all_rules(self) -> List[Dict[str, Any]]:
        """返回所有已加载规则的元信息"""
        return [
            {
                'rule_id': r.rule_id,
                'name': r.name,
                'description': r.description,
                'weight': r.weight,
            }
            for r in self._rules.values()
        ]

    def set_active_rules(self, rule_ids: List[str]):
        """设置本次分析激活的规则列表"""
        self._active_rule_ids = rule_ids

    def _get_effective_rules(self) -> List[BaseAnalysisRule]:
        if self._active_rule_ids is not None:
            return [self._rules[rid] for rid in self._active_rule_ids if rid in self._rules]
        return list(self._rules.values())

    # ------------------------------------------------------------------
    # 市场检测 / 数据获取
    # ------------------------------------------------------------------

    def detect_market(self, code: str) -> str:
        code = code.strip().upper()
        if re.match(r'^\d{6}$', code):
            return 'a_stock'
        if re.match(r'^(HK)?\d{4,5}$', code, re.I):
            return 'hk_stock'
        if re.match(r'^[A-Z]{1,5}$', code):
            return 'us_stock'
        return 'a_stock'

    def _fetch_price_data(self, code: str, market: str, days: int = 180) -> pd.DataFrame:
        """通过 data_provider 获取历史 K 线"""
        try:
            manager = DataFetcherManager()
            normalized = normalize_stock_code(code)
            df, _ = manager.get_daily_data(stock_code=normalized, days=days)
            if df is None or df.empty:
                return pd.DataFrame()
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')
            if 'pct_chg' in df.columns and 'change_pct' not in df.columns:
                df['change_pct'] = df['pct_chg']
            return df
        except Exception as e:
            logger.warning(f"获取 {market} {code} 行情失败: {e}")
            return pd.DataFrame()

    @staticmethod
    def _standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
        cn_map = {'日期': 'date', '开盘': 'open', '收盘': 'close',
                  '最高': 'high', '最低': 'low', '成交量': 'volume',
                  '涨跌幅': 'change_pct'}
        df = df.rename(columns={k: v for k, v in cn_map.items() if k in df.columns})
        for col in ['open', 'close', 'high', 'low', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
        return df

    def _get_stock_name(self, code: str, market: str) -> str:
        try:
            manager = DataFetcherManager()
            name = manager.get_stock_name(normalize_stock_code(code))
            if name:
                return name
        except Exception:
            pass
        return code

    # ------------------------------------------------------------------
    # 技术指标计算（供规则使用）
    # ------------------------------------------------------------------

    @staticmethod
    def calc_technical(df: pd.DataFrame) -> Dict[str, Any]:
        if df.empty or 'close' not in df.columns:
            return {'ma_trend': '数据不足', 'rsi': 50.0, 'macd_signal': '数据不足',
                    'bb_position': 0.5, 'volume_status': '数据不足'}

        def sf(v, d=0.0):
            try:
                v = float(v)
                return d if (math.isnan(v) or math.isinf(v)) else v
            except Exception:
                return d

        result: Dict[str, Any] = {}

        # MA
        df['ma5'] = df['close'].rolling(5, min_periods=1).mean()
        df['ma10'] = df['close'].rolling(10, min_periods=1).mean()
        df['ma20'] = df['close'].rolling(20, min_periods=1).mean()
        p = sf(df['close'].iloc[-1])
        ma5 = sf(df['ma5'].iloc[-1], p)
        ma10 = sf(df['ma10'].iloc[-1], p)
        ma20 = sf(df['ma20'].iloc[-1], p)
        if p > ma5 > ma10 > ma20:
            result['ma_trend'] = '多头排列'
        elif p < ma5 < ma10 < ma20:
            result['ma_trend'] = '空头排列'
        else:
            result['ma_trend'] = '震荡整理'

        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14, min_periods=1).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14, min_periods=1).mean()
        rs = gain / loss.replace(0, 1e-10)
        rsi_series = 100 - 100 / (1 + rs)
        result['rsi'] = sf(rsi_series.iloc[-1], 50.0)

        # MACD
        ema12 = df['close'].ewm(span=12, min_periods=1).mean()
        ema26 = df['close'].ewm(span=26, min_periods=1).mean()
        macd_line = ema12 - ema26
        signal = macd_line.ewm(span=9, min_periods=1).mean()
        hist = macd_line - signal
        if len(hist) >= 2:
            cur, prev = sf(hist.iloc[-1]), sf(hist.iloc[-2])
            result['macd_signal'] = '金叉向上' if cur > prev and cur > 0 else ('死叉向下' if cur < prev and cur < 0 else '横盘整理')
        else:
            result['macd_signal'] = '数据不足'

        # Bollinger
        bb_mid = df['close'].rolling(min(20, len(df)), min_periods=1).mean()
        bb_std = df['close'].rolling(min(20, len(df)), min_periods=1).std()
        bb_up = bb_mid + 2 * bb_std
        bb_lo = bb_mid - 2 * bb_std
        u, l = sf(bb_up.iloc[-1]), sf(bb_lo.iloc[-1])
        result['bb_position'] = sf((p - l) / max(u - l, 1e-10), 0.5)

        # Volume
        avg_vol = sf(df['volume'].rolling(min(20, len(df)), min_periods=1).mean().iloc[-1])
        cur_vol = sf(df['volume'].iloc[-1])
        chg = 0.0
        if 'change_pct' in df.columns:
            chg = sf(df['change_pct'].iloc[-1])
        elif len(df) >= 2:
            prev_p = sf(df['close'].iloc[-2])
            if prev_p > 0:
                chg = (p - prev_p) / prev_p * 100
        if cur_vol > avg_vol * 1.5:
            result['volume_status'] = '放量上涨' if chg > 0 else '放量下跌'
        elif cur_vol < avg_vol * 0.5:
            result['volume_status'] = '缩量调整'
        else:
            result['volume_status'] = '温和放量'

        # Price info
        result['current_price'] = p
        result['price_change'] = chg
        vol_ratio = cur_vol / max(avg_vol, 1)
        result['volume_ratio'] = sf(vol_ratio, 1.0)

        return result

    # ------------------------------------------------------------------
    # 主分析入口
    # ------------------------------------------------------------------

    def analyze(self, stock_code: str, rule_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        对单只股票执行完整分析

        @param stock_code 股票代码（自动检测市场）
        @param rule_ids   可选，本次使用的规则 id 列表
        @returns 分析报告字典
        """
        if rule_ids:
            self.set_active_rules(rule_ids)

        market = self.detect_market(stock_code)
        normalized = stock_code.strip().upper()
        stock_name = self._get_stock_name(normalized, market)

        logger.info(f"开始分析 {stock_name}({normalized}) [{self.MARKET_META.get(market, {}).get('label', market)}]")

        # 获取行情
        price_df = self._fetch_price_data(normalized, market)
        if price_df.empty:
            return self._empty_report(normalized, stock_name, market, '无法获取行情数据')

        # 技术指标
        technical = self.calc_technical(price_df)

        # 构建上下文
        ctx: Dict[str, Any] = {
            'stock_code': normalized,
            'stock_name': stock_name,
            'market': market,
            'price_data': price_df,
            'technical': technical,
            'fundamental': {},
            'sentiment': {},
        }

        # 执行规则
        rules = self._get_effective_rules()
        rule_results: Dict[str, Any] = {}
        weighted_sum = 0.0
        weight_total = 0.0

        for rule in rules:
            try:
                res = rule.evaluate(ctx)
                s = res.get('score', 50)
                w = rule.weight
                rule_results[rule.rule_id] = {
                    'name': rule.name,
                    'score': s,
                    'weight': w,
                    'details': res.get('details', ''),
                }
                if w > 0:
                    weighted_sum += s * w
                    weight_total += w
            except Exception as e:
                logger.warning(f"规则 {rule.rule_id} 执行失败: {e}")
                rule_results[rule.rule_id] = {
                    'name': rule.name, 'score': 50, 'weight': rule.weight,
                    'details': f'执行异常: {e}',
                }

        comprehensive = weighted_sum / weight_total if weight_total > 0 else 50.0

        # 投资建议
        if comprehensive >= 80:
            recommendation = '强烈推荐买入'
        elif comprehensive >= 65:
            recommendation = '建议买入'
        elif comprehensive >= 45:
            recommendation = '持有观望'
        elif comprehensive >= 30:
            recommendation = '建议减仓'
        else:
            recommendation = '建议卖出'

        market_label = self.MARKET_META.get(market, {}).get('label', market)
        recommendation += f' ({market_label})'

        return {
            'stock_code': normalized,
            'stock_name': stock_name,
            'market': market,
            'market_label': market_label,
            'currency': self.MARKET_META.get(market, {}).get('currency', ''),
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'price_info': {
                'current_price': technical.get('current_price', 0),
                'price_change': technical.get('price_change', 0),
                'volume_ratio': technical.get('volume_ratio', 1),
            },
            'technical': technical,
            'rule_results': rule_results,
            'comprehensive_score': round(comprehensive, 1),
            'recommendation': recommendation,
            'active_rules': [r.rule_id for r in rules],
        }

    def _empty_report(self, code, name, market, reason):
        return {
            'stock_code': code,
            'stock_name': name,
            'market': market,
            'market_label': self.MARKET_META.get(market, {}).get('label', market),
            'currency': self.MARKET_META.get(market, {}).get('currency', ''),
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'price_info': {'current_price': 0, 'price_change': 0, 'volume_ratio': 1},
            'technical': {},
            'rule_results': {},
            'comprehensive_score': 0,
            'recommendation': reason,
            'active_rules': [],
            'error': reason,
        }
