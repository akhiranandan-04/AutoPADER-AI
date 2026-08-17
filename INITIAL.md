# Feature: GenAR Version 0 PADER Generator

## FEATURE

Build a working prototype that converts the supplied Bisoprolol
ICSR safety dataset into a structured, evidence-backed PADER-style
report.

The system must:

1. Load the supplied safety dataset.
2. Validate the dataset.
3. Normalize case-level and reaction-level data.
4. Perform deterministic statistical analysis.
5. Build section-specific evidence packets.
6. Send only scoped evidence to the LLM.
7. Generate narrative report sections.
8. Allow human review.
9. Generate a final Markdown PADER-style report.

## REQUIRED ANALYSIS

Calculate deterministically:

- total unique cases
- serious cases
- non-serious cases
- age groups
- sex
- country
- most common reactions
- most common serious reactions
- outcomes
- time trends
- expedited/15-day cases
- case listing

## CRITICAL DATA RULES

The dataset has multiple rows per case.

Use safetyreportid for case-level deduplication.

Do not treat the number of rows as the number of cases.

Reaction analysis should operate at reaction level.

The dataset does not contain System Organ Class.

Do not infer SOC.

No product label/CCDS is supplied.

Expectedness is therefore out of scope.

No history-of-actions data is supplied.

Do not invent actions.

## AI ROLE

The LLM must not calculate authoritative statistics.

The LLM receives a section-specific evidence packet.

The LLM may convert deterministic analysis into regulatory-neutral
narrative.

The LLM must not make unsupported safety conclusions.

## REPORT SECTIONS

Generate:

1. Reporting Period
2. Narrative Summary and Analysis
3. Summary Analysis of Cases
4. Reaction / Adverse Event Analysis
5. Serious Cases / 15-Day Alerts
6. Trends and Important Observations
7. History of Actions
8. Case Index / Listing

## HUMAN REVIEW

Provide a mechanism for a reviewer to:

- approve
- flag
- edit

generated sections before final report generation.

## OUTPUT

Generate:

report_output.md

Also produce:

architecture.md

and expose the actual prompts/context templates.

## VALIDATION

The implementation must include tests for:

- case deduplication
- serious case counting
- reaction counting
- missing values
- age bucketing
- evidence generation
- prompt generation
- report generation

## EXAMPLES

Use the supplied PADER sample report only as a reference
for general shape and tone.

Do not copy its unsupported content.

## DOCUMENTATION

Use:

PADER Starter Guide
GenAR AI Engineering Challenge
Submission Guide
Data Usage Notice

as project requirements.

## IMPORTANT

The final system must make it possible to trace every important
number in generated narrative back to deterministic analysis.