# -*- coding: utf-8 -*-
"""
SQLAlchemy Declarative 模型：与 data/cchan_web.db 表结构一致。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.db import Base


# ---------------------------------------------------------------------------
# 推荐与运行记录（backend/app.py）
# ---------------------------------------------------------------------------


class StockRecommendation(Base):
    """每日推荐股票记录。"""

    __tablename__ = "stock_recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    stock_name = Column(String)
    market = Column(String)
    current_price = Column(Float)
    total_score = Column(Float)
    tech_score = Column(Float)
    auction_score = Column(Float)
    auction_ratio = Column(Float)
    gap_type = Column(String)
    confidence = Column(String)
    strategy = Column(String)
    entry_price = Column(Float)
    stop_loss = Column(Float)
    target_price = Column(Float)
    status = Column(String, default="pending")
    created_at = Column(DateTime, server_default=func.current_timestamp())

    def to_dict(self) -> Dict[str, Any]:
        """转为字典，与原有 cursor 返回格式兼容。"""
        return {
            "id": self.id,
            "date": self.date,
            "symbol": self.symbol,
            "stock_name": self.stock_name,
            "market": self.market,
            "current_price": self.current_price,
            "total_score": self.total_score,
            "tech_score": self.tech_score,
            "auction_score": self.auction_score,
            "auction_ratio": self.auction_ratio,
            "gap_type": self.gap_type,
            "confidence": self.confidence,
            "strategy": self.strategy,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "target_price": self.target_price,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SystemConfig(Base):
    """系统配置键值（如 strategy_*）。"""

    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_key = Column(String, unique=True, nullable=False)
    config_value = Column(String)
    updated_at = Column(DateTime, server_default=func.current_timestamp())


class SystemLog(Base):
    """系统日志（当前仅建表，未使用）。"""

    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    level = Column(String, nullable=False)
    message = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.current_timestamp())


class AnalysisRun(Base):
    """分析任务运行记录。"""

    __tablename__ = "analysis_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String, nullable=False)
    status = Column(String, nullable=False)
    started_at = Column(String)
    finished_at = Column(String)
    result_count = Column(Integer)
    result_date = Column(String)
    error_message = Column(String)
    created_at = Column(DateTime, server_default=func.current_timestamp())

    def to_dict(self) -> Dict[str, Any]:
        """转为字典。"""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "result_count": self.result_count,
            "result_date": self.result_date,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# 选股记录与模板（stock_screener/models.py）
# ---------------------------------------------------------------------------


class ScreenerRecord(Base):
    """选股记录（条件 + 结果摘要 + 完整 result_data）。"""

    __tablename__ = "screener_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    conditions = Column(Text, nullable=False)  # JSON
    result_count = Column(Integer, default=0)
    result_symbols = Column(Text)  # JSON list
    result_summary = Column(Text)  # JSON
    result_data = Column(Text)  # JSON
    preset_key = Column(String)
    created_at = Column(DateTime, server_default=func.current_timestamp())


class ScreenerTemplate(Base):
    """选股模板（仅条件，不存结果）。"""

    __tablename__ = "screener_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(String)
    conditions = Column(Text, nullable=False)  # JSON
    created_at = Column(DateTime, server_default=func.current_timestamp())


# ---------------------------------------------------------------------------
# 自选股（stock_screener/watchlist.py）
# ---------------------------------------------------------------------------


class WatchlistGroup(Base):
    """自选分组。"""

    __tablename__ = "watchlist_groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.current_timestamp())

    stocks = relationship(
        "WatchlistStock",
        back_populates="group",
        cascade="all, delete-orphan",
        foreign_keys="WatchlistStock.group_id",
    )


class WatchlistStock(Base):
    """自选股；同一分组内 symbol 唯一。"""

    __tablename__ = "watchlist_stocks"
    __table_args__ = (
        UniqueConstraint("group_id", "symbol", name="uq_watchlist_stocks_group_symbol"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(
        Integer,
        ForeignKey("watchlist_groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    symbol = Column(String, nullable=False)
    stock_name = Column(String)
    market = Column(String)
    note = Column(String, default="")
    added_at = Column(DateTime, server_default=func.current_timestamp())

    group = relationship("WatchlistGroup", back_populates="stocks", foreign_keys=[group_id])


# ---------------------------------------------------------------------------
# 深度分析（analysis/deep_stock_analyzer.py）
# ---------------------------------------------------------------------------


class DeepAnalysis(Base):
    """深度分析结果（按 symbol + analysis_date 可做 upsert）。"""

    __tablename__ = "deep_analysis"
    __table_args__ = (
        UniqueConstraint("symbol", "analysis_date", name="uq_deep_analysis_symbol_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String, nullable=False)
    stock_name = Column(String)
    analysis_date = Column(String)
    # 基础数据
    current_price = Column(Float)
    price_change_pct = Column(Float)
    volume_ratio = Column(Float)
    market_cap_billion = Column(Float)
    # 技术指标
    rsi_14 = Column(Float)
    macd_signal = Column(String)
    ma5 = Column(Float)
    ma10 = Column(Float)
    ma20 = Column(Float)
    ma60 = Column(Float)
    bollinger_position = Column(Float)
    # 资金流向
    main_inflow = Column(Float)
    retail_inflow = Column(Float)
    institutional_inflow = Column(Float)
    net_inflow = Column(Float)
    # 竞价
    auction_ratio = Column(Float)
    auction_volume_ratio = Column(Float)
    gap_type = Column(String)
    # LLM 分析
    llm_analysis_text = Column(Text)
    investment_rating = Column(String)
    confidence_level = Column(String)
    risk_assessment = Column(String)
    # 投资建议
    buy_point = Column(String)
    sell_point = Column(String)
    stop_loss_price = Column(Float)
    target_price = Column(Float)
    expected_return_pct = Column(Float)
    holding_period_days = Column(Integer)
    position_suggestion = Column(Float)
    # 评分
    technical_score = Column(Float)
    fundamental_score = Column(Float)
    sentiment_score = Column(Float)
    total_score = Column(Float)
    created_at = Column(DateTime, server_default=func.current_timestamp())


# ---------------------------------------------------------------------------
# 分析解释与迷你价格（analysis/optimized_stock_analyzer.py 写入）
# ---------------------------------------------------------------------------


class StockAnalysis(Base):
    """单只股票分析结果（explain_html、mini_prices）；按 symbol+date 可替换。"""

    __tablename__ = "stock_analysis"
    __table_args__ = (
        UniqueConstraint("symbol", "analysis_date", name="uq_stock_analysis_symbol_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String, nullable=False)
    stock_name = Column(String)
    analysis_date = Column(String)
    total_score = Column(Float)
    tech_score = Column(Float)
    auction_score = Column(Float)
    confidence = Column(String)
    entry_price = Column(Float)
    stop_loss = Column(Float)
    target_price = Column(Float)
    explanation = Column(Text)
    explain_html = Column(Text)
    mini_prices = Column(Text)  # JSON
    created_at = Column(DateTime, server_default=func.current_timestamp())
