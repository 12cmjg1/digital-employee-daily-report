# 真实部署 Agent 运行说明

本项目支持两种运行方式：

- `config.yaml`：离线 demo 模式，适合课堂演示。
- `config.real.yaml`：真实数据模式，从 RSS、arXiv、GitHub 采集公开信息，再交给三个数字员工分析。

## 本地真实运行

```bash
cd digital_employee_daily_report
pip install -r requirements.txt
python main.py --config config.real.yaml
```

输出文件：

```text
reports/daily_report.md
data/raw_items.json
data/analyzed_results.json
```

## 接入真实 LLM

默认 `config.real.yaml` 使用 `llm_provider: "mock"`，这表示真实采集数据，但分析文字用本地 mock，保证没有 API Key 也能跑通。

如果要让 Agent 调用真实模型：

```yaml
runtime:
  mode: "real"
  llm_provider: "openai"
```

然后在 `.env` 中配置：

```env
OPENAI_API_KEY=你的key
OPENAI_MODEL=gpt-4o-mini
```

也可以使用 SiliconFlow 中转：

```yaml
runtime:
  llm_provider: "siliconflow"
```

```env
SILICONFLOW_API_KEY=你的 SiliconFlow Key
SILICONFLOW_MODEL=Qwen/Qwen2.5-7B-Instruct
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
```

也可以使用 Anthropic：

```yaml
runtime:
  llm_provider: "anthropic"
```

```env
ANTHROPIC_API_KEY=你的key
ANTHROPIC_MODEL=claude-3-5-sonnet-latest
```

## 三个真实部署 Agent

- AI 技术员工：读取真实采集到的 AI、arXiv、GitHub 条目，生成摘要、价值判断、风险提醒和评分。
- 机器人与具身智能员工：读取真实机器人、ROS2、SLAM、导航、操作相关条目，生成分析。
- 产业与产品员工：读取真实产品、平台、公司和 GitHub 项目信息，判断商业化价值。
- 总控员工：合并三位员工输出，生成最终 Markdown 日报。

## 云服务器运行

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv git -y

git clone <your_repo_url>
cd digital_employee_daily_report
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python main.py --config config.real.yaml
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

真实数据模式依赖服务器能访问 RSS、arXiv 和 GitHub。GitHub 未配置 Token 时也能访问公开搜索，但速率限制更低。
