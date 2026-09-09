#!/bin/zsh
set -eu

ROOT="${0:A:h:h}"
PYTHON="$ROOT/backend/.venv/bin/python"
NODE="${CREATOROS_NODE:-$(command -v node || true)}"

if [[ ! -x "$PYTHON" ]]; then
  print -u2 "缺少 backend/.venv，请先按 README 安装后端依赖。"
  exit 1
fi

if [[ -z "$NODE" ]]; then
  BUNDLED_NODE="/Users/vincent/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node"
  [[ -x "$BUNDLED_NODE" ]] && NODE="$BUNDLED_NODE"
fi

if [[ -z "$NODE" ]]; then
  print -u2 "未找到 Node.js，请先安装 Node.js 22 或设置 CREATOROS_NODE。"
  exit 1
fi

export CREATOROS_ENV_FILE="${CREATOROS_ENV_FILE:-$ROOT/backend/.env}"

cleanup() {
  kill "$API_PID" "$WEB_PID" 2>/dev/null || true
  wait "$API_PID" "$WEB_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

cd "$ROOT"
"$PYTHON" -m uvicorn backend.app:app --host 127.0.0.1 --port 8001 &
API_PID=$!

cd "$ROOT/frontend"
PORT=5174 "$NODE" node_modules/vite/bin/vite.js --host 127.0.0.1 &
WEB_PID=$!

print "CreatorOS 已启动：http://127.0.0.1:5174/"
wait "$API_PID" "$WEB_PID"
