# OpenClaw Agent Layout

This workspace maps the course project into official OpenClaw-style Agents and Skills.

## Agents

### AI 技术 Claw

- Owner: 队友 1
- Skill: `ai-intelligence-daily`
- Responsibility: large models, AI agents, multimodal AI, open-source AI projects, model/product updates.

### 机器人与具身智能 Claw

- Owner: 组长
- Skill: `robotics-intelligence-daily`
- Responsibility: ROS2, SLAM, navigation, robot manipulation, embodied intelligence, VLA, robot learning, arXiv robotics papers.

### 产业与产品 Claw

- Owner: 队友 2
- Skill: `industry-intelligence-daily`
- Responsibility: robotics companies, AI products, commercialization scenarios, investment news, product launches.

### 总控 Claw

- Owner: 组长统筹
- Skill: `manager-report-synthesis`
- Responsibility: merge three Claw reports into the manager daily report and weekly report.

## Runtime Policy

- Do not run three separate services.
- Use one shared project tool: `openclaw_tools.py`.
- Use DeepSeek or another remote API only for summarization and report editing.
- Use deterministic project tools for search and report file operations.
- Keep historical archived reports read-only.
