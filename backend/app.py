#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能选股助手 — Flask API 服务
仅提供 JSON API，前端由 Vue3 管理后台 (admin-panel) 负责。
"""

from flask import Flask, request, jsonify
import os
import json
import sqlite3
from datetime import datetime, timedelta
import threading
from dotenv import load_dotenv

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.email_config import EmailSender
from backend.daily_report_generator import DailyReportGenerator
from analysis.trading_day_scheduler import TradingDayScheduler
from stock_screener.screener import StockScreener
from stock_screener.models import ScreenerRecordManager
from stock_screener.analyzer.ai_model import get_ai_model_manager
from stock_screener.analyzer.engine import StockAnalysisEngine
from stock_screener.watchlist import WatchlistManager

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'smart-stock-assistant')


# =====================================================================
# CORS
# =====================================================================

@app.after_request
def add_cors_headers(response):
    origin = request.headers.get('Origin', '')
    if origin.startswith('http://localhost:') or origin.startswith('http://127.0.0.1:'):
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response


@app.route('/api/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    return '', 204


# =====================================================================
# 数据管理器
# =====================================================================

scheduler_instance = None
scheduler_thread = None


class WebAppManager:
    """核心数据管理器 — 操作 SQLite"""

    def __init__(self):
        self.db_path = "data/cchan_web.db"
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS stock_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL, symbol TEXT NOT NULL, stock_name TEXT,
            market TEXT, current_price REAL, total_score REAL,
            tech_score REAL, auction_score REAL, auction_ratio REAL,
            gap_type TEXT, confidence TEXT, strategy TEXT,
            entry_price REAL, stop_loss REAL, target_price REAL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        c.execute('''CREATE TABLE IF NOT EXISTS system_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_key TEXT UNIQUE NOT NULL, config_value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        c.execute('''CREATE TABLE IF NOT EXISTS system_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            level TEXT NOT NULL, message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        conn.commit()
        conn.close()

    def get_recommendations(self, date=None, limit=50):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        if date:
            c.execute('SELECT * FROM stock_recommendations WHERE date=? ORDER BY total_score DESC LIMIT ?', (date, limit))
        else:
            c.execute('SELECT * FROM stock_recommendations ORDER BY created_at DESC LIMIT ?', (limit,))
        cols = [d[0] for d in c.description]
        rows = [dict(zip(cols, r)) for r in c.fetchall()]
        conn.close()
        return rows

    def save_recommendations(self, recs, date):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('DELETE FROM stock_recommendations WHERE date=?', (date,))
        for s in recs:
            c.execute('''INSERT INTO stock_recommendations
                (date,symbol,stock_name,market,current_price,total_score,
                 tech_score,auction_score,auction_ratio,gap_type,confidence,
                 strategy,entry_price,stop_loss,target_price)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
                date, s.get('symbol'), s.get('stock_name'), s.get('market'),
                s.get('current_price'), s.get('total_score'), s.get('tech_score'),
                s.get('auction_score'), s.get('auction_ratio'), s.get('gap_type'),
                s.get('confidence'), s.get('strategy'),
                s.get('entry_price'), s.get('stop_loss'), s.get('target_price')))
        conn.commit()
        conn.close()

    def get_system_status(self):
        global scheduler_instance
        load_dotenv(override=True)
        return {
            'scheduler_running': scheduler_instance is not None and scheduler_instance.is_running,
            'today_recommendations': len(self.get_recommendations(datetime.now().strftime('%Y-%m-%d'))),
            'email_configured': all([os.getenv('SENDER_EMAIL'), os.getenv('SENDER_PASSWORD'), os.getenv('RECIPIENT_EMAILS')]),
            'last_update': self._last_update(),
            'system_health': 'good',
        }

    def _last_update(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT MAX(created_at) FROM stock_recommendations')
        r = c.fetchone()[0]
        conn.close()
        return r or '从未更新'

    def get_strategy_config(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT config_key, config_value FROM system_config WHERE config_key LIKE 'strategy_%'")
        rows = c.fetchall()
        conn.close()
        cfg = {'tech_weight': 0.65, 'auction_weight': 0.35, 'score_threshold': 0.65,
               'max_recommendations': 15, 'min_price': 2.0, 'max_price': 300.0}
        for k, v in rows:
            name = k.replace('strategy_', '')
            if name in cfg:
                try:
                    cfg[name] = float(v) if name != 'max_recommendations' else int(v)
                except ValueError:
                    pass
        return cfg

    def save_strategy_config(self, cfg):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        for k, v in cfg.items():
            c.execute('INSERT OR REPLACE INTO system_config (config_key,config_value,updated_at) VALUES (?,?,CURRENT_TIMESTAMP)',
                      (f'strategy_{k}', str(v)))
        conn.commit()
        conn.close()


web_manager = WebAppManager()


# =====================================================================
# 分析任务队列（深度分析进度）
# =====================================================================

_analysis_tasks = {}  # task_id -> {id, status, progress, total, current_stock, message, phase, result, error, created_at}
_analysis_task_lock = threading.Lock()
_analysis_task_counter = 0


def _run_analysis_task(task_id):
    """后台执行分析任务"""
    with _analysis_task_lock:
        if task_id not in _analysis_tasks:
            return
        _analysis_tasks[task_id]['status'] = 'running'

    def progress_cb(current, total, stock, msg, phase):
        with _analysis_task_lock:
            if task_id in _analysis_tasks:
                _analysis_tasks[task_id].update({
                    'progress': current,
                    'total': total,
                    'current_stock': stock,
                    'message': msg,
                    'phase': phase,
                })

    try:
        from analysis.optimized_stock_analyzer import OptimizedStockAnalyzer
        analyzer = OptimizedStockAnalyzer()
        report = analyzer.generate_optimized_recommendations(progress_callback=progress_cb)
        with _analysis_task_lock:
            if task_id in _analysis_tasks:
                if report and 'recommendations' in report:
                    recs = report['recommendations']
                    web_manager.save_recommendations(recs, report['date'])
                    _analysis_tasks[task_id].update({
                        'status': 'completed',
                        'message': f'分析完成，共 {len(recs)} 只推荐股票',
                        'result': {'count': len(recs), 'date': report['date']},
                    })
                else:
                    _analysis_tasks[task_id].update({
                        'status': 'completed',
                        'message': '分析完成但无推荐股票',
                        'result': {},
                    })
    except Exception as e:
        import traceback
        traceback.print_exc()
        with _analysis_task_lock:
            if task_id in _analysis_tasks:
                _analysis_tasks[task_id].update({
                    'status': 'failed',
                    'message': str(e),
                    'error': str(e),
                })


# =====================================================================
# 每日推荐 API
# =====================================================================

@app.route('/api/daily/status')
def api_daily_status():
    return jsonify({'success': True, 'data': web_manager.get_system_status()})


@app.route('/api/daily/recommendations')
def api_daily_recommendations():
    date_filter = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    limit = request.args.get('limit', 50, type=int)
    return jsonify({'success': True, 'data': web_manager.get_recommendations(date_filter, limit), 'date': date_filter})


@app.route('/api/daily/run_analysis', methods=['POST'])
def api_daily_run_analysis():
    """启动分析任务（异步），返回 task_id，前端轮询 /api/daily/analysis_queue 获取进度"""
    global _analysis_task_counter
    try:
        with _analysis_task_lock:
            _analysis_task_counter += 1
            task_id = f"analysis-{_analysis_task_counter}"
            _analysis_tasks[task_id] = {
                'id': task_id,
                'status': 'pending',
                'progress': 0,
                'total': 0,
                'current_stock': None,
                'message': '任务已创建，等待启动...',
                'phase': 'pending',
                'result': None,
                'error': None,
                'created_at': datetime.now().isoformat(),
            }
        t = threading.Thread(target=_run_analysis_task, args=(task_id,), daemon=True)
        t.start()
        return jsonify({
            'success': True,
            'message': '分析任务已启动',
            'data': {'task_id': task_id},
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'启动失败: {e}'})


@app.route('/api/daily/analysis_queue')
def api_daily_analysis_queue():
    """获取分析任务队列（运行中 + 最近完成的）"""
    limit = request.args.get('limit', 20, type=int)
    with _analysis_task_lock:
        tasks = list(_analysis_tasks.values())
    # 按创建时间倒序，取最近 limit 条
    tasks.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    tasks = tasks[:limit]
    return jsonify({'success': True, 'data': {'tasks': tasks}})


@app.route('/api/daily/from_screener', methods=['POST'])
def api_daily_from_screener():
    """将条件选股记录的结果设为今日推荐"""
    try:
        d = request.json or {}
        record_id = d.get('record_id')
        if not record_id:
            return jsonify({'success': False, 'message': '请指定 record_id'})
        target_date = d.get('date', datetime.now().strftime('%Y-%m-%d'))

        record = screener_record_mgr.get_record_by_id(int(record_id))
        if not record:
            return jsonify({'success': False, 'message': '选股记录不存在'})

        result_data = record.get('result_data') or []
        if not result_data:
            return jsonify({'success': False, 'message': '该记录无筛选结果'})

        web_manager.save_recommendations(result_data, target_date)
        return jsonify({
            'success': True,
            'message': f'已从「{record.get("name", "")}」导入 {len(result_data)} 只股票为 {target_date} 推荐',
            'data': {'count': len(result_data), 'date': target_date},
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/daily/update_status', methods=['POST'])
def api_daily_update_status():
    try:
        d = request.json or {}
        conn = sqlite3.connect(web_manager.db_path)
        conn.cursor().execute('UPDATE stock_recommendations SET status=? WHERE id=?', (d.get('status'), d.get('id')))
        conn.commit(); conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# =====================================================================
# 策略配置 API
# =====================================================================

@app.route('/api/strategy/config', methods=['GET'])
def api_get_strategy_config():
    return jsonify({'success': True, 'config': web_manager.get_strategy_config()})


@app.route('/api/strategy/config', methods=['POST'])
def api_save_strategy_config():
    try:
        cfg = request.json or {}
        web_manager.save_strategy_config(cfg)
        return jsonify({'success': True, 'message': '策略参数已保存'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# =====================================================================
# 调度器 API
# =====================================================================

@app.route('/api/scheduler/start', methods=['POST'])
def api_start_scheduler():
    global scheduler_instance, scheduler_thread
    try:
        if scheduler_instance and scheduler_instance.is_running:
            return jsonify({'success': False, 'message': '调度器已在运行中'})
        scheduler_instance = TradingDayScheduler()
        scheduler_thread = threading.Thread(target=scheduler_instance.start_scheduler, daemon=True)
        scheduler_thread.start()
        return jsonify({'success': True, 'message': '调度器已启动'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/scheduler/stop', methods=['POST'])
def api_stop_scheduler():
    global scheduler_instance
    try:
        if scheduler_instance:
            scheduler_instance.stop_scheduler()
            scheduler_instance = None
        return jsonify({'success': True, 'message': '调度器已停止'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# =====================================================================
# 邮件 API
# =====================================================================

@app.route('/api/email/config', methods=['GET'])
def api_get_email_config():
    load_dotenv(override=True)
    return jsonify({'success': True, 'data': {
        'sender_email': os.getenv('SENDER_EMAIL', ''),
        'recipient_emails': os.getenv('RECIPIENT_EMAILS', ''),
        'email_provider': os.getenv('EMAIL_PROVIDER', 'gmail'),
        'configured': all([os.getenv('SENDER_EMAIL'), os.getenv('SENDER_PASSWORD'), os.getenv('RECIPIENT_EMAILS')]),
    }})


@app.route('/api/email/test', methods=['POST'])
def api_test_email():
    try:
        load_dotenv(override=True)
        sender = EmailSender()
        if not sender.sender_email or not sender.sender_password:
            return jsonify({'success': False, 'message': '邮件未配置'})
        from backend.app import web_manager as wm
        recs = wm.get_recommendations(datetime.now().strftime('%Y-%m-%d'), 10)
        test_data = {'date': datetime.now().strftime('%Y-%m-%d'), 'analysis_time': datetime.now().strftime('%H:%M:%S'),
                     'recommendations': recs, 'market_summary': {'total_analyzed': 0, 'avg_score': 0}, 'auction_analysis': {}}
        ok = sender.send_daily_report(test_data)
        return jsonify({'success': ok, 'message': '发送成功' if ok else '发送失败'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# =====================================================================
# AI 模型管理 API
# =====================================================================

@app.route('/api/models/providers', methods=['GET'])
def api_models_list():
    mgr = get_ai_model_manager()
    return jsonify({'success': True, 'data': {'providers': mgr.list_providers(), 'default_provider_id': mgr._cfg.get('default_provider_id', '')}})

@app.route('/api/models/providers', methods=['POST'])
def api_models_add():
    return jsonify({'success': True, 'data': get_ai_model_manager().add_provider(request.json or {})})

@app.route('/api/models/providers/<pid>', methods=['PUT'])
def api_models_update(pid):
    p = get_ai_model_manager().update_provider(pid, request.json or {})
    return jsonify({'success': bool(p), 'data': p})

@app.route('/api/models/providers/<pid>', methods=['DELETE'])
def api_models_delete(pid):
    return jsonify({'success': get_ai_model_manager().delete_provider(pid)})

@app.route('/api/models/providers/<pid>/default', methods=['POST'])
def api_models_set_default(pid):
    get_ai_model_manager().set_default_provider(pid)
    return jsonify({'success': True})

@app.route('/api/models/providers/<pid>/test', methods=['POST'])
def api_models_test(pid):
    return jsonify(get_ai_model_manager().test_provider(pid))

@app.route('/api/models/callers', methods=['GET'])
def api_models_callers():
    return jsonify({'success': True, 'data': get_ai_model_manager().get_caller_list()})

@app.route('/api/models/callers/<cid>', methods=['PUT'])
def api_models_set_caller(cid):
    pid = (request.json or {}).get('provider_id', '')
    if pid: get_ai_model_manager().set_caller_provider(cid, pid)
    else: get_ai_model_manager().remove_caller_mapping(cid)
    return jsonify({'success': True})


# =====================================================================
# 股票分析引擎 API
# =====================================================================

_analysis_engine = StockAnalysisEngine()
_analysis_engine.load_rules()

@app.route('/api/analyzer/rules')
def api_analyzer_rules():
    return jsonify({'success': True, 'data': _analysis_engine.get_all_rules()})

@app.route('/api/analyzer/analyze', methods=['POST'])
def api_analyzer_analyze():
    try:
        d = request.json or {}
        code = d.get('stock_code', '').strip()
        if not code:
            return jsonify({'success': False, 'message': '请输入股票代码'})
        return jsonify({'success': True, 'data': _analysis_engine.analyze(code, rule_ids=d.get('rule_ids'))})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'message': f'分析失败: {e}'})


# =====================================================================
# 条件选股 API
# =====================================================================

screener_record_mgr = ScreenerRecordManager()

@app.route('/api/screener/run', methods=['POST'])
def api_screener_run():
    try:
        d = request.json or {}
        conditions = d.get('conditions', {})
        name = d.get('name', '').strip()
        preset_key = d.get('preset_key', '')
        if preset_key:
            tpl = StockScreener.PRESET_TEMPLATES.get(preset_key)
            if tpl:
                conditions = tpl['conditions']
                if not name: name = tpl['name']
        if not name: name = f"选股 {datetime.now().strftime('%m-%d %H:%M')}"

        today = datetime.now().strftime('%Y-%m-%d')
        pool = web_manager.get_recommendations(today, limit=200)
        if not pool:
            try:
                from analysis.optimized_stock_analyzer import OptimizedStockAnalyzer
                report = OptimizedStockAnalyzer().generate_optimized_recommendations()
                if report and 'recommendations' in report:
                    pool = report['recommendations']
                    web_manager.save_recommendations(pool, today)
            except Exception:
                pass
        if not pool:
            return jsonify({'success': False, 'message': '没有可用的股票数据，请先运行"立即分析"'})

        results = StockScreener().screen(pool, conditions)
        save_cond = dict(conditions)
        if preset_key: save_cond['_preset_key'] = preset_key
        rid = screener_record_mgr.save_record(name, save_cond, results)
        return jsonify({'success': True, 'message': f'筛选完成，共 {len(results)} 只', 'data': {'record_id': rid, 'total': len(results), 'stocks': results}})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/screener/presets')
def api_screener_presets():
    return jsonify({'success': True, 'data': StockScreener.get_preset_list()})

@app.route('/api/screener/records')
def api_screener_records():
    return jsonify({'success': True, 'data': screener_record_mgr.get_records(request.args.get('limit', 20, type=int))})

@app.route('/api/screener/records/<int:rid>', methods=['GET'])
def api_screener_record_detail(rid):
    r = screener_record_mgr.get_record_by_id(rid)
    return jsonify({'success': bool(r), 'data': r} if r else {'success': False, 'message': '记录不存在'})

@app.route('/api/screener/records/<int:rid>', methods=['DELETE'])
def api_screener_record_delete(rid):
    return jsonify({'success': screener_record_mgr.delete_record(rid)})


# =====================================================================
# 自选股 API
# =====================================================================

_watchlist_mgr = WatchlistManager()

@app.route('/api/watchlist/groups', methods=['GET'])
def api_watchlist_groups():
    return jsonify({'success': True, 'data': _watchlist_mgr.list_groups()})

@app.route('/api/watchlist/groups', methods=['POST'])
def api_watchlist_add_group():
    name = (request.json or {}).get('name', '').strip() or '新分组'
    return jsonify({'success': True, 'data': _watchlist_mgr.add_group(name)})

@app.route('/api/watchlist/groups/<int:gid>', methods=['PUT'])
def api_watchlist_rename(gid):
    name = (request.json or {}).get('name', '').strip()
    if not name: return jsonify({'success': False, 'message': '名称不能为空'})
    return jsonify({'success': _watchlist_mgr.rename_group(gid, name)})

@app.route('/api/watchlist/groups/<int:gid>', methods=['DELETE'])
def api_watchlist_delete_group(gid):
    return jsonify({'success': _watchlist_mgr.delete_group(gid)})

@app.route('/api/watchlist/groups/<int:gid>/stocks', methods=['GET'])
def api_watchlist_stocks(gid):
    return jsonify({'success': True, 'data': _watchlist_mgr.list_stocks(gid)})

@app.route('/api/watchlist/groups/<int:gid>/stocks', methods=['POST'])
def api_watchlist_add_stock(gid):
    d = request.json or {}
    r = _watchlist_mgr.add_stock(gid, d.get('symbol', ''), d.get('stock_name', ''), d.get('market', ''), d.get('note', ''))
    if 'error' in r: return jsonify({'success': False, 'message': r['message']})
    return jsonify({'success': True, 'data': r})

@app.route('/api/watchlist/stocks/<int:sid>', methods=['DELETE'])
def api_watchlist_remove_stock(sid):
    return jsonify({'success': _watchlist_mgr.remove_stock(sid)})

@app.route('/api/watchlist/quotes', methods=['POST'])
def api_watchlist_quotes():
    try:
        from stock_screener.realtime_quote import fetch_realtime_quotes
        symbols = (request.json or {}).get('symbols', [])
        if not symbols: return jsonify({'success': True, 'data': {}})
        return jsonify({'success': True, 'data': fetch_realtime_quotes(symbols)})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# =====================================================================
# 健康检查
# =====================================================================

@app.route('/health')
def health():
    return 'ok', 200


# =====================================================================
# 启动
# =====================================================================

if __name__ == '__main__':
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    os.makedirs(data_dir, exist_ok=True)
    print("🚀 智能选股助手 API 服务启动中...")
    print("🌐 API 地址: http://localhost:8080")
    print("🛑 停止服务: Ctrl+C")
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
