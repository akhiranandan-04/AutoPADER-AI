name: "GenAR Version 0 — Evidence-Grounded PADER Generator (DeepSeek + Deterministic Python)"
description: |

## Purpose
Build a working Python prototype (`autopader/`) that converts the supplied Bisoprolol ICSR dataset into a structured, evidence-backed PADER-style report. Every authoritative statistic is computed deterministically in Python; the DeepSeek LLM receives only per-section "evidence packets" and converts them into regulatory-neutral narrative. Every important number in the final report must trace to a deterministic analysis result.

## Core Principles
1. **Grounding First** — No number reaches narrative unless produced by deterministic Python. LLM arithmetic is forbidden by design (prompt + scoping, not hope).
2. **Scoped Context** — The LLM never sees raw CSV. Each section gets a small packet: section name, reporting period, approved metrics, observations, source case IDs where appropriate, and explicit limitations.
3. **Traceability** — Every `EvidenceSource` carries an `evidence_id` and `provenance`. A manifest records dataset hash, analysis version, model, and prompt version.
4. **Separation of Concerns** — data ingestion / validation / deterministic analysis / evidence construction / AI generation / human review / report rendering are separate modules (AGENTS.md).
5. **Configuration over Code Paths** — Section→evidence declarations mean PADER is the first report type, not the only one (the Version 1 lens: PSUR/PBRER/DSUR later).
6. **Validation Loops** — Executable tests/lints the agent runs and fixes until green. Every component needs happy-path, edge-case, and failure tests.
7. **Global rules** — Follow AGENTS.md: Python, type hints, Pydantic schemas, pandas for deterministic analysis, files < 500 lines, pytest before completion, README + architecture documented.

---

## Goal
Deliver a working prototype that goes from raw XLSX → validate → normalize (case-level + reaction-level) → deterministic analysis → evidence packets → DeepSeek narrative → human review → final `report_output.md`. Also produce `architecture.md` and expose the actual per-section prompt/context templates. Traceability of every important number is the core deliverable.

## Why
- **Business value**: Automates Periodic Adverse Drug Experience Report (PADER) drafting per 21 CFR 314.80(c)(2) — currently a manual, error-prone regulatory task.
- **Problem solved**: LLMs cannot be trusted to compute authoritative statistics from raw rows. This architecture hands the model exactly the data it may repeat, and nothing it must compute.
- **Generalization**: A config-driven report/section registry means "add a report type" is mostly adding configuration and data, not new code paths.

## What
A CLI: `python -m autopader.cli --input <xlsx|csv> --output report_output.md [--skip-llm] [--review-file review_state.json]`

### Success Criteria
- [ ] 1,024 unique cases counted (NOT 1,068 rows); serious = 1,023; not serious = 1
- [ ] 1,023 expedited/15-day cases; 1 non-expedited
- [ ] Reaction analysis at reaction level: 3,648 reaction tokens, 1,122 unique PTs (exploded from comma-separated cells)
- [ ] No SOC inference (dataset has no SOC field); no expectedness (no label/CCDS); no invented history-of-actions
- [ ] DeepSeek generates every narrative section from a scoped evidence packet only
- [ ] Every number in each narrative section is traceable to a deterministic `EvidenceSource` (grounding checker passes)
- [ ] Human review (approve/flag/edit) gates final report assembly
- [ ] `report_output.md` contains all 8 required sections; `architecture.md` written; `prompts/` templates exposed
- [ ] All validation loops green (ruff, mypy, black, pytest); 8 required test areas covered
- [ ] Evaluation harness can check report correctness beyond eyeballing (traceability + coverage checks, batch mode)

## All Needed Context

### Documentation & References (MUST READ)
```yaml
# Project requirements (in repo root)
- file: AGENTS.md
  why: Global engineering rules — deterministic/AI split, data rules, testing, code conventions. Follow always.
- file: INITIAL.md
  why: The authoritative feature request. Do not deviate from its data rules.
- file: PLANNING.md
  why: Agreed architecture: deterministic layer vs AI layer vs evidence layer vs human review vs report.
- file: TASK.md
  why: Phase plan (Foundation → Deterministic Analysis → Evidence → AI/DeepSeek → Review → Report → Submission).

# Assessment materials (PDFs, project root)
- file: "GenAR - AI Engineering Challenge.pdf"
  why: Evaluation criteria — grounding, context engineering, prompt design, architecture, no-LLM-arithmetic, 8 report sections, human control, Version 1 generalization. The "worked example" defines the packet pattern.
- file: PADER_Starter_Guide.pdf
  why: Section-by-section content expectations + Appendix B dataset gotchas. Regulatory basis: 21 CFR 314.80(c)(2).
- file: DATA_USAGE_NOTICE.pdf
  why: Synthetic/derived data, exercise-only, no commercial use, delete after evaluation.
- file: PADER-FDA-Y0AHP_PADER_Full_sample_data_B-1_CLIENT_DEV_01_FDA_v1_20260810.pdf
  why: Reference for SHAPE and TONE ONLY. Its SOC tabulations, CCDS/label text, and narratives are NOT supported by our dataset — do not copy.

# NOTE: No Submission Guide file exists in the repo. The challenge PDF says deliverables are
# (1) working prototype, (2) one generated report, (3) README, (4) architecture diagram,
# (5) Version 1 implementation or one-page design doc. Treat the challenge PDF "Deliverables"
# and "What We're Evaluating" sections as the submission guide. Flag to user.
```

### Verified dataset facts (deterministic ground truth — obtained by inspecting the XLSX)
```yaml
shape:                1068 rows × 67 columns
unique safetyreportid: 1024              # 41 cases appear in >1 row (38×2 rows, 3×3 rows)
reporting period:      receivedate 20241227 → 20251226 (one year, in-data)
serious (case level):  serious=1023, 'not serious'=1   # value is 'not serious', NOT 'non-serious'
expedited:             fulfillexpeditecriteria yes=1023, no=1
sex (case level):      female=503, male=493, missing=28
numeric age:           941 non-null (patient_patientonsetage), min=1, max=104
age unit column:       year=975, month=5, day=3, week=1, NaN=81, INVALID '800'=3   # dirty
age group column:      mostly blank (NaN=1037, elderly=19, adult=9, neonate=3)  # UNRELIABLE → bucket from numeric age
reaction data:         comma-separated MedDRA PT tokens inside patient_reaction_reactionmeddrapt
                         → 3,648 reaction tokens total, 1,122 unique PTs, up to 60 tokens/cell (681 rows multi-token)
                         → positional partner column patient_reaction_reactionoutcome (6 rows token-count mismatch)
reaction level:        case=2 reactions on same PT? No repeats within case (case-distinct total == token total 3,648)
drug data:             comma-separated too — 9,601 drug tokens in 'drugs'
outcomes (token):      recovered/resolved=1347, unknown=1135, not recovered/not resolved/ongoing=569,
                       recovering/resolving=420, fatal=137, recovered/resolved with sequelae=34
seriousness flags:     independent yes/no — hospitalization yes=504, lifethreatening yes=110,
                       death yes=69, disabling yes=46, other yes=945, congenitalanomali yes=8 (row level)
reporttype:            spontaneous report=1056, report from study=12
reporter qualification: physician=518, pharmacist=259, other health professional=171, consumer/non-health=120
country:               occurcountry (7 null) vs primarysource_reportercountry (0 null); 1 row mismatched
dates:                 stored as int YYYYMMDD with 'format' columns (102 = CCYYMMDD); report_date column is proper datetime
top reactions (token): Acute kidney injury=81, Drug ineffective=60, Hypotension=48, Drug interaction=45,
                       Dizziness=40, Bradycardia=39, Dyspnoea=39, Fatigue=35, Off label use=34, Diarrhoea=33
sample report check:   sample PADER totals (e.g., 3,648 total, top PTs) differ slightly from ours
                       (AKI 80 vs 81, Drug ineffective 53 vs 60) → do NOT copy its numbers; recompute.
```

### Current Codebase tree
```bash
.
├── AGENTS.md                  # Global rules (read FIRST)
├── INITIAL.md                 # Feature request
├── PLANNING.md                # Architecture
├── TASK.md                    # Phase plan
├── README.md                  # Context engineering template docs (PRP workflow)
├── PRPs/
│   ├── templates/prp_base.md
│   ├── EXAMPLE_multi_agent_prp.md
│   └── genar-version0.md      # THIS FILE
├── examples/                  # Empty (.gitkeep)
├── validation/                # Validation workflow guidance (ultimate_validate_command.md)
└── use-cases/                 # Context-engineering meta-templates (not application code)
```

### Desired Codebase tree (files to be added)
```bash
autopader/
├── __init__.py
├── cli.py                     # argparse entry point
├── config/
│   ├── __init__.py
│   ├── settings.py            # python-dotenv; DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, DEEPSEEK_TIMEOUT_S
│   └── report_config.py       # Report-type registry: PADER section declarations → required evidence keys + narration rules
├── data/
│   ├── __init__.py
│   ├── loader.py              # XLSX (openpyxl) / CSV → DataFrame; errors for bad path/format
│   ├── validator.py           # Schema + domain validation; returns ValidationReport (errors, warnings)
│   └── normalizer.py          # case table (dedupe by safetyreportid) + reaction table (exploded PT tokens); age bucketing
├── analysis/
│   ├── __init__.py
│   ├── results.py             # Pydantic AnalysisResult + EvidenceSource (evidence_id, value, kind, provenance)
│   ├── case_metrics.py        # total/serious/not-serious/expedited, sex, country, age-group counts
│   ├── reaction_metrics.py    # exploded-PT counts, serious-reaction counts, outcome counts
│   └── time_trends.py         # monthly case volume, month-over-month deltas, period bounds
├── evidence/
│   ├── __init__.py
│   ├── packet.py              # EvidencePacket assembly (scoped per section)
│   └── manifest.py            # dataset sha256, analysis version, model, prompt version, generated_at
├── llm/
│   ├── __init__.py
│   ├── client.py              # Thin DeepSeek HTTP client (httpx) + EchoClient for tests/--skip-llm
│   ├── prompts.py             # render_prompt(section, packet) using templates
│   └── grounding.py           # post-generation check: every number in narrative ⊆ packet values
├── prompts/
│   ├── system_rules.md.tpl    # global system message (role, safety rules)
│   ├── narrative_summary.md.tpl
│   ├── summary_analysis.md.tpl
│   ├── reaction_analysis.md.tpl
│   ├── serious_alerts.md.tpl
│   └── trends.md.tpl
├── review/
│   ├── __init__.py
│   └── review.py              # approve/flag/edit; review_state.json; blocks assembly of pending/flagged
├── report/
│   ├── __init__.py
│   ├── assembler.py           # merge approved narrative + deterministic tables → report_output.md
│   └── case_listing.py        # case index (safetyreportid, PTs, seriousness, receivedate, country, outcomes)
├── evaluate/
│   ├── __init__.py
│   ├── trace_check.py         # number↔evidence matching
│   ├── coverage_check.py      # required key facts present per section
│   └── run_batch.py           # run over many (dataset,report config) pairs; aggregate scores
├── architecture.md            # components + data flow (deliverable)
├── report_output.md           # final report (deliverable)
└── requirements.txt           # pandas, openpyxl, pydantic, python-dotenv, httpx, pytest (no OpenAI SDK needed)
tests/
├── __init__.py
├── conftest.py                # real xlsx path fixture + tiny synthetic dataset fixtures
├── test_loader.py
├── test_validator.py
├── test_normalizer.py         # case dedup, reaction explode, age bucketing
├── test_case_metrics.py       # serious/expedited/sex/country
├── test_reaction_metrics.py   # reaction counting
├── test_missing_values.py
├── test_evidence.py           # packet scoping + traceability ids
├── test_prompts.py            # prompt rendering, forbidden-content
├── test_llm_client.py         # httpx mocked, retry/timeout, EchoClient
├── test_grounding.py          # number↔packet matching
├── test_review.py             # approve/flag/edit gating
└── test_report.py             # 8 sections, traceability, review gating
```

### Known Gotchas (verified against the actual dataset & libraries)
```python
# CRITICAL: 1,068 ROWS != 1,068 CASES. Case-level counts dedupe by safetyreportid.
#           AND each row packs MULTIPLE reactions as comma-separated tokens —
#           so reaction counts are NOT row counts either. Explode tokens first.
#           Correct ground truth: 1,024 cases / 3,648 reaction tokens / 1,122 unique PTs.
# CRITICAL: The single non-serious case has value 'not serious' (not 'non-serious').
#           Normalize to internal enum {serious, not_serious} early; never hardcode the raw string.
# CRITICAL: patient_patientagegroup is mostly blank → bucket from numeric patient_patientonsetage;
#           handle units year/month/day/week and the garbage unit value 800 (treat as unknown).
# CRITICAL: No System Organ Class column. NEVER infer SOC. Report at MedDRA PT level only.
# CRITICAL: No product label/CCDS → expectedness is OUT OF SCOPE. Never say expected/unexpected.
# CRITICAL: No history-of-actions data → section must explicitly state none were provided.
# CRITICAL: occurcountry vs primarysource_reportercountry can differ (1 row) and occurcountry
#           has 7 nulls → define the rule: use occurcountry, fall back to reportercountry, record count.
# CRITICAL: 6 rows have PT-token count != outcome-token count → validator must flag (warn, don't drop).
# CRITICAL: Dates are ints (YYYYMMDD) + separate 'format' columns (102=CCYYMMDD); parse via format code.
# CRITICAL: pandas read_excel auto-selects openpyxl for .xlsx — pin engine='openpyxl'; no sep= param (use str.split+explode).
# CRITICAL: pydantic v2 — use field_validator/model_validator; raise ValueError inside validators; model_validate() for dicts.
# CRITICAL: httpx default timeout is 5s — too low for LLM calls; set httpx.Timeout(connect=10, read=120, write=120, pool=10).
#           Retry only ConnectError/ConnectTimeout (HTTPTransport retries) or 429/5xx via explicit loop; never retry 4xx.
# CRITICAL: DeepSeek is OpenAI-compatible: base_url https://api.deepseek.com (or /v1), Bearer key,
#           model ids deepseek-v4-flash / deepseek-v4-pro, POST /chat/completions.
#           'thinking' is enabled by default in V4 — disable (thinking.type=disabled) for fast cheap narrative.
#           Response is OpenAI-shaped: choices[0].message.content.
# CRITICAL: 'serious' and 'fulfillexpeditecriteria' are nearly the same population (1,023/1,024) — normal for
#           spontaneous ICSR data; not a bug. Seriousness reason flags are independent yes/no (not mutually exclusive).
```

---

## The Exact Deterministic / LLM Split (non-negotiable)

**Python computes (never the LLM):**
- total unique cases (dedupe by safetyreportid)
- serious vs not-serious case counts and percentages
- expedited/15-day case count
- age-group counts (bucketed from numeric age, unit-aware)
- sex counts (incl. missing)
- country counts (incl. missing; rule chosen)
- reaction counts (exploded PT tokens) — overall and serious-only
- outcome counts (token level)
- time trends: monthly case volume, deltas, period start/end
- reporter qualification counts (optional, if surfaced)
- case listing table (fully deterministic rows)
- any percentage/ratio/ordering presented in the report

**LLM receives ONLY (per section):**
- section name + narration instructions (from config)
- reporting period (start/end strings, from Python)
- approved metrics/observations as an `EvidencePacket` (typed values + evidence ids, from Python)
- source case IDs where appropriate (from Python)
- explicit limitations (e.g., "no SOC field", "no label supplied", "no actions supplied")
- a hard rule set: quote packet figures verbatim; never compute, infer, or invent

**LLM produces:** regulatory-neutral narrative text only. Its output is post-checked by the grounding checker.

---

## Implementation Blueprint — 11 Required Design Areas

### 1. Data ingestion (`autopader/data/loader.py`)
```python
def load_dataset(path: Path) -> pd.DataFrame:
    # GOTCHA: read_excel has no sep=; rely on engine selection.
    # Pattern: dispatch on suffix; pin engine='openpyxl' for .xlsx (dtype_object=True keeps values raw).
    if suffix == ".xlsx":
        return pd.read_excel(path, engine="openpyxl", dtype=object)
    if suffix == ".csv":
        return pd.read_csv(path, dtype=object)
    raise LoadError(f"unsupported format: {suffix}")
```
- Preserve raw values (`dtype=object`) so token-splitting and int dates are handled by one normalizer, not the loader.
- Compute `dataset_sha256` for the manifest at load time.
- Validate the file exists / is non-empty; raise typed `LoadError`.

### 2. Case / reaction normalization (`autopader/data/normalizer.py`)
```python
class CaseTable(BaseModel):
    rows: pd.DataFrame          # first row per safetyreportid; case-level attrs
    n_cases: int
    reaction_counts_per_case: dict[int, int]

def build_case_table(df) -> CaseTable:
    # case level: first-row-wins per safetyreportid (keep="first")
    # reaction_rows_per_case = groupby size (includes cross-row + within-row tokens)

def build_reaction_table(df) -> pd.DataFrame:
    # reaction level: split patient_reaction_reactionmeddrapt on ',', strip,
    # explode to one row per (case, PT-token), positionally align outcome tokens.
    # 6 mismatch rows → flagged, aligned by position, remainder dropped w/ warning (never silently)
    # Returns columns: safetyreportid, reaction (PT), outcome, serious (case flag), receivedate, ...
```
- Case-level normalization: dedupe, normalize `serious` → enum, pick country rule, parse dates via format code.
- Reaction-level normalization: explode tokens (`.str.split(',')` then `.explode()`), strip whitespace, drop empties; assert positional outcome alignment.
- Age bucketing: convert unit→years; buckets `0-17, 18-64, 65-74, 75-84, 85+, unknown`; garbage unit/NaN → `unknown` (recorded, not dropped).
- Every normalization rule is a pure function returning counts of what it changed (missing values surfaced, never hidden).

### 3. Deterministic analysis (`autopader/analysis/`)
```python
# analysis/results.py
class EvidenceSource(BaseModel):
    evidence_id: str          # e.g. "case.total_cases.v1"
    value: str                # exact display value the LLM may quote ("1,024")
    kind: Literal["count","percent","list","date_range","flag","ratio"]
    provenance: str           # "case_metrics.total_cases()" + dataset sha256 short

class AnalysisResult(BaseModel):
    reporting_period: tuple[str, str]
    total_cases: int
    serious_cases: int
    not_serious_cases: int
    expedited_cases: int
    age_group_counts: dict[str, int]
    sex_counts: dict[str, int]
    country_counts: dict[str, int]
    top_reactions: list[tuple[str, int]]
    top_serious_reactions: list[tuple[str, int]]
    outcome_counts: dict[str, int]
    monthly_cases: list[dict]            # [{month:"2025-01", count:n, delta:±n}]
    reporter_qualification_counts: dict[str, int]
    case_listing: list[dict]             # row data for the case index
    evidence: dict[str, EvidenceSource]  # ALL computed values, keyed by evidence_id
```
- One module per metric family (case_metrics, reaction_metrics, time_trends); each returns values that are wrapped into `EvidenceSource`.
- Percentages computed by Python (e.g., serious % = 99.9%), never by the LLM.
- Time trends: month buckets from `receivedate`; delta vs prior month; only factual statements ("X cases in Jan, Y in Mar"), never "signal".

### 4. Evidence packets (`autopader/evidence/packet.py` + `config/report_config.py`)
```python
class EvidencePacket(BaseModel):
    section: str
    evidence: list[EvidenceSource]   # ONLY what this section may reference
    case_ids: list[int]              # source case IDs where appropriate
    limitations: list[str]           # e.g. ["No SOC field; analysis at PT level only",
                                     #  "No product label supplied; expectedness not assessed",
                                     #  "No history-of-actions data supplied"]
    narration_rules: list[str]       # from report_config section declaration

# report_config declares, per section, the ALLOWED evidence keys:
REPORT_SECTIONS = {
  "narrative_summary": {
      "required_evidence": ["case.total_cases","case.serious_cases","case.serious_pct",
                            "case.not_serious_cases","case.expedited_cases","react.top_reactions",
                            "case.period_start","case.period_end"],
      "narration_rules": ["quote packet figures verbatim", "do not infer safety conclusions", ...] },
  "summary_analysis":  { "required_evidence": ["case.age_groups","case.sex","case.country", ...] },
  "reaction_analysis": { "required_evidence": ["react.top_reactions","react.top_serious_reactions",
                                               "react.outcome_counts", ...] },
  "serious_alerts":    { "required_evidence": ["case.expedited_cases","react.top_serious_reactions",
                                               "listing.expedited_case_ids", ...] },
  "trends":            { "required_evidence": ["trend.monthly_cases", ...] },
}
```
- `packet_for(section, results)` returns a packet containing ONLY the declared evidence keys (plus `case_ids`/`limitations`).
- This is the mechanism that makes it impossible for the LLM to see the full dataset. Report config is the single source of "what a PADER is".

### 5. DeepSeek integration (`autopader/llm/client.py`)
```python
# Research-based: DeepSeek is OpenAI-compatible. No first-party SDK; use httpx directly (or openai pkg).
# base_url: https://api.deepseek.com  (POST /chat/completions)
# model: deepseek-v4-flash (default; cheap, adequate for narrative) or deepseek-v4-pro
# auth: Authorization: Bearer $DEEPSEEK_API_KEY
# V4 enables 'thinking' by default → send {"thinking": {"type": "disabled"}} for fast deterministic-cost narrative
class DeepSeekClient:
    def __init__(self, api_key, base_url="https://api.deepseek.com", model="deepseek-v4-flash"):
        self._http = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=httpx.Timeout(connect=10, read=120, write=120, pool=10),  # default 5s too short
            transport=httpx.HTTPTransport(retries=2),   # retries ConnectError/ConnectTimeout only
        )
    def generate(self, messages: list[dict], temperature=0.2, max_tokens=1500) -> str:
        # POST /chat/completions {model, messages, temperature, max_tokens, stream:false, thinking:{"type":"disabled"}}
        # on 429/5xx: explicit bounded backoff loop (e.g., 3 attempts, exp backoff); never retry 4xx
        # parse choices[0].message.content; raise LLMError on non-200/empty
class EchoClient:  # used when DEEPSEEK_API_KEY missing or --skip-llm
    def generate(self, messages): return render_deterministic_echo(messages)  # template filled, no call
```
- Client is thin and swappable behind a `generate(messages) -> str` interface; tests use `EchoClient` or mocked httpx.
- Temperature low (0.2) for factual narrative stability; no streaming needed for Version 0.
- Never send the dataset or packets beyond the scoped one for the current section.

### 6. Prompt / context architecture (`autopader/llm/prompts.py` + `prompts/*.md.tpl`)
Two-message design, one template per narrative section, all templates checked into `prompts/` (deliverable):

```markdown
# prompts/system_rules.md.tpl   (static system message)
You are a pharmacovigilance report writer. You convert APPROVED deterministic analysis
into regulatory-neutral narrative. RULES:
- Quote every figure exactly as provided in the evidence packet. Never round, compute, or "recalculate".
- You are given only the evidence for the section you are writing. Do not introduce facts, numbers,
  cases, or conclusions not present in this packet.
- Do not assess expectedness (no product label supplied). Do not assign System Organ Class.
- Do not claim safety signals or causality. Present observations; do not interpret them as confirmed risks.
- If a limitation is listed (e.g., no actions supplied), state it plainly.
- Output Markdown narrative only, no preamble.

# prompts/narrative_summary.md.tpl   (user message, rendered per section)
Section: Narrative Summary and Analysis
Reporting period: {{period_start}} to {{period_end}}
APPROVED ANALYSIS (quote verbatim):
{{evidence_table}}     # markdown table: evidence_id | value | kind
SOURCE CASE IDS: {{case_ids}}
LIMITATIONS: {{limitations}}
{{narration_rules}}
Write the narrative summary. Every number you use must come from APPROVED ANALYSIS.
```
- **System** message: fixed role + safety rules (regulatory tone, no arithmetic, no invention).
- **User** message: assembled dynamically per section from the evidence packet (the only dynamic part).
- Evidence rendered as a markdown table (human-readable, forces verbatim quoting) — do NOT dump JSON of the full analysis.
- `render_prompt(section, packet)` loads the template, binds ONLY packet values via `{{...}}` placeholders. `str.format`/jinja2 optional; a small custom renderer is fine — keep it dependency-light.
- Templates are checked in and exposed per INITIAL.md ("expose the actual prompts/context templates").

### 7. Grounding / traceability (`autopader/llm/grounding.py` + `evidence/manifest.py`)
```python
class ReportManifest(BaseModel):
    dataset_sha256: str
    analysis_version: str      # e.g. "1.0.0" — bump on any analysis rule change
    model: str                 # deepseek-v4-flash
    prompt_version: str        # derived from prompts/ dir hash
    generated_at: str
    sections: dict[str, list[str]]   # section -> evidence_ids used
```
- **During assembly**: each `EvidencePacket` remembers its `evidence_id`s; the report appendix lists, per section, the evidence ids + values + provenance.
- **Post-generation grounding check** (`grounding.py`): regex-extract numbers from generated narrative; for every number, assert an exact match exists in the section's packet values. Mismatch → section marked `flagged_grounding` and blocked from final unless reviewer overrides.
- The manifest is embedded as an appendix in `report_output.md` (provenance chain: dataset → analysis function → packet → narrative).

### 8. Human review (`autopader/review/review.py`)
```python
class SectionReview(BaseModel):
    section: str
    status: Literal["pending","approved","flagged","edited"]
    reviewer_notes: str = ""
    edited_text: str | None = None   # takes precedence over generated text when present
```
- `review_state.json` persists per-section status. CLI subcommands: `review approve <section>`, `review flag <section> --note ...`, `review edit <section> --text ...`.
- Assembler refuses to finalize any section whose status is `pending` or `flagged`; `edited` uses the reviewer text verbatim (with a marker in the report).
- Both analysis results and generated sections are reviewable (reviewer can approve the deterministic analysis snapshot too — a simple "analysis summary review" item).

### 9. Report generation (`autopader/report/assembler.py` + `case_listing.py`)
- Assembler renders the 8 PADER sections in order: Reporting Period / Narrative Summary and Analysis / Summary Analysis of Cases / Reaction Analysis / Serious Cases & 15-Day Alerts / Trends and Important Observations / History of Actions / Case Index / Listing.
- Narrative sections: only approved/edited LLM text. Tabular sections (Summary tabulation, Serious/Alerts table, Case listing, Trends table): rendered **directly from AnalysisResult** (deterministic), never through the LLM.
- Reporting Period header: product = Bisoprolol, period from analysis, report type = PADER-style (quarterly/periodic), application number = "not supplied" (honest).
- History of Actions section: fixed template text stating no actions were supplied for this exercise (from limitations).
- Case listing: Markdown table (safetyreportid, reactions, seriousness, receivedate, country, outcomes) + note that expectedness/SOC are not included because not supplied.
- Append traceability appendix + manifest. Write `report_output.md`.
- `architecture.md` is generated/maintained describing components and the data flow (deliverable).

### 10. Testing (`tests/`)
- pytest; `conftest.py` with the real XLSX path fixture + synthetic fixtures (multi-row case, multi-token reaction, missing age, 'not serious' value, mismatch rows).
- Per AGENTS.md, every component gets happy-path, edge-case, and failure tests. Minimum suite (8 required areas from INITIAL.md):
  - case deduplication (1,068 rows → 1,024 cases), serious counting (1,023 / 1)
  - reaction counting (3,648 tokens, 1,122 unique PTs; serious-only filter)
  - missing values (NaN age → unknown bucket; blank agegroup ignored; unit '800' → unknown)
  - age bucketing (boundaries 17/18, 64/65, 74/75, 84/85; unit conversions)
  - evidence generation (packet scoping: narrative packet has total_cases but NOT monthly_cases; evidence ids present)
  - prompt generation (rendered prompt contains only packet values; system rules present; no raw CSV markers)
  - grounding check (numbers in narrative ⊆ packet; false number → flagged)
  - report generation (8 sections present; pending/flagged blocks final; appendix manifest present)
- Failure tests: bad file path, wrong format, missing required column, empty reaction token, HTTP 500, timeout, empty LLM response.

### 11. Evaluation at scale (`autopader/evaluate/`)
Version 0 needs "some way of checking whether a generated report is actually correct, beyond eyeballing it" (challenge doc). Design a layered harness, all runnable in batch:
```yaml
Level A — Deterministic correctness (always run):
  - Golden-number assertions on the supplied dataset (1,024 / 1,023 / 1 / 3,648 / 1,122 / period bounds).
  - Regression: rerun analysis, diff against stored expected JSON. Fail on any drift.

Level B — Traceability (always run, per report):
  - grounding_check on every narrative section (numbers ⊆ packet). Fail count must be 0 for final.

Level C — Coverage (always run):
  - coverage_check: each section must mention its required key facts (e.g., Narrative Summary must
    mention total cases, serious count, top reaction; History of Actions must state no actions supplied).
  - Implemented as required-mention list per section in report_config (not LLM-judged).

Level D — Batch scale (Version 0 script, run over many configs/datasets):
  - evaluate/run_batch.py: (dataset, report_config, model) matrix → per-run Levels A–C + aggregated
    metrics (grounding violation count, coverage pass rate). Serves the Version 1 "reusable analyses +
    config-driven report types" path and stress-tests generalization without new code paths.

Level E — Optional qualitative (offline, not a gate):
  - LLM-as-judge (DeepSeek) comparing generated narrative vs reference on groundedness/verbosity rubric.
    Numbers are STILL verified by Level B deterministically; the judge never adjudicates arithmetic.
```
- Design principle: every correctness signal that can be computed in Python is computed in Python. The LLM judge is advisory only.

## Task List (in order)
```yaml
Task 1:  Scaffold autopader/ package + config/settings.py + requirements.txt + .env.example (DEEPSEEK_* vars)
Task 2:  data/loader.py (openpyxl pinned, dtype=object, sha256) + tests
Task 3:  data/validator.py (schema, domains, mismatch/missing reporting) + tests
Task 4:  data/normalizer.py (case table, reaction explode w/ positional alignment, age buckets, serious enum, country rule, date parsing) + tests
Task 5:  analysis/ (results.py EvidenceSource/AnalysisResult, case_metrics, reaction_metrics, time_trends) + tests
Task 6:  config/report_config.py (PADER section declarations) + evidence/packet.py + manifest.py + tests
Task 7:  prompts/*.md.tpl + llm/prompts.py renderer + tests (exposed templates)
Task 8:  llm/client.py (DeepSeek httpx client, EchoClient, retries/timeouts) + tests (mocked httpx)
Task 9:  llm/grounding.py (number↔packet matching) + tests
Task 10: review/review.py (approve/flag/edit, review_state.json) + tests
Task 11: report/assembler.py + case_listing.py (8 sections, appendix, manifest) + tests
Task 12: cli.py end-to-end wiring (--skip-llm deterministic path, real DeepSeek path)
Task 13: evaluate/ (trace_check, coverage_check, run_batch) + tests
Task 14: architecture.md + README (run steps, AI vs deterministic split, prompts, design decisions, limitations, Version 1 sketch)
Task 15: Full validation loops green; generate report_output.md on supplied dataset
```

## Validation Loop

### Level 1: Syntax & Style
```bash
python -m pip install -r requirements.txt
ruff check autopader/ tests/ --fix
black --check autopader/ tests/
mypy autopader/
# Expected: clean. Fix before proceeding.
```

### Level 2: Unit Tests
```bash
python -m pytest tests/ -v
# Every component: happy / edge / failure. Iterate until green; never mock-to-pass.
```

### Level 3: Integration (real dataset)
```bash
# Deterministic dry-run (no API key required):
python -m autopader.cli --input "Bisoprolol_icsr_sample_1068rows.xlsx" --output report_output.md --skip-llm
# Expected: report with all 8 sections; tables deterministic; sections pending review.

# Review flow:
python -m autopader.review list            # all pending
python -m autopader.review approve narrative_summary
python -m autopader.review flag trends --note "confirm monthly deltas"
python -m autopader.review edit summary_analysis --text "..."
# Expected: report assembly excludes pending/flagged, uses edited text.

# Full pipeline (DeepSeek):
python -m autopader.cli --input "Bisoprolol_icsr_sample_1068rows.xlsx" --output report_output.md
# Expected: narrative sections generated from packets; grounding check passes; manifest appendix present.

# Evaluation batch:
python -m autopader.evaluate.run_batch --config autopader/config/report_config.py
# Expected: Levels A–C all pass; aggregated metrics printed.
```

## Final Validation Checklist
- [ ] All tests pass: `python -m pytest tests/ -v`
- [ ] No lint/type/format errors (ruff, mypy, black)
- [ ] Deterministic golden numbers match: 1,024 cases / 1,023 serious / 1 not serious / 1,023 expedited / 3,648 reaction tokens / 1,122 unique PTs / period 2024-12-27→2025-12-26
- [ ] report_output.md has all 8 sections; no SOC, no expectedness, no invented actions
- [ ] Grounding check passes on all narrative sections (0 violations)
- [ ] Review gate blocks pending/flagged sections
- [ ] DeepSeek path works with a real key; EchoClient path works without one
- [ ] Prompts/ templates + architecture.md + README updated
- [ ] Evaluation harness (Levels A–D) runnable and green

---

## Anti-Patterns to Avoid
- ❌ Feeding raw CSV (or full analysis JSON) to the LLM — defeats grounding
- ❌ Letting the LLM compute/round any statistic
- ❌ Treating rows as cases, or rows as reactions (both wrong here)
- ❌ Inferring SOC from PTs, or expectedness without a label
- ❌ Inventing history-of-actions or case narratives
- ❌ One global mega-prompt containing every datum for every section
- ❌ Hardcoding 'non-serious' (raw value is 'not serious')
- ❌ Using patient_patientagegroup (unreliable) for age analysis
- ❌ Silent data handling — missing/mismatched rows must be surfaced in validation
- ❌ Copying sample-report numbers (they differ from recomputed ground truth)
- ❌ Building report-type knowledge into every module (keep it in report_config)

## Confidence Score: 8/10
High confidence because: the feature request, architecture (PLANNING.md), phase plan (TASK.md), and global rules (AGENTS.md) are explicit; dataset structure, null patterns, and case/reaction semantics were verified directly against the XLSX; DeepSeek's OpenAI-compatible contract is well documented; and the deterministic/AI split is precisely defined.

## Unresolved Risks
1. **No Submission Guide file in the repo** — INITIAL.md references it, but only the challenge PDF's Deliverables/Evaluation sections exist. Confirm packaging, size limit, and submission target before packaging. (HIGH)
2. **LLM narrative quality is not fully deterministic** — grounding/traceability and coverage checks are enforced deterministically, but tone/verbosity vary by model/temperature. Mitigated by low temperature + mandatory packet-only wording; residual risk is wording, not numbers. (MEDIUM)
3. **No DeepSeek API key configured in the environment** — pipeline is fully testable via EchoClient/`--skip-llm`, but a live key is needed for the real report deliverable. (MEDIUM)
4. **Reaction-level semantics choice** — token-explosion (3,648) vs row-count (1,068) is a definitional decision; the sample report used token totals, supporting the choice, but it must be documented in the README and consistent everywhere. (LOW, once documented)
5. **Six misaligned PT/outcome rows** — must be surfaced in validation and handled by a documented rule (positional alignment + warning), not dropped silently. (LOW)
6. **Version 1 generalization** — the config-driven section registry covers it structurally; the one-page design doc in README should make the argument explicit (the "real test" in the challenge). (MEDIUM)
7. **OpenAI-SDK vs raw httpx choice** — raw httpx avoids a dependency and keeps the client thin, but if DeepSeek later requires SDK-only features (e.g., Responses API), a small adapter may be needed. (LOW)
