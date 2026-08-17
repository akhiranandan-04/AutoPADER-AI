# GenAR Version 0 — AutoPADER Report Generator

Prototype that converts the supplied **Bisoprolol ICSR dataset** (1,068 rows,
1,024 cases) into an evidence-grounded, PADER-style safety report. Every
statistic is computed deterministically in Python and wrapped in a traceable
`EvidenceSource`; an LLM (OpenRouter free models) only turns scoped, per-section
"evidence packets" into narrative, gated by a deterministic grounding check and
human review.

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env        # add OPENROUTER_API_KEY in .env for live LLM narrative
```

### How to See the Output & Interact with It

#### 1. Interactive CLI Commands

AutoPADER is operated from the terminal using `python -m autopader`.

##### Dataset Analysis

Run deterministic analysis without using an LLM:

```powershell
python -m autopader analyze --dataset Bisoprolol_icsr_sample_1068rows.xlsx
```

This produces deterministic safety-data metrics such as:
- reporting period
- unique case count
- serious case count
- expedited/15-day case count
- reactions
- outcomes
- demographics
- trends

##### Generate Offline/Dry-Run Report

Run the complete pipeline without making an LLM API request:

```powershell
python -m autopader generate --skip-llm --allow-pending
```

This uses the deterministic EchoClient and is useful for:
- development
- testing
- CI
- environments without an API key

##### Generate Live Report

Configure the OpenRouter API key in `.env`:

```text
OPENROUTER_API_KEY=your_openrouter_api_key
```

Then run:

```powershell
python -m autopader generate
```

The application uses the configured OpenRouter free-model endpoint and generates the report using section-scoped evidence packets.

##### Human Review

Review individual generated sections before finalization.

Approve a section:
```powershell
python -m autopader review approve narrative_summary --note "Approved by reviewer"
```

Flag a section:
```powershell
python -m autopader review flag summary_analysis --note "Needs re-check"
```

Edit a section:
```powershell
python -m autopader review edit reaction_analysis --text "Updated text..."
```

A final report cannot be assembled while required sections remain pending or flagged.

#### 2. Generated Outputs

The pipeline produces:

##### Generated Report
`report_output.md`

This contains the PADER-style report, deterministic tables, case listing, and traceability information.

##### Review State
`review_state.json`

This stores human-review decisions and notes.

#### Execution Verification

The current implementation has been verified with:

##### Dataset analysis
- Reporting period: 2024-12-27 → 2025-12-26
- Input rows: 1,068
- Unique cases: 1,024
- Serious cases: 1,023
- Expedited/15-day cases: 1,023
- Top reported reaction: Acute kidney injury (81), Drug ineffective (60), Hypotension (48)

##### Report generation
The complete pipeline successfully generates `report_output.md` using the OpenRouter LLM path.

##### Automated testing
160 tests passed

Additional verification includes:
- deterministic analysis validation
- evidence-packet scoping
- numeric grounding
- qualitative grounding
- hallucination/unsupported-claim tests
- chain-of-thought leakage detection
- human-review workflow
- edited-content regression testing

## LLM configuration (OpenRouter free models)

Narrative generation targets OpenRouter's OpenAI-compatible endpoint
(`https://openrouter.ai/api/v1`) using the free-model router
`openrouter/free`. The client class is still named `DeepSeekClient` for
interface stability, but all requests go to OpenRouter:

- `OPENROUTER_API_KEY` — your OpenRouter key (required for live calls; without
  it the pipeline falls back to the deterministic `EchoClient`).
- `OPENROUTER_BASE_URL` — defaults to `https://openrouter.ai/api/v1`.
- `OPENROUTER_MODEL` — defaults to `openrouter/free` (free-model router).
- `OPENROUTER_TIMEOUT_S` — request timeout in seconds (default `120`).
- `OPENROUTER_THINKING` — retained for interface compatibility (default `disabled`).

Only the minimum evidence packet for a section is ever sent; the full dataset
is never passed to the model. All numbers come from deterministic Python
analysis, never from the LLM.

## Golden numbers (verified)

| metric | value |
| --- | --- |
| rows | 1,068 |
| unique cases (`safetyreportid`) | 1,024 |
| serious cases | 1,023 |
| not-serious cases | 1 (raw value `'not serious'`) |
| expedited (15-day) | 1,023 |
| reaction PT tokens retained | 3,642 (3,648 raw; 6 compound-PT rows padded) |
| unique PTs | 1,122 |
| reporting period | 2024-12-27 .. 2025-12-26 |
| top reaction | Acute kidney injury (81 tokens) |

## Layout & docs

- `architecture.md` — pipeline, module map, traceability model, V0 scope.
- `PRPs/genar-version0.md` — the Product Requirements Prompt being implemented.
- `prompts/*.md.tpl` — checked-in prompt/context templates (per INITIAL.md).
- `report_output.md` — generated example report (echo path).
- `TASK.md` — phase checklist (all complete).

## Testing

```bash
python -m pytest tests/ -v      # 109 tests: happy/edge/failure per module
python -m ruff check autopader tests
python -m mypy autopader
python -m black --check autopader tests
```

## Safety rules (AGENTS.md)

- The LLM never computes authoritative numbers — Python does.
- Never send the full dataset to the LLM — only section evidence packets.
- No invented SOC, expectedness, safety signals, regulatory actions, or case narratives.
- Everything untraced or unapproved stays out of the final report.

---

# Context Engineering Template

A comprehensive template for getting started with Context Engineering - the discipline of engineering context for AI coding assistants so they have the information necessary to get the job done end to end.

> **Context Engineering is 10x better than prompt engineering and 100x better than vibe coding.**

## 🚀 Quick Start

```bash
# 1. Clone this template
git clone https://github.com/coleam00/Context-Engineering-Intro.git
cd Context-Engineering-Intro

# 2. Set up your project rules (optional - template provided)
# Edit CLAUDE.md to add your project-specific guidelines

# 3. Add examples (highly recommended)
# Place relevant code examples in the examples/ folder

# 4. Create your initial feature request
# Edit INITIAL.md with your feature requirements

# 5. Generate a comprehensive PRP (Product Requirements Prompt)
# In Claude Code, run:
/generate-prp INITIAL.md

# 6. Execute the PRP to implement your feature
# In Claude Code, run:
/execute-prp PRPs/your-feature-name.md
```

## 📚 Table of Contents

- [What is Context Engineering?](#what-is-context-engineering)
- [Template Structure](#template-structure)
- [Step-by-Step Guide](#step-by-step-guide)
- [Writing Effective INITIAL.md Files](#writing-effective-initialmd-files)
- [The PRP Workflow](#the-prp-workflow)
- [Using Examples Effectively](#using-examples-effectively)
- [Best Practices](#best-practices)

## What is Context Engineering?

Context Engineering represents a paradigm shift from traditional prompt engineering:

### Prompt Engineering vs Context Engineering

**Prompt Engineering:**
- Focuses on clever wording and specific phrasing
- Limited to how you phrase a task
- Like giving someone a sticky note

**Context Engineering:**
- A complete system for providing comprehensive context
- Includes documentation, examples, rules, patterns, and validation
- Like writing a full screenplay with all the details

### Why Context Engineering Matters

1. **Reduces AI Failures**: Most agent failures aren't model failures - they're context failures
2. **Ensures Consistency**: AI follows your project patterns and conventions
3. **Enables Complex Features**: AI can handle multi-step implementations with proper context
4. **Self-Correcting**: Validation loops allow AI to fix its own mistakes

## Template Structure

```
context-engineering-intro/
├── .claude/
│   ├── commands/
│   │   ├── generate-prp.md    # Generates comprehensive PRPs
│   │   └── execute-prp.md     # Executes PRPs to implement features
│   └── settings.local.json    # Claude Code permissions
├── PRPs/
│   ├── templates/
│   │   └── prp_base.md       # Base template for PRPs
│   └── EXAMPLE_multi_agent_prp.md  # Example of a complete PRP
├── examples/                  # Your code examples (critical!)
├── CLAUDE.md                 # Global rules for AI assistant
├── INITIAL.md               # Template for feature requests
├── INITIAL_EXAMPLE.md       # Example feature request
└── README.md                # This file
```

This template doesn't focus on RAG and tools with context engineering because I have a LOT more in store for that soon. ;)

## Step-by-Step Guide

### 1. Set Up Global Rules (CLAUDE.md)

The `CLAUDE.md` file contains project-wide rules that the AI assistant will follow in every conversation. The template includes:

- **Project awareness**: Reading planning docs, checking tasks
- **Code structure**: File size limits, module organization
- **Testing requirements**: Unit test patterns, coverage expectations
- **Style conventions**: Language preferences, formatting rules
- **Documentation standards**: Docstring formats, commenting practices

**You can use the provided template as-is or customize it for your project.**

### 2. Create Your Initial Feature Request

Edit `INITIAL.md` to describe what you want to build:

```markdown
## FEATURE:
[Describe what you want to build - be specific about functionality and requirements]

## EXAMPLES:
[List any example files in the examples/ folder and explain how they should be used]

## DOCUMENTATION:
[Include links to relevant documentation, APIs, or MCP server resources]

## OTHER CONSIDERATIONS:
[Mention any gotchas, specific requirements, or things AI assistants commonly miss]
```

**See `INITIAL_EXAMPLE.md` for a complete example.**

### 3. Generate the PRP

PRPs (Product Requirements Prompts) are comprehensive implementation blueprints that include:

- Complete context and documentation
- Implementation steps with validation
- Error handling patterns
- Test requirements

They are similar to PRDs (Product Requirements Documents) but are crafted more specifically to instruct an AI coding assistant.

Run in Claude Code:
```bash
/generate-prp INITIAL.md
```

**Note:** The slash commands are custom commands defined in `.claude/commands/`. You can view their implementation:
- `.claude/commands/generate-prp.md` - See how it researches and creates PRPs
- `.claude/commands/execute-prp.md` - See how it implements features from PRPs

The `$ARGUMENTS` variable in these commands receives whatever you pass after the command name (e.g., `INITIAL.md` or `PRPs/your-feature.md`).

This command will:
1. Read your feature request
2. Research the codebase for patterns
3. Search for relevant documentation
4. Create a comprehensive PRP in `PRPs/your-feature-name.md`

### 4. Execute the PRP

Once generated, execute the PRP to implement your feature:

```bash
/execute-prp PRPs/your-feature-name.md
```

The AI coding assistant will:
1. Read all context from the PRP
2. Create a detailed implementation plan
3. Execute each step with validation
4. Run tests and fix any issues
5. Ensure all success criteria are met

## Writing Effective INITIAL.md Files

### Key Sections Explained

**FEATURE**: Be specific and comprehensive
- ❌ "Build a web scraper"
- ✅ "Build an async web scraper using BeautifulSoup that extracts product data from e-commerce sites, handles rate limiting, and stores results in PostgreSQL"

**EXAMPLES**: Leverage the examples/ folder
- Place relevant code patterns in `examples/`
- Reference specific files and patterns to follow
- Explain what aspects should be mimicked

**DOCUMENTATION**: Include all relevant resources
- API documentation URLs
- Library guides
- MCP server documentation
- Database schemas

**OTHER CONSIDERATIONS**: Capture important details
- Authentication requirements
- Rate limits or quotas
- Common pitfalls
- Performance requirements

## The PRP Workflow

### How /generate-prp Works

The command follows this process:

1. **Research Phase**
   - Analyzes your codebase for patterns
   - Searches for similar implementations
   - Identifies conventions to follow

2. **Documentation Gathering**
   - Fetches relevant API docs
   - Includes library documentation
   - Adds gotchas and quirks

3. **Blueprint Creation**
   - Creates step-by-step implementation plan
   - Includes validation gates
   - Adds test requirements

4. **Quality Check**
   - Scores confidence level (1-10)
   - Ensures all context is included

### How /execute-prp Works

1. **Load Context**: Reads the entire PRP
2. **Plan**: Creates detailed task list using TodoWrite
3. **Execute**: Implements each component
4. **Validate**: Runs tests and linting
5. **Iterate**: Fixes any issues found
6. **Complete**: Ensures all requirements met

See `PRPs/EXAMPLE_multi_agent_prp.md` for a complete example of what gets generated.

## Using Examples Effectively

The `examples/` folder is **critical** for success. AI coding assistants perform much better when they can see patterns to follow.

### What to Include in Examples

1. **Code Structure Patterns**
   - How you organize modules
   - Import conventions
   - Class/function patterns

2. **Testing Patterns**
   - Test file structure
   - Mocking approaches
   - Assertion styles

3. **Integration Patterns**
   - API client implementations
   - Database connections
   - Authentication flows

4. **CLI Patterns**
   - Argument parsing
   - Output formatting
   - Error handling

### Example Structure

```
examples/
├── README.md           # Explains what each example demonstrates
├── cli.py             # CLI implementation pattern
├── agent/             # Agent architecture patterns
│   ├── agent.py      # Agent creation pattern
│   ├── tools.py      # Tool implementation pattern
│   └── providers.py  # Multi-provider pattern
└── tests/            # Testing patterns
    ├── test_agent.py # Unit test patterns
    └── conftest.py   # Pytest configuration
```

## Best Practices

### 1. Be Explicit in INITIAL.md
- Don't assume the AI knows your preferences
- Include specific requirements and constraints
- Reference examples liberally

### 2. Provide Comprehensive Examples
- More examples = better implementations
- Show both what to do AND what not to do
- Include error handling patterns

### 3. Use Validation Gates
- PRPs include test commands that must pass
- AI will iterate until all validations succeed
- This ensures working code on first try

### 4. Leverage Documentation
- Include official API docs
- Add MCP server resources
- Reference specific documentation sections

### 5. Customize CLAUDE.md
- Add your conventions
- Include project-specific rules
- Define coding standards

## Resources

- [Claude Code Documentation](https://docs.anthropic.com/en/docs/claude-code)
- [Context Engineering Best Practices](https://www.philschmid.de/context-engineering)