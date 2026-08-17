"""Grounding checks: numeric + qualitative gates for generated narrative.

Numeric gate (``grounding_check``): every number in the narrative must exist in
the packet. Qualitative gate (``qualitative_check``): claims that require data
the packet does not supply (expectedness, System Organ Class, history of
actions, safety signals, causality) are flagged as unsupported interpretation.

Both gates are deterministic — the LLM never judges arithmetic or meaning.
The numeric gate is the original interface and is unchanged; the qualitative
gate is additive, so existing callers keep working.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from pydantic import BaseModel

from ..config.report_config import PRODUCT_NAME
from ..evidence.packet import EvidencePacket

_NUMBER = re.compile(r"\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?")
_FIXED_WINDOW = re.compile(r"\b15\s*[\u2010-\u2015-]?\s*day\b", re.IGNORECASE)

# --- numeric gate ---


def extract_numbers(text: str) -> set[str]:
    """All numeric tokens in ``text``, normalized (commas stripped).

    The fixed regulatory "15-day" reporting-window expression is not a
    dataset-derived statistic, so its "15" is masked out before extraction.
    """
    masked = _FIXED_WINDOW.sub(" ", text)
    return {m.replace(",", "") for m in _NUMBER.findall(masked)}


def packet_numbers(packet: EvidencePacket) -> set[str]:
    values = " ".join(source.value for source in packet.evidence)
    return extract_numbers(values)


def grounding_check(section: str, text: str, packet: EvidencePacket) -> tuple[bool, list[str]]:
    """Return ``(passed, offending_numbers)``.

    Offending numbers are numbers in the narrative that do not appear in any
    packet value.
    """
    allowed = packet_numbers(packet)
    found = extract_numbers(text) - allowed
    offenders = sorted(found)
    return (not offenders, offenders)


class GroundingResult:
    """Recorded outcome of a grounding check for a generated section."""

    def __init__(self, section: str, passed: bool, offenders: list[str]) -> None:
        self.section = section
        self.passed = passed
        self.offenders = offenders


# --- qualitative gate ---


class QualitativeOffender(BaseModel):
    """A qualitative rule violation: an unsupported interpretation claim."""

    section: str
    rule: str
    matched_phrase: str
    reason: str


@dataclass(frozen=True)
class _Rule:
    rule: str
    patterns: tuple[str, ...]
    reason: str
    required_limitation: str = ""


# "PRODUCT" placeholders are replaced with the real product name at check time.
_RULES: tuple[_Rule, ...] = (
    _Rule(
        rule="expectedness",
        patterns=(
            r"\b(?:un)?expected(?:ness)?\b",
            r"\b(?:per|according to|consistent with|listed in|documented in)\s+"
            r"(?:the\s+)?(?:product\s+)?(?:label|labelling|labeling|ccds)\b",
        ),
        reason=(
            "expectedness is not assessed because no product label/CCDS was supplied; "
            "claims that an event is or is not expected are unsupported"
        ),
        required_limitation="expectedness",
    ),
    _Rule(
        rule="system_organ_class",
        patterns=(
            r"\bsystem\s+organ\s+class\b",
            r"\borgan\s+class\b",
            r"\bsoc\b",
        ),
        reason=(
            "System Organ Class is not supplied in this dataset; assigning a "
            "reaction to an organ class is unsupported"
        ),
        required_limitation="system organ class",
    ),
    _Rule(
        rule="history_of_actions",
        patterns=(
            r"\bregulatory\s+(?:action|measure)s?\b",
            r"\bsafety\s+(?:action|measure)s?\b",
            r"\blabell?ing\s+update\b",
            r"\bwithdrawal\b",
            r"\bsuspension\b",
            r"\bdear\s+doctor\b",
            r"\bcorrective\s+actions?\b",
            r"\bactions?\s+taken\b",
            r"\brestriction\b",
        ),
        reason=(
            "no history-of-actions data was supplied; asserting that a "
            "regulatory or safety action was taken is unsupported"
        ),
        required_limitation="history-of-actions",
    ),
    _Rule(
        rule="safety_signal",
        patterns=(
            r"\bsafety\s+signal\b",
            r"\bsignal\b",
        ),
        reason="no signal assessment is supported by the supplied evidence",
    ),
    _Rule(
        rule="safety_conclusion",
        patterns=(
            r"\bproven?\s+safe\b",
            r"\bprove[sd]?\b",
            r"\b(?:is|are)\s+(?:generally\s+)?(?:safe|well\s+tolerated)\b",
            r"\bsafe\s+and\s+(?:effective|well\s+tolerated)\b",
            r"\bsafety\s+profile\b",
            r"\bno\s+safety\s+concerns\b",
        ),
        reason=(
            "safety cannot be proven (or disproven) from these data; "
            "unsupported safety conclusion"
        ),
    ),
    _Rule(
        rule="causality",
        patterns=(
            r"\bthe\s+(?:product|drug|medicine)\s+(?:did\s+not\s+cause|caused?)\b",
            r"\b(caused?|due to|attribut(?:able|ed) to|resulted? from|induced?|"
            r"linked to|related to)\b[\w\s,;:'-]{0,80}?\bPRODUCT\b",
            r"\bPRODUCT\b[\w\s,;:'-]{0,80}?\b(caused?|due to|attribut(?:able|ed) to|"
            r"resulted? from|induced?|linked to|related to|is\s+safe)\b",
        ),
        reason=("causality cannot be established; no causal analysis evidence is supplied"),
    ),
    _Rule(
        rule="chain_of_thought",
        patterns=(
            r"<[a-zA-Z][a-zA-Z0-9]+(?:[\s-]+[a-zA-Z0-9]+)*>",
            r"\bwe\s+need\s+to\b",
            r"\bwe\s+must\b",
            r"\bwe\s+(?:already\s+have|have\s+to)\b",
            r"\blet[’']s\b",
            r"\bthe\s+(?:requirement|instruction)s?\b",
            r"\bmust\s+open\s+with\b",
            r"\b(?:verbatim|placeholder)\b",
        ),
        reason=(
            "output contains chain-of-thought, echoed template instructions, or "
            "unconsumed placeholders instead of a finished narrative"
        ),
    ),
)

_MAX_PHRASE = 100

# Denial/limitation markers: evidence was NOT supplied/available, or an
# assessment was NOT performed. A trigger term inside such a statement is a
# compliant description of missing data, not an unsupported claim.
_DENIAL = re.compile(
    r"\b(?:not|no)\s+(?:\w+\s+){0,6}?"
    r"(?:assessed|evaluated|supplied|provided|available|established|"
    r"determined|performed|conducted|measured|given|taken|claimed|"
    r"inferred|withdrawn|suspended|issued|initiated|implemented)\b"
    r"|\b(?:not assessed|not evaluated|not supplied|not provided|"
    r"not available|not established|unavailable)\b"
    r"|\bcannot\s+be\s+(?:assessed|evaluated|determined|established)\b"
    r"|\bcould\s+not\s+be\s+(?:assessed|evaluated|determined|established)\b",
    re.IGNORECASE,
)


def _sentence_containing(text: str, pos: int) -> str:
    """Return the sentence (or bullet line) that contains ``pos``."""
    start = max(text.rfind(sep, 0, pos) for sep in ".!?;\n") + 1
    ends = [text.find(sep, pos) for sep in ".!?;\n"]
    available = [i for i in ends if i != -1]
    end = min(available) + 1 if available else len(text)
    return text[start:end].strip()


def _declared_limitations(packet: EvidencePacket) -> str:
    return " ".join(packet.limitations).lower()


def qualitative_check(section: str, text: str, packet: EvidencePacket) -> list[QualitativeOffender]:
    """Flag narrative claims that interpret data the packet does not supply.

    Returns one :class:`QualitativeOffender` per violated rule (first non-denied
    match). Data-gated rules only fire when the packet's declared limitations
    say the needed evidence is unavailable; the standing safety-signal and
    causality rules always fire because no packet in this prototype supports
    them.

    Matches inside denial/limitation statements ("... is not assessed",
    "No ... supplied") describe the ABSENCE of evidence and are exempt.
    """
    limitations = _declared_limitations(packet)
    offenders: list[QualitativeOffender] = []
    product = re.escape(PRODUCT_NAME)
    for rule in _RULES:
        if rule.required_limitation and rule.required_limitation not in limitations:
            continue
        for pattern in rule.patterns:
            compiled = re.compile(pattern.replace("PRODUCT", product), re.IGNORECASE)
            for match in compiled.finditer(text):
                sentence = _sentence_containing(text, match.start())
                if _DENIAL.search(sentence):
                    continue
                phrase = match.group(0).strip()
                if len(phrase) > _MAX_PHRASE:
                    phrase = phrase[:_MAX_PHRASE] + "..."
                offenders.append(
                    QualitativeOffender(
                        section=section,
                        rule=rule.rule,
                        matched_phrase=phrase,
                        reason=rule.reason,
                    )
                )
                break
    return offenders
