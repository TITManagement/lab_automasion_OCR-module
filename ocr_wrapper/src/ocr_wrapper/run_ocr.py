from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

ALLOWED_LANGS = {"japan", "en", "ch"}


def _run(cmd: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, env=env)


def _enforce_policy(lang: str, image: Path) -> None:
    if lang not in ALLOWED_LANGS:
        raise ValueError(f"lang '{lang}' is not allowed. allowed={sorted(ALLOWED_LANGS)}")
    if not image.exists() or not image.is_file():
        raise ValueError(f"image not found: {image}")


def _build_offline_env() -> dict[str, str]:
    env = dict(os.environ)
    # Force no external fetch from command runtime.
    env["PADDLE_PDX_MODEL_SOURCE"] = "local"
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    env["NO_PROXY"] = "*"
    env["no_proxy"] = "*"
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        env.pop(key, None)
    return env


def _audit_fail_fast(max_vulns: int) -> None:
    proc = _run(["pip-audit"])
    # pip-audit returns non-zero when vulnerabilities exist.
    if proc.returncode == 0:
        return
    lines = (proc.stdout or "") + "\n" + (proc.stderr or "")
    found = 0
    for line in lines.splitlines():
        if line.startswith("Found ") and " known vulnerabilities" in line:
            # e.g. "Found 8 known vulnerabilities in 5 packages"
            try:
                found = int(line.split()[1])
                break
            except Exception:
                pass
    if found > max_vulns:
        raise RuntimeError(f"security gate failed: vulnerabilities={found} > max_vulns={max_vulns}")


def run_ocr(image: Path, out: Path, lang: str, *, security_gate: bool, max_vulns: int) -> int:
    _enforce_policy(lang, image)
    if security_gate:
        _audit_fail_fast(max_vulns=max_vulns)
    out.parent.mkdir(parents=True, exist_ok=True)
    env = _build_offline_env()
    cmd = [
        "paddleocr",
        "ocr",
        "-i",
        str(image),
        "--lang",
        lang,
    ]
    proc = _run(cmd, env=env)
    payload = {
        "cmd": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "policy": {
            "offline_enforced": True,
            "security_gate": security_gate,
            "max_vulns": max_vulns,
            "allowed_langs": sorted(ALLOWED_LANGS),
        },
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--lang", default="japan")
    parser.add_argument("--security-gate", action="store_true", help="Run pip-audit and fail if vulnerabilities exceed threshold")
    parser.add_argument("--max-vulns", type=int, default=0)
    args = parser.parse_args()
    return run_ocr(
        Path(args.image),
        Path(args.out),
        args.lang,
        security_gate=bool(args.security_gate),
        max_vulns=int(args.max_vulns),
    )


if __name__ == "__main__":
    raise SystemExit(main())
