# 飞书 Channel 配置

本项目支持通过飞书自定义机器人 webhook 推送生成后的日报。

## 1. 创建飞书机器人

在飞书群中添加“自定义机器人”，复制 webhook 地址。

## 2. 配置服务器环境变量

在服务器项目目录的 `.env` 中添加：

```env
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/你的机器人token
```

不要把真实 webhook 提交到 GitHub。

## 3. 启用 channel

编辑 `config.real.yaml`：

```yaml
channels:
  feishu:
    enabled: true
    webhook_env: "FEISHU_WEBHOOK_URL"
    title: "每日 AI 与机器人技术情报报告"
    max_chars: 3500
    timeout_seconds: 15
```

## 4. 运行

```bash
python main.py --config config.real.yaml
```

生成 `reports/daily_report.md` 后，系统会自动把报告摘要推送到飞书群。
