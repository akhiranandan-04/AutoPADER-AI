"""Time-trend metrics: monthly case volume from received dates.

Only factual statements are produced (counts and deltas) — no signal
inference. Months with no data simply have count 0 (with delta 0).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd

from ..data.columns import RECEIVED_DATE_COL
from ..data.normalizer import CaseTable
from .case_metrics import build_provenance
from .results import EvidenceSource, fmt_int

Provenance = Callable[[str], str]


def monthly_case_counts(cases: pd.DataFrame) -> list[dict]:
    """Count cases per calendar month of received date; return chronological list."""
    dates = pd.to_datetime(cases[RECEIVED_DATE_COL])
    months = dates.dt.to_period("M")
    counts = months.value_counts().sort_index()
    if counts.empty:
        return []
    out: list[dict] = []
    prev = 0
    for period, count in counts.items():
        delta = int(count) - prev
        out.append({"month": str(period), "count": int(count), "delta": delta})
        prev = int(count)
    return out


def compute_time_trends(
    case_table: CaseTable, dataset_hash: str
) -> tuple[dict[str, EvidenceSource], dict[str, Any]]:
    """Compute trend evidence plus raw AnalysisResult fields."""
    prov = build_provenance(dataset_hash, module="time_trends")
    evidence: dict[str, EvidenceSource] = {}

    monthly = monthly_case_counts(case_table.rows)
    rendered = ", ".join(
        f"{m['month']}: {fmt_int(m['count'])} "
        f"({'+' if m['delta'] >= 0 else '-'}{abs(m['delta'])})"
        for m in monthly
    )
    evidence["trend.monthly_cases"] = EvidenceSource(
        evidence_id="trend.monthly_cases",
        value=rendered if rendered else "no dated cases",
        kind="list",
        provenance=prov("compute_time_trends.monthly_cases"),
    )

    return evidence, {"monthly_cases": monthly}
