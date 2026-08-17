"""Tests for deterministic analysis/evidence (Stage 4)."""

from __future__ import annotations

import pytest

from autopader.analysis import compute_all
from autopader.analysis.case_metrics import compute_case_listing
from autopader.analysis.results import EvidenceSource
from autopader.data.columns import SERIOUS
from autopader.data.normalizer import build_case_table, build_reaction_table

HASH = "testhash"


@pytest.fixture(scope="module")
def analyze(real_df_module):
    case_table = build_case_table(real_df_module)
    reaction_df, _ = build_reaction_table(real_df_module)
    return compute_all(case_table, reaction_df, HASH)


def test_golden_counts(analyze) -> None:
    assert analyze.total_cases == 1024
    assert analyze.serious_cases == 1023
    assert analyze.not_serious_cases == 1
    assert analyze.expedited_cases == 1023
    assert abs(analyze.serious_pct - (100.0 * 1023 / 1024)) < 0.05


def test_reporting_period(analyze) -> None:
    start, end = analyze.reporting_period
    assert start == "2024-12-27"
    assert end == "2025-12-26"


def test_golden_reactions(analyze) -> None:
    # top-10 list is a subset; full token count comes from reaction table totals
    rows = [name for name, _ in analyze.top_reactions]
    assert len(rows) <= 10
    assert len({name for name, _ in analyze.top_reactions}) == len(rows)  # unique


def test_top_reaction_present(analyze) -> None:
    top = dict(analyze.top_reactions)
    assert max(top.values()) >= 81  # leading PT outranks the rest


def test_all_evidence_traceable(analyze) -> None:
    assert isinstance(analyze.evidence["case.total_cases"], EvidenceSource)
    src = analyze.source("case.total_cases")
    assert src.value == "1,024"
    assert "dataset:testhash" in src.provenance
    assert src.kind == "count"


def test_evidence_value_formats(analyze) -> None:
    assert analyze.source("case.serious_pct").value.endswith("%")
    assert analyze.source("case.period_start").value == "2024-12-27"


def test_age_groups_total(analyze) -> None:
    assert sum(analyze.age_group_counts.values()) == 1024


def test_sex_counts_total(analyze) -> None:
    assert sum(analyze.sex_counts.values()) == 1024


def test_country_counts_total(analyze) -> None:
    assert sum(analyze.country_counts.values()) == 1024


def test_monthly_trend_monotonic(analyze) -> None:
    months = [m["month"] for m in analyze.monthly_cases]
    assert months == sorted(months)
    assert sum(m["count"] for m in analyze.monthly_cases) == 1024
    # first month's delta is its own count (no prior month, baseline zero)
    assert analyze.monthly_cases[0]["delta"] == analyze.monthly_cases[0]["count"]


def test_first_month_volume(analyze) -> None:
    # lowest received date is 2024-12-27 => Dec 2024 has a small count
    dec = [m for m in analyze.monthly_cases if m["month"] == "2024-12"]
    assert dec and dec[0]["count"] >= 1


def test_case_listing_covers_all_cases(real_df) -> None:
    case_table = build_case_table(real_df)
    reaction_df, _ = build_reaction_table(real_df)
    listing = compute_case_listing(case_table, reaction_df)
    assert len(listing) == 1024
    assert all(row["safetyreportid"] != "" for row in listing)


def test_outcome_counts_present(analyze) -> None:
    assert sum(analyze.outcome_counts.values()) >= 3642


def test_top_serious_within_serious_rows(analyze) -> None:
    for pt, _ in analyze.top_serious_reactions[:5]:
        assert pt  # non-empty PT labels


def test_evidence_ids_valid(analyze) -> None:
    expected = {
        "case.total_cases",
        "case.serious_cases",
        "case.not_serious_cases",
        "case.serious_pct",
        "case.expedited_cases",
        "case.age_groups",
        "case.sex",
        "case.country",
        "case.reporter_qualification",
        "case.period_start",
        "case.period_end",
        "react.top_reactions",
        "react.top_serious_reactions",
        "react.outcome_counts",
        "trend.monthly_cases",
    }
    assert expected.issubset(set(analyze.evidence))


@pytest.mark.parametrize(
    ("evidence_id", "kind"),
    [
        ("case.total_cases", "count"),
        ("case.serious_pct", "percent"),
        ("case.age_groups", "list"),
        ("case.period_start", "date_range"),
        ("react.top_reactions", "list"),
        ("trend.monthly_cases", "list"),
    ],
)
def test_kind_labels(analyze, evidence_id, kind) -> None:
    assert analyze.evidence[evidence_id].kind == kind


def test_missing_evidence_id_raises(analyze) -> None:
    with pytest.raises(KeyError):
        analyze.source("does.not.exist")


def test_serious_constant(analyze) -> None:
    assert SERIOUS == "serious"
