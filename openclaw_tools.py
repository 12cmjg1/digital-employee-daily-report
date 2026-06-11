from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from agents.ai_agent import run_ai_agent
from agents.industry_agent import run_industry_agent
from agents.robotics_agent import run_robotics_agent
from core.config_loader import load_config
from core.llm_client import call_llm_with_fallback
from core.storage import save_json, save_text
from main import CLAW_REPORTS, _archive_report, _render_claw_daily_report, _report_date, run_daily_report, run_weekly_report
from skills.classify_skill import classify_items
from skills.collect_skill import collect_from_industry_news, collect_items, normalize_search_query


CLAW_RUNNERS = {
    "ai": run_ai_agent,
    "robotics": run_robotics_agent,
    "industry": run_industry_agent,
}

CLAW_NAMES = {
    "ai": "AI 技术 Claw",
    "robotics": "机器人与具身智能 Claw",
    "industry": "产业与产品 Claw",
}

DEFAULT_DAILY_QUERIES = {
    "ai": "AI agent large language model multimodal latest news",
    "robotics": "arXiv latest robotics research papers",
    "industry": "site:therobotreport.com OR site:robotics247.com robotics startup funding product deployment 2026",
}


def _print_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _now_for_config(config: dict) -> str:
    timezone = config.get("project", {}).get("timezone", "Asia/Shanghai")
    return datetime.now(ZoneInfo(timezone)).strftime("%Y-%m-%d %H:%M:%S %Z")


def _run_search(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    items = collect_items(config, query=args.query)
    selected = items
    if args.claw != "all":
        grouped = classify_items(items, config)
        selected = grouped.get(args.claw, []) or items
    max_results = args.limit or config.get("runtime", {}).get("max_search_results", 6)
    payload = {
        "ok": True,
        "action": "search",
        "claw": args.claw,
        "query": args.query,
        "normalized_query": normalize_search_query(args.query),
        "count": len(selected[:max_results]),
        "items": [
            {
                "title": item.title,
                "url": item.url,
                "source": item.source,
                "published_at": item.published_at,
                "summary": item.summary,
                "category": item.category,
                "tags": item.tags[:8],
            }
            for item in selected[:max_results]
        ],
    }
    _print_json(payload)
    return 0


def _run_claw_daily(args: argparse.Namespace) -> int:
    if args.claw == "all":
        markdown = run_daily_report(args.config, include_weekly=False)
        _print_json(
            {
                "ok": True,
                "action": "daily",
                "claw": "all",
                "path": "reports/daily_report.md",
                "chars": len(markdown),
            }
        )
        return 0

    config = load_config(args.config)
    if args.claw == "industry":
        raw_items = collect_from_industry_news(config)
    else:
        raw_items = collect_items(config, query=DEFAULT_DAILY_QUERIES[args.claw])
    if not raw_items:
        raw_items = collect_items(config)
    grouped = classify_items(raw_items, config)
    max_n = config.get("runtime", {}).get("max_items_per_agent", 5)
    selected_items = grouped.get(args.claw, [])[:max_n]
    if not selected_items:
        selected_items = raw_items[:max_n]
    agent_report = CLAW_RUNNERS[args.claw](selected_items, config)
    path, title, heading = CLAW_REPORTS[args.claw]
    timezone = config.get("project", {}).get("timezone", "Asia/Shanghai")
    run_id = datetime.now(ZoneInfo(timezone)).strftime("%Y%m%d-%H%M%S")
    markdown = _render_claw_daily_report(title, heading, agent_report, config, run_id)
    save_text(path, markdown)
    _archive_report(path, _report_date(config))
    save_json(
        f"data/{args.claw}_openclaw_daily_result.json",
        {
            "generated_at": _now_for_config(config),
            "claw": args.claw,
            "path": path,
            "items": [item.model_dump() for item in selected_items],
            "agent_report": agent_report.model_dump(),
        },
    )
    _print_json(
        {
            "ok": True,
            "action": "daily",
            "claw": args.claw,
            "path": path,
            "item_count": len(selected_items),
            "chars": len(markdown),
        }
    )
    return 0


def _target_report(claw: str, report: str | None) -> Path:
    if report == "weekly":
        return Path("reports/weekly_report.md")
    if report == "manager":
        return Path("reports/daily_report.md")
    if claw in CLAW_REPORTS:
        return Path(CLAW_REPORTS[claw][0])
    raise ValueError(f"unknown claw/report target: claw={claw}, report={report}")


def _backup_report(path: Path) -> str | None:
    if not path.exists():
        return None
    revision_dir = Path("reports/versions")
    revision_dir.mkdir(parents=True, exist_ok=True)
    revision_path = revision_dir / f"{path.stem}_{datetime.now().strftime('%Y%m%d%H%M%S')}.md"
    revision_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return str(revision_path)


def _run_revise(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    target = _target_report(args.claw, args.report)
    old_content = target.read_text(encoding="utf-8") if target.exists() else ""
    backup_path = _backup_report(target)
    if args.content:
        new_content = args.content
    else:
        prompt = f"""
请根据用户要求修改下面这份 Markdown 报告。

要求：
- 保留事实来源和链接。
- 不要编造新材料。
- 输出完整 Markdown，不要解释过程。
- 语言更精简，重点更突出。

用户要求：
{args.instruction}

原报告：
{old_content[:12000]}
"""
        provider = config.get("runtime", {}).get("llm_provider", "mock")
        new_content = call_llm_with_fallback(
            prompt,
            provider=provider,
            system_prompt="你是严谨的报告编辑助手，只能基于原报告内容修改。",
        )
    save_text(target, new_content)
    _archive_report(str(target), _report_date(config))
    save_json(
        "data/openclaw_revision_latest.json",
        {
            "updated_at": _now_for_config(config),
            "target": str(target),
            "backup_path": backup_path,
            "instruction": args.instruction,
        },
    )
    _print_json(
        {
            "ok": True,
            "action": "revise",
            "target": str(target),
            "backup_path": backup_path,
            "chars": len(new_content),
        }
    )
    return 0


def _run_weekly(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    markdown = run_weekly_report(_report_date(config))
    _print_json(
        {
            "ok": True,
            "action": "weekly",
            "path": "reports/weekly_report.md",
            "chars": len(markdown),
        }
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Lightweight command tools for official OpenClaw Skills."
    )
    parser.add_argument("--config", default="config.real.yaml")
    subparsers = parser.add_subparsers(dest="command", required=True)

    search_parser = subparsers.add_parser("search", help="Search real intelligence material.")
    search_parser.add_argument("--claw", choices=["ai", "robotics", "industry", "all"], default="all")
    search_parser.add_argument("--query", required=True)
    search_parser.add_argument("--limit", type=int, default=0)
    search_parser.set_defaults(func=_run_search)

    daily_parser = subparsers.add_parser("daily", help="Generate one Claw daily report.")
    daily_parser.add_argument("--claw", choices=["ai", "robotics", "industry", "all"], required=True)
    daily_parser.set_defaults(func=_run_claw_daily)

    weekly_parser = subparsers.add_parser("weekly", help="Generate manager weekly report.")
    weekly_parser.set_defaults(func=_run_weekly)

    revise_parser = subparsers.add_parser("revise", help="Revise a current report with backup.")
    revise_parser.add_argument("--claw", choices=["ai", "robotics", "industry"], default="robotics")
    revise_parser.add_argument("--report", choices=["claw", "manager", "weekly"], default="claw")
    revise_parser.add_argument("--instruction", required=True)
    revise_parser.add_argument("--content", default="")
    revise_parser.set_defaults(func=_run_revise)
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except Exception as exc:
        _print_json({"ok": False, "error": str(exc), "command": args.command})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
