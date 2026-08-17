"""Pydantic schemas for deterministic analysis results and evidence.

Every statistic used anywhere in the report is wrapped in an
:class:`EvidenceSource` carrying an ``evidence_id`` and the exact display
value the LLM may quote. ``provenance`` names the computing function plus the
analysis version and dataset hash, giving full traceability from a number in
the narrative back to deterministic Python.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ANALYSIS_VERSION = "1.0.0"

EvidenceKind = Literal["count", "percent", "list", "date_range", "flag", "ratio"]


def fmt_int(value: int) -> str:
    return f"{value:,}"


def fmt_pct(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "0.0%"
    return f"{100.0 * numerator / denominator:.1f}%"


def fmt_groups(counts: dict[str, int]) -> str:
    return ", ".join(f"{k}: {fmt_int(v)}" for k, v in sorted(counts.items()))


def fmt_pairs(pairs: list[tuple[str, int]]) -> str:
    return ", ".join(f"{name} ({fmt_int(n)})" for name, n in pairs)


class EvidenceSource(BaseModel):
    """One deterministic value a narrative section may reference."""

    evidence_id: str = Field(description="e.g. 'case.total_cases'")
    value: str = Field(description="exact display value the LLM may quote, e.g. '1,024'")
    kind: EvidenceKind
    provenance: str = Field(description="'module.function() v<version> dataset:<sha256 short>'")

    def quote(self) -> str:
        return self.value


class AnalysisResult(BaseModel):
    """Snapshot of the full deterministic analysis."""

    reporting_period: tuple[str, str]
    total_cases: int
    serious_cases: int
    not_serious_cases: int
    expedited_cases: int
    serious_pct: float
    age_group_counts: dict[str, int]
    sex_counts: dict[str, int]
    country_counts: dict[str, int]
    top_reactions: list[tuple[str, int]]
    top_serious_reactions: list[tuple[str, int]]
    outcome_counts: dict[str, int]
    monthly_cases: list[dict]
    reporter_qualification_counts: dict[str, int]
    case_listing: list[dict]
    evidence: dict[str, EvidenceSource] = Field(
        description="ALL computed values, keyed by evidence_id"
    )

    def source(self, evidence_id: str) -> EvidenceSource:
        try:
            return self.evidence[evidence_id]
        except KeyError:
            raise KeyError(f"no evidence source registered for '{evidence_id}'") from None
