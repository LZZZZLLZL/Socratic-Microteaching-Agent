#!/bin/bash
# ==========================================================================
#  学思践悟 AI 多模态实训系统 · 新样式版
#  一键启动脚本（macOS / Linux）
#
#  用法：
#     ./start.sh              → 交互式菜单，选择启动模式
#     ./start.sh preview      → 直接启动快速预览模式（零依赖，给评委看）
#     ./start.sh full         → 直接启动完整模式（前端 + 后端）
#     ./start.sh stop         → 停止所有正在运行的服务
# ==========================================================================

set -uo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
FRONTEND_DIR="$PROJECT_DIR/frontend"
BACKEND_DIR="$PROJECT_DIR/backend"
PID_DIR="$PROJECT_DIR/.run"
LOG_DIR="$PROJECT_DIR/.run/logs"

FRONTEND_PORT="${FRONTEND_PORT:-3000}"
BACKEND_PORT="${BACKEND_PORT:-8000}"

# --- 颜色 ---
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; GRAY='\033[0;90m'; BOLD='\033[1m'; NC='\033[0m'

mkdir -p "$PID_DIR" "$LOG_DIR"

# --------------------------------------------------------------------------
# 工具函数
# --------------------------------------------------------------------------
info()  { echo -e "  ${GRAY}·${NC} $1"; }
ok()    { echo -e "  ${GREEN}✓${NC} $1"; }
warn()  { echo -e "  ${YELLOW}!${NC} $1"; }
err()   { echo -e "  ${RED}✗${NC} $1"; }

banner() {
  echo ""
  echo -e "${CYAN}  ╔══════════════════════════════════════════════════╗${NC}"
  echo -e "${CYAN}  ║${NC}   ${BOLD}学思践悟${NC} · AI 多模态实训系统                  ${CYAN}║${NC}"
  echo -e "${CYAN}  ║${NC}   Editorial Edition · 新样式版                   ${CYAN}║${NC}"
  echo -e "${CYAN}  ╚══════════════════════════════════════════════════╝${NC}"
  echo ""
}

# 端口是否被占用
port_busy() {
  lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

# 找到可用的前端工具链
detect_pm() {
  if [ -x "$FRONTEND_DIR/node_modules/.bin/nuxt" ]; then
    echo "local"
  elif command -v pnpm >/dev/null 2>&1; then
    echo "pnpm"
  elif command -v npm >/dev/null 2>&1; then
    echo "npm"
  else
    echo ""
  fi
}

open_browser() {
  local url="$1"
  sleep 3
  if command -v open >/dev/null 2>&1; then
    open "$url" >/dev/null 2>&1
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$url" >/dev/null 2>&1
  fi
}

# --------------------------------------------------------------------------
# 依赖检查
# --------------------------------------------------------------------------
check_node() {
  if ! command -v node >/dev/null 2>&1; then
    err "未找到 Node.js —— 请先安装 Node.js 18+ ：https://nodejs.org"
    return 1
  fi
  local v
  v="$(node --version)"
  ok "Node.js $v"
  return 0
}

ensure_frontend_deps() {
  if [ -d "$FRONTEND_DIR/node_modules" ]; then
    ok "前端依赖已就绪"
    return 0
  fi

  warn "首次运行，正在安装前端依赖（约需 1-3 分钟）…"
  cd "$FRONTEND_DIR" || return 1

  if command -v pnpm >/dev/null 2>&1; then
    pnpm install --silent && ok "前端依赖安装完成" && return 0
  fi
  if command -v npm >/dev/null 2>&1; then
    npm install --silent && ok "前端依赖安装完成" && return 0
  fi

  err "未找到 pnpm / npm，无法安装前端依赖"
  return 1
}

check_backend_deps() {
  local missing=()
  for pkg in fastapi uvicorn; do
    python3 -c "import $pkg" 2>/dev/null || missing+=("$pkg")
  done

  if [ ${#missing[@]} -gt 0 ]; then
    warn "缺少后端依赖: ${missing[*]}"
    info "正在安装（首次可能需要几分钟）…"
    python3 -m pip install -q -r "$BACKEND_DIR/requirements.txt" \
      || python3 -m pip install -q -r "$BACKEND_DIR/requirements.txt" --user \
      || { err "后端依赖安装失败，请手动执行："; \
           echo -e "     ${CYAN}cd backend && pip install -r requirements.txt${NC}"; return 1; }
    ok "后端依赖安装完成"
  else
    ok "后端依赖已就绪"
  fi

  # ffmpeg 用于音视频处理
  if ! command -v ffmpeg >/dev/null 2>&1; then
    warn "未找到 ffmpeg —— 视频转写与姿态分析将不可用"
    info "macOS 安装：brew install ffmpeg"
  else
    ok "ffmpeg 已就绪"
  fi

  # DEEPSEEK_API_KEY：启动阶段不再提示，也不在此处配置。
  # 改为进入系统后在「分析工作台 → API 设置」面板里填写（保存即生效，无需重启）。

  return 0
}

# --------------------------------------------------------------------------
# 服务启停
# --------------------------------------------------------------------------
start_frontend() {
  if port_busy "$FRONTEND_PORT"; then
    warn "端口 $FRONTEND_PORT 已被占用，复用现有服务"
    return 0
  fi

  local pm
  pm="$(detect_pm)"
  if [ -z "$pm" ]; then
    err "无法启动前端：缺少 node_modules 且未找到包管理器"
    return 1
  fi

  cd "$FRONTEND_DIR" || return 1
  local log="$LOG_DIR/frontend.log"

  case "$pm" in
    local) nohup ./node_modules/.bin/nuxt dev --port "$FRONTEND_PORT" >"$log" 2>&1 & ;;
    pnpm)  nohup pnpm dev --port "$FRONTEND_PORT"  >"$log" 2>&1 & ;;
    npm)   nohup npm run dev -- --port "$FRONTEND_PORT" >"$log" 2>&1 & ;;
  esac

  echo $! > "$PID_DIR/frontend.pid"
  info "前端启动中（日志：.run/logs/frontend.log）…"

  # 等待端口就绪，最多 60 秒
  local i=0
  while [ $i -lt 60 ]; do
    if port_busy "$FRONTEND_PORT"; then
      ok "前端已就绪 → http://localhost:$FRONTEND_PORT"
      return 0
    fi
    sleep 1; i=$((i + 1))
  done

  err "前端启动超时，请查看日志："
  echo -e "     ${CYAN}tail -30 .run/logs/frontend.log${NC}"
  return 1
}

start_backend() {
  if port_busy "$BACKEND_PORT"; then
    warn "端口 $BACKEND_PORT 已被占用，复用现有服务"
    return 0
  fi

  cd "$BACKEND_DIR" || return 1
  local log="$LOG_DIR/backend.log"

  nohup python3 -m uvicorn main:app --host 127.0.0.1 --port "$BACKEND_PORT" \
    >"$log" 2>&1 &
  echo $! > "$PID_DIR/backend.pid"
  info "后端启动中（日志：.run/logs/backend.log）…"

  local i=0
  while [ $i -lt 90 ]; do
    if curl -s -m 2 "http://127.0.0.1:$BACKEND_PORT/api/v1/models" >/dev/null 2>&1; then
      ok "后端已就绪 → http://127.0.0.1:$BACKEND_PORT"
      return 0
    fi
    sleep 1; i=$((i + 1))
  done

  err "后端启动超时，请查看日志："
  echo -e "     ${CYAN}tail -30 .run/logs/backend.log${NC}"
  return 1
}

stop_all() {
  local stopped=0
  for name in frontend backend; do
    local pidfile="$PID_DIR/$name.pid"
    if [ -f "$pidfile" ]; then
      local pid
      pid="$(cat "$pidfile" 2>/dev/null)"
      if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        # 结束整个进程组，避免残留子进程
        kill -TERM "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null
        stopped=$((stopped + 1))
        ok "已停止 $name (PID $pid)"
      fi
      rm -f "$pidfile"
    fi
  done

  # 兜底：按端口清理
  for port in "$FRONTEND_PORT" "$BACKEND_PORT"; do
    local pids
    pids="$(lsof -nP -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null)"
    if [ -n "$pids" ]; then
      # shellcheck disable=SC2086
      kill -TERM $pids 2>/dev/null && ok "已释放端口 $port"
    fi
  done

  [ $stopped -eq 0 ] && info "没有正在运行的服务"
  return 0
}

# --------------------------------------------------------------------------
# 启动模式
# --------------------------------------------------------------------------
launch_preview() {
  echo -e "${GREEN}${BOLD}  ▶ 快速预览模式${NC} ${GRAY}（零依赖 · 无需模型 · 无需 API Key）${NC}"
  echo ""

  check_node || return 1
  ensure_frontend_deps || return 1

  echo ""
  start_frontend || return 1

  echo ""
  echo -e "${GREEN}  ─────────────────────────────────────────────────${NC}"
  echo -e "${GREEN}   系统已启动！${NC}"
  echo ""
  echo -e "   浏览器访问： ${CYAN}${BOLD}http://localhost:$FRONTEND_PORT${NC}"
  echo ""
  echo -e "   ${GRAY}· 默认即为「快速预览模式」，可直接演示${NC}"
  echo -e "   ${GRAY}· 右上角开关可切到「完整模式」${NC}"
  echo -e "   ${GRAY}· 停止服务： ./start.sh stop  或按 Ctrl+C${NC}"
  echo -e "${GREEN}  ─────────────────────────────────────────────────${NC}"
  echo ""

  if [ "${NO_OPEN:-0}" != "1" ]; then
    open_browser "http://localhost:$FRONTEND_PORT" &
  fi

  # 前台等待，便于 Ctrl+C 退出
  wait
}

launch_full() {
  echo -e "${GREEN}${BOLD}  ▶ 完整模式${NC} ${GRAY}（前端 + 后端 · 本地模型推理）${NC}"
  echo ""

  check_node || return 1
  ensure_frontend_deps || return 1
  echo ""
  check_backend_deps || return 1

  echo ""
  start_backend || return 1
  start_frontend || return 1

  echo ""
  echo -e "${GREEN}  ─────────────────────────────────────────────────${NC}"
  echo -e "${GREEN}   系统已启动！${NC}"
  echo ""
  echo -e "   浏览器访问： ${CYAN}${BOLD}http://localhost:$FRONTEND_PORT${NC}"
  echo -e "   后端接口：   ${GRAY}http://127.0.0.1:$BACKEND_PORT${NC}"
  echo ""
  echo -e "   ${GRAY}· 请把右上角开关切到「FULL / 完整版」${NC}"
  echo -e "   ${GRAY}· 首次分析会自动监测模型并让你选 Whisper 精度${NC}"
  echo -e "   ${GRAY}· 停止服务： ./start.sh stop  或按 Ctrl+C${NC}"
  echo -e "${GREEN}  ─────────────────────────────────────────────────${NC}"
  echo ""

  if [ "${NO_OPEN:-0}" != "1" ]; then
    open_browser "http://localhost:$FRONTEND_PORT" &
  fi

  wait
}

# --------------------------------------------------------------------------
# 菜单
# --------------------------------------------------------------------------
show_menu() {
  banner
  echo -e "  请选择启动模式："
  echo ""
  echo -e "    ${GREEN}${BOLD}1${NC}  快速预览模式   ${GRAY}零依赖，不需要模型和 API Key${NC}"
  echo -e "        ${GRAY}── 推荐给评委演示，打开即可用${NC}"
  echo ""
  echo -e "    ${GREEN}${BOLD}2${NC}  完整模式       ${GRAY}前端 + 后端，真实视频分析${NC}"
  echo -e "        ${GRAY}── 需要 Python 依赖与 ffmpeg${NC}"
  echo ""
  echo -e "    ${GREEN}${BOLD}3${NC}  停止所有服务"
  echo ""
  echo -e "    ${GREEN}${BOLD}q${NC}  退出"
  echo ""
  printf "  输入选项 [1]: "
  read -r choice
  choice="${choice:-1}"

  case "$choice" in
    1) launch_preview ;;
    2) launch_full ;;
    3) stop_all ;;
    q|Q) exit 0 ;;
    *) err "无效选项：$choice"; exit 1 ;;
  esac
}

# --------------------------------------------------------------------------
# 入口
# --------------------------------------------------------------------------
cd "$PROJECT_DIR" || exit 1

case "${1:-}" in
  preview)  banner; launch_preview ;;
  full)     banner; launch_full ;;
  stop)     echo ""; stop_all; echo "" ;;
  -h|--help|help)
    banner
    echo -e "  用法： ${CYAN}./start.sh [命令]${NC}"
    echo ""
    echo -e "    ${BOLD}(无参数)${NC}    交互式菜单"
    echo -e "    ${BOLD}preview${NC}     快速预览模式（零依赖）"
    echo -e "    ${BOLD}full${NC}        完整模式（前端 + 后端）"
    echo -e "    ${BOLD}stop${NC}        停止所有服务"
    echo ""
    echo -e "  环境变量："
    echo -e "    ${BOLD}FRONTEND_PORT${NC}  前端端口（默认 3000）"
    echo -e "    ${BOLD}BACKEND_PORT${NC}   后端端口（默认 8000）"
    echo -e "    ${BOLD}NO_OPEN=1${NC}      启动后不自动打开浏览器"
    echo ""
    ;;
  "")       show_menu ;;
  *)        banner; err "未知命令：$1"; echo -e "   运行 ${CYAN}./start.sh help${NC} 查看用法"; exit 1 ;;
esac
