"""Evidence packet construction: the mechanism that keeps the LLM scoped.

``packet_for`` returns ONLY the evidence keys a section is allowed to see.
The LLM can never access the full analysis result or raw dataset.
"""

from __future__ import annotations

from typing import cast

from pydantic import BaseModel, Field

from ..analysis.results import AnalysisResult, EvidenceSource
from ..config import report_config


class EvidencePacket(BaseModel):
    """Scoped evidence for a single narrative section."""

    section: str
    evidence: list[EvidenceSource] = Field(description="ONLY what this section may reference")
    case_ids: list[int] = Field(
        default_factory=list, description="source case IDs where appropriate"
    )
    limitations: list[str]
    narration_rules: list[str]

    @property
    def evidence_ids(self) -> list[str]:
        return [e.evidence_id for e in self.evidence]


def packet_for(
    section: str,
    results: AnalysisResult,
    case_ids: list[int] | None = None,
) -> EvidencePacket:
    """Build the packet containing ONLY the section's declared evidence keys."""
    if section not in report_config.REPORT_SECTIONS:
        raise ValueError(f"unknown report section '{section}'")

    declared = report_config.REPORT_SECTIONS[section]
    required: list[str] = cast(list[str], declared["required_evidence"])
    missing = [key for key in required if key not in results.evidence]
    if missing:
        raise KeyError(f"section '{section}' requires evidence keys not computed: {missing}")

    evidence = [results.evidence[key] for key in required]
    rules: list[str] = cast(list[str], declared["narration_rules"])
    return EvidencePacket(
        section=section,
        evidence=evidence,
        case_ids=list(case_ids or []),
        limitations=list(report_config.LIMITATIONS),
        narration_rules=rules,
    )
