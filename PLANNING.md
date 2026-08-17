# GenAR Architecture

## Goal

Build a prototype that transforms Bisoprolol ICSR safety data
into an evidence-backed PADER-style report.

## Pipeline

Raw XLSX/CSV
    ↓
Data Loader
    ↓
Data Validator
    ↓
Case-Level Normalization
    ↓
Deterministic Analysis
    ↓
Evidence Packets
    ↓
LLM Narrative Generation
    ↓
Human Review
    ↓
Report Renderer

## Deterministic Layer

Python is responsible for:

- total cases
- serious cases
- non-serious cases
- age groups
- sex
- country
- reactions
- serious reactions
- outcomes
- trends
- expedited cases
- case listing

## AI Layer

The LLM is responsible for:

- narrative wording
- summarization
- interpretation of supplied observations
- report-section drafting

## Evidence Layer

Every AI section receives:

- section name
- reporting period
- approved metrics
- observations
- source case IDs where appropriate
- explicit limitations

## Human Review

Generated sections must be reviewable before finalization.

## Report

Generate Markdown initially.

Possible future outputs:

- HTML
- DOCX
- PDF