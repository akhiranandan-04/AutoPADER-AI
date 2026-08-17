"""Pipeline: load -> validate -> normalize -> analyze -> generate -> review -> assemble."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .analysis import compute_all
from .data.loader import load_dataset
from .data.normalizer import build_case_table, build_reaction_table
from .data.validator import validate
from .evidence.manifest import ReportManifest, build_manifest
from .evidence.packet import EvidencePacket
from .llm.client import LLMClient, build_client
from .llm.generator import GeneratedSection, generate_section
from .llm.prompts import prompt_version
from .report.assembler import assemble_report
from .report.writer import write_report
from .review.review import load_review_state, save_review_state

ClientFactory = Callable[[EvidencePacket], LLMClient]


def default_client_factory(skip_llm: bool) -> ClientFactory:
    def _factory(packet: EvidencePacket) -> LLMClient:
        return build_client(packet, skip_llm=skip_llm)

    return _factory


def run_pipeline(
    dataset_path: str | Path,
    output_path: str | Path,
    review_path: str | Path,
    client_factory: ClientFactory | None = None,
    skip_llm: bool = False,
    allow_pending: bool = False,
) -> tuple[ReportManifest, Path]:
    """Run the full pipeline and write ``report_output.md``.

    Returns ``(manifest, output_path)``.
    """
    df, dataset_sha256 = load_dataset(dataset_path)
    validation = validate(df)
    if validation.errors:
        raise RuntimeError(f"dataset validation failed: {'; '.join(validation.errors)}")

    case_table = build_case_table(df)
    reaction_df, _ = build_reaction_table(df)
    results = compute_all(case_table, reaction_df, dataset_sha256[:8])

    factory = client_factory or default_client_factory(skip_llm=skip_llm)

    generated: dict[str, GeneratedSection] = {}
    sections = (
        "narrative_summary",
        "summary_analysis",
        "reaction_analysis",
        "serious_alerts",
        "trends",
        "history_of_actions",
    )
    for section in sections:
        generated[section] = generate_section(section, results, factory)

    review = load_review_state(Path(review_path))
    for section in generated:
        review.get(section)  # ensure every section has a review entry

    manifest = build_manifest(
        dataset_sha256=dataset_sha256,
        model=next(iter(generated.values())).model,
        prompt_version=prompt_version(),
        packets={s: g.packet for s, g in generated.items()},
    )

    markdown = assemble_report(
        results,
        generated,
        review,
        manifest,
        allow_pending=allow_pending,
    )
    output = write_report(output_path, markdown)
    save_review_state(review, Path(review_path))
    return manifest, output
