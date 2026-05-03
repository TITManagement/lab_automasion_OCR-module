#!/usr/bin/env bash
set -euo pipefail
BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
REPO_DIR="$BASE_DIR/../PaddleOCR"
VENV="$REPO_DIR/.venv_paddleocr"
OUT_DIR="$BASE_DIR/reports/wheelhouse"
mkdir -p "$OUT_DIR"
source "$VENV/bin/activate"
python -m pip download -r "$BASE_DIR/reports/requirements.lock.txt" -d "$OUT_DIR"
echo "wrote wheelhouse: $OUT_DIR"
