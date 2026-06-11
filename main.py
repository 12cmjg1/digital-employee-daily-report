from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from agents.ai_agent import run_ai_agent
from agents.industry_agent import run_industry_agent
from agents.manager_agent import run_manager_agent
from agents.robotics_agent import run_robotics_agent
from channels.dingtalk_channel import send_dingtalk_report
from channels.feishu_channel import send_feishu_report
from core.config_loader import load_config
from core.storage import save_json, save_text
from skills.classify_skill import classify_items
from skills.collect_skill import collect_from_industry_news, collect_items
from skills.report_skill import render_agent_section


CLAW_REPORTS = {
    "ai": ("reports/ai_claw_daily_report.md", "AI 技术 Claw 日报", "AI 技术动态"),
    "robotics": ("reports/robotics_claw_daily_report.md", "机器人与具身智能 Claw 日报", "机器人与具身智能动态"),
    "industry": ("reports/industry_claw_daily_report.md", "产业与产品 Claw 日报", "产业与产品动态"),
}

REPORT_ARCHIVE_DIR = Path("reports/archive")


def _report_date(config: dict) -> str:
    timezone = config.get("project", {}).get("timezone", "Asia/Shanghai")
    return datetime.now(ZoneInfo(timezone)).strftime("%Y-%m-%d")


def _archive_report(path: str, report_date: str) -> None:
    source = Path(path)
    if not source.exists():
        return
    archive_path = REPORT_ARCHIVE_DIR / report_date / source.name
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def _render_claw_daily_report(title: str, heading: str, agent_report, config: dict, run_id: str) -> str:
    timezone = config.get("project", {}).get("timezone", "Asia/Shanghai")
    include_scores = config.get("report", {}).get("include_scores", True)
    generated_at = datetime.now(ZoneInfo(timezone)).strftime("%Y-%m-%d %H:%M:%S %Z")
    lines = [
        f"# {title}",
        "",
        f"生成时间：{generated_at}",
        f"运行 ID：{run_id}",
        f"负责员工：{agent_report.agent_name}",
        "",
        "## 核心摘要",
        "",
        agent_report.executive_summary,
        "",
        render_agent_section(agent_report, heading, include_scores),
    ]
    return "\n".join(lines)


def run_weekly_report(report_date: str | None = None) -> str:
    report_sources = [
        ("AI 技术 Claw", "reports/ai_claw_daily_report.md"),
        ("机器人与具身智能 Claw", "reports/robotics_claw_daily_report.md"),
        ("产业与产品 Claw", "reports/industry_claw_daily_report.md"),
        ("总控日报", "reports/daily_report.md"),
    ]
    lines = [
        "# AI 与机器人技术情报周报",
        "",
        "本周报基于当前已生成的三个 Claw 日报和总控日报汇总，用于课堂展示和组内复盘。",
        "",
    ]
    for title, path in report_sources:
        report_path = Path(path)
        lines.extend([f"## {title}", ""])
        if report_path.exists():
            content = report_path.read_text(encoding="utf-8")
            excerpt = content[:2500].rstrip()
            lines.append(excerpt)
            if len(content) > len(excerpt):
                lines.append("\n> 内容较长，已截取前半部分；完整内容见对应日报文件。")
        else:
            lines.append("尚未生成。")
        lines.append("")
    weekly = "\n".join(lines)
    save_text("reports/weekly_report.md", weekly)
    if report_date:
        _archive_report("reports/weekly_report.md", report_date)
    return weekly


def run_daily_report(config_path: str = "config.yaml", include_weekly: bool = True) -> str:
    config = load_config(config_path)
    timezone = config.get("project", {}).get("timezone", "Asia/Shanghai")
    run_id = datetime.now(ZoneInfo(timezone)).strftime("%Y%m%d-%H%M%S")
    report_date = _report_date(config)
    raw_items = collect_items(config)
    grouped = classify_items(raw_items, config)
    if not grouped["industry"]:
        grouped["industry"] = collect_from_industry_news(config)
    max_n = config.get("runtime", {}).get("max_items_per_agent", 5)

    ai_report = run_ai_agent(grouped["ai"][:max_n], config)
    robotics_report = run_robotics_agent(grouped["robotics"][:max_n], config)
    industry_report = run_industry_agent(grouped["industry"][:max_n], config)

    claw_outputs = {
        "ai": ai_report,
        "robotics": robotics_report,
        "industry": industry_report,
    }
    for key, agent_report in claw_outputs.items():
        path, title, heading = CLAW_REPORTS[key]
        save_text(path, _render_claw_daily_report(title, heading, agent_report, config, run_id))
        _archive_report(path, report_date)

    markdown = run_manager_agent(ai_report, robotics_report, industry_report, config, run_id)

    save_json(
        "data/analyzed_results.json",
        {
            "run_id": run_id,
            "generated_at": datetime.now(ZoneInfo(timezone)).isoformat(),
            "ai_report": ai_report.model_dump(),
            "robotics_report": robotics_report.model_dump(),
            "industry_report": industry_report.model_dump(),
        },
    )
    output_path = config.get("report", {}).get("output_path", "reports/daily_report.md")
    save_text(output_path, markdown)
    _archive_report(output_path, report_date)
    if include_weekly:
        run_weekly_report(report_date)
    send_feishu_report(markdown, config, output_path)
    send_dingtalk_report(markdown, config, output_path)
    return markdown


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Run the digital employee daily report pipeline.")
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config file. Use config.real.yaml for real data collection.",
    )
    args = parser.parse_args()
    print(run_daily_report(args.config))
