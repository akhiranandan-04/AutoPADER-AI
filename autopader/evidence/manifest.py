"""Traceability manifest for one generated report.

Binds the dataset hash, analysis version, model and prompt version to the
per-section evidence ids actually used, forming the provenance chain
dataset -> analysis function -> packet -> narrative.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from ..analysis.results import ANALYSIS_VERSION
from .packet import EvidencePacket


class ReportManifest(BaseModel):
    dataset_sha256: str
    analysis_version: str
    model: str
    prompt_version: str
    generated_at: str
    sections: dict[str, list[str]] = Field(description="section -> evidence_ids used")


def build_manifest(
    dataset_sha256: str,
    model: str,
    prompt_version: str,
    packets: dict[str, EvidencePacket],
    generated_at: str | None = None,
) -> ReportManifest:
    return ReportManifest(
        dataset_sha256=dataset_sha256,
        analysis_version=ANALYSIS_VERSION,
        model=model,
        prompt_version=prompt_version,
        generated_at=generated_at or datetime.now(UTC).isoformat(),
        sections={section: packet.evidence_ids for section, packet in packets.items()},
    )
