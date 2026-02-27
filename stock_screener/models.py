#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
条件选股记录持久化管理

将每次筛选条件与结果摘要保存到 SQLite，支持历史回看。
"""

import sqlite3
import json
import os
from datetime import datetime


class ScreenerRecordManager:
    """选股记录管理器"""

    def __init__(self, db_path="data/cchan_web.db"):
        self.db_path = db_path
        self._ensure_table()

    # ------------------------------------------------------------------
    # 建表
    # ------------------------------------------------------------------
    def _ensure_table(self):
        """确保 screener_records 表存在，并包含 result_data 列"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS screener_records (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                conditions  TEXT NOT NULL,
                result_count INTEGER DEFAULT 0,
                result_symbols TEXT,
                result_summary TEXT,
                result_data TEXT,
                preset_key  TEXT,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # 兼容旧表：如果 result_data 列不存在则添加
        try:
            cursor.execute("SELECT result_data FROM screener_records LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE screener_records ADD COLUMN result_data TEXT")
        conn.commit()
        conn.close()

    # ------------------------------------------------------------------
    # 写入
    # ------------------------------------------------------------------
    def save_record(self, name, conditions, results):
        """
        保存一条选股记录（包含完整的条件和结果数据）

        @param {str} name - 记录名称
        @param {dict} conditions - 筛选条件
        @param {list} results - 符合条件的股票列表
        @returns {int} 新记录 id
        """
        symbols = [s.get('symbol', '') for s in results]
        summary = self._build_summary(results)
        full_data = self._serialize_results(results)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO screener_records
                (name, conditions, result_count, result_symbols,
                 result_summary, result_data, preset_key, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            name,
            json.dumps(conditions, ensure_ascii=False),
            len(results),
            json.dumps(symbols, ensure_ascii=False),
            json.dumps(summary, ensure_ascii=False),
            json.dumps(full_data, ensure_ascii=False),
            conditions.get('_preset_key', ''),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        ))
        record_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return record_id

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------
    def get_records(self, limit=50):
        """
        获取历史选股记录（列表不含完整 result_data 以节省带宽）

        @param {int} limit - 最大返回条数
        @returns {list[dict]} 记录列表，按创建时间降序
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, name, conditions, result_count, result_symbols,
                   result_summary, preset_key, created_at
            FROM screener_records
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))

        columns = [desc[0] for desc in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()

        for row in rows:
            row['conditions'] = json.loads(row['conditions']) if row['conditions'] else {}
            row['result_symbols'] = json.loads(row['result_symbols']) if row['result_symbols'] else []
            row['result_summary'] = json.loads(row['result_summary']) if row['result_summary'] else {}

        return rows

    def get_record_by_id(self, record_id):
        """
        按 id 获取单条记录（包含完整 result_data）

        @param {int} record_id
        @returns {dict|None}
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, name, conditions, result_count, result_symbols,
                   result_summary, result_data, preset_key, created_at
            FROM screener_records
            WHERE id = ?
        ''', (record_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        columns = ['id', 'name', 'conditions', 'result_count', 'result_symbols',
                    'result_summary', 'result_data', 'preset_key', 'created_at']
        record = dict(zip(columns, row))
        record['conditions'] = json.loads(record['conditions']) if record['conditions'] else {}
        record['result_symbols'] = json.loads(record['result_symbols']) if record['result_symbols'] else []
        record['result_summary'] = json.loads(record['result_summary']) if record['result_summary'] else {}
        record['result_data'] = json.loads(record['result_data']) if record.get('result_data') else []
        return record

    def delete_record(self, record_id):
        """
        删除一条选股记录

        @param {int} record_id
        @returns {bool}
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM screener_records WHERE id = ?', (record_id,))
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected > 0

    # ------------------------------------------------------------------
    # 辅助
    # ------------------------------------------------------------------
    @staticmethod
    def _serialize_results(results):
        """
        序列化完整的筛选结果用于持久化（只保留关键字段，去除 created_at 等数据库元数据）

        @param {list} results - 股票列表
        @returns {list[dict]}
        """
        keep_keys = [
            'symbol', 'stock_name', 'market', 'current_price',
            'total_score', 'tech_score', 'auction_score',
            'auction_ratio', 'gap_type', 'confidence',
            'strategy', 'entry_price', 'stop_loss', 'target_price',
            'rsi', 'market_cap_billion',
        ]
        serialized = []
        for s in results:
            item = {}
            for k in keep_keys:
                v = s.get(k)
                if v is not None:
                    item[k] = round(v, 4) if isinstance(v, float) else v
            serialized.append(item)
        return serialized

    @staticmethod
    def _build_summary(results):
        """从筛选结果中提取统计摘要"""
        if not results:
            return {
                'count': 0,
                'avg_score': 0,
                'high_confidence_count': 0,
                'markets': [],
                'price_range': [0, 0],
                'top_stocks': [],
            }

        scores = [s.get('total_score', 0) for s in results]
        prices = [s.get('current_price', 0) for s in results]
        markets = list({s.get('market', '') for s in results})
        high_conf = [s for s in results if s.get('confidence') == 'very_high']

        top_stocks = sorted(results, key=lambda x: x.get('total_score', 0), reverse=True)[:5]
        top_list = [
            {
                'symbol': s.get('symbol', ''),
                'stock_name': s.get('stock_name', ''),
                'total_score': round(s.get('total_score', 0), 3),
                'current_price': s.get('current_price', 0),
                'confidence': s.get('confidence', ''),
            }
            for s in top_stocks
        ]

        return {
            'count': len(results),
            'avg_score': round(sum(scores) / len(scores), 3) if scores else 0,
            'high_confidence_count': len(high_conf),
            'markets': markets,
            'price_range': [round(min(prices), 2), round(max(prices), 2)] if prices else [0, 0],
            'top_stocks': top_list,
        }
