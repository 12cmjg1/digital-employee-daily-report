from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

from dotenv import load_dotenv
import requests


load_dotenv()


def _trim_markdown(markdown: str, max_chars: int) -> str:
    if len(markdown) <= max_chars:
        return markdown
    return f"{markdown[:max_chars].rstrip()}\n\n..."


def _sign_url(webhook_url: str, secret: str) -> str:
    if not secret:
        return webhook_url
    timestamp = str(round(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{secret}"
    digest = hmac.new(
        secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    sign = quote_plus(base64.b64encode(digest).decode("utf-8"))
    separator = "&" if "?" in webhook_url else "?"
    return f"{webhook_url}{separator}timestamp={timestamp}&sign={sign}"


def _build_text_message(title: str, markdown: str, report_path: str, max_chars: int) -> dict[str, Any]:
    body = _trim_markdown(markdown, max_chars)
    text = f"{title}\n\n{body}\n\n报告文件：{report_path}"
    return {"msgtype": "text", "text": {"content": text}}


def send_dingtalk_report(markdown: str, config: dict[str, Any], report_path: str | Path) -> bool:
    """Send the generated report to a DingTalk custom robot webhook."""
    dingtalk_config = config.get("channels", {}).get("dingtalk", {})
    if not dingtalk_config.get("enabled", False):
        return False

    webhook_env = dingtalk_config.get("webhook_env", "DINGTALK_WEBHOOK_URL")
    secret_env = dingtalk_config.get("secret_env", "DINGTALK_SECRET")
    webhook_url = os.getenv(webhook_env, "").strip()
    secret = os.getenv(secret_env, "").strip()
    if not webhook_url:
        raise RuntimeError(f"DingTalk channel is enabled, but {webhook_env} is not configured.")

    title = dingtalk_config.get("title") or config.get("report", {}).get("title", "每日技术情报报告")
    max_chars = int(dingtalk_config.get("max_chars", 3500))
    timeout = int(dingtalk_config.get("timeout_seconds", 15))
    payload = _build_text_message(title, markdown, str(report_path), max_chars)

    response = requests.post(_sign_url(webhook_url, secret), json=payload, timeout=timeout)
    response.raise_for_status()
    result = response.json()
    code = result.get("errcode", 0)
    if code != 0:
        raise RuntimeError(f"DingTalk webhook returned errcode={code}: {result.get('errmsg', result)}")
    return True
