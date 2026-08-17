"""Tests for case/reaction normalization."""

from __future__ import annotations

import pandas as pd
import pytest

from autopader.data.columns import (
    AGE_BUCKET_COL,
    COUNTRY_COL,
    NOT_SERIOUS,
    REACTION_PT_COL,
    RECEIVED_DATE_COL,
    SERIOUS,
    SERIOUS_NORM_COL,
    UNKNOWN,
)
from autopader.data.normalizer import (
    bucket_age,
    build_case_table,
    build_reaction_table,
    parse_receivedate,
)


def _multi_row_df() -> pd.DataFrame:
    """Two cases: case A has 2 rows, case B has 1 row with 2 reactions."""
    return pd.DataFrame(
        [
            {
                "safetyreportid": 2001,
                "serious": "serious",
                "fulfillexpeditecriteria": "yes",
                "patient_patientsex": "female",
                "patient_patientonsetage": 50,
                "patient_patientonsetageunit": "year",
                "occurcountry": "italy",
                "primarysource_reportercountry": "italy",
                "receivedate": 20250101,
                "patient_reaction_reactionmeddrapt": "Headache",
                "patient_reaction_reactionoutcome": "recovered/resolved",
                "primarysource_qualification": "physician",
            },
            {
                "safetyreportid": 2001,
                "serious": "serious",
                "fulfillexpeditecriteria": "yes",
                "patient_patientsex": "female",
                "patient_patientonsetage": 50,
                "patient_patientonsetageunit": "year",
                "occurcountry": "italy",
                "primarysource_reportercountry": "italy",
                "receivedate": 20250101,
                "patient_reaction_reactionmeddrapt": "Dizziness",
                "patient_reaction_reactionoutcome": "unknown",
                "primarysource_qualification": "physician",
            },
            {
                "safetyreportid": 2002,
                "serious": "not serious",
                "fulfillexpeditecriteria": "no",
                "patient_patientsex": "male",
                "patient_patientonsetage": 20,
                "patient_patientonsetageunit": "year",
                "occurcountry": "france",
                "primarysource_reportercountry": "france",
                "receivedate": 20250202,
                "patient_reaction_reactionmeddrapt": "Fatigue,Cough",
                "patient_reaction_reactionoutcome": "unknown,recovered/resolved",
                "primarysource_qualification": "physician",
            },
        ]
    )


def test_case_dedup_counts_unique_cases(_real_df: pd.DataFrame) -> None:
    table = build_case_table(_real_df)
    assert table.n_cases == 1024
    assert len(table.rows) == 1024
    assert table.report.raw_rows == 1068


def test_multi_row_case_kept_once(_real_df: pd.DataFrame) -> None:
    table = build_case_table(_real_df)
    assert len(table.report.rows_per_case) == 1024
    multi = {k: v for k, v in table.report.rows_per_case.items() if v > 1}
    assert len(multi) == 41


def test_serious_normalization(_real_df: pd.DataFrame) -> None:
    table = build_case_table(_real_df)
    counts = table.rows[SERIOUS_NORM_COL].value_counts().to_dict()
    assert counts[SERIOUS] == 1023
    assert counts[NOT_SERIOUS] == 1
    assert "not_serious" in counts  # raw value was 'not serious', not 'non-serious'


def test_age_bucket_applied(_real_df: pd.DataFrame) -> None:
    table = build_case_table(_real_df)
    buckets = table.rows[AGE_BUCKET_COL].value_counts()
    assert buckets.get("65-74", 0) > 0
    assert buckets.get(UNKNOWN, 0) > 0


def test_country_fallback_used(_real_df: pd.DataFrame) -> None:
    table = build_case_table(_real_df)
    assert table.report.country_fallback_rows == 7
    # no unknown countries after fallback (reporter country is complete)
    assert int(table.rows[COUNTRY_COL].isna().sum()) == 0


def test_received_date_parsed(_real_df: pd.DataFrame) -> None:
    table = build_case_table(_real_df)
    dates = table.rows[RECEIVED_DATE_COL].dropna()
    assert dates.min().isoformat() == "2024-12-27"
    assert dates.max().isoformat() == "2025-12-26"


def test_reaction_explode_real_counts(_real_df: pd.DataFrame) -> None:
    reactions, report = build_reaction_table(_real_df)
    assert report.reaction_tokens == 3648
    assert len(reactions) == 3648
    assert reactions[REACTION_PT_COL].nunique() == 1122
    assert report.misaligned_rows == 6


def test_reaction_explode_multi_row_case(_real_df: pd.DataFrame) -> None:
    reactions, _ = build_reaction_table(_real_df)
    # every case keeps its tokens; token count per case sums to total
    assert int(reactions.groupby("safetyreportid").size().sum()) == 3648


def test_reaction_mismatch_padded_not_silent() -> None:
    df = _multi_row_df()
    df.loc[df["safetyreportid"] == 2002, "patient_reaction_reactionmeddrapt"] = (
        "Fatigue,Cough,Extra"
    )
    reactions, report = build_reaction_table(df)
    assert report.misaligned_rows == 1
    assert report.padded_outcome_tokens == 1
    assert report.dropped_outcome_tokens == 0
    # all 3 PT tokens of case 2002 retained; the mismatch must be visible in the report
    assert len(reactions) == 2 + 3  # case 2001: 2 rows x 1 token; case 2002: 3 tokens
    padded = reactions[
        (reactions["safetyreportid"] == 2002)
        & (reactions["patient_reaction_reactionmeddrapt"] == "Extra")
    ]["patient_reaction_reactionoutcome"].iloc[0]
    assert padded == "unknown"


def test_case_serious_via_multi_row() -> None:
    table = build_case_table(_multi_row_df())
    assert table.n_cases == 2
    assert table.report.rows_per_case[2001] == 2


@pytest.mark.parametrize(
    ("age", "unit", "expected"),
    [
        (17.9, "year", "0-17"),
        (18, "year", "18-64"),
        (64.9, "year", "18-64"),
        (65, "year", "65-74"),
        (74.9, "year", "65-74"),
        (75, "year", "75-84"),
        (84.9, "year", "75-84"),
        (85, "year", "85+"),
        (104, "year", "85+"),
        (1, "year", "0-17"),
        (6, "month", "0-17"),
        (1, "day", "0-17"),
        (None, "year", UNKNOWN),
        (50, None, UNKNOWN),
        (50, "800", UNKNOWN),
        (50, "stone", UNKNOWN),
    ],
)
def test_bucket_age(age: object, unit: object, expected: str) -> None:
    assert bucket_age(age, unit) == expected


def test_parse_receivedate() -> None:
    assert parse_receivedate(20250115).isoformat() == "2025-01-15"
    assert parse_receivedate("20251226").isoformat() == "2025-12-26"
    assert parse_receivedate(None) is None
    assert parse_receivedate(20251) is None
    assert parse_receivedate("not-a-date") is None


# -- fixture injection: reuse real_df under an alias --


@pytest.fixture
def _real_df(real_df: pd.DataFrame) -> pd.DataFrame:
    return real_df
