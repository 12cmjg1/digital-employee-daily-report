from __future__ import annotations

from core.llm_client import call_llm_with_fallback
from core.schemas import AgentReport, AnalyzedItem
from core.utils import now_string, today_string
from skills.report_skill import render_agent_section


def _item_digest(items: list[AnalyzedItem], limit: int = 12) -> str:
    rows: list[str] = []
    for analyzed in items[:limit]:
        item = analyzed.raw_item
        rows.append(
            f"- {item.title} | category={item.category} | source={item.source} | "
            f"recommendation={analyzed.score.recommendation} | "
            f"keywords={', '.join(analyzed.technical_keywords[:4])} | "
            f"value={analyzed.value_analysis} | risk={analyzed.risk_analysis}"
        )
    return "\n".join(rows)


def _parse_manager_text(text: str) -> dict[str, str]:
    sections = {"summary": "", "technical": "", "risk": "", "advice": ""}
    mapping = {
        "今日摘要": "summary",
        "重点技术解读": "technical",
        "风险与趋势判断": "risk",
        "后续建议": "advice",
        "后续学习/开发建议": "advice",
    }
    current_key: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        matched = False
        for label, key in mapping.items():
            if line.startswith(label):
                current_key = key
                sections[key] = line.split("：", 1)[-1].strip() if "：" in line else ""
                matched = True
                break
        if not matched and current_key:
            sections[current_key] = f"{sections[current_key]}\n{line}".strip()
    return sections


def _manager_synthesis(all_items: list[AnalyzedItem], mode: str, provider: str) -> dict[str, str]:
    prompt = f"""
你是总控数字员工，负责把三个员工的分析整合成日报的全局判断。

请基于下面的真实情报摘要生成四段中文内容：
1. 今日摘要：2-3 句话，说明今天最重要的整体变化。
2. 重点技术解读：3 条要点，用 Markdown 列表。
3. 风险与趋势判断：3 条要点，用 Markdown 列表。
4. 后续建议：3 条要点，用 Markdown 列表。

要求：
- 不要编造来源中没有的公司、数字或结论。
- 语言要像技术负责人写给团队的日报，不要像广告。
- 必须按下面标题输出：
今日摘要：
重点技术解读：
风险与趋势判断：
后续建议：

运行模式：{mode}
LLM Provider：{provider}
情报条目：
{_item_digest(all_items)}
"""
    text = call_llm_with_fallback(
        prompt,
        provider=provider,
        system_prompt="你是真实部署的总控数字员工，负责严谨整合多 Agent 技术情报。",
    )
    parsed = _parse_manager_text(text)
    if not parsed["summary"]:
        parsed["summary"] = (
            f"系统以 {mode} 模式收集并分析了 {len(all_items)} 条 AI、机器人和产业产品信息。"
            "三个数字员工分别完成领域分析，总控员工已基于条目价值和风险进行整合。"
        )
    if not parsed["technical"]:
        parsed["technical"] = "- AI Agent、机器人应用和产业基础设施是今日主要关注方向。"
    if not parsed["risk"]:
        parsed["risk"] = "- 需要继续核验来源可信度、复现成本和真实部署约束。"
    if not parsed["advice"]:
        parsed["advice"] = "- 优先选择可复现条目做小实验，并保留来源链接便于答辩追溯。"
    return parsed


def run_manager_agent(
    ai_report: AgentReport,
    robotics_report: AgentReport,
    industry_report: AgentReport,
    config: dict,
    run_id: str | None = None,
) -> str:
    title = config.get("report", {}).get("title", "每日 AI 与机器人技术情报报告")
    timezone = config.get("project", {}).get("timezone", "Asia/Shanghai")
    include_scores = config.get("report", {}).get("include_scores", True)
    mode = config.get("runtime", {}).get("mode", "demo")
    provider = config.get("runtime", {}).get("llm_provider", "mock")
    generated_date = today_string(timezone)
    generated_at = now_string(timezone)
    all_items = (
        ai_report.analyzed_items
        + robotics_report.analyzed_items
        + industry_report.analyzed_items
    )
    synthesis = _manager_synthesis(all_items, mode, provider)
    top_items = sorted(
        all_items,
        key=lambda item: (
            item.score.recommendation == "A",
            item.score.engineering_value + item.score.learning_value + item.score.business_value,
        ),
        reverse=True,
    )[:5]

    lines = [
        f"# {title}",
        "",
        f"生成日期：{generated_date}",
        f"生成时间：{generated_at}",
        f"运行 ID：{run_id or 'manual'}",
        f"运行模式：{mode}；LLM Provider：{provider}",
        "",
        "## 今日摘要",
        "",
        synthesis["summary"],
        "",
        "## 今日推荐关注",
        "",
    ]
    if top_items:
        for analyzed in top_items:
            lines.append(
                f"- {analyzed.raw_item.title}：推荐级别 {analyzed.score.recommendation}，"
                f"建议关注 {', '.join(analyzed.technical_keywords[:3]) or '相关技术'}。"
            )
    else:
        lines.append("- 暂无推荐条目。")
    lines.append("")

    lines.append(render_agent_section(ai_report, "AI 技术动态", include_scores))
    lines.append(render_agent_section(robotics_report, "机器人与具身智能动态", include_scores))
    lines.append(render_agent_section(industry_report, "产业与产品动态", include_scores))

    lines.extend(
        [
            "## 重点技术解读",
            "",
            synthesis["technical"],
            "",
            "## 风险与趋势判断",
            "",
            synthesis["risk"],
            "",
            "## 后续学习/开发建议",
            "",
            synthesis["advice"],
            "",
            "## 附录：信息来源",
            "",
        ]
    )
    for analyzed in all_items:
        item = analyzed.raw_item
        url = item.url or "无链接"
        lines.append(f"- {item.id} | {item.source} | {item.title} | {url}")
    lines.append("")
    return "\n".join(lines)
