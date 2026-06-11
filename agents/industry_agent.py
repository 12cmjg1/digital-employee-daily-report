from __future__ import annotations

from agents.common import build_agent_analysis
from core.schemas import AgentReport, AnalyzedItem, RawItem
from skills.score_skill import score_item
from skills.summarize_skill import summarize_item


def run_industry_agent(items: list[RawItem], config: dict) -> AgentReport:
    analyzed_items: list[AnalyzedItem] = []
    for item in items:
        value_analysis, risk_analysis = build_agent_analysis(item, config, "产业与产品员工")
        analyzed_items.append(
            AnalyzedItem(
                raw_item=item,
                short_summary=summarize_item(item, config),
                technical_keywords=item.tags,
                value_analysis=value_analysis,
                risk_analysis=risk_analysis,
                score=score_item(item),
            )
        )

    key_findings = [
        "仓储、制造质检和仿真平台是机器人产业化的明确应用入口。",
        "开发平台更新说明生态厂商正在争夺机器人应用开发者。",
    ]
    learning_advice = [
        "对比同类产品的目标场景、成本结构和部署条件。",
        "在答辩中说明技术指标如何转化为企业使用价值。",
    ]
    return AgentReport(
        agent_name="产业与产品员工",
        category="industry",
        executive_summary=f"今日产业员工分析了 {len(analyzed_items)} 条信息，重点关注产品发布、平台生态和商业化价值。",
        analyzed_items=analyzed_items,
        key_findings=key_findings,
        learning_advice=learning_advice,
    )
