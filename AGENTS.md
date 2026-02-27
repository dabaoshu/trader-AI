# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

智能选股助手 — A 股智能选股分析平台。Flask 纯 API 后端 + Vue3 TypeScript 前端。

### Running the application

```bash
./dev.sh            # 启动 Flask :8080 + Vue :5173
./dev.sh stop       # 停止
./dev.sh status     # 查看状态
./dev.sh install    # 安装依赖
```

详见 `README.md`。

### Key details

- **前后端分离架构**: Flask 仅提供 JSON API（无模板渲染），Vue3 管理后台通过 Vite 代理 `/api` 到 `:8080`。
- **SQLite 数据库** (`data/cchan_web.db`) 自动创建，无需外部数据库。
- **AI 模型配置** 保存在 `data/ai_models.json`，通过管理后台「模型管理」页面配置。
- **分析引擎** (`stock_screener/analyzer/`) 支持动态加载规则，在 `rules/` 目录下添加 `.py` 文件即自动发现。
- **无正式测试框架**。`backend/` 下没有测试文件。
- **外部 API** (akshare/baostock) 请求较慢，有降级到模拟数据的机制。
- **实时行情** 依赖 `akshare stock_zh_a_spot_em()`，仅交易时段返回数据，非交易时段返回空值。
