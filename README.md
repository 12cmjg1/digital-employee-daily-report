# 每日 AI 与机器人技术情报 · 数字员工系统

三个 AI Agent 协作，每天早上自动推送一份 AI + 机器人 + 产业的技术情报日报。

**在线演示**：[47.97.114.62:8501](http://47.97.114.62:8501)

---

## 做了什么

- 三个数字员工（AI 技术 / 机器人与具身智能 / 产业与产品）并行采集和分析信息
- 每条情报五维度评分（新颖性 / 工程价值 / 学习价值 / 商业价值 / 实现难度），给出 A/B/C 推荐等级
- 每天早上 8 点自动生成日报，每周日生成周报，通过钉钉机器人推送到手机
- Streamlit 网页支持日报浏览、在线修改、对话搜索，部署在阿里云上

---

## 系统架构

![系统架构](这里放架构图截图)

---

## 效果展示

**首页总览**

![首页](这里放首页截图)

**日报中心**

![日报](这里放日报截图)

**OpenClaw 对话工作区**

![对话](这里放对话截图)

**钉钉推送**

![钉钉](这里放钉钉截图)

---

## 项目结构

```
digital_employee_daily_report/
├── app.py                  Streamlit Web UI（4 页面）
├── main.py                 日报生成主流程
├── scheduler.py            定时任务（APScheduler）
├── agents/                 三个数字员工 + 总控
├── skills/                 采集 / 分类 / 摘要 / 评分 / 报告
├── core/                   LLM 客户端 / 配置 / 数据结构
├── channels/               钉钉 / 飞书推送
├── data/                   样例数据
└── reports/                生成的日报归档
```

---

## 怎么跑

```bash
pip install -r requirements.txt
# Demo 模式（零 API 开销，无需网络）
python main.py
# 带 Web UI
streamlit run app.py
```

配置文件 `config.yaml` 中切换 Demo / 真实数据模式。

---

## 技术栈

Python · Streamlit · Pydantic · APScheduler · 多 Provider LLM（DeepSeek / OpenAI / Anthropic）· 钉钉机器人 · 阿里云 Ubuntu

---

## 关于

浙江大学《人工智能基础 A》综合实践项目，胡尊昊、刘雨菲、刘子轩，2026 年 6 月。
