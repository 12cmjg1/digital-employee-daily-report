from __future__ import annotations

from core.llm_client import call_llm_with_fallback
from core.schemas import RawItem


def _template_analysis(item: RawItem) -> tuple[str, str]:
    tags = "、".join(item.tags[:3]) if item.tags else "相关技术"
    value = f"该信息围绕 {tags} 展开，可用于跟踪工程方向、学习重点和潜在产品化机会。"
    risk = "仍需核验来源可信度、真实部署条件、复现成本和长期维护风险。"
    return value, risk


def build_agent_analysis(item: RawItem, config: dict, role: str) -> tuple[str, str]:
    if not config.get("runtime", {}).get("use_llm_for_agent_analysis", False):
        return _template_analysis(item)

    provider = config.get("runtime", {}).get("llm_provider", "mock")
    prompt = f"""
你是{role}。请基于下面真实采集到的情报，输出两段中文分析：
1. 价值判断：说明它为什么值得关注，和工程/学习/产业有什么关系。
2. 风险提醒：说明还需要验证什么，避免夸大。

要求：
- 不要编造输入中没有的事实。
- 每段不超过 80 字。
- 输出格式固定为：
价值判断：...
风险提醒：...

标题：{item.title}
来源：{item.source}
发布时间：{item.published_at or "未知"}
摘要：{item.summary}
正文片段：{item.content or ""}
标签：{", ".join(item.tags)}
"""
    text = call_llm_with_fallback(
        prompt,
        provider=provider,
        system_prompt="你是真实部署的数字员工，负责严谨、克制地分析技术情报。",
    )
    value, risk = _template_analysis(item)
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("价值判断"):
            value = stripped.split("：", 1)[-1].strip()
        elif stripped.startswith("风险提醒"):
            risk = stripped.split("：", 1)[-1].strip()
    return value, risk
