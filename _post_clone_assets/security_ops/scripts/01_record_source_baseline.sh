#!/usr/bin/env bash
set -euo pipefail
BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
REPO_RELATIVE_PATH="../../vendor/PaddleOCR"
REPO_DIR="$BASE_DIR/../../vendor/PaddleOCR"
OUT="$BASE_DIR/reports/source_baseline.txt"
mkdir -p "$(dirname "$OUT")"
{
  echo "timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "repo=$REPO_RELATIVE_PATH"
  echo "remote=$(git -C "$REPO_DIR" remote get-url origin)"
  echo "branch=$(git -C "$REPO_DIR" rev-parse --abbrev-ref HEAD)"
  echo "commit=$(git -C "$REPO_DIR" rev-parse HEAD)"
  echo "status_clean=$( [ -z "$(git -C "$REPO_DIR" status --porcelain)" ] && echo yes || echo no )"
} > "$OUT"
echo "wrote: $OUT"
