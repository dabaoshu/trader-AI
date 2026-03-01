# 项目数据库表设计（data/cchan_web.db）

本文档描述智能选股助手使用的 SQLite 库 `data/cchan_web.db` 的表结构，与 `models/schema.py` 中的 SQLAlchemy 模型一一对应。

---

## 表关联关系

### 外键关联（数据库层）

当前库中**仅有一组表间外键**：

| 主表 | 从表 | 外键 | 说明 |
|------|------|------|------|
| **watchlist_groups** | **watchlist_stocks** | `watchlist_stocks.group_id` → `watchlist_groups.id` | 一个分组下有多只自选股；删除分组时级联删除该分组下所有股票（ON DELETE CASCADE）。同一分组内 `(group_id, symbol)` 唯一。 |

- **watchlist_groups**（1）───< **watchlist_stocks**（N）：一对多；ORM 中 `WatchlistGroup.stocks`、`WatchlistStock.group` 互为 `relationship`。

### 独立表（无外键）

以下表之间**无数据库外键**，彼此独立存储：

| 表名 | 说明 |
|------|------|
| stock_recommendations | 按日期、股票存储每日推荐，无引用其他表。 |
| system_config | 键值配置，无引用。 |
| system_logs | 日志，无引用。 |
| analysis_runs | 分析任务运行记录，无引用。 |
| screener_records | 选股记录（含条件与结果 JSON），无引用。 |
| screener_templates | 选股模板（仅条件 JSON），无引用。 |
| deep_analysis | 深度分析结果，按 `(symbol, analysis_date)` 唯一，无引用。 |
| stock_analysis | 单只股票分析解释（explain_html / mini_prices），按 `(symbol, analysis_date)` 唯一，无引用。 |

### 业务上的逻辑关联（应用层）

- **stock_recommendations**、**stock_analysis**、**deep_analysis** 均以 `symbol`（及可选 `date` / `analysis_date`）表示同一只股票在不同功能下的数据，在应用层通过 `symbol`、日期做关联或汇总，不在库中建外键。
- **screener_records** 与 **screener_templates** 结构相似（都含 `conditions` JSON），模板用于“保存/加载条件”，记录用于“条件+结果快照”，二者无主外键关系。

---

## 1. stock_recommendations（每日推荐）

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| date | TEXT | NOT NULL | 推荐日期 |
| symbol | TEXT | NOT NULL | 股票代码 |
| stock_name | TEXT | | 股票名称 |
| market | TEXT | | 市场 |
| current_price | REAL | | 当前价 |
| total_score | REAL | | 综合得分 |
| tech_score | REAL | | 技术面得分 |
| auction_score | REAL | | 竞价得分 |
| auction_ratio | REAL | | 竞价比例 |
| gap_type | TEXT | | 缺口类型 |
| confidence | TEXT | | 信心等级 |
| strategy | TEXT | | 策略 |
| entry_price | REAL | | 建议入场价 |
| stop_loss | REAL | | 止损价 |
| target_price | REAL | | 目标价 |
| status | TEXT | DEFAULT 'pending' | 状态 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**使用位置**: `backend/app.py`（WebAppManager）

---

## 2. system_config（系统配置）

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| config_key | TEXT | UNIQUE, NOT NULL | 配置键（如 strategy_*） |
| config_value | TEXT | | 配置值 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**使用位置**: `backend/app.py`（策略配置）、`analysis/optimized_stock_analyzer.py`（读取策略）

---

## 3. system_logs（系统日志）

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| level | TEXT | NOT NULL | 日志级别 |
| message | TEXT | NOT NULL | 消息内容 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**使用位置**: 当前仅建表，未使用；保留供后续打点。

---

## 4. analysis_runs（分析任务运行记录）

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| task_id | TEXT | NOT NULL | 任务 ID |
| status | TEXT | NOT NULL | 状态 |
| started_at | TEXT | | 开始时间 |
| finished_at | TEXT | | 结束时间 |
| result_count | INTEGER | | 结果数量 |
| result_date | TEXT | | 结果日期 |
| error_message | TEXT | | 错误信息 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**使用位置**: `backend/app.py`（分析历史）

---

## 5. screener_records（选股记录）

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| name | TEXT | NOT NULL | 记录名称 |
| conditions | TEXT | NOT NULL | 筛选条件（JSON） |
| result_count | INTEGER | DEFAULT 0 | 结果数量 |
| result_symbols | TEXT | | 结果代码列表（JSON） |
| result_summary | TEXT | | 结果摘要（JSON） |
| result_data | TEXT | | 完整结果数据（JSON） |
| preset_key | TEXT | | 预设键 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**使用位置**: `stock_screener/models.py`（ScreenerRecordManager）

---

## 6. screener_templates（选股模板）

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| name | TEXT | NOT NULL | 模板名称 |
| description | TEXT | | 描述 |
| conditions | TEXT | NOT NULL | 条件（JSON） |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**使用位置**: `stock_screener/models.py`（ScreenerTemplateManager）

---

## 7. watchlist_groups（自选分组）

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| name | TEXT | NOT NULL | 分组名称 |
| sort_order | INTEGER | DEFAULT 0 | 排序 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**使用位置**: `stock_screener/watchlist.py`（WatchlistManager）

---

## 8. watchlist_stocks（自选股）

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| group_id | INTEGER | NOT NULL, FK → watchlist_groups.id ON DELETE CASCADE | 分组 ID |
| symbol | TEXT | NOT NULL | 股票代码 |
| stock_name | TEXT | | 股票名称 |
| market | TEXT | | 市场 |
| note | TEXT | DEFAULT '' | 备注 |
| added_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 添加时间 |

**唯一约束**: (group_id, symbol)

**使用位置**: `stock_screener/watchlist.py`（WatchlistManager）

---

## 9. deep_analysis（深度分析结果）

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| symbol | TEXT | NOT NULL | 股票代码 |
| stock_name | TEXT | | 股票名称 |
| analysis_date | TEXT | | 分析日期 |
| current_price | REAL | | 当前价 |
| price_change_pct | REAL | | 涨跌幅 |
| volume_ratio | REAL | | 量比 |
| market_cap_billion | REAL | | 市值（亿） |
| rsi_14 | REAL | | RSI(14) |
| macd_signal | TEXT | | MACD 信号 |
| ma5, ma10, ma20, ma60 | REAL | | 均线 |
| bollinger_position | REAL | | 布林位置 |
| main_inflow, retail_inflow, institutional_inflow, net_inflow | REAL | | 资金流向 |
| auction_ratio, auction_volume_ratio | REAL | | 竞价相关 |
| gap_type | TEXT | | 缺口类型 |
| llm_analysis_text | TEXT | | LLM 分析文本 |
| investment_rating | TEXT | | 投资评级 |
| confidence_level | TEXT | | 信心等级 |
| risk_assessment | TEXT | | 风险评估 |
| buy_point, sell_point | TEXT | | 买卖点 |
| stop_loss_price, target_price | REAL | | 止损/目标价 |
| expected_return_pct | REAL | | 预期收益率 |
| holding_period_days | INTEGER | | 建议持有天数 |
| position_suggestion | REAL | | 仓位建议 |
| technical_score, fundamental_score, sentiment_score, total_score | REAL | | 各项评分 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**唯一约束**: (symbol, analysis_date)，用于 upsert。

**使用位置**: `analysis/deep_stock_analyzer.py`

---

## 10. stock_analysis（单只股票分析解释）

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| symbol | TEXT | NOT NULL | 股票代码 |
| stock_name | TEXT | | 股票名称 |
| analysis_date | TEXT | | 分析日期 |
| total_score | REAL | | 综合得分 |
| tech_score | REAL | | 技术得分 |
| auction_score | REAL | | 竞价得分 |
| confidence | TEXT | | 信心等级 |
| entry_price | REAL | | 入场价 |
| stop_loss | REAL | | 止损价 |
| target_price | REAL | | 目标价 |
| explanation | TEXT | | 文字解释 |
| explain_html | TEXT | | HTML 解释 |
| mini_prices | TEXT | | 迷你价格数据（JSON） |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**唯一约束**: (symbol, analysis_date)，用于 upsert。

**使用位置**: `analysis/optimized_stock_analyzer.py`（写入 explain_html / mini_prices）

---

## 库与连接

- **数据库文件**: `data/cchan_web.db`（可通过环境变量 `CCHAN_WEB_DB_PATH` 覆盖）
- **ORM 入口**: `models/db.py`（engine、SessionLocal、Base、get_session_context、init_db）
- **模型定义**: `models/schema.py`
- **建表**: 应用启动或首次使用前调用 `models.init_db()`，会执行 `Base.metadata.create_all(engine)`，与原有 `CREATE TABLE IF NOT EXISTS` 等价。
