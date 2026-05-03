#!/usr/bin/env bash
set -euo pipefail

# Offline-first execution wrapper for paddleocr CLI.
# Location: _post_clone_assets/security_ops/scripts/  (outside PaddleOCR tree)
#
# Usage (from lab_automasion_OCR-module root):
#   _post_clone_assets/security_ops/scripts/run_paddleocr_offline.sh ocr -i ./doc.png --lang japan
#
# Strict offline mode (default):
#   - Verifies required model cache exists before execution.
#   - Fails fast instead of allowing model source fallback to network.

if [[ $# -eq 0 ]]; then
  echo "usage: $0 <paddleocr args...>" >&2
  exit 2
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PADDLEOCR_ROOT="$(cd -- "${SCRIPT_DIR}/../../../vendor/PaddleOCR" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"

# Prefer Python 3.11 security-maintained venv. Fallback can be overridden.
PYTHON_BIN="${PADDLEOCR_PYTHON_BIN:-${PROJECT_ROOT}/.venv_OCR/bin/python}"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "[ERROR] Python executable not found: ${PYTHON_BIN}" >&2
  echo "        Create venv first, e.g. python3.11 -m venv ${PROJECT_ROOT}/.venv_OCR" >&2
  exit 2
fi

export PADDLE_PDX_MODEL_SOURCE=local
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True
export NO_PROXY='*'
export no_proxy='*'
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy

if ! "${PYTHON_BIN}" -c "import paddle" >/dev/null 2>&1; then
  echo "[ERROR] paddlepaddle is not installed in selected runtime: ${PYTHON_BIN}" >&2
  echo "        Install it, e.g. ${PYTHON_BIN} -m pip install paddlepaddle==3.1.0 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/" >&2
  exit 3
fi

if ! "${PYTHON_BIN}" -c "import paddleocr" >/dev/null 2>&1; then
  echo "[ERROR] paddleocr is not installed in selected runtime: ${PYTHON_BIN}" >&2
  echo "        Install it, e.g. ${PYTHON_BIN} -m pip install -e ${PADDLEOCR_ROOT}" >&2
  exit 3
fi

STRICT_OFFLINE="${PADDLEOCR_STRICT_OFFLINE:-1}"
if [[ "${STRICT_OFFLINE}" == "1" ]] && [[ "$1" == "ocr" ]]; then
  MODEL_ROOT="${PADDLEOCR_MODEL_CACHE_DIR:-${HOME}/.paddlex/official_models}"
  lang="ch"
  ocr_version="PP-OCRv5"
  use_doc_orientation_classify="True"
  use_doc_unwarping="True"
  use_textline_orientation="True"

  args=("$@")
  for ((i = 0; i < ${#args[@]}; i++)); do
    case "${args[$i]}" in
      --lang)
        if ((i + 1 < ${#args[@]})); then
          lang="${args[$((i + 1))]}"
        fi
        ;;
      --ocr_version)
        if ((i + 1 < ${#args[@]})); then
          ocr_version="${args[$((i + 1))]}"
        fi
        ;;
      --use_doc_orientation_classify)
        if ((i + 1 < ${#args[@]})); then
          use_doc_orientation_classify="${args[$((i + 1))]}"
        fi
        ;;
      --use_doc_unwarping)
        if ((i + 1 < ${#args[@]})); then
          use_doc_unwarping="${args[$((i + 1))]}"
        fi
        ;;
      --use_textline_orientation)
        if ((i + 1 < ${#args[@]})); then
          use_textline_orientation="${args[$((i + 1))]}"
        fi
        ;;
    esac
  done

  required_models=()
  if [[ "${use_doc_orientation_classify}" != "False" ]]; then
    required_models+=("PP-LCNet_x1_0_doc_ori")
  fi
  if [[ "${use_doc_unwarping}" != "False" ]]; then
    required_models+=("UVDoc")
  fi
  if [[ "${use_textline_orientation}" != "False" ]]; then
    required_models+=("PP-LCNet_x1_0_textline_ori")
  fi

  if [[ "${ocr_version}" == "PP-OCRv3" ]]; then
    required_models+=("PP-OCRv3_mobile_det")
    case "${lang}" in
      ch)
        required_models+=("PP-OCRv3_mobile_rec")
        ;;
      *)
        required_models+=("${lang}_PP-OCRv3_mobile_rec")
        ;;
    esac
  elif [[ "${ocr_version}" == "PP-OCRv4" ]]; then
    required_models+=("PP-OCRv4_mobile_det")
    if [[ "${lang}" == "en" ]]; then
      required_models+=("en_PP-OCRv4_mobile_rec")
    else
      required_models+=("PP-OCRv4_mobile_rec")
    fi
  else
    required_models+=("PP-OCRv5_server_det")
    case "${lang}" in
      ch|chinese_cht|japan)
        required_models+=("PP-OCRv5_server_rec")
        ;;
      en)
        required_models+=("en_PP-OCRv5_mobile_rec")
        ;;
      *)
        required_models+=("${lang}_PP-OCRv5_mobile_rec")
        ;;
    esac
  fi

  missing=()
  for m in "${required_models[@]}"; do
    if [[ ! -d "${MODEL_ROOT}/${m}" ]]; then
      missing+=("${m}")
    fi
  done

  if [[ ${#missing[@]} -gt 0 ]]; then
    echo "[ERROR] strict offline is enabled and required model cache is missing." >&2
    echo "        cache dir: ${MODEL_ROOT}" >&2
    printf '        missing models:\n' >&2
    for m in "${missing[@]}"; do
      echo "          - ${m}" >&2
    done
    echo "        prefetch these models in a controlled networked step, then retry." >&2
    echo "        (set PADDLEOCR_STRICT_OFFLINE=0 to allow fallback download temporarily)" >&2
    exit 4
  fi
fi

exec "${PYTHON_BIN}" -m paddleocr "$@"
