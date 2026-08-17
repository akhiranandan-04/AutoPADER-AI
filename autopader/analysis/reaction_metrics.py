"""Reaction-level deterministic metrics.

Reaction analysis may use individual reaction rows (a case can contribute
several reactions). Counts are reaction-row counts per MedDRA Preferred Term,
deduplicated within a case only for the case-level listing.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd

from ..data.columns import REACTION_OUTCOME_COL, REACTION_PT_COL, SERIOUS, SERIOUS_NORM_COL
from .case_metrics import build_provenance
from .results import EvidenceSource, fmt_int, fmt_pairs

Provenance = Callable[[str], str]


def _outcomes_counts(reaction_df: pd.DataFrame) -> dict[str, int]:
    return {
        str(k): int(v)
        for k, v in reaction_df[REACTION_OUTCOME_COL]
        .fillna("unknown")
        .astype(str)
        .value_counts()
        .items()
    }


def top_pt_counts(reaction_df: pd.DataFrame, k: int = 10) -> list[tuple[str, int]]:
    counts = reaction_df[REACTION_PT_COL].value_counts().head(k).items()
    return [(str(pt), int(n)) for pt, n in counts]


def compute_reaction_metrics(
    reaction_df: pd.DataFrame, dataset_hash: str, top_k: int = 10
) -> tuple[dict[str, EvidenceSource], dict[str, Any]]:
    """Compute reaction-level evidence plus raw AnalysisResult fields."""
    prov = build_provenance(dataset_hash, module="reaction_metrics")
    evidence: dict[str, EvidenceSource] = {}

    top = top_pt_counts(reaction_df, top_k)
    evidence["react.top_reactions"] = EvidenceSource(
        evidence_id="react.top_reactions",
        value=fmt_pairs(top),
        kind="list",
        provenance=prov("compute_reaction_metrics.top_reactions"),
    )

    serious_rows = reaction_df[reaction_df[SERIOUS_NORM_COL] == SERIOUS]
    top_serious = top_pt_counts(serious_rows, top_k)
    evidence["react.top_serious_reactions"] = EvidenceSource(
        evidence_id="react.top_serious_reactions",
        value=fmt_pairs(top_serious),
        kind="list",
        provenance=prov("compute_reaction_metrics.top_serious_reactions"),
    )

    outcomes = _outcomes_counts(reaction_df)
    evidence["react.outcome_counts"] = EvidenceSource(
        evidence_id="react.outcome_counts",
        value=", ".join(f"{k}: {fmt_int(v)}" for k, v in sorted(outcomes.items())),
        kind="list",
        provenance=prov("compute_reaction_metrics.outcomes"),
    )

    fields: dict[str, Any] = {
        "top_reactions": top,
        "top_serious_reactions": top_serious,
        "outcome_counts": outcomes,
    }
    return evidence, fields
