# GenAR Engineering Rules

## Project

This project builds a prototype AI system for generating
evidence-backed PADER-style safety reports from the supplied
Bisoprolol ICSR dataset.

## Critical Safety Rule

The LLM must NEVER calculate authoritative numerical results
from raw safety data.

All numerical analysis must be performed deterministically
using Python.

The LLM may:

- interpret approved analysis
- summarize evidence
- write narrative text
- identify observations
- organize report sections

The LLM must NOT:

- invent numbers
- calculate case counts
- infer unsupported medical conclusions
- invent safety signals
- invent regulatory actions
- invent expectedness
- invent case narratives

## Data Rules

The dataset contains multiple rows per safety case.

Case-level counts must use unique safetyreportid.

Reaction-level analysis may use individual reaction rows.

Do not confuse row count with case count.

## Dataset-Specific Rules

There are 1,068 rows.

There are 1,024 unique cases.

Seriousness is represented at case level.

Seriousness reason fields are independent flags.

The dataset does not contain System Organ Class.

Do not invent SOC information.

Expectedness cannot be determined because no product label/
CCDS is supplied.

History of safety actions is not supplied.

Do not invent safety actions.

## Architecture

Separate:

1. data ingestion
2. validation
3. deterministic analysis
4. evidence construction
5. AI generation
6. human review
7. report rendering

## AI Usage

Never send the complete raw dataset to the LLM.

Send only the minimum evidence required for a section.

Every generated section must have an evidence packet.

## Testing

Every new component requires:

- happy-path test
- edge-case test
- failure test

Run pytest before declaring completion.

## Code

Use Python.

Use type hints.

Use Pydantic for schemas.

Use pandas for deterministic data analysis.

Keep modules small.

Prefer files below 500 lines.

## Completion

Do not claim completion until:

- tests pass
- analysis validation passes
- report generation works
- evidence traceability works
- README is updated
- architecture is documented