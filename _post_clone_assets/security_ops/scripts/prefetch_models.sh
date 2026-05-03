#!/usr/bin/env bash
set -euo pipefail

# prefetch_models.sh — Pre-download required PaddleOCR model weights in a
# controlled networked step so that subsequent offline execution can succeed.
# Location: _post_clone_assets/security_ops/scripts/  (outside PaddleOCR tree)
#
# Usage (network-connected environment):
#   _post_clone_assets/security_ops/scripts/prefetch_models.sh [--model-source <source>] [--cache-dir <dir>]
#
# Options:
#   --model-source  Download source: modelscope | huggingface | baidubce (default: modelscope)
#   --cache-dir     Override model cache directory (default: ~/.paddlex/official_models)
#   --dry-run       Show what would be downloaded without executing
#
# Environment overrides:
#   PADDLEOCR_PYTHON_BIN    Python binary (default: <PaddleOCR>/.venv_paddleocr311/bin/python)
#   PADDLEOCR_MODEL_CACHE_DIR  Model cache directory
#   PADDLE_PDX_MODEL_SOURCE    Download source

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PADDLEOCR_ROOT="$(cd -- "${SCRIPT_DIR}/../../../PaddleOCR" && pwd)"

PYTHON_BIN="${PADDLEOCR_PYTHON_BIN:-${PADDLEOCR_ROOT}/.venv_paddleocr311/bin/python}"
MODEL_SOURCE="${PADDLE_PDX_MODEL_SOURCE:-modelscope}"
CACHE_DIR="${PADDLEOCR_MODEL_CACHE_DIR:-${HOME}/.paddlex/official_models}"
DRY_RUN=0

# ── Argument parsing ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --model-source)  MODEL_SOURCE="$2"; shift 2 ;;
    --cache-dir)     CACHE_DIR="$2"; shift 2 ;;
    --dry-run)       DRY_RUN=1; shift ;;
    -h|--help)
      sed -n '/^# /p' "$0" | sed 's/^# //'
      exit 0
      ;;
    *) echo "[ERROR] unknown option: $1" >&2; exit 2 ;;
  esac
done

REQUIRED_MODELS=(
  "PP-LCNet_x1_0_doc_ori"
  "UVDoc"
  "PP-LCNet_x1_0_textline_ori"
  "PP-OCRv5_server_det"
  "PP-OCRv5_server_rec"
)

echo "=== PaddleOCR model prefetch ==="
echo "  Python     : ${PYTHON_BIN}"
echo "  Source     : ${MODEL_SOURCE}"
echo "  Cache dir  : ${CACHE_DIR}"
echo "  Dry-run    : $([ "${DRY_RUN}" -eq 1 ] && echo YES || echo no)"
echo ""

# ── Pre-flight checks ─────────────────────────────────────────────────────────
if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "[ERROR] Python executable not found: ${PYTHON_BIN}" >&2
  echo "        Create the venv first:" >&2
  echo "          python3.11 -m venv ${PADDLEOCR_ROOT}/.venv_paddleocr311" >&2
  echo "          ${PADDLEOCR_ROOT}/.venv_paddleocr311/bin/pip install paddlepaddle==3.1.0 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/" >&2
  echo "          ${PADDLEOCR_ROOT}/.venv_paddleocr311/bin/pip install -e ${PADDLEOCR_ROOT}" >&2
  exit 2
fi

if ! "${PYTHON_BIN}" -c "import paddle" >/dev/null 2>&1; then
  echo "[ERROR] paddlepaddle is not installed in selected runtime: ${PYTHON_BIN}" >&2
  exit 3
fi

if ! "${PYTHON_BIN}" -c "import paddleocr" >/dev/null 2>&1; then
  echo "[ERROR] paddleocr is not installed in selected runtime: ${PYTHON_BIN}" >&2
  exit 3
fi

# ── Show already-cached models ────────────────────────────────────────────────
echo "--- Checking existing cache ---"
already_cached=()
to_fetch=()
for model in "${REQUIRED_MODELS[@]}"; do
  if [[ -d "${CACHE_DIR}/${model}" ]]; then
    echo "  [CACHED]  ${model}"
    already_cached+=("${model}")
  else
    echo "  [MISSING] ${model}"
    to_fetch+=("${model}")
  fi
done
echo ""

if [[ ${#to_fetch[@]} -eq 0 ]]; then
  echo "All required models are already cached. Nothing to download."
  exit 0
fi

if [[ "${DRY_RUN}" -eq 1 ]]; then
  echo "[dry-run] Would download ${#to_fetch[@]} model(s) from source: ${MODEL_SOURCE}"
  for m in "${to_fetch[@]}"; do
    echo "  - ${m}"
  done
  exit 0
fi

# ── Download missing models via paddleocr on a dummy 1×1 PNG ─────────────────
# Trigger model weight download by running a minimal OCR call.
# PADDLEOCR_STRICT_OFFLINE=0 disables the pre-check guard in run_paddleocr_offline.sh.
echo "--- Downloading ${#to_fetch[@]} missing model(s) from '${MODEL_SOURCE}' ---"

DUMMY_IMG="${SCRIPT_DIR}/_dummy_prefetch.png"

if [[ ! -f "${DUMMY_IMG}" ]]; then
  "${PYTHON_BIN}" - "${DUMMY_IMG}" <<'PYEOF'
import sys, struct, zlib, pathlib
sig  = b'\x89PNG\r\n\x1a\n'
def chunk(tag, data):
    raw = tag + data
    return struct.pack('>I', len(data)) + raw + struct.pack('>I', zlib.crc32(raw) & 0xFFFFFFFF)
ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
idat = chunk(b'IDAT', zlib.compress(b'\x00\xFF\xFF\xFF'))
iend = chunk(b'IEND', b'')
pathlib.Path(sys.argv[1]).write_bytes(sig + ihdr + idat + iend)
PYEOF
fi

PADDLEOCR_STRICT_OFFLINE=0 \
  PADDLE_PDX_MODEL_SOURCE="${MODEL_SOURCE}" \
  PADDLEOCR_MODEL_CACHE_DIR="${CACHE_DIR}" \
  "${PYTHON_BIN}" -m paddleocr ocr -i "${DUMMY_IMG}" --lang japan 2>&1 | \
  grep -E "(Downloading|Using cached|Model files|ERROR|WARN|already exist)" || true

echo ""

# ── Post-download verification ────────────────────────────────────────────────
echo "--- Verifying cache after download ---"
failed=()
for model in "${REQUIRED_MODELS[@]}"; do
  if [[ -d "${CACHE_DIR}/${model}" ]]; then
    echo "  [OK]      ${model}"
  else
    echo "  [FAIL]    ${model}  ← still missing" >&2
    failed+=("${model}")
  fi
done
echo ""

if [[ ${#failed[@]} -gt 0 ]]; then
  echo "[ERROR] ${#failed[@]} model(s) failed to download:" >&2
  for m in "${failed[@]}"; do
    echo "  - ${m}" >&2
  done
  echo "" >&2
  echo "  Suggestions:" >&2
  echo "    - Try a different source: --model-source huggingface" >&2
  echo "    - Check network connectivity and proxy settings" >&2
  echo "    - Manually download and place models in: ${CACHE_DIR}" >&2
  exit 5
fi

echo "All ${#REQUIRED_MODELS[@]} required model(s) are cached."
echo "You can now run offline:"
echo "  _post_clone_assets/security_ops/scripts/run_paddleocr_offline.sh ocr -i <image> --lang japan"

rm -f "${DUMMY_IMG}"
