#!/bin/bash
set -e

# 启动 LibreOffice headless 服务（后台运行）
libreoffice --headless --accept="socket,host=localhost,port=2002;urp;" \
    --nologo --nofirststartwizard &

# 等待 LibreOffice UNO 服务启动
sleep 3

# 启动 FastAPI 应用（监听 0.0.0.0:8000）
exec python3 main.py  --api  --host 0.0.0.0 --port 8000