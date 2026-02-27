#!/bin/bash
# ============================================================
#  智能选股助手 — 一键开发环境启动脚本
#
#  用法:
#    ./dev.sh          启动所有服务（Flask + Vue 开发服务器）
#    ./dev.sh backend  仅启动 Flask 后端
#    ./dev.sh frontend 仅启动 Vue 前端
#    ./dev.sh install  安装所有依赖
#    ./dev.sh stop     停止所有服务
#    ./dev.sh status   查看服务状态
# ============================================================

set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
FLASK_PORT=8080
VITE_PORT=5173
PID_DIR="$ROOT_DIR/.pids"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

mkdir -p "$PID_DIR" "$ROOT_DIR/data"

log_info()  { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }
log_step()  { echo -e "${BLUE}[→]${NC} $1"; }

# ----------------------------------------------------------
# 依赖安装
# ----------------------------------------------------------
do_install() {
    echo ""
    echo "========================================"
    echo "  智能选股助手 — 安装依赖"
    echo "========================================"
    echo ""

    log_step "安装 Python 依赖..."
    pip install -r "$ROOT_DIR/requirements.txt" -q
    log_info "Python 依赖安装完成"

    log_step "安装 Vue 前端依赖..."
    cd "$ROOT_DIR/admin-panel" && npm install --silent
    log_info "前端依赖安装完成"

    cd "$ROOT_DIR"
    echo ""
    log_info "全部依赖安装完成！"
}

# ----------------------------------------------------------
# 启动 Flask 后端
# ----------------------------------------------------------
start_backend() {
    local pid_file="$PID_DIR/flask.pid"

    if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
        log_warn "Flask 后端已在运行 (PID: $(cat "$pid_file"))"
        return
    fi

    log_step "启动 Flask 后端 (端口 $FLASK_PORT)..."

    cd "$ROOT_DIR"
    export PYTHONPATH="$ROOT_DIR"
    python3 backend/app.py > >(tee -a "$ROOT_DIR/data/flask.log") 2>&1 &
    local pid=$!
    echo "$pid" > "$pid_file"

    sleep 2
    if kill -0 "$pid" 2>/dev/null; then
        log_info "Flask 后端已启动  →  http://localhost:$FLASK_PORT  (PID: $pid)"
    else
        log_error "Flask 启动失败，查看日志: data/flask.log"
        return 1
    fi
}

# ----------------------------------------------------------
# 启动 Vue 前端
# ----------------------------------------------------------
start_frontend() {
    local pid_file="$PID_DIR/vite.pid"

    if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
        log_warn "Vue 前端已在运行 (PID: $(cat "$pid_file"))"
        return
    fi

    log_step "启动 Vue 管理后台 (端口 $VITE_PORT)..."

    cd "$ROOT_DIR/admin-panel"
    npx vite --host 0.0.0.0 --port "$VITE_PORT" > >(tee -a "$ROOT_DIR/data/vite.log") 2>&1 &
    local pid=$!
    echo "$pid" > "$pid_file"

    sleep 3
    if kill -0 "$pid" 2>/dev/null; then
        log_info "Vue 管理后台已启动  →  http://localhost:$VITE_PORT  (PID: $pid)"
    else
        log_error "Vue 启动失败，查看日志: data/vite.log"
        return 1
    fi

    cd "$ROOT_DIR"
}

# ----------------------------------------------------------
# 停止所有服务
# ----------------------------------------------------------
do_stop() {
    echo ""
    log_step "停止所有服务..."

    for name in flask vite; do
        local pid_file="$PID_DIR/$name.pid"
        if [ -f "$pid_file" ]; then
            local pid
            pid=$(cat "$pid_file")
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid" 2>/dev/null
                log_info "已停止 $name (PID: $pid)"
            fi
            rm -f "$pid_file"
        fi
    done

    log_info "所有服务已停止"
}

# ----------------------------------------------------------
# 查看状态
# ----------------------------------------------------------
do_status() {
    echo ""
    echo "========================================"
    echo "  智能选股助手 — 服务状态"
    echo "========================================"
    echo ""

    for entry in "flask:Flask 后端:$FLASK_PORT" "vite:Vue 管理后台:$VITE_PORT"; do
        IFS=':' read -r name label port <<< "$entry"
        local pid_file="$PID_DIR/$name.pid"
        if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
            log_info "$label   运行中  →  http://localhost:$port  (PID: $(cat "$pid_file"))"
        else
            log_error "$label   未运行"
        fi
    done
    echo ""
}

# ----------------------------------------------------------
# 启动全部
# ----------------------------------------------------------
do_start_all() {
    echo ""
    echo "========================================"
    echo "  智能选股助手 — 开发环境启动"
    echo "========================================"
    echo ""

    start_backend
    start_frontend

    echo ""
    echo "========================================"
    echo "  服务已启动"
    echo "========================================"
    echo ""
    echo "  Flask 后端:      http://localhost:$FLASK_PORT"
    echo "  Vue 管理后台:    http://localhost:$VITE_PORT"
    echo ""
    echo "  日志文件:"
    echo "    Flask:  data/flask.log"
    echo "    Vite:   data/vite.log"
    echo ""
    echo "  停止服务:  ./dev.sh stop"
    echo "  查看状态:  ./dev.sh status"
    echo ""

    # 保持脚本常驻，便于在部署或前台查看日志时使用
    # 按 Ctrl+C 将触发优雅停止
    trap 'echo ""; log_step "收到退出信号，正在停止所有服务..."; do_stop; exit 0' INT TERM

    log_step "脚本将保持运行，按 Ctrl+C 可停止所有服务。"

    # 简单健康检查循环：如果核心后端进程退出，则一起退出
    while true; do
        sleep 30
        if [ -f "$PID_DIR/flask.pid" ]; then
            if ! kill -0 "$(cat "$PID_DIR/flask.pid")" 2>/dev/null; then
                log_error "检测到 Flask 后端已退出，dev.sh 也将退出。"
                exit 1
            fi
        fi
    done
}

# ----------------------------------------------------------
# 主入口
# ----------------------------------------------------------
case "${1:-}" in
    install)
        do_install
        ;;
    backend)
        start_backend
        ;;
    frontend)
        start_frontend
        ;;
    stop)
        do_stop
        ;;
    status)
        do_status
        ;;
    *)
        do_start_all
        ;;
esac
