# AutoPADER AI — Evidence-Backed Pharmacovigilance Safety Report Generator

AutoPADER AI is an evidence-grounded AI system engineered for pharmacovigilance and regulatory compliance. It processes Individual Case Safety Report (ICSR) datasets—specifically demonstrated on the **Bisoprolol ICSR dataset** (1,068 rows across 1,024 unique safety cases)—and generates audit-ready Periodic Adverse Drug Experience Reports (PADER).

Unlike generic LLM applications, AutoPADER AI strictly decouples **deterministic numerical analysis** from **AI narrative synthesis**:
- **Deterministic Python Engine**: Calculates all case counts, seriousness flags, reaction MedDRA Preferred Terms (PT), demographics, and temporal reporting periods.
- **Evidence Packets**: Only minimal, section-scoped data extracts (never raw datasets) are provided to the LLM.
- **Grounding & Guardrails**: LLM narrative outputs undergo automated grounding checks and Chain-of-Thought (CoT) leakage detection.
- **Human Review**: Built-in human-in-the-loop workflow allows safety reviewers to approve, flag, or edit sections before final report assembly.

---

## 🏗️ System Architecture

![AutoPADER AI Architecture](https://raw.githubusercontent.com/akhiranandan-04/AutoPADER-AI/main/docs/architecture.png)

---

## 🎯 Where This Can Be Used (Use Cases)

AutoPADER AI is designed for drug safety operations, clinical research organizations (CROs), and pharmaceutical regulatory affairs:

1. **Periodic Safety Reporting (PADER / PSUR / DSUR)**
   - Automatically generates structured safety report sections for post-marketing surveillance requirements.
2. **Pharmacovigilance & Case Safety Analysis**
   - Analyzes incoming ICSR safety data, identifying top adverse reactions, patient demographics, and seriousness distributions.
3. **Expedited (15-Day) Case Auditing**
   - Segregates serious expedited cases from non-expedited incidents with deterministic accuracy.
4. **Regulatory Audit Trail & Traceability**
   - Every statistic in the generated report links directly to a verifiable Python `EvidenceSource`, guaranteeing zero numerical hallucination.
5. **Human-in-the-Loop Medical Review**
   - Streamlines medical review by enabling safety scientists to review, flag, or edit AI-generated narratives before report sign-off.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10 or higher
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/akhiranandan-04/AutoPADER-AI.git
cd AutoPADER-AI

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
```

To enable live LLM narrative generation, set your API key in `.env`:
```text
OPENROUTER_API_KEY=your_openrouter_api_key
```

---

## 💻 Execution & Command Guide

AutoPADER AI is operated via a command-line interface (`python -m autopader`).

### 1. Deterministic Dataset Analysis

Run data ingestion and deterministic metric analysis without invoking an LLM:

```powershell
python -m autopader analyze --dataset Bisoprolol_icsr_sample_1068rows.xlsx
```

**Key Metrics Analyzed:**
- Reporting Period (2024-12-27 to 2025-12-26)
- Unique Cases (1,024) and Serious Cases (1,023)
- Expedited / 15-Day Cases (1,023)
- Top Reaction Preferred Terms (Acute kidney injury: 81, Drug ineffective: 60, Hypotension: 48)
- Patient Demographics & Outcome Breakdown

### 2. Generate Dry-Run Report (Offline Mode)

Execute the full pipeline locally without making external API calls:

```powershell
python -m autopader generate --skip-llm --allow-pending
```

*This uses the built-in deterministic `EchoClient`, ideal for CI/CD pipelines, offline development, and testing.*

### 3. Generate Live LLM Safety Report

Generate narrative report sections using OpenRouter's free model router:

```powershell
python -m autopader generate
```

### 4. Interactive Human Review Workflow

Review individual sections before final report assembly:

- **Approve a section**:
  ```powershell
  python -m autopader review approve narrative_summary --note "Approved by safety reviewer"
  ```
- **Flag a section for re-check**:
  ```powershell
  python -m autopader review flag summary_analysis --note "Requires updated narrative details"
  ```
- **Edit section content directly**:
  ```powershell
  python -m autopader review edit reaction_analysis --text "Updated reaction narrative text..."
  ```

---

## 📊 Dataset Golden Metrics (Verified)

| Metric | Value | Description |
| :--- | :--- | :--- |
| **Total Rows** | 1,068 | Total reaction records in dataset |
| **Unique Cases** | 1,024 | Distinct `safetyreportid` cases |
| **Serious Cases** | 1,023 | Cases flagged serious |
| **Not-Serious Cases** | 1 | Raw value `'not serious'` |
| **Expedited (15-Day)** | 1,023 | Cases meeting 15-day reporting criteria |
| **Reporting Period** | 2024-12-27 to 2025-12-26 | Date range of case submission |
| **Top Reported Reaction** | Acute kidney injury (81) | Most frequent MedDRA Preferred Term |

---

## 🛡️ Critical Safety Rules & Architecture

As outlined in `AGENTS.md`, the system adheres to strict safety principles:

- **No Authoritative LLM Calculations**: Numerical analysis is performed 100% deterministically in Python using `pandas` and `pydantic`.
- **Minimal Context Transfer**: Raw datasets are never transmitted to LLM endpoints. Only section-scoped evidence packets are provided.
- **No Hallucinated Regulatory Data**: The system never invents System Organ Classes (SOC), expectedness, safety actions, or unsupported case narratives.
- **Reviewer Gating**: Reports cannot be finalized while required sections remain flagged or pending approval.

---

## 🧪 Testing & Code Quality

The codebase includes a comprehensive suite of 160 unit and integration tests covering happy paths, edge cases, and failure modes.

```bash
# Run unit & integration test suite (160 tests passing)
python -m pytest tests/ -v

# Linting & Type Checking
python -m ruff check autopader tests
python -m mypy autopader
python -m black --check autopader tests
```

---

## 📁 Repository Structure

```
AutoPADER-AI/
├── autopader/                   # Core Python application package
│   ├── ingestion.py             # ICSR dataset loading & validation
│   ├── analysis.py              # Deterministic safety analysis engine
│   ├── evidence.py              # Section evidence packets & grounding
│   ├── client.py                # OpenRouter LLM & Echo client implementations
│   ├── reviewer.py              # Human-in-the-loop review state manager
│   ├── generator.py             # Section generator & pipeline orchestrator
│   └── renderer.py              # Final Markdown report renderer
├── tests/                       # Automated test suite (160 tests)
├── prompts/                     # Section prompt templates
├── Bisoprolol_icsr_sample_1068rows.xlsx # Target ICSR safety dataset
├── AGENTS.md                    # Safety rules & engineering principles
├── architecture.md              # Detailed technical architecture documentation
└── README.md                    # Project documentation
```