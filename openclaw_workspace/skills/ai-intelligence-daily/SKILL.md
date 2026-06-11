---
name: ai-intelligence-daily
description: Use this skill when the user asks the AI technology Claw to search, summarize, generate, or revise daily AI technology intelligence.
---

# AI Technology Intelligence Daily

Use this skill for the AI technology member. Focus on large models, AI agents, multimodal models, open-source AI projects, model releases, and engineering value.

## Commands

Search real material:

```bash
python openclaw_tools.py search --claw ai --query "<user query>"
```

Generate this Claw's daily report:

```bash
python openclaw_tools.py daily --claw ai
```

Revise this Claw's current daily report:

```bash
python openclaw_tools.py revise --claw ai --instruction "<revision instruction>"
```

## Output Rules

- Start with found material, then give a short analysis.
- Keep source titles and URLs.
- If the tool returns no useful material, say the data is insufficient.
- Do not invent companies, dates, papers, model names, or links.
- Keep the answer concise enough for a course demo.
