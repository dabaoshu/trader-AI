# -*- coding: utf-8 -*-
"""
统一 SQLAlchemy 引擎与 Session，连接 data/cchan_web.db。
"""

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

# 默认使用项目根下的 data/cchan_web.db（与原有 sqlite3 路径一致）
_DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "cchan_web.db",
)
DB_PATH = os.environ.get("CCHAN_WEB_DB_PATH", _DEFAULT_DB_PATH)
SQLALCHEMY_DATABASE_URI = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URI,
    connect_args={"check_same_thread": False},
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_session() -> Generator[Session, None, None]:
    """获取数据库 Session，用于 with 或依赖注入。"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session_context() -> Session:
    """
    获取一个 Session 实例，调用方负责 commit/rollback/close。
    用于在单次请求内多次操作后统一提交。
    """
    return SessionLocal()


def init_db() -> None:
    """创建所有表（等价于原有 CREATE TABLE IF NOT EXISTS）。"""
    from models import schema  # noqa: F401  # 确保所有模型已注册到 Base.metadata

    Base.metadata.create_all(bind=engine)
