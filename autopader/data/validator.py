"""Dataset validation.

The validator checks the raw (unnormalized) dataframe for structural
correctness and expected value domains. It returns a ``ValidationReport``
with ``errors`` (must be fixed) and ``warnings`` (surfaced, never hidden,
but not blocking).

Validation is deterministic and pure: no LLM involvement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

REQUIRED_COLUMNS = [
    "safetyreportid",
    "serious",
    "fulfillexpeditecriteria",
    "patient_patientsex",
    "patient_patientonsetage",
    "patient_patientonsetageunit",
    "occurcountry",
    "primarysource_reportercountry",
    "receivedate",
    "receivedateformat",
    "patient_reaction_reactionmeddrapt",
    "patient_reaction_reactionoutcome",
    "primarysource_qualification",
]

SERIOUS_VALUES = {"serious", "not serious"}
YES_NO_VALUES = {"yes", "no"}
SEX_VALUES = {"female", "male"}
QUALIFICATION_VALUES = {
    "physician",
    "pharmacist",
    "other health professional",
    "consumer or non-health professional",
}


@dataclass
class ValidationReport:
    """Result of validating a dataset."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """True when there are no blocking errors."""
        return len(self.errors) == 0

    def merge(self, other: ValidationReport) -> None:
        """Merge another report's errors and warnings into this one."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)


def _domain_violations(series: pd.Series, allowed: set[str], col: str) -> list[str]:
    """List distinct non-null values in ``series`` that are outside ``allowed``."""
    distinct = {str(v) for v in series.dropna().unique()}
    unexpected = sorted(distinct - allowed)
    if not unexpected:
        return []
    return [f"column '{col}' contains unexpected value(s): {unexpected}"]


def validate(df: pd.DataFrame) -> ValidationReport:
    """Validate a raw dataframe and return a report of errors and warnings."""
    report = ValidationReport()

    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        report.errors.append(f"missing required columns: {missing_cols}")
        return report

    if df.empty:
        report.errors.append("dataset has no rows")
        return report

    if df["safetyreportid"].isna().any():
        report.errors.append("column 'safetyreportid' contains missing values")

    report.errors.extend(_domain_violations(df["serious"], SERIOUS_VALUES, "serious"))
    report.errors.extend(
        _domain_violations(df["fulfillexpeditecriteria"], YES_NO_VALUES, "fulfillexpeditecriteria")
    )
    report.errors.extend(
        _domain_violations(df["patient_patientsex"], SEX_VALUES, "patient_patientsex")
    )
    report.errors.extend(
        _domain_violations(
            df["primarysource_qualification"],
            QUALIFICATION_VALUES,
            "primarysource_qualification",
        )
    )

    # seriousness reason flags must be independent yes/no
    flag_cols = [
        "seriousnessdeath",
        "seriousnesslifethreatening",
        "seriousnesshospitalization",
        "seriousnessdisabling",
        "seriousnesscongenitalanomali",
        "seriousnessother",
    ]
    for col in flag_cols:
        if col in df.columns:
            report.errors.extend(_domain_violations(df[col], YES_NO_VALUES, col))

    # dates: receivedate must be YYYYMMDD ints
    bad_dates = 0
    for raw in df["receivedate"].dropna():
        s = str(int(raw)) if _is_numeric(raw) else str(raw)
        if not (len(s) == 8 and s.isdigit()):
            bad_dates += 1
    if bad_dates:
        report.errors.append(f"column 'receivedate' has {bad_dates} non-YYYYMMDD value(s)")

    # reaction/outcome token-count alignment (warning, not error)
    try:
        pt_tokens = df["patient_reaction_reactionmeddrapt"].astype(str).str.split(",").str.len()
        outcome_tokens = df["patient_reaction_reactionoutcome"].astype(str).str.split(",").str.len()
        mismatched = int((pt_tokens != outcome_tokens).sum())
        if mismatched:
            report.warnings.append(
                f"{mismatched} row(s) have reaction/outcome token-count mismatch; "
                "PTs are kept and missing outcome positions padded as 'unknown' "
                "(excess outcome tokens dropped)"
            )
    except Exception as exc:  # pragma: no cover - defensive
        report.errors.append(f"failed to inspect reaction/outcome alignment: {exc}")

    null_country = int(df["occurcountry"].isna().sum())
    if null_country:
        report.warnings.append(
            f"{null_country} row(s) missing 'occurcountry'; "
            "primarysource_reportercountry will be used as fallback"
        )

    null_age = int(df["patient_patientonsetage"].isna().sum())
    if null_age:
        report.warnings.append(
            f"{null_age} row(s) missing numeric onset age; " "they will be bucketed as 'unknown'"
        )

    return report


def _is_numeric(value: Any) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False
