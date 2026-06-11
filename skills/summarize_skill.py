from __future__ import annotations

from core.llm_client import call_llm_with_fallback
from core.schemas import RawItem


def summarize_item(item: RawItem, config: dict) -> str:
    """Summarize one raw item into a short Chinese summary."""
    provider = config.get("runtime", {}).get("llm_provider", "mock")
    prompt = (
        "请生成 100 字以内中文技术摘要。"
        f"标题：{item.title}\n来源：{item.source}\n摘要：{item.summary}\n正文：{item.content or ''}"
    )
    use_llm = config.get("runtime", {}).get("use_llm_for_item_summary", False)
    if provider == "mock" or not use_llm:
        tags = "、".join(item.tags[:3]) if item.tags else "相关技术"
        return f"{item.title}：围绕 {tags} 展开，核心信息是 {item.summary}"
    return call_llm_with_fallback(prompt, provider=provider)
