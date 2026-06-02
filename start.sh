#!/bin/bash
set -e

cd "$(dirname "$0")"

# 首次运行自动创建 venv 并安装依赖
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install -r requirements.txt
else
    source .venv/bin/activate
fi

echo "🚀 Starting mflux API server on port ${MFLUX_PORT:-8100}..."
python server.py
