#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票分析服务 — 解耦分析逻辑，支持异步执行、进度回写与日志记录。
"""

import os
import logging
from datetime import datetime
from typing import Callable, Optional

# 分析日志：写入 data/analysis.log
_log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data')
os.makedirs(_log_dir, exist_ok=True)
_log_file = os.path.join(_log_dir, 'analysis.log')

_logger = logging.getLogger('stock_analysis')
_logger.setLevel(logging.INFO)
if not _logger.handlers:
    _fh = logging.FileHandler(_log_file, encoding='utf-8')
    _fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    _logger.addHandler(_fh)


class StockAnalysisService:
    """
    负责执行股票分析：在后台线程中调用 OptimizedStockAnalyzer，
    通过 progress_callback 将进度写回任务状态，并写分析日志。
    支持并行：每个任务在独立线程中运行，可同时存在多个分析任务。
    """

    def run_analysis(
        self,
        task_id: str,
        state_updater: Callable[..., None],
        save_recommendations_fn: Callable,
        on_finish: Optional[Callable[..., None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None,
    ) -> None:
        """
        在当前线程内执行一次分析（由 app.py 在 daemon 线程中调用）。
        通过 state_updater(**kwargs) 更新任务状态，供 /api/daily/analysis_queue 返回。
        结束时调用 on_finish 写入分析历史。支持通过 is_cancelled 中止分析。

        :param task_id: 任务 ID，用于日志
        :param state_updater: 更新函数，调用方加锁后更新 _analysis_tasks[task_id]；签名为 (**kwargs) -> None
        :param save_recommendations_fn: (recs: list, date: str) -> None，保存推荐结果
        :param on_finish: (status, finished_at, result_count, result_date, error_message) -> None，结束时写入历史
        :param is_cancelled: () -> bool，返回 True 时分析循环会中止并标记为 cancelled
        """
        state_updater(status='running')
        if on_finish:
            on_finish('running', '', result_count=None, result_date=None, error_message=None)

        def progress_cb(current: int, total: int, stock: Optional[dict], msg: str, phase: str = 'analyzing'):
            state_updater(progress=current, total=total, current_stock=stock, message=msg, phase=phase)
            _logger.info("[%s] %s | %s/%s | %s", task_id, phase, current, total, msg)

        _logger.info("[%s] 分析任务开始", task_id)
        finished_at = None
        try:
            from analysis.optimized_stock_analyzer import OptimizedStockAnalyzer
            analyzer = OptimizedStockAnalyzer()
            report = analyzer.generate_optimized_recommendations(
                progress_callback=progress_cb,
                is_cancelled=is_cancelled,
            )

            if report and report.get('cancelled'):
                state_updater(status='cancelled', message='已停止分析')
                _logger.info("[%s] 分析已停止", task_id)
                finished_at = datetime.now().isoformat()
                recs = report.get('recommendations') or []
                if on_finish:
                    on_finish('cancelled', finished_at, result_count=len(recs), result_date=report.get('date', ''), error_message=None)
                return

            if report and report.get('recommendations'):
                recs = report['recommendations']
                date_str = report.get('date', '')
                save_recommendations_fn(recs, date_str)
                state_updater(status='completed', message=f'分析完成，共 {len(recs)} 只推荐股票',
                              result={'count': len(recs), 'date': date_str})
                _logger.info("[%s] 分析完成，推荐 %s 只，日期 %s", task_id, len(recs), date_str)
                finished_at = datetime.now().isoformat()
                if on_finish:
                    on_finish('completed', finished_at, result_count=len(recs), result_date=date_str, error_message=None)
            else:
                state_updater(status='completed', message='分析完成但无推荐股票', result={})
                _logger.info("[%s] 分析完成，无推荐股票", task_id)
                finished_at = datetime.now().isoformat()
                if on_finish:
                    on_finish('completed', finished_at, result_count=0, result_date='', error_message=None)
        except Exception as e:
            _logger.exception("[%s] 分析失败: %s", task_id, e)
            state_updater(status='failed', message=str(e), error=str(e))
            finished_at = datetime.now().isoformat()
            if on_finish:
                on_finish('failed', finished_at, result_count=None, result_date=None, error_message=str(e))
