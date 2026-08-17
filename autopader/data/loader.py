"""Dataset loading.

Reads the supplied safety dataset (XLSX or CSV) into a pandas DataFrame,
preserving raw values (``dtype=object``) so that token splitting and integer
date parsing are handled by the normalizer, not the loader.

The loader also computes a SHA-256 hash of the raw file for the report
manifest (traceability).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

SUPPORTED_SUFFIXES = {".xlsx", ".xls", ".csv"}


class LoadError(RuntimeError):
    """Raised when a dataset cannot be loaded."""


def compute_sha256(path: Path) -> str:
    """Return the SHA-256 hex digest of a file's raw bytes."""
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_dataset(path: str | Path) -> tuple[pd.DataFrame, str]:
    """Load a dataset file and return ``(dataframe, sha256_hex)``.

    Raises:
        LoadError: if the file is missing, empty, unsupported, or unreadable.
    """
    p = Path(path)
    if not p.exists():
        raise LoadError(f"dataset file not found: {p}")
    if not p.is_file():
        raise LoadError(f"dataset path is not a file: {p}")

    suffix = p.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        supported = sorted(SUPPORTED_SUFFIXES)
        raise LoadError(f"unsupported dataset format '{suffix}'; expected one of {supported}")

    try:
        if suffix in {".xlsx", ".xls"}:
            df = pd.read_excel(p, engine="openpyxl", dtype=object)
        else:
            df = pd.read_csv(p, dtype=object)
    except Exception as exc:  # pragma: no cover - depends on file contents
        raise LoadError(f"failed to parse dataset '{p}': {exc}") from exc

    if df.empty:
        raise LoadError(f"dataset file is empty: {p}")

    return df, compute_sha256(p)
