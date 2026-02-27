# 智能选股助手

A 股智能选股分析平台，提供每日推荐、条件选股、股票分析、自选股管理等功能。

## 快速启动

```bash
# 安装依赖
./dev.sh install

# 启动服务（Flask API :8080 + Vue 管理后台 :5173）
./dev.sh

# 查看状态
./dev.sh status

# 停止
./dev.sh stop
```

启动后访问：
- **管理后台** http://localhost:5173
- **API 服务** http://localhost:8080

## 项目结构

```
├── backend/                   # Flask API 服务
│   ├── app.py                 # API 入口（纯 JSON，无页面渲染）
│   ├── daily_report_generator.py  # 日报生成器
│   ├── explain_builder.py     # 分析报告 HTML 构建
│   ├── explain_generator.py   # 策略解释生成
│   └── services/
│       └── email_config.py    # 邮件发送
│
├── analysis/                  # 分析引擎
│   ├── optimized_stock_analyzer.py  # 优化版选股分析器
│   ├── deep_stock_analyzer.py       # 深度 LLM 分析器
│   └── trading_day_scheduler.py     # 交易日定时调度
│
├── stock_screener/            # 选股核心模块
│   ├── screener.py            # 条件选股引擎（5 个预置模板）
│   ├── models.py              # 选股记录持久化
│   ├── watchlist.py           # 自选股管理（多分组）
│   ├── realtime_quote.py      # 实时行情查询
│   └── analyzer/              # 股票分析引擎
│       ├── engine.py          # 动态规则加载引擎
│       ├── base_rule.py       # 规则基类
│       ├── ai_model.py        # 统一 AI 模型调用
│       └── rules/             # 分析规则
│           ├── technical_rule.py     # 技术面
│           ├── fundamental_rule.py   # 基本面
│           ├── sentiment_rule.py     # 市场情绪
│           ├── sector_tech.py        # 科技板块
│           ├── sector_finance.py     # 金融板块
│           └── sector_consumer.py    # 消费板块
│
├── admin-panel/               # Vue3 + TypeScript 管理后台
│   ├── src/
│   │   ├── views/             # 页面视图
│   │   │   ├── DailyView.vue        # 每日推荐（首页）
│   │   │   ├── RecordsView.vue      # 选股记录
│   │   │   ├── ScreenerView.vue     # 条件选股
│   │   │   ├── AnalyzerView.vue     # 股票分析
│   │   │   ├── WatchlistView.vue    # 自选股（实时行情）
│   │   │   └── ModelsView.vue       # AI 模型管理
│   │   ├── components/        # 组件
│   │   │   ├── AddToWatchlist.vue   # 全局「☆自选」按钮
│   │   │   └── ToastNotify.vue      # 通知提示
│   │   ├── api.ts             # API 封装
│   │   ├── types.ts           # TypeScript 类型
│   │   ├── router.ts          # 路由
│   │   └── main.ts            # 入口
│   └── vite.config.js         # Vite 配置（含 API 代理）
│
├── data/                      # 数据目录（自动创建）
│   ├── cchan_web.db           # SQLite 数据库
│   └── ai_models.json         # AI 模型配置
│
├── dev.sh                     # 一键启动脚本
└── requirements.txt           # Python 依赖
```

## 功能模块

| 模块 | 说明 |
|------|------|
| 每日推荐 | 系统状态仪表盘 + 按信心等级三层分组展示推荐股票 |
| 条件选股 | 同花顺风格多维度筛选，5 个预置模板 + 手动自定义规则 |
| 股票分析 | 多市场支持（A股/港股/美股），动态加载规则引擎 |
| 自选股 | 多分组管理 + 实时行情（5 秒刷新）+ 全局添加按钮 |
| 选股记录 | 历史选股条件与完整结果持久化 |
| 模型管理 | AI 模型提供商配置 + 调用者路由 |

## 技术栈

**后端:** Python 3.9+ / Flask / SQLite / akshare / baostock

**前端:** Vue 3 / TypeScript / Vite / Tailwind CSS / vue-router

## API 概览

| 分类 | 路由 | 说明 |
|------|------|------|
| 每日推荐 | `GET /api/daily/status` | 系统状态 |
| | `GET /api/daily/recommendations?date=` | 推荐列表 |
| | `POST /api/daily/run_analysis` | 执行分析 |
| 条件选股 | `POST /api/screener/run` | 执行选股 |
| | `GET /api/screener/presets` | 预置模板 |
| | `GET /api/screener/records` | 历史记录 |
| 股票分析 | `GET /api/analyzer/rules` | 分析规则 |
| | `POST /api/analyzer/analyze` | 执行分析 |
| 自选股 | `GET /api/watchlist/groups` | 分组列表 |
| | `POST /api/watchlist/quotes` | 实时行情 |
| 模型管理 | `GET /api/models/providers` | 提供商列表 |
| | `GET /api/models/callers` | 调用者绑定 |
| 健康检查 | `GET /health` | 服务状态 |
