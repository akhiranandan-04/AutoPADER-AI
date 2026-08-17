"""Tests for evidence packets, prompt rendering, grounding, review and report."""

from __future__ import annotations

import pytest

from autopader.analysis import compute_all
from autopader.config.report_config import REPORT_SECTIONS, SECTION_ORDER
from autopader.data.normalizer import build_case_table, build_reaction_table
from autopader.evidence.manifest import build_manifest
from autopader.evidence.packet import packet_for
from autopader.llm.client import EchoClient
from autopader.llm.generator import generate_section
from autopader.llm.grounding import extract_numbers, grounding_check
from autopader.llm.prompts import render_prompt, render_template
from autopader.report.assembler import ReportNotReadyError, assemble_report
from autopader.review.review import ReviewState, load_review_state, save_review_state


@pytest.fixture(scope="module")
def results(real_df_module):
    case_table = build_case_table(real_df_module)
    reaction_df, _ = build_reaction_table(real_df_module)
    return compute_all(case_table, reaction_df, "testhash")


def test_packet_scoping_excludes_other_sections(results) -> None:
    packet = packet_for("narrative_summary", results)
    ids = set(packet.evidence_ids)
    assert "case.total_cases" in ids
    assert "trend.monthly_cases" not in ids  # trends packet only for trends


def test_packet_matches_declared_evidence(results) -> None:
    for section in SECTION_ORDER:
        packet = packet_for(section, results)
        declared = REPORT_SECTIONS[section]["required_evidence"]
        assert set(packet.evidence_ids) == set(declared)


def test_packet_unknown_section(results) -> None:
    with pytest.raises(ValueError):
        packet_for("not_a_section", results)


def test_packet_missing_evidence_key(results) -> None:
    # remove a required key and expect a clear error
    ev = dict(results.evidence)
    ev.pop("case.total_cases")
    stub = results.model_copy(update={"evidence": ev})
    with pytest.raises(KeyError):
        packet_for("narrative_summary", stub)


def test_packet_carries_limitations(results) -> None:
    packet = packet_for("reaction_analysis", results)
    assert any("expectedness" in line for line in packet.limitations)


def test_prompt_contains_only_packet_values(results) -> None:
    packet = packet_for("narrative_summary", results)
    messages = render_prompt("narrative_summary", packet)
    assert messages[0]["role"] == "system"
    assert "pharmacovigilance report writer" in messages[0]["content"]
    user = messages[1]["content"]
    assert "1,024" in user
    assert "trend.monthly_cases" not in user
    assert "no raw dataset" not in user


@pytest.mark.parametrize(
    ("section", "required_phrases"),
    [
        (
            "narrative_summary",
            [
                "total number of unique cases",
                "serious case count",
                "expedited",
                "most frequently reported reaction",
                "chain-of-thought",
            ],
        ),
        (
            "serious_alerts",
            [
                'Do NOT respond with "None"',
                "number of serious cases",
                "number of expedited",
                "top_serious_reactions",
                "chain-of-thought",
            ],
        ),
        (
            "trends",
            [
                "None",
                "trend.monthly_cases",
                "largest increase",
                "largest decrease",
                "at least six figures",
                "chain-of-thought",
            ],
        ),
    ],
)
def test_section_prompt_requires_substantive_output(results, section, required_phrases) -> None:
    packet = packet_for(section, results)
    user = render_prompt(section, packet)[1]["content"]
    for phrase in required_phrases:
        assert phrase in user, f"section prompt for {section} lacks: {phrase!r}"


def test_render_template_leftover_placeholder() -> None:
    with pytest.raises(KeyError):
        render_template("hello {{missing}}", present="x")


def test_render_template_unknown_placeholder() -> None:
    with pytest.raises(KeyError):
        render_template("hello {{unknown}}")


def test_grounding_pass_for_quoted_figures(results) -> None:
    packet = packet_for("narrative_summary", results)
    text = "During 2024-12-27 to 2025-12-26 there were 1,024 cases; 1,023 were serious (99.9%)."
    passed, offenders = grounding_check("narrative_summary", text, packet)
    assert passed, offenders


def test_grounding_flags_fabricated_number(results) -> None:
    packet = packet_for("narrative_summary", results)
    text = "There were 999,999 cases."
    passed, offenders = grounding_check("narrative_summary", text, packet)
    assert not passed
    assert "999999" in offenders


def test_extract_numbers() -> None:
    assert extract_numbers("1,024 and 99.9% and 3.5 and none") == {"1024", "99.9", "3.5"}


def test_echo_generation_grounds(results) -> None:
    section = generate_section(
        "narrative_summary",
        results,
        lambda packet: EchoClient(packet),
    )
    assert section.grounding_passed, section.grounding_offenders
    assert section.section == "narrative_summary"
    assert section.model == "echo"


def test_review_state_roundtrip(tmp_path) -> None:
    path = tmp_path / "review_state.json"
    state = ReviewState()
    state.set_status("narrative_summary", "approved", note="ok")
    state.set_status("trends", "edited", edited_text="custom text")
    save_review_state(state, path)
    loaded = load_review_state(path)
    assert loaded.get("narrative_summary").status == "approved"
    assert loaded.get("trends").edited_text == "custom text"


def test_review_load_missing_file(tmp_path) -> None:
    state = load_review_state(tmp_path / "missing.json")
    assert state.reviews == {}
    assert state.get("narrative_summary").status == "pending"


def test_pending_blocks_final(results) -> None:
    generated = _echo_generated(results)
    review = ReviewState()
    manifest = build_manifest("hash", "echo", "p1", {s: g.packet for s, g in generated.items()})
    with pytest.raises(ReportNotReadyError):
        assemble_report(results, generated, review, manifest, allow_pending=False)


def test_approved_allows_final(results) -> None:
    generated = _echo_generated(results)
    review = ReviewState()
    for section in generated:
        review.set_status(section, "approved")
    manifest = build_manifest("hash", "echo", "p1", {s: g.packet for s, g in generated.items()})
    markdown = assemble_report(results, generated, review, manifest, allow_pending=False)
    assert "PADER-style Periodic Report" in markdown
    assert "Case Index" in markdown
    assert "Appendix" in markdown


def test_edited_text_precedence(results) -> None:
    generated = _echo_generated(results)
    review = ReviewState()
    for section in generated:
        review.set_status(section, "approved")
    review.set_status("narrative_summary", "edited", edited_text="REVIEWER WORDS")
    manifest = build_manifest("hash", "echo", "p1", {s: g.packet for s, g in generated.items()})
    markdown = assemble_report(results, generated, review, manifest, allow_pending=False)
    assert "REVIEWER WORDS" in markdown
    assert "Edited by reviewer" in markdown


def test_edited_text_survives_approve_after_edit(results) -> None:
    generated = _echo_generated(results)
    review = ReviewState()
    for section in generated:
        review.set_status(section, "approved")
    review.set_status("narrative_summary", "edited", edited_text="REVIEWER WORDS")
    review.set_status("narrative_summary", "approved", note="reviewer approved the edit")
    manifest = build_manifest("hash", "echo", "p1", {s: g.packet for s, g in generated.items()})
    markdown = assemble_report(results, generated, review, manifest, allow_pending=False)
    assert "REVIEWER WORDS" in markdown
    assert review.get("narrative_summary").status == "approved"
    assert "Edited by reviewer" in markdown


def test_allow_pending_drafts(results) -> None:
    generated = _echo_generated(results)
    review = ReviewState()  # all pending
    manifest = build_manifest("hash", "echo", "p1", {s: g.packet for s, g in generated.items()})
    markdown = assemble_report(results, generated, review, manifest, allow_pending=True)
    assert "not included in the final report" in markdown


def _echo_generated(results) -> dict:
    generated = {}
    for section in (
        "narrative_summary",
        "summary_analysis",
        "reaction_analysis",
        "serious_alerts",
        "trends",
        "history_of_actions",
    ):
        generated[section] = generate_section(section, results, lambda packet: EchoClient(packet))
    return generated
