"""Case-level deterministic metrics.

All case-level counts use unique ``safetyreportid`` (AGENTS.md: do not confuse
row count with case count). A case's demographic fields come from its first
row in the normalized case table.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd

from ..data.columns import (
    AGE_BUCKET_COL,
    COUNTRY_COL,
    EXPEDITE_NORM_COL,
    NOT_SERIOUS,
    REACTION_PT_COL,
    RECEIVED_DATE_COL,
    REPORTER_QUALIFICATION_COL,
    SAFETYREPORTID,
    SERIOUS,
    SERIOUS_NORM_COL,
    SEX_COL,
)
from ..data.normalizer import CaseTable
from .results import (
    ANALYSIS_VERSION,
    EvidenceKind,
    EvidenceSource,
    fmt_groups,
    fmt_int,
    fmt_pct,
)

Provenance = Callable[[str], str]


def build_provenance(dataset_hash: str, module: str = "case_metrics") -> Provenance:
    """Build a provenance formatter bound to the dataset hash and module name."""

    def _prov(evidence_id: str) -> str:
        return f"{module}.{evidence_id}() v{ANALYSIS_VERSION} dataset:{dataset_hash}"

    return _prov


def _show_counts(series: pd.Series) -> dict[str, int]:
    return {str(k): int(v) for k, v in series.value_counts(dropna=False).items()}


def compute_case_metrics(
    case_table: CaseTable, dataset_hash: str
) -> tuple[dict[str, EvidenceSource], dict[str, Any]]:
    """Compute case-level evidence plus raw AnalysisResult fields."""
    prov = build_provenance(dataset_hash)
    cases: pd.DataFrame = case_table.rows
    report = case_table.report
    evidence: dict[str, EvidenceSource] = {}

    total = report.unique_cases
    serious = int((cases[SERIOUS_NORM_COL] == SERIOUS).sum())
    not_serious = int((cases[SERIOUS_NORM_COL] == NOT_SERIOUS).sum())
    expedited = int(cases[EXPEDITE_NORM_COL].eq("yes").sum())

    evidence["case.total_cases"] = _case_metric(prov, "case.total_cases", fmt_int(total), "count")
    evidence["case.serious_cases"] = _case_metric(
        prov, "case.serious_cases", fmt_int(serious), "count"
    )
    evidence["case.not_serious_cases"] = _case_metric(
        prov, "case.not_serious_cases", fmt_int(not_serious), "count"
    )
    evidence["case.serious_pct"] = _case_metric(
        prov, "case.serious_pct", fmt_pct(serious, total), "percent"
    )
    evidence["case.expedited_cases"] = _case_metric(
        prov, "case.expedited_cases", fmt_int(expedited), "count"
    )

    age_groups = _show_counts(cases[AGE_BUCKET_COL])
    evidence["case.age_groups"] = _case_metric(
        prov, "case.age_groups", fmt_groups(age_groups), "list"
    )
    sex_counts = _show_counts(cases[SEX_COL].fillna("unknown").astype(str).str.lower())
    evidence["case.sex"] = _case_metric(prov, "case.sex", fmt_groups(sex_counts), "list")
    country_counts = _show_counts(cases[COUNTRY_COL].fillna("unknown").astype(str))
    evidence["case.country"] = _case_metric(
        prov, "case.country", fmt_groups(country_counts), "list"
    )
    qual_counts = _show_counts(cases[REPORTER_QUALIFICATION_COL].fillna("unknown").astype(str))
    evidence["case.reporter_qualification"] = _case_metric(
        prov, "case.reporter_qualification", fmt_groups(qual_counts), "list"
    )

    period_start_t = cases[RECEIVED_DATE_COL].min()
    period_end_t = cases[RECEIVED_DATE_COL].max()
    period_start = period_start_t.isoformat() if period_start_t is not None else "unknown"
    period_end = period_end_t.isoformat() if period_end_t is not None else "unknown"
    evidence["case.period_start"] = _case_metric(
        prov, "case.period_start", period_start, "date_range"
    )
    evidence["case.period_end"] = _case_metric(prov, "case.period_end", period_end, "date_range")

    fields: dict[str, Any] = {
        "reporting_period": (period_start, period_end),
        "total_cases": total,
        "serious_cases": serious,
        "not_serious_cases": not_serious,
        "expedited_cases": expedited,
        "serious_pct": round(100.0 * serious / total, 1) if total else 0.0,
        "age_group_counts": age_groups,
        "sex_counts": sex_counts,
        "country_counts": country_counts,
        "reporter_qualification_counts": qual_counts,
    }
    return evidence, fields


def compute_case_listing(case_table: CaseTable, reaction_df: pd.DataFrame) -> list[dict]:
    """Build case-index rows (one per unique case) for the tabular listing."""
    reactions_joined = (
        reaction_df.groupby(SAFETYREPORTID)[REACTION_PT_COL]
        .apply(lambda s: "; ".join(dict.fromkeys(s)))
        .to_dict()
    )
    panel = []
    for _, row in case_table.rows.iterrows():
        case_id = int(row[SAFETYREPORTID])
        received = row.get(RECEIVED_DATE_COL)
        panel.append(
            {
                "safetyreportid": case_id,
                "serious_norm": str(row[SERIOUS_NORM_COL]),
                "expedited": str(row.get(EXPEDITE_NORM_COL, "unknown")),
                "sex": str(row.get(SEX_COL, "unknown")),
                "age_bucket": str(row.get(AGE_BUCKET_COL, "unknown")),
                "country": str(row.get(COUNTRY_COL, "unknown")),
                "received_date": (received.isoformat() if received is not None else "unknown"),
                "reactions": reactions_joined.get(case_id, ""),
            }
        )
    return panel


def _case_metric(
    prov: Provenance, evidence_id: str, value: str, kind: EvidenceKind
) -> EvidenceSource:
    return EvidenceSource(
        evidence_id=evidence_id, value=value, kind=kind, provenance=prov(evidence_id)
    )
