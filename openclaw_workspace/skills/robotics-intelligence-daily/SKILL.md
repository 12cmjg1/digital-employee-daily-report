---
name: robotics-intelligence-daily
description: Use this skill when the robotics and embodied intelligence Claw needs to search, summarize, generate, or revise robotics intelligence reports.
---

# Robotics And Embodied Intelligence Daily

Use this skill for the group leader's Claw. Focus on ROS2, SLAM, navigation, robot manipulation, embodied intelligence, VLA, robot learning, and arXiv robotics papers.

## Commands

Search real material:

```bash
python openclaw_tools.py search --claw robotics --query "<user query>"
```

Generate this Claw's daily report:

```bash
python openclaw_tools.py daily --claw robotics
```

Revise this Claw's current daily report:

```bash
python openclaw_tools.py revise --claw robotics --instruction "<revision instruction>"
```

## Search Rules

- If the user asks for arXiv, papers, research, or论文, use the search command directly; the project tool routes it to arXiv.
- For VLA, embodied intelligence, robot learning, ROS2, SLAM, and navigation, keep the query terms specific.
- Do not use ordinary web results when the user clearly asks for papers.

## Output Rules

- First list found materials with links.
- Then explain what they mean for robotics learning or engineering practice.
- Briefly state what is still missing.
- Mention the Agent/tool used only at the end.
- Do not fabricate results when evidence is weak.
