#!/usr/bin/env bash
set -euo pipefail

pnpm api:dev &
api_pid=$!

pnpm dashboard:dev &
dashboard_pid=$!

cleanup() {
  kill "$api_pid" "$dashboard_pid" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

wait -n "$api_pid" "$dashboard_pid"
