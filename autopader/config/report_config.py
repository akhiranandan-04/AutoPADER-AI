"""Report configuration: the single source of "what a PADER report is".

Each section declares which evidence keys its narrative may reference, the
narration rules the LLM must follow, and the key facts it must mention
(coverage check). Deterministic tables are rendered directly from the analysis
result and never pass through the LLM.
"""

from __future__ import annotations

PRODUCT_NAME = "Bisoprolol"
REPORT_TYPE = "PADER-style (quarterly/periodic)"
APPLICATION_NUMBER = "not supplied"

LIMITATIONS: list[str] = [
    "No System Organ Class field supplied; analysis is at Preferred Term level only",
    "No product label/CCDS supplied; expectedness is not assessed",
    "No history-of-actions data supplied for this exercise",
]

SECTION_ORDER: list[str] = [
    "narrative_summary",
    "summary_analysis",
    "reaction_analysis",
    "serious_alerts",
    "trends",
    "history_of_actions",
]

# Sections rendered by the LLM from evidence packets.
NARRATIVE_SECTIONS: set[str] = set(SECTION_ORDER)

# Sections rendered deterministically from AnalysisResult.
DETERMINISTIC_SECTIONS: set[str] = {
    "reporting_period",
    "case_index",
    "case_listing",
}

REPORT_SECTIONS: dict[str, dict[str, object]] = {
    "narrative_summary": {
        "title": "Narrative Summary and Analysis",
        "required_evidence": [
            "case.period_start",
            "case.period_end",
            "case.total_cases",
            "case.serious_cases",
            "case.serious_pct",
            "case.not_serious_cases",
            "case.expedited_cases",
            "react.top_reactions",
        ],
        "narration_rules": [
            "quote packet figures verbatim",
            "state the reporting period",
            "report total, serious and expedited case counts",
            "name the most frequent reaction",
            "do not infer safety conclusions",
        ],
        "required_mentions": [
            "total case count",
            "serious case count",
            "most frequent reaction",
        ],
    },
    "summary_analysis": {
        "title": "Summary Analysis of Cases",
        "required_evidence": [
            "case.age_groups",
            "case.sex",
            "case.country",
            "case.reporter_qualification",
            "case.total_cases",
        ],
        "narration_rules": [
            "quote packet figures verbatim",
            "describe demographic and country distribution without interpretation",
            "do not infer safety conclusions",
        ],
        "required_mentions": ["sex distribution", "age-group distribution"],
    },
    "reaction_analysis": {
        "title": "Reaction Analysis",
        "required_evidence": [
            "react.top_reactions",
            "react.top_serious_reactions",
            "react.outcome_counts",
        ],
        "narration_rules": [
            "quote packet figures verbatim",
            "list the most frequent reactions and their frequencies",
            "describe outcome distribution without interpreting causality",
            "do not assess expectedness",
        ],
        "required_mentions": ["most frequent reaction", "outcome distribution"],
    },
    "serious_alerts": {
        "title": "Serious Cases and 15-Day Alerts",
        "required_evidence": [
            "case.serious_cases",
            "case.expedited_cases",
            "react.top_serious_reactions",
            "case.period_start",
            "case.period_end",
        ],
        "narration_rules": [
            "quote packet figures verbatim",
            "state the count of serious cases and of expedited (15-day) reports",
            "describe the reactions reported in serious cases without claiming a signal",
        ],
        "required_mentions": ["serious case count", "expedited report count"],
    },
    "trends": {
        "title": "Trends and Important Observations",
        "required_evidence": [
            "trend.monthly_cases",
            "case.period_start",
            "case.period_end",
        ],
        "narration_rules": [
            "quote packet figures verbatim",
            "report monthly case volumes and month-over-month changes",
            "never characterize any trend as a safety signal",
        ],
        "required_mentions": ["monthly case volume"],
    },
    "history_of_actions": {
        "title": "History of Actions",
        "required_evidence": [],
        "narration_rules": [
            "state plainly that no history-of-actions data was supplied",
        ],
        "required_mentions": [],
    },
}
