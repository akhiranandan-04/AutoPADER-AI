"""Tests for the dataset validator."""

from __future__ import annotations

import pandas as pd
import pytest

from autopader.data.validator import validate

from .conftest import REQUIRED_COLUMNS, synthetic_rows


def _copy_rows(rows: list[dict]) -> list[dict]:
    return [dict(r) for r in rows]


def test_valid_synthetic_passes(synthetic_df: pd.DataFrame) -> None:
    report = validate(synthetic_df)
    assert report.is_valid
    assert report.errors == []


def test_valid_real_dataset_passes(real_df: pd.DataFrame) -> None:
    report = validate(real_df)
    assert report.is_valid, report.errors
    assert any("occurcountry" in w for w in report.warnings)  # 7 nulls surfaced
    assert any("token-count mismatch" in w for w in report.warnings)  # 6 rows surfaced


def test_missing_required_column(synthetic_df: pd.DataFrame) -> None:
    bad = synthetic_df.drop(columns=["serious"])
    report = validate(bad)
    assert not report.is_valid
    assert any("missing required columns" in e for e in report.errors)


def test_unexpected_serious_value(synthetic_df: pd.DataFrame) -> None:
    bad = synthetic_df.copy()
    bad["serious"] = bad["serious"].astype(object)
    bad.loc[0, "serious"] = "non-serious"
    report = validate(bad)
    assert not report.is_valid
    assert any("serious" in e and "unexpected value" in e for e in report.errors)


def test_unexpected_sex_value(synthetic_df: pd.DataFrame) -> None:
    bad = synthetic_df.copy()
    bad.loc[0, "patient_patientsex"] = "other"
    report = validate(bad)
    assert not report.is_valid


def test_bad_receivedate(synthetic_df: pd.DataFrame) -> None:
    bad = synthetic_df.copy()
    bad["receivedate"] = bad["receivedate"].astype(object)
    bad.loc[0, "receivedate"] = "2025-01-15"
    report = validate(bad)
    assert not report.is_valid
    assert any("receivedate" in e and "non-YYYYMMDD" in e for e in report.errors)


def test_missing_safetyreportid(synthetic_df: pd.DataFrame) -> None:
    bad = synthetic_df.copy()
    bad.loc[0, "safetyreportid"] = None
    report = validate(bad)
    assert not report.is_valid


def test_empty_dataframe_is_error() -> None:
    df = pd.DataFrame(columns=REQUIRED_COLUMNS)
    report = validate(df)
    assert not report.is_valid


def test_token_mismatch_warns_not_errors(synthetic_df: pd.DataFrame) -> None:
    rows = _copy_rows(synthetic_rows())
    rows[0]["patient_reaction_reactionmeddrapt"] = "A,B,C"
    rows[0]["patient_reaction_reactionoutcome"] = "x,y"
    report = validate(pd.DataFrame(rows))
    assert report.is_valid
    assert any("token-count mismatch" in w for w in report.warnings)


@pytest.mark.parametrize(
    ("col", "value"),
    [
        ("seriousnessdeath", "maybe"),
        ("seriousnesshospitalization", "YES"),
        ("fulfillexpeditecriteria", "1"),
    ],
)
def test_bad_yes_no_domain(synthetic_df: pd.DataFrame, col: str, value: object) -> None:
    bad = synthetic_df.copy()
    bad.loc[0, col] = value
    report = validate(bad)
    assert not report.is_valid
