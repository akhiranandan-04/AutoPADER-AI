"""Canonical column names for the Bisoprolol ICSR line-listing dataset.

Centralising column names keeps the normalizer, analysis and report layers
consistent and makes the data model explicit.
"""

from __future__ import annotations

SAFETYREPORTID = "safetyreportid"
SERIOUS_COL = "serious"
EXPEDITE_COL = "fulfillexpeditecriteria"
SEX_COL = "patient_patientsex"
AGE_COL = "patient_patientonsetage"
AGE_UNIT_COL = "patient_patientonsetageunit"
OCCUR_COUNTRY_COL = "occurcountry"
REPORTER_COUNTRY_COL = "primarysource_reportercountry"
RECEIVEDATE_COL = "receivedate"
RECEIVEDATE_FORMAT_COL = "receivedateformat"
REACTION_PT_COL = "patient_reaction_reactionmeddrapt"
REACTION_OUTCOME_COL = "patient_reaction_reactionoutcome"
REPORTER_QUALIFICATION_COL = "primarysource_qualification"
REPORT_TYPE_COL = "reporttype"

SERIOUSNESS_FLAG_COLS = [
    "seriousnessdeath",
    "seriousnesslifethreatening",
    "seriousnesshospitalization",
    "seriousnessdisabling",
    "seriousnesscongenitalanomali",
    "seriousnessother",
]

# Normalized values used internally
SERIOUS = "serious"
NOT_SERIOUS = "not_serious"
UNKNOWN = "unknown"
UNKNOWN_OUTCOME = "unknown"

# Normalized dataframe column names added by the normalizer
SERIOUS_NORM_COL = "_serious_norm"
EXPEDITE_NORM_COL = "_expedite_norm"
COUNTRY_COL = "_country"
COUNTRY_SOURCE_COL = "_country_source"
AGE_BUCKET_COL = "_age_bucket"
RECEIVED_DATE_COL = "_received_date"
