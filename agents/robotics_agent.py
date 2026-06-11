from __future__ import annotations

from agents.common import build_agent_analysis
from core.schemas import AgentReport, AnalyzedItem, RawItem
from skills.score_skill import score_item
from skills.summarize_skill import summarize_item


def run_robotics_agent(items: list[RawItem], config: dict) -> AgentReport:
    analyzed_items: list[AnalyzedItem] = []
    for item in items:
        value_analysis, risk_analysis = build_agent_analysis(item, config, "机器人与具身智能员工")
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
        "动态环境导航、双臂操作和 SLAM 鲁棒性是机器人系统从 demo 走向应用的关键点。",
        "开源包和基准数据集比单次演示更适合做课程项目复现。",
    ]
    learning_advice = [
        "优先熟悉 ROS2 节点、话题、导航栈和 SLAM 评估流程。",
        "选择一个可复现场景，比较静态与动态障碍下的导航表现。",
    ]
    return AgentReport(
        agent_name="机器人与具身智能员工",
        category="robotics",
        executive_summary=f"今日机器人员工分析了 {len(analyzed_items)} 条信息，重点关注 ROS2、导航、SLAM 和机器人操作。",
        analyzed_items=analyzed_items,
        key_findings=key_findings,
        learning_advice=learning_advice,
    )
