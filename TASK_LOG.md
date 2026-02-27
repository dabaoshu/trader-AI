# 任务执行日志

> 生成时间: 2026-02-26  
> 项目: CChanTrader-AI 智能交易管理平台

---

## 任务一：条件选股模块（同花顺风格）

### 涉及文件

| 文件路径 | 说明 |
|---------|------|
| `stock_screener/__init__.py` | 模块入口，导出 `StockScreener`、`ScreenerRecordManager` |
| `stock_screener/screener.py` | 选股引擎核心逻辑，支持多维度条件筛选 + 手动自定义规则 |
| `stock_screener/models.py` | 选股记录持久化（SQLite），保存完整条件与结果 |
| `backend/app.py` | Flask 路由：`/screener` 页面、`/api/screener/*` API |
| `frontend/templates/screener.html` | 条件选股前端页面（Jinja2 + Tailwind + 原生JS） |
| `frontend/templates/base.html` | 导航栏新增"条件选股"入口 |

### 功能说明

#### 1. 筛选引擎 (`stock_screener/screener.py`)

**核心类:** `StockScreener`

- `screen(stock_list, conditions)` — 根据条件字典筛选股票列表
- `screen_with_preset(stock_list, preset_key)` — 使用预置模板选股
- `_match(stock, conditions)` — 逐项检查条件是否满足
- `_eval_custom_rule(stock, rule)` — 评估手动输入的自定义规则

**支持的筛选条件:**
- 价格区间: `price_min`, `price_max`
- 综合评分: `total_score_min`, `total_score_max`
- 技术评分: `tech_score_min`, `tech_score_max`
- 竞价评分: `auction_score_min`, `auction_score_max`
- 竞价涨幅: `auction_ratio_min`, `auction_ratio_max`
- RSI: `rsi_min`, `rsi_max`
- 市值: `market_cap_min`, `market_cap_max`
- 跳空类型: `gap_types` (数组)
- 信心等级: `confidence_levels` (数组)
- 市场板块: `markets` (数组)
- 关键词: `keyword`
- 手动自定义规则: `custom_rules` (数组，每项包含 field/op/value)

**自定义规则操作符:** `gt`, `gte`, `lt`, `lte`, `eq`, `neq`, `contains`

**5个预置模板:**
1. `low_price_breakout` — 低价突破股
2. `strong_momentum` — 强势动量股
3. `value_pick` — 价值精选
4. `oversold_rebound` — 超跌反弹
5. `small_cap_growth` — 中小盘成长

#### 2. 记录持久化 (`stock_screener/models.py`)

**核心类:** `ScreenerRecordManager`

- `save_record(name, conditions, results)` — 保存完整的条件 + 结果到数据库
- `get_records(limit)` — 获取历史记录列表（不含完整结果数据，节省带宽）
- `get_record_by_id(record_id)` — 获取单条记录详情（含完整 `result_data`）
- `delete_record(record_id)` — 删除记录

**数据库表:** `screener_records`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| name | TEXT | 记录名称 |
| conditions | TEXT (JSON) | 完整筛选条件 |
| result_count | INTEGER | 结果数量 |
| result_symbols | TEXT (JSON) | 股票代码列表 |
| result_summary | TEXT (JSON) | 统计摘要 |
| result_data | TEXT (JSON) | 每只股票的完整数据 |
| preset_key | TEXT | 使用的预置模板 key |
| created_at | TIMESTAMP | 创建时间 |

#### 3. Flask API 路由 (`backend/app.py`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/screener` | 条件选股页面 |
| POST | `/api/screener/run` | 执行选股并保存记录 |
| GET | `/api/screener/presets` | 获取预置模板列表 |
| GET | `/api/screener/records` | 获取历史记录列表 |
| GET | `/api/screener/records/<id>` | 获取单条记录详情 |
| DELETE | `/api/screener/records/<id>` | 删除记录 |

---

## 任务二：Vue3 + Vite 管理后台

### 涉及文件

| 文件路径 | 说明 |
|---------|------|
| `admin-panel/` | Vue3 + Vite 前端工程根目录 |
| `admin-panel/vite.config.js` | Vite 配置，含 API 代理到 Flask :8080 |
| `admin-panel/src/App.vue` | 主页面组件，包含记录列表/详情/快捷选股 |
| `admin-panel/src/api.js` | API 封装层 |
| `admin-panel/src/main.js` | 应用入口 |
| `admin-panel/src/style.css` | Tailwind CSS 入口 |

### 功能

- 选股记录列表：表格展示所有历史记录，支持搜索过滤
- 记录详情面板：查看完整的筛选条件 JSON + 统计摘要 + 全部结果股票
- 快捷选股：一键执行预置模板选股
- 删除记录：支持单条删除
- 统计看板：总记录数、累计筛选股票数、模板选股数

### 运行方式

```bash
cd admin-panel
npm install
npm run dev     # 开发模式，端口 5173，API 代理到 :8080
npm run build   # 构建生产版本到 dist/
```

---

## 任务三：手动输入自定义条件

### 前端交互 (`screener.html`)

- 点击"添加条件"按钮可动态添加自定义筛选行
- 每行包含：字段选择（下拉）、操作符选择（下拉）、值输入
- 支持的字段：当前价格、综合评分、技术评分、竞价评分、竞价涨幅、RSI、市值、入场价、止损价、目标价、股票代码、股票名称、市场、策略
- 支持的操作符：>、≥、<、≤、=、≠、包含

### 后端逻辑 (`screener.py :: _eval_custom_rule`)

- 数值类型自动转换后比较
- 字符串类型使用 `contains` 操作符做子串匹配
- 所有自定义规则之间为 AND 关系

---

## 任务四：完整记录每次条件和结果

- 每次执行选股时，`result_data` 字段保存所有通过筛选的股票的完整数据
- 保留字段包括：symbol, stock_name, market, current_price, total_score, tech_score, auction_score, auction_ratio, gap_type, confidence, strategy, entry_price, stop_loss, target_price, rsi, market_cap_billion
- 历史记录详情 API (`GET /api/screener/records/<id>`) 返回完整 `result_data`
- Vue 管理后台详情面板可以展示每只股票的完整信息
