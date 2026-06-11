---
name: manager-report-synthesis
description: Use this skill when the manager Claw needs to generate or revise the combined daily report or weekly report.
---

# Manager Report Synthesis

Use this skill for the manager Claw. It integrates the AI technology Claw, robotics Claw, and industry/product Claw into one daily or weekly report.

## Commands

Generate all Claw daily reports and the manager daily report:

```bash
python openclaw_tools.py daily --claw all
```

Generate the weekly report:

```bash
python openclaw_tools.py weekly
```

Revise the manager daily report:

```bash
python openclaw_tools.py revise --report manager --instruction "<revision instruction>"
```

Revise the weekly report:

```bash
python openclaw_tools.py revise --report weekly --instruction "<revision instruction>"
```

## Output Rules

- Summarize the three Claws as technology learning, engineering practice, and product trend.
- Keep reports concise.
- Preserve source links.
- Do not rewrite archived historical reports.
- When revising, keep a backup before replacing the current report.
