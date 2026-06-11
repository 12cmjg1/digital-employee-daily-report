# Daily AI & Robotics Intelligence System

这是一个面向“人工智能基础”综合大作业的 Python + Streamlit 项目。项目没有采用作业示例中的股票大盘、板块、个股结构，而是围绕 AI 技术学习和机器人方向跟踪，设计了“每日 AI 与机器人技术情报数字员工系统”。系统可以读取 demo 数据，也可以从 RSS、arXiv、GitHub 采集真实公开信息，交给 AI 技术员工、机器人与具身智能员工、产业与产品员工分别分析，最后由总控员工合成为 Markdown 技术日报。

## 功能

- demo 模式：无需网络和 API Key，适合课堂演示。
- real 模式：采集真实 RSS、arXiv、GitHub 信息。
- 支持 mock、OpenAI、SiliconFlow、DeepSeek、Anthropic 五种 LLM Provider。
- 真实 LLM 不可用时自动回退 mock，保证部署流水线能跑完。
- 将信息分为 AI、robotics、industry 三类。
- 生成评分、摘要、价值分析、风险提醒和学习建议。
- 输出 `reports/daily_report.md`。
- 分别输出三个 Claw 日报，并汇总成总控日报和周报。
- 提供 Streamlit 页面预览和下载 Markdown。
- 提供 4 个官方 OpenClaw 可接入的 Skill 文件夹，并通过 `openclaw_tools.py` 调用真实工具。
- 页面直接展示三名数字员工分工、原创选题、创新点、数据来源和防编造设计。

## 作业分工设计

```text
队友 1 / AI 技术员工：
  关注大模型、Agent、多模态、开源项目，判断技术新颖性、学习价值和工程复现价值。

组长 / 机器人与具身智能员工：
  关注 ROS2、SLAM、导航、机器人操作，判断工程落地条件和复现实验价值。
  同时负责服务器部署、网页运行、代码整合和总报告组织。

队友 2 / 产业与产品员工：
  关注机器人公司、AI 产品、商业化场景、投融资动态，判断产品趋势、市场价值和真实应用风险。

总控员工：
  整合三名员工结果，生成“技术学习 + 工程实践 + 产品趋势”综合日报。
```

## 原创性与创新点

1. 从“财经分析”改为“AI + 机器人技术情报分析”，更贴合人工智能课程。
2. 三个员工分别覆盖技术、工程、产业三个视角，避免简单重复总结。
3. 报告不只总结新闻，还给出学习建议、工程价值、风险提醒和推荐等级。
4. 每条信息保留来源链接，便于答辩追溯，降低 AI 编造风险。
5. 支持 demo 模式和真实数据模式，课堂演示稳定，真实部署可扩展。
6. 用 OpenClaw Skill 连接采集、摘要、评分、报告生成和报告修改能力，网页只负责展示。

## 运行

```bash
cd digital_employee_daily_report
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

真实数据模式：

```bash
python main.py --config config.real.yaml
```

默认真实配置会限制条目数量，避免真实模型调用过多。需要更完整日报时，可以调大 `max_items_total`、`max_items_per_agent` 和 `max_items_per_source`。

默认只让总控员工调用真实 LLM 生成全局摘要、技术解读、风险趋势和后续建议。若要让每条情报也调用 LLM，把 `use_llm_for_agent_analysis` 改成 `true`，但会明显增加耗时和费用。

网页模式：

```bash
streamlit run app.py
```

浏览器访问：

```text
http://localhost:8501
```

公网演示页面已增加访问密码。默认密码为 `fengyuwuzu`，也可以通过服务器环境变量 `APP_PASSWORD` 修改。

## 真实 LLM

如果要让 Agent 调用真实大模型，把 `config.real.yaml` 中的 `llm_provider` 改成 `openai`、`siliconflow`、`deepseek` 或 `anthropic`，并在 `.env` 中配置对应 API Key。没有 API Key 时也可以保持 `mock`，此时是真实采集数据 + 本地模板分析。

SiliconFlow 示例：

```env
SILICONFLOW_API_KEY=你的 SiliconFlow Key
SILICONFLOW_MODEL=Qwen/Qwen2.5-7B-Instruct
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
```

DeepSeek 官方 API 示例：

```env
DEEPSEEK_API_KEY=你的 DeepSeek Key
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

网页中的“OpenClaw 接入”页面只展示接入方式，不再模拟官方 OpenClaw 对话。三个 Claw 应在 OpenClaw 中作为 Agent 身份管理：AI 技术 Claw、机器人与具身智能 Claw、产业与产品 Claw。它们通过 `openclaw_workspace/skills/` 下的 Skill 调用 `openclaw_tools.py`，完成搜索、日报生成、周报生成和报告修改。DeepSeek 只负责基于真实材料总结，不负责替代搜索。

## 目录说明

```text
agents/             三个分析员工和一个总控员工
skills/             采集、分类、摘要、评分、报告渲染能力
core/               配置、Schema、存储和 LLM 客户端
data/               demo 数据、真实采集结果和中间结果
reports/            生成的 Markdown 日报
openclaw_workspace/ 官方 OpenClaw Agent 与 Skill 接入文件
openclaw_skills/    早期 Skill 设计文档，保留作业过程参考
deploy/             云服务器部署说明
```

报告输出：

```text
reports/ai_claw_daily_report.md          AI 技术 Claw 日报
reports/robotics_claw_daily_report.md    机器人与具身智能 Claw 日报
reports/industry_claw_daily_report.md    产业与产品 Claw 日报
reports/daily_report.md                  总控汇总日报
reports/weekly_report.md                 汇总周报
```

## 答辩展示建议

1. 打开 Streamlit 页面，展示原创选题和三员工分工。
2. 点击“生成今日技术日报”，展示完整运行过程。
3. 展示 `data/raw_items.json` 中的来源记录，说明如何避免 AI 编造。
4. 展示 `reports/daily_report.md` 的结构化内容。
5. 展示“实验方案对比”和“项目创新点”页面。
6. 展示 `openclaw_workspace/skills/` 下的 Skill 文档，说明三个 Claw 如何正式调用项目工具。
7. 说明云服务器部署方式和 2C2G 资源下的成本控制策略。
