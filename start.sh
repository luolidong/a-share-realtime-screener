#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

echo "Starting A-share realtime screener..."
docker compose up -d

echo
docker compose ps
echo
echo "Started. Open: http://127.0.0.1:8080"
