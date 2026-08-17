"""Adversarial grounding tests: numeric gate + qualitative gate.

The numeric gate (``grounding_check``) rejects invented numbers. The
qualitative gate (``qualitative_check``) rejects unsupported interpretation
claims — expectedness, System Organ Class, regulatory actions, safety signals,
and causality — while leaving ordinary observed-data descriptions alone.

No production code is modified by these tests.
"""

from __future__ import annotations

import pytest

from autopader.analysis import compute_all
from autopader.data.normalizer import build_case_table, build_reaction_table
from autopader.evidence.packet import packet_for
from autopader.llm.generator import generate_section
from autopader.llm.grounding import extract_numbers, grounding_check, qualitative_check


class StubClient:
    """Deterministic client that returns a canned adversarial response."""

    name = "adversarial"

    def __init__(self, text: str) -> None:
        self._text = text

    def generate(self, messages: list[dict]) -> str:
        return self._text


@pytest.fixture(scope="module")
def results(real_df_module):
    case_table = build_case_table(real_df_module)
    reaction_df, _ = build_reaction_table(real_df_module)
    return compute_all(case_table, reaction_df, "adversarialhash")


def grounded_facts(section: str, results) -> str:
    """Narrative built ONLY from the packet's own values (numeric gate immune)."""
    packet = packet_for(section, results)
    return " ".join(source.value for source in packet.evidence)


def offenders_by_rule(offenders, rule: str):
    return [o for o in offenders if o.rule == rule]


# --- numeric gate ---


def test_numeric_hallucination_rejected(results) -> None:
    packet = packet_for("narrative_summary", results)
    text = grounded_facts("narrative_summary", results) + " There were 424,242 cases."
    passed, offenders = grounding_check("narrative_summary", text, packet)
    assert not passed
    assert "424242" in offenders


def test_valid_number_accepted(results) -> None:
    packet = packet_for("narrative_summary", results)
    text = "During 2024-12-27 to 2025-12-26 there were 1,024 cases; " "1,023 were serious (99.9%)."
    passed, offenders = grounding_check("narrative_summary", text, packet)
    assert passed, offenders


# --- Issue 2: fixed 15-day regulatory window is not a data statistic ---


def test_fixed_15_day_window_not_flagged(results) -> None:
    assert extract_numbers("expedited (15-day) reports") == set()
    assert extract_numbers("expedited (15 day) reports") == set()
    assert extract_numbers("15\u2011day reporting window") == set()
    packet = packet_for("narrative_summary", results)
    text = "During the period, 1,023 expedited (15-day) reports were made."
    passed, offenders = grounding_check("narrative_summary", text, packet)
    assert passed, offenders


def test_fabricated_fifteen_still_flagged(results) -> None:
    assert extract_numbers("15 cases were reported") == {"15"}
    packet = packet_for("narrative_summary", results)
    passed, offenders = grounding_check("narrative_summary", "15 cases were reported", packet)
    assert not passed
    assert "15" in offenders


# --- Issue 1: limitation/denial echo must NOT be flagged ---

_LIMITATION_ECHO_STATEMENTS = [
    "No System Organ Class field supplied.",
    "System Organ Class data were not provided.",
    "Expectedness is not assessed.",
    "Expectedness could not be evaluated because no label was supplied.",
    "No history of regulatory actions was provided.",
    "No System Organ Class field supplied; analysis is at Preferred Term level only.",
    "No product label/CCDS supplied; expectedness is not assessed.",
    "No history-of-actions data supplied for this exercise.",
]


@pytest.mark.parametrize("statement", _LIMITATION_ECHO_STATEMENTS)
def test_limitation_echo_statements_allowed(results, statement) -> None:
    packet = packet_for("reaction_analysis", results)
    offenders = qualitative_check("reaction_analysis", statement, packet)
    assert offenders == [], [o.rule for o in offenders]


# --- Issue 1: unsupported claims must STILL be flagged ---

_UNSUPPORTED_CLAIMS = [
    ("The event belongs to the Nervous System SOC.", "system_organ_class"),
    ("The event was expected according to the label.", "expectedness"),
    ("A regulatory action was taken.", "history_of_actions"),
    ("The product was proven safe.", "safety_conclusion"),
    ("A new safety signal was confirmed.", "safety_signal"),
    ("Bisoprolol caused the event.", "causality"),
]


@pytest.mark.parametrize(("statement", "rule"), _UNSUPPORTED_CLAIMS)
def test_unsupported_claims_still_flagged(results, statement, rule) -> None:
    packet = packet_for("reaction_analysis", results)
    offenders = qualitative_check("reaction_analysis", statement, packet)
    assert any(
        o.rule == rule for o in offenders
    ), f"expected rule {rule!r} to be flagged for: {statement!r}"


# --- qualitative gate: unsupported claims must be flagged ---


def test_expectedness_claim_rejected(results) -> None:
    packet = packet_for("reaction_analysis", results)
    facts = grounded_facts("reaction_analysis", results)
    text = facts + " The most frequent reaction is expected according to the product label/CCDS."
    offenders = qualitative_check("reaction_analysis", text, packet)
    expected = offenders_by_rule(offenders, "expectedness")
    assert expected, "expectedness claim was not flagged"
    assert expected[0].section == "reaction_analysis"
    assert expected[0].matched_phrase


def test_soc_claim_rejected(results) -> None:
    packet = packet_for("reaction_analysis", results)
    facts = grounded_facts("reaction_analysis", results)
    text = facts + " The most frequent reaction belongs to System Organ Class Cardiac disorders."
    offenders = qualitative_check("reaction_analysis", text, packet)
    assert offenders_by_rule(offenders, "system_organ_class"), "SOC claim was not flagged"


def test_regulatory_action_rejected(results) -> None:
    packet = packet_for("narrative_summary", results)
    facts = grounded_facts("narrative_summary", results)
    text = facts + " A regulatory action was taken as a result of these reports."
    offenders = qualitative_check("narrative_summary", text, packet)
    assert offenders_by_rule(offenders, "history_of_actions"), "action claim was not flagged"


def test_safety_signal_rejected(results) -> None:
    packet = packet_for("narrative_summary", results)
    facts = grounded_facts("narrative_summary", results)
    text = facts + " These data suggest a new safety signal of bradycardia."
    offenders = qualitative_check("narrative_summary", text, packet)
    assert offenders_by_rule(offenders, "safety_signal"), "signal claim was not flagged"


def test_safety_conclusion_rejected(results) -> None:
    packet = packet_for("narrative_summary", results)
    facts = grounded_facts("narrative_summary", results)
    text = facts + " Bisoprolol has a favorable safety profile."
    offenders = qualitative_check("narrative_summary", text, packet)
    assert offenders_by_rule(offenders, "safety_conclusion"), "safety conclusion was not flagged"


def test_causality_claim_rejected(results) -> None:
    packet = packet_for("narrative_summary", results)
    facts = grounded_facts("narrative_summary", results)
    text = facts + " Bisoprolol caused the bradycardia reported above."
    offenders = qualitative_check("narrative_summary", text, packet)
    assert offenders_by_rule(offenders, "causality"), "causality claim was not flagged"


# --- qualitative gate: ordinary observed data must NOT be flagged ---


def test_observed_data_narrative_passes(results) -> None:
    packet = packet_for("narrative_summary", results)
    text = (
        "1,023 cases were serious. Headache was among the reported reactions. "
        "The number of reports increased in March."
    )
    qual = qualitative_check("narrative_summary", text, packet)
    assert qual == [], [o.matched_phrase for o in qual]
    passed, offenders = grounding_check("narrative_summary", text, packet)
    assert passed, offenders


def test_clean_trends_narrative_passes(results) -> None:
    packet = packet_for("trends", results)
    text = (
        "During the reporting period 2024-12-27 to 2025-12-26, case volumes ranged "
        "from 21 (2024-12) to 109 (2025-07). The largest increase occurred in "
        "2025-01 (+54) and the largest decrease in 2025-08 (-45). Two additional "
        "months, 2025-02 (94, +19) and 2025-10 (102, +26), also contributed to the rise."
    )
    qual = qualitative_check("trends", text, packet)
    assert qual == [], [o.matched_phrase for o in qual]
    passed, offenders = grounding_check("trends", text, packet)
    assert passed, offenders


# --- Issue: chain-of-thought / prompt-echo leaks must be flagged ---

_COT_LEAKS = [
    "We need to produce a concise professional paragraph (4-7 sentences) built from the table.",
    "We need to extract from trend.monthly_cases: list of months with counts and deltas.",
    "Lowest: 2024-12 with 21. Highest: 2025-07 with 109. We need to quote at least six figures.",
    "The requirement says we must quote figures verbatim from the evidence packet.",
    "Let's parse counts: 21, 75, 94. We can include 2025-02 (94, +19).",
    "We must open with the reporting period sentence.",
    "During the reporting period 2024-12-27 to 2025-12-26, case volumes ranged "
    "from <lowest-month count> to <highest-month count>.",
]


@pytest.mark.parametrize("statement", _COT_LEAKS)
def test_chain_of_thought_leaks_flagged(results, statement) -> None:
    packet = packet_for("trends", results)
    offenders = qualitative_check("trends", statement, packet)
    assert offenders_by_rule(offenders, "chain_of_thought"), statement


def test_placeholder_residue_flagged(results) -> None:
    packet = packet_for("trends", results)
    offenders = qualitative_check("trends", "Case volumes ranged from <month> (<count>).", packet)
    assert offenders_by_rule(offenders, "chain_of_thought")


# --- Issue: denial/limitation statements with plural or action verbs ---

_HISTORY_DENIAL_STATEMENTS = [
    "No regulatory action was taken.",
    "No regulatory actions are claimed or inferred.",
    "No regulatory actions were issued for this product during the period.",
    "No safety actions were initiated in response to these reports.",
    "No history of withdrawals, suspensions, or labelling updates was supplied.",
    "No corrective actions were implemented.",
    "No restrictions were placed on the product.",
]


@pytest.mark.parametrize("statement", _HISTORY_DENIAL_STATEMENTS)
def test_history_denial_statements_allowed(results, statement) -> None:
    packet = packet_for("reaction_analysis", results)
    offenders = qualitative_check("reaction_analysis", statement, packet)
    assert not offenders_by_rule(offenders, "history_of_actions"), statement


@pytest.mark.parametrize(
    "statement",
    [
        "Regulatory actions were taken in response to these reports.",
        "A withdrawal of the product was announced.",
        "Corrective actions were implemented after these cases.",
    ],
)
def test_history_claims_with_plural_still_flagged(results, statement) -> None:
    packet = packet_for("reaction_analysis", results)
    offenders = qualitative_check("reaction_analysis", statement, packet)
    assert offenders_by_rule(offenders, "history_of_actions"), statement


# --- end-to-end: generate_section propagates the qualitative failure ---


def test_generate_section_propagates_qualitative_failure(results) -> None:
    facts = grounded_facts("narrative_summary", results)
    text = facts + " These data prove that Bisoprolol is safe and confirm a new safety signal."
    section = generate_section(
        "narrative_summary",
        results,
        lambda packet: StubClient(text),
    )
    assert not section.grounding_passed
    assert not section.grounding_offenders  # numbers were all valid
    assert section.qualitative_offenders


def test_generate_section_echo_still_passes(results) -> None:
    section = generate_section(
        "narrative_summary",
        results,
        lambda packet: StubClient(grounded_facts("narrative_summary", results)),
    )
    assert section.grounding_passed, [o.matched_phrase for o in section.qualitative_offenders]
    assert section.qualitative_offenders == []


def test_generate_section_propagates_cot_leak(results) -> None:
    leak = (
        "We need to produce a paragraph from trend.monthly_cases. "
        "Lowest month is 2024-12 with 21. We need to quote figures verbatim."
    )
    section = generate_section(
        "trends",
        results,
        lambda packet: StubClient(leak),
    )
    assert not section.grounding_passed
    assert not section.grounding_offenders  # only packet figures were used
    assert offenders_by_rule(section.qualitative_offenders, "chain_of_thought")
