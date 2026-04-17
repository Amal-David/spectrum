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

while kill -0 "$api_pid" 2>/dev/null && kill -0 "$dashboard_pid" 2>/dev/null; do
  sleep 1
done

wait "$api_pid" 2>/dev/null || true
wait "$dashboard_pid" 2>/dev/null || true
