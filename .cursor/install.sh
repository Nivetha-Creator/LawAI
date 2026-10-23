#!/usr/bin/env bash
set -euo pipefail

if ! dpkg -s python3.12-venv >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3.12-venv
fi

cd /workspace
npm ci

cd /workspace/backend
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
.venv/bin/pip install -r requirements.txt
