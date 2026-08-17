"""Assemble the final PADER-style Markdown report.

Narrative sections use only approved/edited LLM text; tabular sections are
rendered deterministically from AnalysisResult; a traceability appendix lists
per-section evidence ids with values and provenance, plus the manifest.
"""

from __future__ import annotations

from ..analysis.results import AnalysisResult
from ..config import report_config
from ..evidence.manifest import ReportManifest
from ..llm.generator import GeneratedSection
from ..review.review import ReviewState, can_finalize
from .case_listing import case_index_table


class ReportNotReadyError(RuntimeError):
    pass


def _table(headers: list[str], rows: list[list[str]]) -> str:
    header_line = "| " + " | ".join(headers) + " |"
    sep_line = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join([header_line, sep_line, *body])


def _count_table(title: str, counts: dict[str, int]) -> str:
    headers = [title, "count"]
    rows = [[k, f"{v:,}"] for k, v in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]
    return _table(headers, rows)


def _pair_table(title: str, pairs: list[tuple[str, int]]) -> str:
    return _count_table(title, dict(pairs))


def _trends_table(monthly: list[dict]) -> str:
    headers = ["month", "cases", "delta vs prior month"]
    rows = [
        [m["month"], f"{m['count']:,}", f"{'+' if m['delta'] >= 0 else '-'}{abs(m['delta'])}"]
        for m in monthly
    ]
    return _table(headers, rows)


def _render_narrative(
    section: str,
    generated: dict[str, GeneratedSection],
    review: ReviewState,
    allow_pending: bool,
) -> str:
    if section not in generated:
        raise ReportNotReadyError(f"no generated text for section '{section}'")
    status = review.get(section).status
    if not can_finalize(status):
        if allow_pending:
            return (
                f"> **Review required:** section '{section}' has status "
                f"'{status}' and is not included in the final report.\n\n"
                "> Draft (not finalized):\n\n"
                f"{generated[section].text}"
            )
        raise ReportNotReadyError(
            f"section '{section}' has status '{status}'; approve or edit before finalizing"
        )
    if review.get(section).edited_text:
        edited = review.get(section).edited_text
        return f"{edited}\n\n> *Edited by reviewer; replaces AI-generated text.*"
    return generated[section].text


def _summary_analysis_table(results: AnalysisResult) -> str:
    blocks = [
        _count_table("Age group", results.age_group_counts),
        _count_table("Sex", results.sex_counts),
        _count_table("Country", results.country_counts),
        _count_table("Reporter qualification", results.reporter_qualification_counts),
    ]
    return "\n\n".join(blocks)


def assemble_report(
    results: AnalysisResult,
    generated: dict[str, GeneratedSection],
    review: ReviewState,
    manifest: ReportManifest,
    allow_pending: bool = False,
) -> str:
    """Assemble the full Markdown report string."""
    sections: list[str] = []
    cfg = report_config
    period_start, period_end = results.reporting_period

    # 1. Reporting period header (deterministic)
    sections.append(
        "\n".join(
            [
                f"# PADER-style Periodic Report — {cfg.PRODUCT_NAME}",
                "",
                f"- **Reporting period:** {period_start} to {period_end}",
                f"- **Product:** {cfg.PRODUCT_NAME}",
                f"- **Report type:** {cfg.REPORT_TYPE}",
                f"- **Application number:** {cfg.APPLICATION_NUMBER}",
                f"- **Dataset SHA-256:** {manifest.dataset_sha256}",
            ]
        )
    )

    narrative_sections = [
        "narrative_summary",
        "summary_analysis",
        "reaction_analysis",
        "serious_alerts",
        "trends",
        "history_of_actions",
    ]
    for section in narrative_sections:
        title = str(cfg.REPORT_SECTIONS[section]["title"])
        parts = [f"## {title}"]
        if section == "summary_analysis":
            parts.append(_render_narrative(section, generated, review, allow_pending))
            parts.append(_summary_analysis_table(results))
        elif section == "reaction_analysis":
            parts.append(_render_narrative(section, generated, review, allow_pending))
            parts.append(_pair_table("Most frequent reactions", results.top_reactions))
            parts.append(_count_table("Reaction outcome", results.outcome_counts))
        elif section == "serious_alerts":
            parts.append(_render_narrative(section, generated, review, allow_pending))
            parts.append(_pair_table("Reactions in serious cases", results.top_serious_reactions))
        elif section == "trends":
            parts.append(_render_narrative(section, generated, review, allow_pending))
            parts.append(_trends_table(results.monthly_cases))
        elif section == "history_of_actions":
            status = review.get(section).status
            if not can_finalize(status) and not allow_pending:
                raise ReportNotReadyError(
                    f"section '{section}' has status '{status}'; approve or edit before finalizing"
                )
            parts.append(
                "No history-of-actions data was supplied for this exercise; "
                "no regulatory actions are claimed or inferred."
            )
        else:
            parts.append(_render_narrative(section, generated, review, allow_pending))
        sections.append("\n".join(parts))

    # Case index (deterministic)
    sections.append("\n".join(["## Case Index", case_index_table(results.case_listing)]))

    # Traceability appendix
    sections.append(_appendix(generated, manifest))
    return "\n\n".join(sections) + "\n"


def _appendix(generated: dict[str, GeneratedSection], manifest: ReportManifest) -> str:
    lines = [
        "## Appendix — Traceability",
        "",
        "Provenance chain: dataset -> analysis function -> evidence packet -> narrative.",
        "",
    ]
    for section in report_config.SECTION_ORDER:
        if section not in generated:
            continue
        gs = generated[section]
        lines.append(f"### {section}")
        lines.append("| evidence_id | value | kind | provenance |")
        lines.append("| --- | --- | --- | --- |")
        for source in gs.packet.evidence:
            lines.append(
                f"| {source.evidence_id} | {source.value} | {source.kind} | {source.provenance} |"
            )
        if gs.grounding_passed:
            ground_line = "grounding: passed"
        else:
            offenders = ", ".join(gs.grounding_offenders)
            ground_line = f"grounding: FAILED: {offenders}"
        lines.append(ground_line)
        lines.append("")
    lines.append("### Manifest")
    lines.append(f"- dataset_sha256: {manifest.dataset_sha256}")
    lines.append(f"- analysis_version: {manifest.analysis_version}")
    lines.append(f"- model: {manifest.model}")
    lines.append(f"- prompt_version: {manifest.prompt_version}")
    lines.append(f"- generated_at: {manifest.generated_at}")
    return "\n".join(lines)
