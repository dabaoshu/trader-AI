#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自选股管理模块

支持多分组（tab），每个分组可重命名，股票可增删查。
使用 models 包中的 SQLAlchemy ORM（WatchlistGroup、WatchlistStock）与 Session。
"""

from typing import Dict, List

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from models import WatchlistGroup, WatchlistStock, get_session_context, init_db


def _group_to_dict(g: WatchlistGroup, stock_count: int = 0) -> Dict:
    """将 WatchlistGroup 转为 API 字典。"""
    return {
        "id": g.id,
        "name": g.name,
        "sort_order": g.sort_order,
        "created_at": g.created_at.isoformat() if getattr(g.created_at, "isoformat", None) else str(g.created_at),
        "stock_count": stock_count,
    }


def _stock_to_dict(s: WatchlistStock) -> Dict:
    """将 WatchlistStock 转为 API 字典。"""
    return {
        "id": s.id,
        "group_id": s.group_id,
        "symbol": s.symbol,
        "stock_name": s.stock_name or "",
        "market": s.market or "",
        "note": s.note or "",
        "added_at": s.added_at.isoformat() if getattr(s.added_at, "isoformat", None) else str(s.added_at),
    }


class WatchlistManager:
    """自选股管理器（基于 SQLAlchemy ORM）"""

    def __init__(self, db_path: str = "data/cchan_web.db"):
        """保留 db_path 以兼容调用方；表结构由 models.init_db 创建。"""
        self._db_path = db_path
        init_db()
        self._ensure_default_groups()

    def _ensure_default_groups(self) -> None:
        """保证至少有一个默认分组和「持有股」分组。"""
        session = get_session_context()
        try:
            count = session.query(func.count(WatchlistGroup.id)).scalar() or 0
            if count == 0:
                session.add(WatchlistGroup(name="默认自选", sort_order=0))
            if not session.query(WatchlistGroup).filter(WatchlistGroup.name == "持有股").first():
                session.add(WatchlistGroup(name="持有股", sort_order=-1))
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_groups(self) -> List[Dict]:
        session = get_session_context()
        try:
            groups = (
                session.query(WatchlistGroup)
                .order_by(WatchlistGroup.sort_order.asc(), WatchlistGroup.id.asc())
                .all()
            )
            result = []
            for g in groups:
                cnt = session.query(func.count(WatchlistStock.id)).filter(WatchlistStock.group_id == g.id).scalar() or 0
                result.append(_group_to_dict(g, stock_count=cnt))
            return result
        finally:
            session.close()

    def add_group(self, name: str) -> Dict:
        session = get_session_context()
        try:
            next_order = (
                session.query(func.coalesce(func.max(WatchlistGroup.sort_order), 0) + 1).scalar()
                or 1
            )
            g = WatchlistGroup(name=name, sort_order=next_order)
            session.add(g)
            session.commit()
            return _group_to_dict(g, stock_count=0)
        finally:
            session.close()

    def rename_group(self, group_id: int, name: str) -> bool:
        session = get_session_context()
        try:
            g = session.query(WatchlistGroup).filter(WatchlistGroup.id == group_id).first()
            if g:
                g.name = name
                session.commit()
                return True
            return False
        finally:
            session.close()

    def delete_group(self, group_id: int) -> bool:
        session = get_session_context()
        try:
            g = session.query(WatchlistGroup).filter(WatchlistGroup.id == group_id).first()
            if not g:
                return False
            if g.name == "持有股":
                return False
            session.delete(g)  # CASCADE 会删除 watchlist_stocks
            session.commit()
            return True
        finally:
            session.close()

    def list_stocks(self, group_id: int) -> List[Dict]:
        session = get_session_context()
        try:
            rows = (
                session.query(WatchlistStock)
                .filter(WatchlistStock.group_id == group_id)
                .order_by(WatchlistStock.added_at.desc())
                .all()
            )
            return [_stock_to_dict(s) for s in rows]
        finally:
            session.close()

    def add_stock(
        self,
        group_id: int,
        symbol: str,
        stock_name: str = "",
        market: str = "",
        note: str = "",
    ) -> Dict:
        session = get_session_context()
        try:
            s = WatchlistStock(
                group_id=group_id,
                symbol=symbol,
                stock_name=stock_name or "",
                market=market or "",
                note=note or "",
            )
            session.add(s)
            session.commit()
            return _stock_to_dict(s)
        except IntegrityError:
            session.rollback()
            return {"error": "duplicate", "message": f"{symbol} 已在该分组中"}
        finally:
            session.close()

    def remove_stock(self, stock_id: int) -> bool:
        session = get_session_context()
        try:
            affected = session.query(WatchlistStock).filter(WatchlistStock.id == stock_id).delete()
            session.commit()
            return affected > 0
        finally:
            session.close()

    def remove_stock_by_symbol(self, group_id: int, symbol: str) -> bool:
        session = get_session_context()
        try:
            affected = (
                session.query(WatchlistStock)
                .filter(WatchlistStock.group_id == group_id, WatchlistStock.symbol == symbol)
                .delete()
            )
            session.commit()
            return affected > 0
        finally:
            session.close()
