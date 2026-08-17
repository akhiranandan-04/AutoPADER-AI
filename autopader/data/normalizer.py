"""Case-level and reaction-level normalization.

The raw dataset is a "wide line-listing": one row per case, with all of a
case's reactions packed into ``patient_reaction_reactionmeddrapt`` as
comma-separated MedDRA Preferred Terms.

Normalization produces two stable views:

- **Case table**: one row per unique ``safetyreportid`` (first-row-wins),
  with normalized seriousness, country, age bucket and received date.
- **Reaction table**: one row per reaction token, exploded from the
  comma-separated cells with positional alignment to outcome tokens.

Every transformation is a pure function; anything discarded or defaulted is
counted in :class:`NormalizationReport` so missing data is surfaced, never
hidden.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

import pandas as pd

from .columns import (
    AGE_BUCKET_COL,
    AGE_COL,
    AGE_UNIT_COL,
    COUNTRY_COL,
    COUNTRY_SOURCE_COL,
    EXPEDITE_COL,
    EXPEDITE_NORM_COL,
    NOT_SERIOUS,
    OCCUR_COUNTRY_COL,
    REACTION_OUTCOME_COL,
    REACTION_PT_COL,
    RECEIVED_DATE_COL,
    RECEIVEDATE_COL,
    REPORTER_COUNTRY_COL,
    SAFETYREPORTID,
    SERIOUS,
    SERIOUS_COL,
    SERIOUS_NORM_COL,
    UNKNOWN,
    UNKNOWN_OUTCOME,
)

SERIOUS_NORM_MAP = {"serious": SERIOUS, "not serious": NOT_SERIOUS}
YES_NO_NORM_MAP = {"yes": "yes", "no": "no"}

AGE_BUCKETS = ["0-17", "18-64", "65-74", "75-84", "85+", UNKNOWN]

_UNIT_TO_YEARS: dict[str, float] = {
    "year": 1.0,
    "month": 1.0 / 12.0,
    "week": 1.0 / 52.1775,
    "day": 1.0 / 365.25,
}


@dataclass
class NormalizationReport:
    """Counts of what normalization changed, added or discarded."""

    raw_rows: int = 0
    unique_cases: int = 0
    reaction_tokens: int = 0
    misaligned_rows: int = 0
    padded_outcome_tokens: int = 0
    dropped_outcome_tokens: int = 0
    country_fallback_rows: int = 0
    unknown_age_cases: int = 0
    unknown_country_cases: int = 0
    rows_per_case: dict[int, int] = field(default_factory=dict)


@dataclass
class CaseTable:
    """One row per unique case, enriched with normalized columns."""

    rows: pd.DataFrame
    report: NormalizationReport

    @property
    def n_cases(self) -> int:
        return self.report.unique_cases

    @property
    def reaction_counts_per_case(self) -> pd.Series:
        return self.rows[SAFETYREPORTID].map(pd.Series(self.report.rows_per_case))


def parse_receivedate(value: Any) -> date | None:
    """Parse an integer ``YYYYMMDD`` (format code 102) into a ``date``."""
    if value is None or pd.isna(value):
        return None
    s = str(value).strip()
    if s.isdigit() and len(s) == 8:
        try:
            return date(int(s[:4]), int(s[4:6]), int(s[6:]))
        except ValueError:
            return None
    return None


def years_from_age_unit(age: Any, unit: Any) -> float | None:
    """Convert an onset age + unit to years, or ``None`` when unusable.

    Garbage unit values (e.g. the ``800`` seen in the real data) and NaN
    produce ``None`` (bucketed as unknown) rather than a wrong number.
    """
    if age is None or pd.isna(age):
        return None
    try:
        age_value = float(age)
    except (TypeError, ValueError):
        return None
    if unit is None or pd.isna(unit):
        return None
    factor = _UNIT_TO_YEARS.get(str(unit).strip().lower())
    if factor is None:
        return None
    return age_value * factor


def bucket_age(age: Any, unit: Any) -> str:
    """Bucket an age into a standard group; unusable ages become ``unknown``."""
    years = years_from_age_unit(age, unit)
    if years is None:
        return UNKNOWN
    if years < 18:
        return "0-17"
    if years < 65:
        return "18-64"
    if years < 75:
        return "65-74"
    if years < 85:
        return "75-84"
    return "85+"


def build_case_table(df: pd.DataFrame) -> CaseTable:
    """Build the case-level table (one row per unique safetyreportid)."""
    report = NormalizationReport(raw_rows=len(df), unique_cases=int(df[SAFETYREPORTID].nunique()))
    report.rows_per_case = {int(k): int(v) for k, v in df.groupby(SAFETYREPORTID).size().items()}

    rows = df.drop_duplicates(subset=SAFETYREPORTID, keep="first").copy()

    # Seriousness: normalize the two allowed raw values; anything else is flagged by the validator.
    rows[SERIOUS_NORM_COL] = rows[SERIOUS_COL].map(SERIOUS_NORM_MAP).fillna(UNKNOWN)

    # Expedited / 15-day flag
    rows[EXPEDITE_NORM_COL] = rows[EXPEDITE_COL].map(YES_NO_NORM_MAP).fillna(UNKNOWN)

    # Country: occurcountry first, fall back to reporter country.
    has_occur = rows[OCCUR_COUNTRY_COL].notna()
    rows[COUNTRY_COL] = rows[OCCUR_COUNTRY_COL].where(has_occur, rows[REPORTER_COUNTRY_COL])
    rows[COUNTRY_SOURCE_COL] = rows[OCCUR_COUNTRY_COL].where(has_occur, other="fallback")
    report.country_fallback_rows = int((~has_occur).sum())
    report.unknown_country_cases = int(rows[COUNTRY_COL].isna().sum())

    # Age buckets (numeric column only — patient_patientagegroup is unreliable).
    rows[AGE_BUCKET_COL] = [
        bucket_age(a, u) for a, u in zip(rows[AGE_COL], rows[AGE_UNIT_COL], strict=True)
    ]
    report.unknown_age_cases = int((rows[AGE_BUCKET_COL] == UNKNOWN).sum())

    # Received date
    rows[RECEIVED_DATE_COL] = [parse_receivedate(v) for v in rows[RECEIVEDATE_COL]]

    return CaseTable(rows=rows, report=report)


def build_reaction_table(df: pd.DataFrame) -> tuple[pd.DataFrame, NormalizationReport]:
    """Build the reaction-level table by exploding comma-separated PT tokens.

    Returns ``(reaction_df, report)``.

    Some MedDRA Preferred Terms legitimately contain commas (e.g.
    ``Hallucination, visual``); the line-listing therefore splits them, making
    the PT token count occasionally exceed the outcome token count. To avoid
    undercounting reactions, ALL PT tokens are retained and missing outcome
    positions are padded with ``UNKNOWN_OUTCOME``. Excess outcome tokens (the
    rare case where outcomes outnumber PTs) are dropped. Both are counted in
    the report so nothing is hidden.
    """
    report = NormalizationReport(raw_rows=len(df), unique_cases=int(df[SAFETYREPORTID].nunique()))

    rows_out: list[dict[str, Any]] = []
    tokens = 0
    misaligned = 0
    padded = 0
    dropped = 0

    for _, row in df.iterrows():
        pts = [p.strip() for p in str(row[REACTION_PT_COL]).split(",") if p.strip()]
        outs = [o.strip() for o in str(row[REACTION_OUTCOME_COL]).split(",") if o.strip()]
        if len(pts) != len(outs):
            misaligned += 1
            if len(outs) < len(pts):
                missing = len(pts) - len(outs)
                padded += missing
                outs = outs + [UNKNOWN_OUTCOME] * missing
            else:
                dropped += len(outs) - len(pts)
                outs = outs[: len(pts)]
        serious_norm = SERIOUS_NORM_MAP.get(str(row[SERIOUS_COL]).strip(), UNKNOWN)
        expedite_norm = YES_NO_NORM_MAP.get(str(row[EXPEDITE_COL]).strip(), UNKNOWN)
        country = (
            row[OCCUR_COUNTRY_COL]
            if not pd.isna(row[OCCUR_COUNTRY_COL])
            else row[REPORTER_COUNTRY_COL]
        )
        received = parse_receivedate(row[RECEIVEDATE_COL])
        for pt, outcome in zip(pts, outs, strict=True):
            tokens += 1
            rows_out.append(
                {
                    SAFETYREPORTID: row[SAFETYREPORTID],
                    REACTION_PT_COL: pt,
                    REACTION_OUTCOME_COL: outcome,
                    SERIOUS_NORM_COL: serious_norm,
                    EXPEDITE_NORM_COL: expedite_norm,
                    COUNTRY_COL: country if not pd.isna(country) else UNKNOWN,
                    RECEIVED_DATE_COL: received,
                }
            )

    report.reaction_tokens = tokens
    report.misaligned_rows = misaligned
    report.padded_outcome_tokens = padded
    report.dropped_outcome_tokens = dropped
    report.unknown_country_cases = int(pd.isna(df[OCCUR_COUNTRY_COL]).sum())

    return pd.DataFrame(rows_out), report
