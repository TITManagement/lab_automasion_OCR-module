#!/usr/bin/env bash
set -euo pipefail
BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
REPO_DIR="$BASE_DIR/../../vendor/PaddleOCR"
PROJECT_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
VENV="$PROJECT_ROOT/.venv_OCR"
OUT_DIR="$BASE_DIR/reports"
mkdir -p "$OUT_DIR"
source "$VENV/bin/activate"
python -m pip freeze --all | LC_ALL=C sort > "$OUT_DIR/requirements.lock.txt"
pip-audit > "$OUT_DIR/pip_audit.txt" || true
pip-audit -f cyclonedx-json -o "$OUT_DIR/sbom.cdx.json" || true
echo "wrote: $OUT_DIR/requirements.lock.txt"
echo "wrote: $OUT_DIR/pip_audit.txt"
echo "wrote: $OUT_DIR/sbom.cdx.json"
