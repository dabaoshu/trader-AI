# -*- coding: utf-8 -*-
"""
项目统一配置入口，供 data_provider、backend 等使用。

参考 daily_stock_analysis 的 config 实现：
- 使用单例模式管理全局配置
- 从 .env 文件加载（setup_env）
- 提供类型明确的配置访问（dataclass + get_config）
"""

import os
from pathlib import Path
from typing import ClassVar, Optional

from dataclasses import dataclass


def setup_env(override: bool = False) -> None:
    """
    从 .env 文件加载环境变量。

    Args:
        override: 为 True 时用 .env 的值覆盖已存在的环境变量；
                  默认 False，保持系统环境变量优先。
    """
    try:
        from dotenv import load_dotenv
    except Exception:
        return
    env_file = os.getenv("ENV_FILE")
    if env_file:
        env_path = Path(env_file)
    else:
        # config/__init__.py -> config/ -> 项目根目录
        env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=env_path, override=override)


@dataclass
class Config:
    """
    系统配置类（单例）。

    仅包含本项目与 data_provider 所需项，与 config/config.py 中
    实时行情相关字段语义一致，便于后续扩展或对齐 daily_stock_analysis。
    """

    # === 数据源 API Token ===
    tushare_token: str = ""

    # === 实时行情与增强数据（与 config/config.py 对齐）===
    enable_realtime_quote: bool = True
    realtime_source_priority: str = "efinance,akshare_em,akshare_sina,akshare_qq,tushare"
    enable_chip_distribution: bool = True
    enable_eastmoney_patch: bool = False

    # 单例实例（类变量，不参与 dataclass 构造）
    _instance: ClassVar[Optional["Config"]] = None

    @classmethod
    def get_instance(cls) -> "Config":
        """
        获取配置单例。
        首次调用时从环境变量加载，之后返回同一实例。
        """
        if cls._instance is None:
            cls._instance = cls._load_from_env()
        return cls._instance

    @classmethod
    def _load_from_env(cls) -> "Config":
        """从 .env / 环境变量加载配置。"""
        setup_env()

        def _bool(key: str, default: bool = True) -> bool:
            v = (os.getenv(key) or "").strip().lower()
            if not v:
                return default
            return v in ("1", "true", "yes", "on")

        def _str(key: str, default: str = "") -> str:
            return (os.getenv(key) or default).strip()

        # 与 config/config.py 一致：有 TUSHARE_TOKEN 时可自动注入 tushare 到优先级
        realtime_priority = _str("REALTIME_SOURCE_PRIORITY")
        if not realtime_priority:
            tushare_token = _str("TUSHARE_TOKEN")
            if tushare_token:
                realtime_priority = "tushare,efinance,akshare_em,akshare_sina,akshare_qq"
            else:
                realtime_priority = "efinance,akshare_em,akshare_sina,akshare_qq,tushare"

        return cls(
            tushare_token=_str("TUSHARE_TOKEN"),
            enable_realtime_quote=_bool("ENABLE_REALTIME_QUOTE", True),
            realtime_source_priority=realtime_priority,
            enable_chip_distribution=_bool("ENABLE_CHIP_DISTRIBUTION", True),
            enable_eastmoney_patch=_bool("ENABLE_EASTMONEY_PATCH", False),
        )

    @classmethod
    def reset_instance(cls) -> None:
        """重置单例（主要用于测试）。"""
        cls._instance = None


def get_config() -> Config:
    """获取全局配置实例的快捷方式。"""
    return Config.get_instance()
