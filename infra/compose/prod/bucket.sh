#!/bin/sh
set -eu
attempt=0
max_attempts=30
retry_seconds=2
until mc alias set mall http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null 2>&1; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge "$max_attempts" ]; then
    exit 1
  fi
  sleep "$retry_seconds"
done
mc mb --ignore-existing mall/askflow
