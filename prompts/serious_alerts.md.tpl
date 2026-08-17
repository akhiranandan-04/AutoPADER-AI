Section: {{section_title}}
Reporting period: {{period_start}} to {{period_end}}
APPROVED ANALYSIS (quote verbatim):
{{evidence_table}}
SOURCE CASE IDS: {{case_ids}}
LIMITATIONS:
{{limitations}}
NARRATION RULES:
{{narration_rules}}

Write the serious cases and 15-day alert section as a concise, professional paragraph (3-6 sentences). REQUIREMENTS:
- Do NOT respond with "None" or an empty statement: APPROVED ANALYSIS supplies serious-case figures (case.serious_cases, case.expedited_cases, react.top_serious_reactions).
- Clearly distinguish the two counts:
  * number of serious cases (case.serious_cases);
  * number of expedited (15-day) cases (case.expedited_cases).
- List the most frequently reported reactions in serious cases and their counts from APPROVED ANALYSIS (react.top_serious_reactions).
- Quote every figure verbatim. Never invent numbers, alert classifications, or regulatory actions.
- If serious or expedited figures are absent from APPROVED ANALYSIS, say "not supplied" rather than inventing them.
- Present observed reactions only; do not claim a safety signal or causality.
- Do not show chain-of-thought or any planning. Output ONLY the finished narrative paragraph, no headings or bullet lists.