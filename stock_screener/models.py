#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
条件选股记录持久化管理

使用 models 包中的 SQLAlchemy ORM（ScreenerRecord、ScreenerTemplate）与 Session。
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from models import ScreenerRecord, ScreenerTemplate, get_session_context


def _row_to_record_dict(
    r: ScreenerRecord,
    *,
    include_result_data: bool = False,
) -> Dict[str, Any]:
    """将 ORM 行转为原有 API 格式（含 JSON 反序列化）。"""
    out = {
        "id": r.id,
        "name": r.name,
        "conditions": json.loads(r.conditions) if r.conditions else {},
        "result_count": r.result_count,
        "result_symbols": json.loads(r.result_symbols) if r.result_symbols else [],
        "result_summary": json.loads(r.result_summary) if r.result_summary else {},
        "preset_key": r.preset_key or "",
        "created_at": r.created_at.isoformat() if getattr(r.created_at, "isoformat", None) else str(r.created_at),
    }
    if include_result_data:
        out["result_data"] = json.loads(r.result_data) if r.result_data else []
    return out


class ScreenerRecordManager:
    """选股记录管理器（基于 SQLAlchemy ORM）"""

    def __init__(self, db_path: str = "data/cchan_web.db"):
        """保留 db_path 参数以兼容调用方，实际使用 models 统一连接。"""
        self._db_path = db_path

    def save_record(self, name: str, conditions: Dict, results: List[Dict]) -> int:
        """
        保存一条选股记录（包含完整的条件和结果数据）

        @param name - 记录名称
        @param conditions - 筛选条件
        @param results - 符合条件的股票列表
        @returns 新记录 id
        """
        symbols = [s.get("symbol", "") for s in results]
        summary = self._build_summary(results)
        full_data = self._serialize_results(results)
        session = get_session_context()
        try:
            rec = ScreenerRecord(
                name=name,
                conditions=json.dumps(conditions, ensure_ascii=False),
                result_count=len(results),
                result_symbols=json.dumps(symbols, ensure_ascii=False),
                result_summary=json.dumps(summary, ensure_ascii=False),
                result_data=json.dumps(full_data, ensure_ascii=False),
                preset_key=conditions.get("_preset_key", ""),
            )
            session.add(rec)
            session.commit()
            return rec.id
        finally:
            session.close()

    def get_records(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取历史选股记录（列表不含完整 result_data 以节省带宽）

        @param limit - 最大返回条数
        @returns 记录列表，按创建时间降序
        """
        session = get_session_context()
        try:
            rows = (
                session.query(ScreenerRecord)
                .order_by(ScreenerRecord.created_at.desc())
                .limit(limit)
                .all()
            )
            return [_row_to_record_dict(r, include_result_data=False) for r in rows]
        finally:
            session.close()

    def get_record_by_id(self, record_id: int) -> Optional[Dict[str, Any]]:
        """
        按 id 获取单条记录（包含完整 result_data）

        @param record_id - 记录 id
        @returns 记录字典或 None
        """
        session = get_session_context()
        try:
            r = session.query(ScreenerRecord).filter(ScreenerRecord.id == record_id).first()
            if not r:
                return None
            return _row_to_record_dict(r, include_result_data=True)
        finally:
            session.close()

    def delete_record(self, record_id: int) -> bool:
        """
        删除一条选股记录

        @param record_id - 记录 id
        @returns 是否删除成功
        """
        session = get_session_context()
        try:
            affected = session.query(ScreenerRecord).filter(ScreenerRecord.id == record_id).delete()
            session.commit()
            return affected > 0
        finally:
            session.close()

    @staticmethod
    def _serialize_results(results: List[Dict]) -> List[Dict]:
        """序列化完整的筛选结果用于持久化。"""
        keep_keys = [
            "symbol", "stock_name", "market", "current_price",
            "total_score", "tech_score", "auction_score",
            "auction_ratio", "gap_type", "confidence",
            "strategy", "entry_price", "stop_loss", "target_price",
            "rsi", "market_cap_billion",
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
    def _build_summary(results: List[Dict]) -> Dict:
        """从筛选结果中提取统计摘要"""
        if not results:
            return {
                "count": 0,
                "avg_score": 0,
                "high_confidence_count": 0,
                "markets": [],
                "price_range": [0, 0],
                "top_stocks": [],
            }
        scores = [s.get("total_score", 0) for s in results]
        prices = [s.get("current_price", 0) for s in results]
        markets = list({s.get("market", "") for s in results})
        high_conf = [s for s in results if s.get("confidence") == "very_high"]
        top_stocks = sorted(results, key=lambda x: x.get("total_score", 0), reverse=True)[:5]
        top_list = [
            {
                "symbol": s.get("symbol", ""),
                "stock_name": s.get("stock_name", ""),
                "total_score": round(s.get("total_score", 0), 3),
                "current_price": s.get("current_price", 0),
                "confidence": s.get("confidence", ""),
            }
            for s in top_stocks
        ]
        return {
            "count": len(results),
            "avg_score": round(sum(scores) / len(scores), 3) if scores else 0,
            "high_confidence_count": len(high_conf),
            "markets": markets,
            "price_range": [round(min(prices), 2), round(max(prices), 2)] if prices else [0, 0],
            "top_stocks": top_list,
        }


class ScreenerTemplateManager:
    """用户自定义选股模板（保存/加载条件，不存结果），基于 SQLAlchemy ORM"""

    def __init__(self, db_path: str = "data/cchan_web.db"):
        """保留 db_path 参数以兼容调用方。"""
        self._db_path = db_path

    def list_templates(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取模板列表，按创建时间降序"""
        session = get_session_context()
        try:
            rows = (
                session.query(ScreenerTemplate)
                .order_by(ScreenerTemplate.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": r.id,
                    "name": r.name,
                    "description": r.description or "",
                    "conditions": json.loads(r.conditions) if r.conditions else {},
                    "created_at": r.created_at.isoformat() if getattr(r.created_at, "isoformat", None) else str(r.created_at),
                }
                for r in rows
            ]
        finally:
            session.close()

    def add_template(self, name: str, conditions: Dict, description: Optional[str] = None) -> int:
        """创建模板，返回新记录 id"""
        session = get_session_context()
        try:
            t = ScreenerTemplate(
                name=name,
                description=description or "",
                conditions=json.dumps(conditions, ensure_ascii=False),
            )
            session.add(t)
            session.commit()
            return t.id
        finally:
            session.close()

    def get_template(self, template_id: int) -> Optional[Dict[str, Any]]:
        """按 id 获取单条模板"""
        session = get_session_context()
        try:
            r = session.query(ScreenerTemplate).filter(ScreenerTemplate.id == template_id).first()
            if not r:
                return None
            return {
                "id": r.id,
                "name": r.name,
                "description": r.description or "",
                "conditions": json.loads(r.conditions) if r.conditions else {},
                "created_at": r.created_at.isoformat() if getattr(r.created_at, "isoformat", None) else str(r.created_at),
            }
        finally:
            session.close()

    def delete_template(self, template_id: int) -> bool:
        """删除模板，返回是否删除成功"""
        session = get_session_context()
        try:
            affected = session.query(ScreenerTemplate).filter(ScreenerTemplate.id == template_id).delete()
            session.commit()
            return affected > 0
        finally:
            session.close()
