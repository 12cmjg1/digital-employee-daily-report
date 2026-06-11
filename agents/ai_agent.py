from __future__ import annotations

from agents.common import build_agent_analysis
from core.schemas import AgentReport, AnalyzedItem, RawItem
from skills.score_skill import score_item
from skills.summarize_skill import summarize_item


def run_ai_agent(items: list[RawItem], config: dict) -> AgentReport:
    analyzed_items: list[AnalyzedItem] = []
    for item in items:
        score = score_item(item)
        value_analysis, risk_analysis = build_agent_analysis(item, config, "AI 技术员工")
        analyzed_items.append(
            AnalyzedItem(
                raw_item=item,
                short_summary=summarize_item(item, config),
                technical_keywords=item.tags,
                value_analysis=value_analysis,
                risk_analysis=risk_analysis,
                score=score,
            )
        )

    key_findings = [
        "多模态、Agent 工具调用和高效微调仍是 AI 工程落地的高频方向。",
        "值得优先关注能降低部署成本、提升评测可靠性的技术更新。",
    ]
    learning_advice = [
        "复习 Transformer、多模态表示学习和参数高效微调基础。",
        "尝试把一个小型 Agent 工作流接入真实工具，记录失败恢复策略。",
    ]
    return AgentReport(
        agent_name="AI 技术员工",
        category="ai",
        executive_summary=f"今日 AI 技术员工分析了 {len(analyzed_items)} 条信息，重点关注模型能力、Agent 编排和训练效率。",
        analyzed_items=analyzed_items,
        key_findings=key_findings,
        learning_advice=learning_advice,
    )
