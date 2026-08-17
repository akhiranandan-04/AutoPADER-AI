"""Per-section generation: packet -> prompt -> LLM -> grounding check."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from ..analysis.results import AnalysisResult
from ..evidence.packet import EvidencePacket, packet_for
from .client import LLMClient
from .grounding import QualitativeOffender, grounding_check, qualitative_check
from .prompts import PROMPTS_DIR, render_prompt


class GeneratedSection(BaseModel):
    section: str
    text: str
    grounding_passed: bool
    grounding_offenders: list[str] = Field(default_factory=list)
    qualitative_offenders: list[QualitativeOffender] = Field(default_factory=list)
    packet: EvidencePacket
    model: str


def generate_section(
    section: str,
    results: AnalysisResult,
    client_factory,  # Callable[[EvidencePacket], LLMClient]
    case_ids: list[int] | None = None,
    prompt_dir: Path = PROMPTS_DIR,
) -> GeneratedSection:
    """Generate one narrative section and run numeric + qualitative grounding."""
    packet = packet_for(section, results, case_ids=case_ids)
    client: LLMClient = client_factory(packet)
    messages = render_prompt(section, packet, prompt_dir=prompt_dir)
    text = client.generate(messages).strip()
    passed, offenders = grounding_check(section, text, packet)
    qualitative = qualitative_check(section, text, packet)
    return GeneratedSection(
        section=section,
        text=text,
        grounding_passed=passed and not qualitative,
        grounding_offenders=offenders,
        qualitative_offenders=qualitative,
        packet=packet,
        model=client.name,
    )
