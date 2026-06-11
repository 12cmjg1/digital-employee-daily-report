from __future__ import annotations

from core.schemas import AgentReport
from core.utils import source_link


def render_agent_section(report: AgentReport, heading: str, include_scores: bool = True) -> str:
    lines = [f"## {heading}", ""]
    if report.key_findings:
        lines.extend(["### 关键发现", ""])
        lines.extend([f"- {finding}" for finding in report.key_findings])
        lines.append("")

    lines.extend(["### 精选条目", ""])
    for analyzed in report.analyzed_items:
        item = analyzed.raw_item
        score = analyzed.score
        lines.extend(
            [
                f"#### {source_link(item.title, item.url)}",
                "",
                f"- 来源：{item.source}；时间：{item.published_at or '未知'}",
                f"- 摘要：{analyzed.short_summary}",
                f"- 价值：{analyzed.value_analysis}",
                f"- 风险：{analyzed.risk_analysis}",
            ]
        )
        keywords = ", ".join(analyzed.technical_keywords[:5])
        if keywords:
            lines.append(f"- 关键词：{keywords}")
        if include_scores:
            lines.append(
                "- 评分："
                f"推荐 {score.recommendation}；工程 {score.engineering_value}/5；"
                f"学习 {score.learning_value}/5；商业 {score.business_value}/5；"
                f"难度 {score.difficulty}/5"
            )
        lines.append("")

    if report.learning_advice:
        lines.extend(["### 后续建议", ""])
        lines.extend([f"- {advice}" for advice in report.learning_advice])
        lines.append("")
    return "\n".join(lines)
