"""Tests for the data loader."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from autopader.data.loader import LoadError, compute_sha256, load_dataset


def test_load_xlsx_happy_path(tmp_xlsx: Path) -> None:
    df, sha = load_dataset(tmp_xlsx)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert len(sha) == 64


def test_load_supplied_dataset(real_dataset_path: Path) -> None:
    df, sha = load_dataset(real_dataset_path)
    assert df.shape == (1068, 67)
    assert df["safetyreportid"].nunique() == 1024
    assert len(sha) == 64


def test_load_missing_file(tmp_path: Path) -> None:
    with pytest.raises(LoadError, match="not found"):
        load_dataset(tmp_path / "does_not_exist.xlsx")


def test_load_unsupported_format(tmp_path: Path) -> None:
    path = tmp_path / "data.txt"
    path.write_text("hello")
    with pytest.raises(LoadError, match="unsupported"):
        load_dataset(path)


def test_load_directory(tmp_path: Path) -> None:
    with pytest.raises(LoadError, match="not a file"):
        load_dataset(tmp_path)


def test_load_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "empty.xlsx"
    path.write_bytes(b"")
    with pytest.raises(LoadError):
        load_dataset(path)


def test_compute_sha256_deterministic(tmp_path: Path) -> None:
    path = tmp_path / "a.csv"
    path.write_text("x,y\n1,2\n", encoding="utf-8")
    assert compute_sha256(path) == compute_sha256(path)
