# OpenClaw Workspace

This folder contains the official OpenClaw-facing workspace assets for the project.

## Install Skills

On the server, copy the skill folders into OpenClaw's skill directory:

```bash
mkdir -p ~/.openclaw/skills
cp -r openclaw_workspace/skills/* ~/.openclaw/skills/
```

Keep the project directory as the command working directory when OpenClaw runs the skills:

```bash
cd ~/apps/digital_employee_daily_report
python openclaw_tools.py search --claw robotics --query "arXiv 最新机器人科研论文"
```

## Low Resource Design

The project does not start three Claw services. Three Claws are Agent identities that call the same lightweight command tool with different `--claw` values.

## Skill Mapping

- AI 技术 Claw -> `ai-intelligence-daily`
- 机器人与具身智能 Claw -> `robotics-intelligence-daily`
- 产业与产品 Claw -> `industry-intelligence-daily`
- 总控 Claw -> `manager-report-synthesis`
