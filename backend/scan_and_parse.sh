#!/bin/bash
set -e

VULS_CONTAINER="${VULS_CONTAINER:-fixpilot-vuls}"
BACKEND_URL="${BACKEND_URL:-http://backend:8000}"

# 执行 Vuls 扫描并生成报告
docker exec "$VULS_CONTAINER" vulsctl scan --config /opt/vuls/config.toml
docker exec "$VULS_CONTAINER" vulsctl report --config /opt/vuls/config.toml

# 调用后台接口解析结果
curl -X POST "$BACKEND_URL/scan/parse"
