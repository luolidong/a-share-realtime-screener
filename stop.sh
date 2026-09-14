#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

echo "Stopping A-share realtime screener..."
docker compose down

echo
echo "Stopped."
