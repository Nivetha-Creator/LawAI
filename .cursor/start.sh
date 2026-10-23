#!/usr/bin/env bash
set -euo pipefail

TMUX=(tmux -f /exec-daemon/tmux.portal.conf)

start_session() {
  local name="$1"
  local dir="$2"
  local cmd="$3"
  if ! "${TMUX[@]}" has-session -t "$name" 2>/dev/null; then
    "${TMUX[@]}" new-session -d -s "$name" -c "$dir" -- bash -lc "$cmd"
  fi
}

start_session lawai_api /workspace/backend \
  '/workspace/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000'

start_session lawai_web /workspace \
  'npm run dev -- --host 0.0.0.0 --port 5173'

for _ in $(seq 1 90); do
  if curl -sf http://127.0.0.1:8000/health >/dev/null; then
    break
  fi
  sleep 1
done

for _ in $(seq 1 90); do
  if curl -sf http://127.0.0.1:5173/ >/dev/null; then
    break
  fi
  sleep 1
done
