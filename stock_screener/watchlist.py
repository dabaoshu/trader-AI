#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自选股管理模块

支持多分组（tab），每个分组可重命名，股票可增删查。
数据持久化到 SQLite。
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Optional


class WatchlistManager:
    """自选股管理器"""

    def __init__(self, db_path: str = "data/cchan_web.db"):
        self.db_path = db_path
        self._ensure_tables()

    def _ensure_tables(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS watchlist_groups (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                sort_order  INTEGER DEFAULT 0,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS watchlist_stocks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id    INTEGER NOT NULL,
                symbol      TEXT NOT NULL,
                stock_name  TEXT,
                market      TEXT,
                note        TEXT DEFAULT '',
                added_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES watchlist_groups(id) ON DELETE CASCADE,
                UNIQUE(group_id, symbol)
            )
        ''')
        # 保证至少有一个默认分组
        c.execute("SELECT COUNT(*) FROM watchlist_groups")
        if c.fetchone()[0] == 0:
            c.execute("INSERT INTO watchlist_groups (name, sort_order) VALUES ('默认自选', 0)")
        conn.commit()
        conn.close()

    # ------------------------------------------------------------------
    # 分组 CRUD
    # ------------------------------------------------------------------

    def list_groups(self) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT id, name, sort_order, created_at FROM watchlist_groups ORDER BY sort_order, id")
        groups = [{'id': r[0], 'name': r[1], 'sort_order': r[2], 'created_at': r[3]} for r in c.fetchall()]
        for g in groups:
            c.execute("SELECT COUNT(*) FROM watchlist_stocks WHERE group_id = ?", (g['id'],))
            g['stock_count'] = c.fetchone()[0]
        conn.close()
        return groups

    def add_group(self, name: str) -> Dict:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT COALESCE(MAX(sort_order),0)+1 FROM watchlist_groups")
        next_order = c.fetchone()[0]
        c.execute("INSERT INTO watchlist_groups (name, sort_order) VALUES (?, ?)", (name, next_order))
        gid = c.lastrowid
        conn.commit()
        conn.close()
        return {'id': gid, 'name': name, 'sort_order': next_order, 'stock_count': 0}

    def rename_group(self, group_id: int, name: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("UPDATE watchlist_groups SET name = ? WHERE id = ?", (name, group_id))
        ok = c.rowcount > 0
        conn.commit()
        conn.close()
        return ok

    def delete_group(self, group_id: int) -> bool:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM watchlist_stocks WHERE group_id = ?", (group_id,))
        c.execute("DELETE FROM watchlist_groups WHERE id = ?", (group_id,))
        ok = c.rowcount > 0
        conn.commit()
        conn.close()
        return ok

    # ------------------------------------------------------------------
    # 股票增删查
    # ------------------------------------------------------------------

    def list_stocks(self, group_id: int) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            SELECT id, group_id, symbol, stock_name, market, note, added_at
            FROM watchlist_stocks WHERE group_id = ? ORDER BY added_at DESC
        """, (group_id,))
        cols = ['id', 'group_id', 'symbol', 'stock_name', 'market', 'note', 'added_at']
        rows = [dict(zip(cols, r)) for r in c.fetchall()]
        conn.close()
        return rows

    def add_stock(self, group_id: int, symbol: str,
                  stock_name: str = '', market: str = '', note: str = '') -> Dict:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            c.execute("""
                INSERT INTO watchlist_stocks (group_id, symbol, stock_name, market, note)
                VALUES (?, ?, ?, ?, ?)
            """, (group_id, symbol, stock_name, market, note))
            sid = c.lastrowid
            conn.commit()
            conn.close()
            return {'id': sid, 'group_id': group_id, 'symbol': symbol,
                    'stock_name': stock_name, 'market': market, 'note': note}
        except sqlite3.IntegrityError:
            conn.close()
            return {'error': 'duplicate', 'message': f'{symbol} 已在该分组中'}

    def remove_stock(self, stock_id: int) -> bool:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM watchlist_stocks WHERE id = ?", (stock_id,))
        ok = c.rowcount > 0
        conn.commit()
        conn.close()
        return ok

    def remove_stock_by_symbol(self, group_id: int, symbol: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM watchlist_stocks WHERE group_id = ? AND symbol = ?", (group_id, symbol))
        ok = c.rowcount > 0
        conn.commit()
        conn.close()
        return ok
