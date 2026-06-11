from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
import requests


load_dotenv()


def _trim_markdown(markdown: str, max_chars: int) -> str:
    if len(markdown) <= max_chars:
        return markdown
    return f"{markdown[:max_chars].rstrip()}\n\n..."


def _build_text_message(title: str, markdown: str, report_path: str, max_chars: int) -> dict[str, Any]:
    body = _trim_markdown(markdown, max_chars)
    text = f"{title}\n\n{body}\n\n报告文件：{report_path}"
    return {"msg_type": "text", "content": {"text": text}}


def send_feishu_report(markdown: str, config: dict[str, Any], report_path: str | Path) -> bool:
    """Send the generated report to a Feishu custom bot webhook."""
    feishu_config = config.get("channels", {}).get("feishu", {})
    if not feishu_config.get("enabled", False):
        return False

    webhook_env = feishu_config.get("webhook_env", "FEISHU_WEBHOOK_URL")
    webhook_url = os.getenv(webhook_env, "").strip()
    if not webhook_url:
        raise RuntimeError(f"Feishu channel is enabled, but {webhook_env} is not configured.")

    title = feishu_config.get("title") or config.get("report", {}).get("title", "每日技术情报报告")
    max_chars = int(feishu_config.get("max_chars", 3500))
    payload = _build_text_message(title, markdown, str(report_path), max_chars)
    timeout = int(feishu_config.get("timeout_seconds", 15))

    response = requests.post(webhook_url, json=payload, timeout=timeout)
    response.raise_for_status()
    result = response.json()
    code = result.get("code", 0)
    if code != 0:
        raise RuntimeError(f"Feishu webhook returned code={code}: {result.get('msg', result)}")
    return True
