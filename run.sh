#!/bin/bash
# Stocker — 美股追蹤工具 啟動腳本
cd "$(dirname "$0")"

# Activate venv if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Initialize DB
python3 -c "import models; models.init_db(); print('DB ready')"

# Start Flask app
echo "Starting Stocker on http://0.0.0.0:5000"
python3 app.py
