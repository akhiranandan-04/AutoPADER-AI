"""Markdown rendering of the case index / listing (deterministic table)."""

from __future__ import annotations

from ..config.report_config import LIMITATIONS


def case_index_table(case_listing: list[dict]) -> str:
    """Render the full case index as a Markdown table."""
    header = (
        "| safetyreportid | received_date | seriousness | expedited | sex | "
        "age_group | country | reactions |"
    )
    sep = "| --- | --- | --- | --- | --- | --- | --- | --- |"
    rows = [
        "| {id} | {d} | {s} | {e} | {sex} | {age} | {country} | {reactions} |".format(
            id=row["safetyreportid"],
            d=row["received_date"],
            s=row["serious_norm"],
            e=row["expedited"],
            sex=row["sex"],
            age=row["age_bucket"],
            country=row["country"],
            reactions=row["reactions"],
        )
        for row in case_listing
    ]
    note = (
        "\n\nNote: expectedness and System Organ Class are not included because "
        + "no product label/CCDS or SOC field was supplied. "
        + "; ".join(LIMITATIONS)
    )
    return "\n".join([header, sep, *rows]) + note
