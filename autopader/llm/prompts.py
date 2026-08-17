"""Prompt template rendering for narrative sections.

Templates live in ``prompts/*.md.tpl`` (checked in, per INITIAL.md). The user
message is assembled per-section from ONLY the evidence packet values, rendered
as a markdown table so the LLM quotes figures verbatim. A tiny custom renderer
keeps the dependency light.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from ..config import report_config
from ..evidence.packet import EvidencePacket

PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"

_PLACEHOLDER = re.compile(r"\{\{([a-z_]+)\}\}")


def render_template(template: str, **mapping: object) -> str:
    """Replace ``{{name}}`` placeholders; error on any leftover placeholder."""

    def _sub(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in mapping:
            raise KeyError(f"template placeholder '{{{{{key}}}}}' has no value")
        return str(mapping[key])

    out = _PLACEHOLDER.sub(_sub, template)
    if _PLACEHOLDER.search(out):
        raise KeyError(f"unfilled placeholder remains in rendered template: {out}")
    return out


def render_evidence_table(packet: EvidencePacket) -> str:
    lines = ["| evidence_id | value | kind |", "| --- | --- | --- |"]
    for source in packet.evidence:
        lines.append(f"| {source.evidence_id} | {source.value} | {source.kind} |")
    return "\n".join(lines)


def load_template(prompt_dir: Path, section: str) -> str:
    tpl = prompt_dir / f"{section}.md.tpl"
    if not tpl.is_file():
        raise FileNotFoundError(f"missing prompt template for section '{section}': {tpl}")
    return tpl.read_text(encoding="utf-8")


def render_prompt(
    section: str,
    packet: EvidencePacket,
    prompt_dir: Path = PROMPTS_DIR,
) -> list[dict]:
    """Return ``[system, user]`` messages for the section's packet."""
    config = report_config.REPORT_SECTIONS[section]
    system = load_template(prompt_dir, "system_rules")
    user = load_template(prompt_dir, section)
    user = render_template(
        user,
        section_title=str(config["title"]),
        period_start=_period_value(packet, "case.period_start"),
        period_end=_period_value(packet, "case.period_end"),
        evidence_table=render_evidence_table(packet),
        case_ids=", ".join(str(c) for c in packet.case_ids) or "not supplied",
        limitations="\n".join(f"- {line}" for line in packet.limitations),
        narration_rules="\n".join(f"- {rule}" for rule in packet.narration_rules),
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _period_value(packet: EvidencePacket, evidence_id: str) -> str:
    for source in packet.evidence:
        if source.evidence_id == evidence_id:
            return source.value
    return "not supplied"


def prompt_version(prompt_dir: Path = PROMPTS_DIR) -> str:
    """Hash of the prompt template files — the 'prompt version' in the manifest."""
    digest = hashlib.sha256()
    for path in sorted(prompt_dir.glob("*.tpl")):
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()[:12]
