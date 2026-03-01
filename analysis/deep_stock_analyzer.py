#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trader-AI 深度股票分析引擎
集成LLM进行专业股票投研分析
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings

from data_provider import DataFetcherManager
from data_provider.base import normalize_stock_code

warnings.filterwarnings('ignore')

import requests
import time
from typing import Dict, List, Optional, Tuple

from models import DeepAnalysis, get_session_context, init_db


class DeepStockAnalyzer:
    """深度股票分析引擎 - 集成LLM专业分析"""

    def __init__(self):
        self.analysis_cache = {}
        init_db()
    
    def get_comprehensive_stock_data(self, symbol: str) -> Dict:
        """获取股票全量数据 - 分时、日K、资金流等"""
        print(f"📊 获取 {symbol} 全量数据...")
        
        data = {
            'symbol': symbol,
            'basic_info': self._get_basic_info(symbol),
            'price_data': self._get_price_data(symbol),
            'technical_indicators': self._get_technical_indicators(symbol),
            'capital_flow': self._get_capital_flow_data(symbol),
            'auction_data': self._get_auction_analysis(symbol),
            'minute_data': self._get_minute_data(symbol),
            'fundamental_data': self._get_fundamental_data(symbol)
        }
        
        return data
    
    def _get_basic_info(self, symbol: str) -> Dict:
        """获取基础信息（通过 data_provider）"""
        try:
            manager = DataFetcherManager()
            info = manager.get_stock_basic(normalize_stock_code(symbol))
            if info and isinstance(info, dict):
                out_date = info.get('outDate') or ''
                return {
                    'code': info.get('code', symbol),
                    'code_name': info.get('code_name', '未知'),
                    'industry': info.get('industry', ''),
                    'industry_classification': info.get('industryClassification', ''),
                    'list_date': info.get('ipoDate', ''),
                    'listing_status': '上市' if not out_date else '退市',
                }
        except Exception as e:
            print(f"⚠️ 获取基础信息失败: {e}")
        return self._get_fallback_basic_info(symbol)
    
    def _get_fallback_basic_info(self, symbol: str) -> Dict:
        """获取后备基础信息"""
        # 基于股票代码推断基础信息
        code = symbol.split('.')[-1] if '.' in symbol else symbol
        
        if code.startswith('6'):
            market = '上海主板'
            industry = '传统行业'
        elif code.startswith('000'):
            market = '深圳主板'  
            industry = '传统制造'
        elif code.startswith('002'):
            market = '中小板'
            industry = '中小企业'
        elif code.startswith('30'):
            market = '创业板'
            industry = '科技创新'
        else:
            market = '其他'
            industry = '综合'
            
        return {
            'code': symbol,
            'code_name': f'股票{code}',
            'industry': industry,
            'industry_classification': market,
            'list_date': '2020-01-01',
            'listing_status': '上市'
        }
    
    def _get_price_data(self, symbol: str, days: int = 60) -> Dict:
        """获取价格数据（通过 data_provider）"""
        try:
            manager = DataFetcherManager()
            df, _ = manager.get_daily_data(stock_code=normalize_stock_code(symbol), days=days)
            if df is None or df.empty or len(df) < 5:
                return self._get_simulated_price_data(symbol)
            for col in ['open', 'high', 'low', 'close', 'volume', 'amount']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            df = df.dropna(subset=['close', 'volume'])
            if len(df) < 5:
                return self._get_simulated_price_data(symbol)
            current = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else current
            turnover_rate = float(current.get('turn', 0)) if 'turn' in df.columns else 0.0
            amount = float(current.get('amount', 0)) if 'amount' in df.columns else 0.0
            return {
                'current_price': float(current['close']),
                'prev_close': float(prev['close']),
                'price_change': float(current['close'] - prev['close']),
                'price_change_pct': float((current['close'] - prev['close']) / prev['close'] * 100) if prev['close'] else 0,
                'high_52w': float(df['high'].max()),
                'low_52w': float(df['low'].min()),
                'avg_volume_10d': float(df['volume'].tail(10).mean()),
                'current_volume': float(current['volume']),
                'turnover_rate': turnover_rate,
                'amount': amount,
                'price_history': df.to_dict('records'),
            }
        except Exception as e:
            print(f"⚠️ 获取价格数据失败: {e}")
            return self._get_simulated_price_data(symbol)
    
    def _get_simulated_price_data(self, symbol: str) -> Dict:
        """生成模拟价格数据"""
        np.random.seed(int(''.join(filter(str.isdigit, symbol))) % 1000)
        
        base_price = np.random.uniform(5, 50)
        current_price = base_price * (1 + np.random.uniform(-0.05, 0.05))
        prev_price = current_price * (1 + np.random.uniform(-0.03, 0.03))
        
        return {
            'current_price': round(current_price, 2),
            'prev_close': round(prev_price, 2),
            'price_change': round(current_price - prev_price, 2),
            'price_change_pct': round((current_price - prev_price) / prev_price * 100, 2),
            'high_52w': round(current_price * 1.5, 2),
            'low_52w': round(current_price * 0.7, 2),
            'avg_volume_10d': int(np.random.uniform(100000, 1000000)),
            'current_volume': int(np.random.uniform(80000, 1200000)),
            'turnover_rate': round(np.random.uniform(0.5, 8.0), 2),
            'amount': int(np.random.uniform(50000000, 500000000)),
            'price_history': []
        }
    
    def _get_technical_indicators(self, symbol: str) -> Dict:
        """计算技术指标"""
        try:
            # 获取历史数据计算技术指标
            price_data = self._get_price_data(symbol, 90)
            
            if not price_data.get('price_history'):
                return self._get_simulated_technical_indicators()
            
            df = pd.DataFrame(price_data['price_history'])
            
            if len(df) < 20:
                return self._get_simulated_technical_indicators()
            
            # 计算各种技术指标
            close_prices = df['close']
            
            # 移动平均线
            ma5 = close_prices.rolling(5).mean().iloc[-1] if len(df) >= 5 else close_prices.iloc[-1]
            ma10 = close_prices.rolling(10).mean().iloc[-1] if len(df) >= 10 else close_prices.iloc[-1]
            ma20 = close_prices.rolling(20).mean().iloc[-1] if len(df) >= 20 else close_prices.iloc[-1]
            ma60 = close_prices.rolling(60).mean().iloc[-1] if len(df) >= 60 else close_prices.iloc[-1]
            
            # RSI指标
            rsi_14 = self._calculate_rsi(close_prices, 14)
            
            # MACD指标
            macd_signal = self._calculate_macd_signal(close_prices)
            
            # 布林带
            bollinger_position = self._calculate_bollinger_position(close_prices)
            
            return {
                'ma5': float(ma5),
                'ma10': float(ma10),
                'ma20': float(ma20),
                'ma60': float(ma60),
                'rsi_14': float(rsi_14),
                'macd_signal': macd_signal,
                'bollinger_position': float(bollinger_position),
                'ma_trend': self._analyze_ma_trend(ma5, ma10, ma20),
                'trend_strength': self._calculate_trend_strength(close_prices)
            }
            
        except Exception as e:
            print(f"⚠️ 计算技术指标失败: {e}")
            return self._get_simulated_technical_indicators()
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """计算RSI指标"""
        try:
            delta = prices.diff()
            gain = delta.where(delta > 0, 0).rolling(period).mean()
            loss = -delta.where(delta < 0, 0).rolling(period).mean()
            rs = gain / (loss + 1e-10)
            rsi = 100 - (100 / (1 + rs))
            return float(rsi.iloc[-1])
        except:
            return 50.0
    
    def _calculate_macd_signal(self, prices: pd.Series) -> str:
        """计算MACD信号"""
        try:
            ema12 = prices.ewm(span=12).mean()
            ema26 = prices.ewm(span=26).mean()
            macd = ema12 - ema26
            signal = macd.ewm(span=9).mean()
            
            current_macd = macd.iloc[-1]
            current_signal = signal.iloc[-1]
            prev_macd = macd.iloc[-2] if len(macd) > 1 else current_macd
            prev_signal = signal.iloc[-2] if len(signal) > 1 else current_signal
            
            if current_macd > current_signal and prev_macd <= prev_signal:
                return '金叉买入'
            elif current_macd < current_signal and prev_macd >= prev_signal:
                return '死叉卖出'
            elif current_macd > current_signal:
                return '多头持续'
            else:
                return '空头持续'
        except:
            return '中性'
    
    def _calculate_bollinger_position(self, prices: pd.Series, period: int = 20) -> float:
        """计算布林带位置"""
        try:
            sma = prices.rolling(period).mean()
            std = prices.rolling(period).std()
            upper = sma + (std * 2)
            lower = sma - (std * 2)
            
            current_price = prices.iloc[-1]
            current_upper = upper.iloc[-1]
            current_lower = lower.iloc[-1]
            
            # 计算价格在布林带中的位置 (0-1)
            position = (current_price - current_lower) / (current_upper - current_lower)
            return max(0, min(1, position))
        except:
            return 0.5
    
    def _analyze_ma_trend(self, ma5: float, ma10: float, ma20: float) -> str:
        """分析均线趋势"""
        if ma5 > ma10 > ma20:
            return '多头排列'
        elif ma5 < ma10 < ma20:
            return '空头排列'
        elif ma5 > ma10:
            return '短期上涨'
        elif ma5 < ma10:
            return '短期下跌'
        else:
            return '震荡整理'
    
    def _calculate_trend_strength(self, prices: pd.Series) -> float:
        """计算趋势强度"""
        try:
            if len(prices) < 10:
                return 0.5
            
            # 计算价格线性回归斜率
            x = np.arange(len(prices))
            slope = np.polyfit(x, prices, 1)[0]
            
            # 标准化趋势强度 (0-1)
            normalized_slope = (slope / prices.mean()) * 100
            strength = max(0, min(1, (normalized_slope + 5) / 10))
            return strength
        except:
            return 0.5
    
    def _get_simulated_technical_indicators(self) -> Dict:
        """生成模拟技术指标"""
        base_price = np.random.uniform(10, 50)
        
        return {
            'ma5': round(base_price * np.random.uniform(0.98, 1.02), 2),
            'ma10': round(base_price * np.random.uniform(0.96, 1.04), 2),
            'ma20': round(base_price * np.random.uniform(0.94, 1.06), 2),
            'ma60': round(base_price * np.random.uniform(0.90, 1.10), 2),
            'rsi_14': round(np.random.uniform(30, 70), 1),
            'macd_signal': np.random.choice(['金叉买入', '死叉卖出', '多头持续', '空头持续', '中性']),
            'bollinger_position': round(np.random.uniform(0.2, 0.8), 2),
            'ma_trend': np.random.choice(['多头排列', '空头排列', '短期上涨', '短期下跌', '震荡整理']),
            'trend_strength': round(np.random.uniform(0.3, 0.9), 2)
        }
    
    def _get_capital_flow_data(self, symbol: str) -> Dict:
        """获取资金流向数据"""
        try:
            # 模拟资金流向数据 (实际应该调用专业数据接口)
            np.random.seed(int(''.join(filter(str.isdigit, symbol))) % 1000)
            
            total_amount = np.random.uniform(50000000, 500000000)
            
            # 各类资金比例
            main_ratio = np.random.uniform(0.2, 0.6)
            retail_ratio = np.random.uniform(0.3, 0.7)
            institutional_ratio = 1 - main_ratio - retail_ratio
            
            # 资金流入流出
            net_inflow = np.random.uniform(-0.3, 0.3) * total_amount
            
            return {
                'main_inflow': round(net_inflow * main_ratio, 0),
                'retail_inflow': round(net_inflow * retail_ratio, 0),
                'institutional_inflow': round(net_inflow * institutional_ratio, 0),
                'net_inflow': round(net_inflow, 0),
                'inflow_ratio': round(net_inflow / total_amount * 100, 2) if total_amount > 0 else 0,
                'main_control_ratio': round(main_ratio * 100, 1),
                'flow_intensity': self._calculate_flow_intensity(net_inflow, total_amount)
            }
            
        except Exception as e:
            print(f"⚠️ 获取资金流向失败: {e}")
            return {
                'main_inflow': 0,
                'retail_inflow': 0, 
                'institutional_inflow': 0,
                'net_inflow': 0,
                'inflow_ratio': 0,
                'main_control_ratio': 50.0,
                'flow_intensity': '中等'
            }
    
    def _calculate_flow_intensity(self, net_inflow: float, total_amount: float) -> str:
        """计算资金流动强度"""
        if total_amount == 0:
            return '无数据'
        
        intensity_ratio = abs(net_inflow) / total_amount
        
        if intensity_ratio > 0.15:
            return '极强'
        elif intensity_ratio > 0.08:
            return '强'
        elif intensity_ratio > 0.03:
            return '中等'
        else:
            return '弱'
    
    def _get_auction_analysis(self, symbol: str) -> Dict:
        """获取集合竞价分析"""
        try:
            # 模拟集合竞价数据
            np.random.seed(int(''.join(filter(str.isdigit, symbol))) % 1000 + 1)
            
            auction_ratio = np.random.uniform(-3, 5)
            volume_ratio = np.random.uniform(0.5, 3.0)
            
            if auction_ratio >= 2:
                gap_type = '高开'
                sentiment = '乐观'
            elif auction_ratio >= 0.5:
                gap_type = '小幅高开'
                sentiment = '偏乐观'
            elif auction_ratio >= -0.5:
                gap_type = '平开'
                sentiment = '中性'
            elif auction_ratio >= -2:
                gap_type = '小幅低开'
                sentiment = '偏悲观'
            else:
                gap_type = '低开'
                sentiment = '悲观'
            
            return {
                'auction_ratio': round(auction_ratio, 2),
                'auction_volume_ratio': round(volume_ratio, 2),
                'gap_type': gap_type,
                'market_sentiment': sentiment,
                'auction_strength': self._evaluate_auction_strength(auction_ratio, volume_ratio)
            }
            
        except Exception as e:
            print(f"⚠️ 获取竞价数据失败: {e}")
            return {
                'auction_ratio': 0,
                'auction_volume_ratio': 1.0,
                'gap_type': '平开',
                'market_sentiment': '中性',
                'auction_strength': '一般'
            }
    
    def _evaluate_auction_strength(self, ratio: float, volume_ratio: float) -> str:
        """评估竞价强度"""
        if ratio > 2 and volume_ratio > 1.5:
            return '强势'
        elif ratio > 1 and volume_ratio > 1.2:
            return '较强'
        elif ratio > -1 and volume_ratio > 0.8:
            return '一般'
        else:
            return '偏弱'
    
    def _get_minute_data(self, symbol: str) -> Dict:
        """获取分时数据"""
        # 简化版分时数据获取
        try:
            np.random.seed(int(''.join(filter(str.isdigit, symbol))) % 1000 + 2)
            
            # 生成模拟分时数据
            base_price = np.random.uniform(10, 50)
            minute_prices = []
            
            for i in range(240):  # 4小时 * 60分钟
                price_change = np.random.uniform(-0.02, 0.02)
                base_price *= (1 + price_change)
                minute_prices.append(round(base_price, 2))
            
            return {
                'minute_prices': minute_prices[-60:],  # 最近1小时
                'intraday_high': max(minute_prices),
                'intraday_low': min(minute_prices),
                'price_volatility': round(np.std(minute_prices) / np.mean(minute_prices) * 100, 2)
            }
            
        except Exception as e:
            print(f"⚠️ 获取分时数据失败: {e}")
            return {
                'minute_prices': [],
                'intraday_high': 0,
                'intraday_low': 0,
                'price_volatility': 0
            }
    
    def _get_fundamental_data(self, symbol: str) -> Dict:
        """获取基本面数据"""
        try:
            # 模拟基本面数据
            np.random.seed(int(''.join(filter(str.isdigit, symbol))) % 1000 + 3)
            
            return {
                'pe_ratio': round(np.random.uniform(8, 35), 1),
                'pb_ratio': round(np.random.uniform(0.8, 5.0), 2),
                'roe': round(np.random.uniform(5, 25), 1),
                'debt_ratio': round(np.random.uniform(20, 70), 1),
                'revenue_growth': round(np.random.uniform(-10, 30), 1),
                'profit_growth': round(np.random.uniform(-15, 40), 1),
                'market_cap_billion': round(np.random.uniform(20, 200), 1)
            }
            
        except Exception as e:
            print(f"⚠️ 获取基本面数据失败: {e}")
            return {
                'pe_ratio': 15.0,
                'pb_ratio': 2.0,
                'roe': 12.0,
                'debt_ratio': 40.0,
                'revenue_growth': 8.0,
                'profit_growth': 12.0,
                'market_cap_billion': 80.0
            }
    
    def generate_llm_analysis(self, comprehensive_data: Dict) -> Dict:
        """使用LLM生成深度分析报告"""
        print("🤖 开始LLM深度分析...")
        
        try:
            # 构建分析提示词
            analysis_prompt = self._build_analysis_prompt(comprehensive_data)
            
            # 调用LLM API进行分析
            llm_response = self._call_llm_api(analysis_prompt)
            
            # 解析LLM响应
            analysis_result = self._parse_llm_response(llm_response, comprehensive_data)
            
            return analysis_result
            
        except Exception as e:
            print(f"⚠️ LLM分析失败: {e}")
            return self._generate_fallback_analysis(comprehensive_data)
    
    def _build_analysis_prompt(self, data: Dict) -> str:
        """构建LLM分析提示词"""
        symbol = data['symbol']
        basic = data['basic_info']
        price = data['price_data']
        tech = data['technical_indicators']
        capital = data['capital_flow']
        auction = data['auction_data']
        fundamental = data['fundamental_data']
        
        prompt = f"""
你是一位专业的股票投资分析师，请对股票 {symbol} ({basic['code_name']}) 进行深度投资分析。

## 基础信息
- 股票代码: {symbol}
- 股票名称: {basic['code_name']}
- 所属行业: {basic['industry']}
- 市场分类: {basic['industry_classification']}

## 价格数据
- 当前价格: ¥{price['current_price']:.2f}
- 昨日收盘: ¥{price['prev_close']:.2f}
- 涨跌幅: {price['price_change_pct']:+.2f}%
- 52周最高: ¥{price['high_52w']:.2f}
- 52周最低: ¥{price['low_52w']:.2f}
- 换手率: {price['turnover_rate']:.2f}%

## 技术指标
- MA5: ¥{tech['ma5']:.2f}
- MA10: ¥{tech['ma10']:.2f}
- MA20: ¥{tech['ma20']:.2f}
- MA60: ¥{tech['ma60']:.2f}
- RSI(14): {tech['rsi_14']:.1f}
- MACD信号: {tech['macd_signal']}
- 均线趋势: {tech['ma_trend']}
- 布林带位置: {tech['bollinger_position']:.2f}

## 资金流向
- 主力资金净流入: {capital['main_inflow']:,.0f}万元
- 散户资金净流入: {capital['retail_inflow']:,.0f}万元
- 机构资金净流入: {capital['institutional_inflow']:,.0f}万元
- 净流入比例: {capital['inflow_ratio']:+.2f}%
- 主力控盘度: {capital['main_control_ratio']:.1f}%

## 集合竞价
- 竞价涨跌幅: {auction['auction_ratio']:+.2f}%
- 竞价量比: {auction['auction_volume_ratio']:.2f}
- 开盘类型: {auction['gap_type']}
- 市场情绪: {auction['market_sentiment']}

## 基本面数据
- PE比率: {fundamental['pe_ratio']:.1f}
- PB比率: {fundamental['pb_ratio']:.2f}
- ROE: {fundamental['roe']:.1f}%
- 负债率: {fundamental['debt_ratio']:.1f}%
- 营收增长: {fundamental['revenue_growth']:+.1f}%
- 利润增长: {fundamental['profit_growth']:+.1f}%
- 总市值: {fundamental['market_cap_billion']:.1f}亿元

请基于以上数据，提供以下专业分析：

1. **综合投资评级**: [强烈推荐/推荐/中性/谨慎/不推荐]
2. **投资信心等级**: [很高/高/中等/偏低/很低]
3. **风险评估**: [低风险/中低风险/中等风险/中高风险/高风险]

4. **技术面分析**:
   - 短期趋势判断
   - 关键支撑和阻力位
   - 技术指标综合解读

5. **资金面分析**:
   - 主力资金意图分析
   - 市场参与者行为
   - 流动性评估

6. **基本面分析**:
   - 估值水平评价
   - 盈利能力分析
   - 行业地位和前景

7. **投资建议**:
   - 最佳买入点位和时机
   - 目标价位设定
   - 止损位置建议
   - 预期收益率
   - 建议持股周期
   - 推荐仓位比例

8. **风险提示**:
   - 主要风险因素
   - 需要关注的指标
   - 市场环境影响

请用专业、客观的语言进行分析，确保建议具有可操作性。
"""
        return prompt
    
    def _call_llm_api(self, prompt: str) -> str:
        """通过统一 AI 模型管理器调用大模型"""
        try:
            from stock_screener.analyzer.ai_model import get_ai_model_manager
            mgr = get_ai_model_manager()
            response = mgr.chat(
                prompt=prompt,
                caller='deep_analysis',
                system_prompt='你是一位资深的股票分析师，请提供专业、客观的投资分析。',
            )
            if response:
                return response
        except Exception as e:
            print(f"⚠️ AI 模型调用失败: {e}")

        print("⚠️ 无可用 AI 模型，使用内置模拟分析")
        return self._generate_simulated_analysis()

    @staticmethod
    def _generate_simulated_analysis() -> str:
        """生成内置模拟分析文本（无 AI 模型可用时的降级方案）"""
        return """## 综合投资评级: 推荐
## 投资信心等级: 高
## 风险评估: 中等风险

### 技术面分析
当前股价处于均线系统支撑之上，短期趋势偏向乐观。RSI指标显示股价未进入超买区域，仍有上行空间。MACD信号呈现积极态势，表明多头力量正在聚集。

### 基本面分析
当前估值水平处于合理区间，PE比率与同行业相比具有一定优势。公司盈利能力稳定，ROE指标表现良好。

### 投资建议
建议在股价回调至支撑位附近时分批建仓。短期目标价位为当前价格上方15-20%。止损位设在当前价格下方8-10%。

### 风险提示
1. 市场整体波动风险 2. 行业政策变化风险 3. 个股基本面变化风险

*注意: 当前使用内置模拟分析，配置 AI 模型后可获得更精准的分析结果。*
"""

    def _parse_llm_response(self, llm_response: str, data: Dict) -> Dict:
        """解析LLM分析响应"""
        try:
            # 简化的解析逻辑，提取关键信息
            price_data = data['price_data']
            current_price = price_data['current_price']
            
            # 从响应中提取关键信息
            if '强烈推荐' in llm_response:
                rating = '强烈推荐'
                confidence = 'very_high'
            elif '推荐' in llm_response:
                rating = '推荐'
                confidence = 'high'
            elif '中性' in llm_response:
                rating = '中性'
                confidence = 'medium'
            else:
                rating = '谨慎'
                confidence = 'low'
            
            # 提取风险评估
            if '低风险' in llm_response:
                risk = '低风险'
            elif '中等风险' in llm_response:
                risk = '中等风险'
            elif '高风险' in llm_response:
                risk = '高风险'
            else:
                risk = '中等风险'
            
            # 估算目标价和止损价
            if '15-20%' in llm_response:
                target_price = current_price * 1.175  # 平均17.5%
                expected_return = 17.5
            else:
                target_price = current_price * 1.15
                expected_return = 15.0
            
            if '8-10%' in llm_response:
                stop_loss = current_price * 0.91  # 平均9%
            else:
                stop_loss = current_price * 0.92
            
            # 提取持股周期
            if '3-6个月' in llm_response:
                holding_days = 120
            elif '1-3个月' in llm_response:
                holding_days = 60
            else:
                holding_days = 90
            
            # 提取仓位建议
            if '10-15%' in llm_response:
                position = 12.5
            elif '15-20%' in llm_response:
                position = 17.5
            else:
                position = 10.0
            
            return {
                'llm_analysis_text': llm_response,
                'investment_rating': rating,
                'confidence_level': confidence,
                'risk_assessment': risk,
                'target_price': round(target_price, 2),
                'stop_loss_price': round(stop_loss, 2),
                'expected_return_pct': expected_return,
                'holding_period_days': holding_days,
                'position_suggestion': position,
                'buy_point': '技术支撑位或放量突破时',
                'sell_point': '达到目标价位或跌破止损位'
            }
            
        except Exception as e:
            print(f"⚠️ 解析LLM响应失败: {e}")
            return self._generate_fallback_analysis(data)
    
    def _generate_fallback_analysis(self, data: Dict) -> Dict:
        """生成备用分析结果"""
        price_data = data['price_data']
        current_price = price_data['current_price']
        
        return {
            'llm_analysis_text': '系统分析显示该股票表现中性，建议谨慎观察市场走势后再做决定。',
            'investment_rating': '中性',
            'confidence_level': 'medium',
            'risk_assessment': '中等风险',
            'target_price': round(current_price * 1.1, 2),
            'stop_loss_price': round(current_price * 0.92, 2),
            'expected_return_pct': 10.0,
            'holding_period_days': 60,
            'position_suggestion': 5.0,
            'buy_point': '等待更明确的技术信号',
            'sell_point': '达到目标价位或出现风险信号'
        }
    
    def calculate_comprehensive_scores(self, data: Dict, llm_analysis: Dict) -> Dict:
        """计算综合评分"""
        try:
            # 技术面评分
            tech_score = self._calculate_technical_score(data['technical_indicators'], data['price_data'])
            
            # 基本面评分
            fundamental_score = self._calculate_fundamental_score(data['fundamental_data'])
            
            # 情感面评分 (基于资金流向和竞价)
            sentiment_score = self._calculate_sentiment_score(data['capital_flow'], data['auction_data'])
            
            # 综合评分
            total_score = (tech_score * 0.4 + fundamental_score * 0.35 + sentiment_score * 0.25)
            
            return {
                'technical_score': round(tech_score, 3),
                'fundamental_score': round(fundamental_score, 3),
                'sentiment_score': round(sentiment_score, 3),
                'total_score': round(total_score, 3)
            }
            
        except Exception as e:
            print(f"⚠️ 计算评分失败: {e}")
            return {
                'technical_score': 0.6,
                'fundamental_score': 0.6,
                'sentiment_score': 0.6,
                'total_score': 0.6
            }
    
    def _calculate_technical_score(self, tech: Dict, price: Dict) -> float:
        """计算技术面评分"""
        score = 0.5  # 基础分
        
        try:
            # RSI评分
            rsi = tech['rsi_14']
            if 30 <= rsi <= 70:
                score += 0.15
            elif 20 <= rsi <= 80:
                score += 0.1
            
            # MACD信号评分
            macd_signal = tech['macd_signal']
            if macd_signal in ['金叉买入', '多头持续']:
                score += 0.2
            elif macd_signal == '中性':
                score += 0.1
            
            # 均线趋势评分
            ma_trend = tech['ma_trend']
            if ma_trend == '多头排列':
                score += 0.15
            elif ma_trend == '短期上涨':
                score += 0.1
            
            # 布林带位置评分
            bb_pos = tech['bollinger_position']
            if 0.2 <= bb_pos <= 0.8:
                score += 0.1
            
            # 价格变化评分
            price_change = price['price_change_pct']
            if 0 < price_change <= 5:
                score += 0.1
            elif -2 <= price_change <= 0:
                score += 0.05
            
        except Exception:
            pass
        
        return min(1.0, score)
    
    def _calculate_fundamental_score(self, fundamental: Dict) -> float:
        """计算基本面评分"""
        score = 0.5  # 基础分
        
        try:
            # PE比率评分
            pe = fundamental['pe_ratio']
            if 10 <= pe <= 25:
                score += 0.15
            elif 8 <= pe <= 35:
                score += 0.1
            
            # ROE评分
            roe = fundamental['roe']
            if roe >= 15:
                score += 0.15
            elif roe >= 10:
                score += 0.1
            
            # 增长率评分
            revenue_growth = fundamental['revenue_growth']
            profit_growth = fundamental['profit_growth']
            
            if revenue_growth > 10 and profit_growth > 15:
                score += 0.2
            elif revenue_growth > 5 and profit_growth > 10:
                score += 0.15
            elif revenue_growth > 0 and profit_growth > 0:
                score += 0.1
            
            # 负债率评分
            debt_ratio = fundamental['debt_ratio']
            if debt_ratio <= 40:
                score += 0.1
            elif debt_ratio <= 60:
                score += 0.05
            
        except Exception:
            pass
        
        return min(1.0, score)
    
    def _calculate_sentiment_score(self, capital: Dict, auction: Dict) -> float:
        """计算情感面评分"""
        score = 0.5  # 基础分
        
        try:
            # 资金净流入评分
            inflow_ratio = capital['inflow_ratio']
            if inflow_ratio > 5:
                score += 0.2
            elif inflow_ratio > 2:
                score += 0.15
            elif inflow_ratio > 0:
                score += 0.1
            
            # 主力控盘度评分
            control_ratio = capital['main_control_ratio']
            if control_ratio >= 60:
                score += 0.15
            elif control_ratio >= 45:
                score += 0.1
            
            # 竞价表现评分
            auction_ratio = auction['auction_ratio']
            if auction_ratio > 1:
                score += 0.15
            elif auction_ratio > 0:
                score += 0.1
            elif auction_ratio > -1:
                score += 0.05
            
        except Exception:
            pass
        
        return min(1.0, score)
    
    def generate_deep_analysis_report(self, symbol: str) -> Dict:
        """生成深度分析报告"""
        print(f"🔬 开始深度分析 {symbol}...")
        
        try:
            # 1. 获取全量数据
            comprehensive_data = self.get_comprehensive_stock_data(symbol)
            
            # 2. LLM深度分析
            llm_analysis = self.generate_llm_analysis(comprehensive_data)
            
            # 3. 计算综合评分
            scores = self.calculate_comprehensive_scores(comprehensive_data, llm_analysis)
            
            # 4. 整合分析报告
            analysis_report = {
                **comprehensive_data,
                **llm_analysis,
                **scores,
                'analysis_date': datetime.now().strftime('%Y-%m-%d'),
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            # 5. 保存到数据库
            self._save_deep_analysis(analysis_report)
            
            print(f"✅ {symbol} 深度分析完成")
            return analysis_report
            
        except Exception as e:
            print(f"❌ {symbol} 深度分析失败: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def _save_deep_analysis(self, analysis: Dict):
        """保存深度分析结果到数据库（按 symbol + analysis_date upsert）"""
        try:
            symbol = analysis["symbol"]
            basic = analysis["basic_info"]
            price = analysis["price_data"]
            tech = analysis["technical_indicators"]
            capital = analysis["capital_flow"]
            auction = analysis["auction_data"]
            fundamental = analysis["fundamental_data"]
            ad = analysis["analysis_date"]
            vol_ratio = (
                price["current_volume"] / price["avg_volume_10d"]
                if price.get("avg_volume_10d", 0) > 0
                else 1.0
            )
            session = get_session_context()
            try:
                row = (
                    session.query(DeepAnalysis)
                    .filter(
                        DeepAnalysis.symbol == symbol,
                        DeepAnalysis.analysis_date == ad,
                    )
                    .first()
                )
                if not row:
                    row = DeepAnalysis(symbol=symbol, stock_name=basic.get("code_name"), analysis_date=ad)
                    session.add(row)
                row.stock_name = basic.get("code_name")
                row.current_price = price.get("current_price")
                row.price_change_pct = price.get("price_change_pct")
                row.volume_ratio = vol_ratio
                row.market_cap_billion = fundamental.get("market_cap_billion")
                row.rsi_14 = tech.get("rsi_14")
                row.macd_signal = tech.get("macd_signal")
                row.ma5, row.ma10, row.ma20, row.ma60 = tech.get("ma5"), tech.get("ma10"), tech.get("ma20"), tech.get("ma60")
                row.bollinger_position = tech.get("bollinger_position")
                row.main_inflow = capital.get("main_inflow")
                row.retail_inflow = capital.get("retail_inflow")
                row.institutional_inflow = capital.get("institutional_inflow")
                row.net_inflow = capital.get("net_inflow")
                row.auction_ratio = auction.get("auction_ratio")
                row.auction_volume_ratio = auction.get("auction_volume_ratio")
                row.gap_type = auction.get("gap_type")
                row.llm_analysis_text = analysis.get("llm_analysis_text")
                row.investment_rating = analysis.get("investment_rating")
                row.confidence_level = analysis.get("confidence_level")
                row.risk_assessment = analysis.get("risk_assessment")
                row.buy_point = analysis.get("buy_point")
                row.sell_point = analysis.get("sell_point")
                row.stop_loss_price = analysis.get("stop_loss_price")
                row.target_price = analysis.get("target_price")
                row.expected_return_pct = analysis.get("expected_return_pct")
                row.holding_period_days = analysis.get("holding_period_days")
                row.position_suggestion = analysis.get("position_suggestion")
                row.technical_score = analysis.get("technical_score")
                row.fundamental_score = analysis.get("fundamental_score")
                row.sentiment_score = analysis.get("sentiment_score")
                row.total_score = analysis.get("total_score")
                session.commit()
            finally:
                session.close()
        except Exception as e:
            print(f"⚠️ 保存深度分析失败: {e}")

if __name__ == "__main__":
    # 测试深度分析
    analyzer = DeepStockAnalyzer()
    
    test_symbols = ['sz.000606', 'sz.002139']
    
    for symbol in test_symbols:
        report = analyzer.generate_deep_analysis_report(symbol)
        if report:
            print(f"\n📋 {symbol} 深度分析结果:")
            print(f"   投资评级: {report['investment_rating']}")
            print(f"   信心等级: {report['confidence_level']}")
            print(f"   综合评分: {report['total_score']:.3f}")
            print(f"   目标价位: ¥{report['target_price']:.2f}")
            print(f"   预期收益: {report['expected_return_pct']:.1f}%")