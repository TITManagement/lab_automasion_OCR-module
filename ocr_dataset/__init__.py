"""Expose the src-layout package when running from the repository root."""

from __future__ import annotations

from pathlib import Path

_src_package = Path(__file__).resolve().parent / "src" / __name__
if _src_package.is_dir():
    __path__.append(str(_src_package))

__version__ = "0.1.0"
