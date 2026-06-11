---
name: generate_daily_report
description: Generate a structured Markdown daily report from multiple digital employees' analysis results.
---

# generate_daily_report

## Purpose

Merge analysis results from AI, robotics, and industry agents into one final daily report.

## Input

- ai_report
- robotics_report
- industry_report

## Output

A Markdown report with summary, AI updates, robotics updates, industry updates, recommendations, risk judgment, learning advice, and source appendix.

## Procedure

1. Read all agent reports.
2. Remove duplicated information.
3. Rank important items first.
4. Generate a concise executive summary.
5. Generate structured Markdown.
6. Preserve source titles and URLs when available.

## Safety Rules

- Do not fabricate sources.
- Clearly mark demo data if the system runs in demo mode.
- Do not include secret keys, local paths, or private credentials in the report.
