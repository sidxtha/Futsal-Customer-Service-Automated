#!/usr/bin/env bash
get_pids() { ss -ltnp 'sport = :8000' | grep -oP 'pid=\K[0-9]+' | sort -u; }

pids=$(get_pids)
if [ -n "$pids" ]; then
  kill $pids 2>/dev/null; sleep 1
  pids=$(get_pids)
  [ -n "$pids" ] && kill -9 $pids && sleep 1
fi
exec uvicorn app.main:app --reload --port 8000
