#!/bin/bash
set -e

# 根据环境变量生成 cron 任务
CRON_EXPR="${SCAN_CRON_EXPRESSION:-0 2 * * *}"
CRON_FILE=/etc/cron.d/fixpilot
mkdir -p /app/logs

{
  echo "VULS_CONTAINER=${VULS_CONTAINER:-fixpilot-vuls}"
  echo "BACKEND_URL=${BACKEND_URL:-http://backend:8000}"
  echo "$CRON_EXPR /app/scan_and_parse.sh >> /app/logs/scheduler.log 2>&1"
} > "$CRON_FILE"

chmod 0644 "$CRON_FILE"
crontab "$CRON_FILE"

# 前台运行 cron
cron -f
