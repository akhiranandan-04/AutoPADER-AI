"""Deterministic analysis: case metrics, reaction metrics, time trends.

``compute_all`` runs every metric family against the normalized tables and
returns a single :class:`AnalysisResult` whose ``evidence`` dict keyed by
evidence_id is the complete, traceable evidence set.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from ..data.normalizer import CaseTable
from .case_metrics import compute_case_listing, compute_case_metrics
from .reaction_metrics import compute_reaction_metrics
from .results import AnalysisResult, EvidenceSource
from .time_trends import compute_time_trends


def compute_all(
    case_table: CaseTable, reaction_df: pd.DataFrame, dataset_hash: str
) -> AnalysisResult:
    """Run the full deterministic analysis and return the merged result.

    ``dataset_hash`` (short) is embedded in every EvidenceSource's provenance,
    binding each number to the exact file it was computed from.
    """
    case_evidence, case_fields = compute_case_metrics(case_table, dataset_hash)
    reaction_evidence, reaction_fields = compute_reaction_metrics(reaction_df, dataset_hash)
    trend_evidence, trend_fields = compute_time_trends(case_table, dataset_hash)

    evidence: dict[str, EvidenceSource] = {}
    evidence.update(case_evidence)
    evidence.update(reaction_evidence)
    evidence.update(trend_evidence)

    fields: dict[str, object] = {}
    fields.update(case_fields)
    fields.update(reaction_fields)
    fields.update(trend_fields)
    fields["case_listing"] = compute_case_listing(case_table, reaction_df)

    reporting_period = _two_tuple(fields["reporting_period"])
    return AnalysisResult(
        reporting_period=reporting_period,
        total_cases=_int(fields["total_cases"]),
        serious_cases=_int(fields["serious_cases"]),
        not_serious_cases=_int(fields["not_serious_cases"]),
        expedited_cases=_int(fields["expedited_cases"]),
        serious_pct=_float(fields["serious_pct"]),
        age_group_counts=_str_int_dict(fields["age_group_counts"]),
        sex_counts=_str_int_dict(fields["sex_counts"]),
        country_counts=_str_int_dict(fields["country_counts"]),
        top_reactions=_pairs(fields["top_reactions"]),
        top_serious_reactions=_pairs(fields["top_serious_reactions"]),
        outcome_counts=_str_int_dict(fields["outcome_counts"]),
        monthly_cases=_list_field(fields["monthly_cases"]),
        reporter_qualification_counts=_str_int_dict(fields["reporter_qualification_counts"]),
        case_listing=_list_field(fields["case_listing"]),
        evidence=evidence,
    )


def _two_tuple(value: Any) -> tuple[str, str]:
    assert isinstance(value, (tuple, list)) and len(value) == 2
    return str(value[0]), str(value[1])


def _int(value: Any) -> int:
    return int(value)


def _float(value: Any) -> float:
    return float(value)


def _str_int_dict(value: Any) -> dict[str, int]:
    return {str(k): int(v) for k, v in (value or {}).items()}


def _pairs(value: Any) -> list[tuple[str, int]]:
    return [(str(k), int(v)) for k, v in (value or [])]


def _list_field(value: Any) -> list:
    return list(value or [])
