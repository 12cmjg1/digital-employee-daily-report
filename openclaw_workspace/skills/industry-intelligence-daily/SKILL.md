---
name: industry-intelligence-daily
description: Use this skill when the industry and product Claw needs to search, summarize, generate, or revise AI and robotics product intelligence.
---

# Industry And Product Intelligence Daily

Use this skill for the industry/product member. Focus on robotics companies, AI products, commercialization scenarios, investment news, product launches, and market value.

## Commands

Search real material:

```bash
python openclaw_tools.py search --claw industry --query "<user query>"
```

Generate this Claw's daily report:

```bash
python openclaw_tools.py daily --claw industry
```

Revise this Claw's current daily report:

```bash
python openclaw_tools.py revise --claw industry --instruction "<revision instruction>"
```

## Output Rules

- Prefer company/product/business materials with source links.
- Explain product value, application scenarios, and risk in short paragraphs.
- Avoid stock-market style language.
- Do not invent funding amounts or product release dates.
- Keep the output useful for a course project report.
