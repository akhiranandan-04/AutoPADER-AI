"""Shared fixtures: the real dataset path plus synthetic data builders."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REAL_DATASET = PROJECT_ROOT / "Bisoprolol_icsr_sample_1068rows.xlsx"

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


def synthetic_rows() -> list[dict]:
    """A tiny, representative dataset: 2 cases, one with 2 reactions in one row."""
    return [
        {
            "safetyreportid": 1001,
            "serious": "serious",
            "fulfillexpeditecriteria": "yes",
            "patient_patientsex": "female",
            "patient_patientonsetage": 71,
            "patient_patientonsetageunit": "year",
            "occurcountry": "italy",
            "primarysource_reportercountry": "italy",
            "receivedate": 20250115,
            "receivedateformat": 102,
            "patient_reaction_reactionmeddrapt": "Acute kidney injury,Drug ineffective",
            "patient_reaction_reactionoutcome": "recovered/resolved,unknown",
            "primarysource_qualification": "physician",
            "seriousnessdeath": "no",
            "seriousnesslifethreatening": "no",
            "seriousnesshospitalization": "yes",
            "seriousnessdisabling": "no",
            "seriousnesscongenitalanomali": "no",
            "seriousnessother": "no",
        },
        {
            "safetyreportid": 1002,
            "serious": "not serious",
            "fulfillexpeditecriteria": "no",
            "patient_patientsex": "male",
            "patient_patientonsetage": 104,
            "patient_patientonsetageunit": "year",
            "occurcountry": "france",
            "primarysource_reportercountry": "france",
            "receivedate": 20250210,
            "receivedateformat": 102,
            "patient_reaction_reactionmeddrapt": "Dizziness",
            "patient_reaction_reactionoutcome": "recovering/resolving",
            "primarysource_qualification": "pharmacist",
            "seriousnessdeath": "no",
            "seriousnesslifethreatening": "no",
            "seriousnesshospitalization": "no",
            "seriousnessdisabling": "no",
            "seriousnesscongenitalanomali": "no",
            "seriousnessother": "no",
        },
    ]


@pytest.fixture
def synthetic_df() -> pd.DataFrame:
    return pd.DataFrame(synthetic_rows())


@pytest.fixture
def real_df() -> pd.DataFrame:
    """Load the supplied dataset once per test call."""
    return pd.read_excel(REAL_DATASET, engine="openpyxl", dtype=object)


@pytest.fixture(scope="module")
def real_df_module() -> pd.DataFrame:
    """Load the supplied dataset once per module (cached across m/y tests)."""
    return pd.read_excel(REAL_DATASET, engine="openpyxl", dtype=object)


@pytest.fixture
def real_dataset_path() -> Path:
    return REAL_DATASET


@pytest.fixture
def tmp_xlsx(tmp_path: Path) -> Path:
    """Write the synthetic dataset to a real XLSX file for loader tests."""
    path = tmp_path / "sample.xlsx"
    pd.DataFrame(synthetic_rows()).to_excel(path, index=False)
    return path
