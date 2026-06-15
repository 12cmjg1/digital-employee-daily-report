from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from agents.ai_agent import run_ai_agent
from agents.industry_agent import run_industry_agent
from agents.robotics_agent import run_robotics_agent
from core.config_loader import load_config
from core.llm_client import call_llm_with_fallback
from core.storage import save_json, save_text
from main import run_daily_report
from skills.classify_skill import classify_items
from skills.collect_skill import collect_items
from skills.report_skill import render_agent_section


APP_PASSWORD = os.getenv("APP_PASSWORD", "fengyuwuzu")

CONFIG_OPTIONS = {
    "演示模式": "config.yaml",
    "真实数据": "config.real.yaml",
}

CLAW_WORKSPACES = {
    "ai_claw": {
        "title": "AI 技术 Claw",
        "owner": "刘雨菲",
        "employee": "AI 技术员工",
        "focus": "大模型、Agent、多模态、开源 AI 项目",
        "agents": [
            "情报采集 Agent",
            "技术摘要 Agent",
            "价值评分 Agent",
            "报告生成 Agent",
        ],
    },
    "robotics_claw": {
        "title": "机器人与具身智能 Claw",
        "owner": "胡尊昊 组长",
        "employee": "机器人与具身智能员工",
        "focus": "ROS2、SLAM、导航、机器人操作、具身智能",
        "agents": [
            "机器人情报采集 Agent",
            "工程可行性 Agent",
            "风险分析 Agent",
            "报告生成 Agent",
        ],
    },
    "industry_claw": {
        "title": "产业与产品 Claw",
        "owner": "刘子轩",
        "employee": "产业与产品员工",
        "focus": "机器人公司、AI 产品、商业化场景、投融资动态",
        "agents": [
            "产业情报采集 Agent",
            "商业价值 Agent",
            "风险判断 Agent",
            "报告生成 Agent",
        ],
    },
}

REPORTS = {
    "总控日报": "reports/daily_report.md",
    "AI 技术 Claw 日报": "reports/ai_claw_daily_report.md",
    "机器人 Claw 日报": "reports/robotics_claw_daily_report.md",
    "产业产品 Claw 日报": "reports/industry_claw_daily_report.md",
    "汇总周报": "reports/weekly_report.md",
}

CLAW_CATEGORY = {
    "ai_claw": "ai",
    "robotics_claw": "robotics",
    "industry_claw": "industry",
}

CLAW_REPORT_PATH = {
    "ai_claw": "reports/ai_claw_daily_report.md",
    "robotics_claw": "reports/robotics_claw_daily_report.md",
    "industry_claw": "reports/industry_claw_daily_report.md",
}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _read_json(path: str, default: Any) -> Any:
    file_path = Path(path)
    if not file_path.exists():
        return default
    return json.loads(file_path.read_text(encoding="utf-8"))


def _write_json(path: str, value: Any) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_text(path: str, fallback: str = "尚未生成。") -> str:
    file_path = Path(path)
    if not file_path.exists():
        return fallback
    return file_path.read_text(encoding="utf-8")


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _archive_report_path(path: str, report_date: str) -> Path:
    return Path("reports/archive") / report_date / Path(path).name


def _report_path_for_date(path: str, report_date: str) -> Path:
    archived = _archive_report_path(path, report_date)
    if archived.exists():
        return archived
    if report_date == _today():
        return Path(path)
    return archived


def _available_report_dates() -> list[str]:
    dates: set[str] = set()
    archive_root = Path("reports/archive")
    if archive_root.exists():
        for child in archive_root.iterdir():
            if child.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", child.name):
                dates.add(child.name)
    if any(Path(path).exists() for path in REPORTS.values()):
        dates.add(_today())
    return sorted(dates, reverse=True) or [_today()]


def _save_today_archive_copy(path: str, content: str) -> None:
    archive_path = _archive_report_path(path, _today())
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path.write_text(content, encoding="utf-8")


def _raw_items() -> list[dict[str, Any]]:
    data = _read_json("data/raw_items.json", [])
    if isinstance(data, dict):
        items = data.get("items", [])
    else:
        items = data
    return items if isinstance(items, list) else []


def _item_matches_claw(item: dict[str, Any], claw_id: str) -> bool:
    category = CLAW_CATEGORY[claw_id]
    if item.get("category") == category:
        return True
    text = " ".join(
        str(item.get(key, "")) for key in ("title", "summary", "content", "source")
    ).lower()
    tags = " ".join(str(tag) for tag in item.get("tags", [])).lower()
    combined = f"{text} {tags}"
    if category == "ai":
        return any(word in combined for word in ["ai", "agent", "model", "llm", "multimodal"])
    if category == "robotics":
        return any(word in combined for word in ["robot", "ros", "slam", "navigation", "humanoid"])
    return any(
        word in combined
        for word in [
            "startup",
            "product",
            "company",
            "market",
            "funding",
            "warehouse",
            "commercialization",
            "deployment",
            "partnership",
            "customer",
            "manufacturing",
            "investment",
        ]
    )


CLAW_AGENT_RUNNERS = {
    "ai_claw": run_ai_agent,
    "robotics_claw": run_robotics_agent,
    "industry_claw": run_industry_agent,
}

CLAW_REPORT_HEADINGS = {
    "ai_claw": "AI 技术动态",
    "robotics_claw": "机器人与具身智能动态",
    "industry_claw": "产业与产品动态",
}

ACTION_KEYWORDS = (
    "搜集",
    "搜索",
    "采集",
    "查找",
    "最新",
    "真实数据",
    "整理",
    "总结",
    "汇报",
    "日报",
    "周报",
    "生成",
    "分析",
    "调用",
    "执行",
    "agent",
    "report",
    "search",
    "collect",
    "summarize",
)


QUERY_PREFIX_WORDS = (
    "搜索",
    "搜集",
    "采集",
    "查找",
    "查询",
    "检索",
    "整理",
    "总结",
    "分析",
    "生成",
    "最新",
    "资料",
    "信息",
    "日报",
    "周报",
    "一下",
    "相关",
    "关于",
)


def _should_run_agent(user_text: str) -> bool:
    lowered = user_text.lower()
    return any(keyword in lowered for keyword in ACTION_KEYWORDS)


def _extract_search_query(user_text: str) -> str:
    text = user_text.strip()
    if not text:
        return ""
    quoted = re.findall(r"[\"“”']([^\"“”']{2,80})[\"“”']", text)
    if quoted:
        return quoted[0].strip()

    cleaned = text
    for word in QUERY_PREFIX_WORDS:
        cleaned = cleaned.replace(word, " ")
    cleaned = re.sub(r"[，。！？、；：,.!?;:()\[\]【】]", " ", cleaned)
    tokens = [token.strip() for token in cleaned.split() if token.strip()]
    if tokens:
        return " ".join(tokens[:6])

    cjk_names = re.findall(r"[\u4e00-\u9fff]{2,8}", text)
    return cjk_names[0] if cjk_names else text[:80]


def _format_agent_evidence(agent_report: Any) -> str:
    rows: list[str] = []
    for index, analyzed in enumerate(agent_report.analyzed_items[:6], start=1):
        item = analyzed.raw_item
        rows.append(
            "\n".join(
                [
                    f"[{index}] 标题：{item.title}",
                    f"来源：{item.source}",
                    f"链接：{item.url or '无链接'}",
                    f"摘要：{analyzed.short_summary}",
                    f"价值判断：{analyzed.value_analysis}",
                    f"风险提醒：{analyzed.risk_analysis}",
                    f"推荐等级：{analyzed.score.recommendation}",
                ]
            )
        )
    return "\n\n".join(rows) if rows else "本轮 Agent 没有拿到可分析条目。"


def _format_agent_evidence_dict(agent_report: dict[str, Any]) -> str:
    rows: list[str] = []
    for index, analyzed in enumerate(agent_report.get("analyzed_items", [])[:6], start=1):
        item = analyzed.get("raw_item", {})
        score = analyzed.get("score", {})
        rows.append(
            "\n".join(
                [
                    f"[{index}] 标题：{item.get('title', '无标题')}",
                    f"来源：{item.get('source', '未知')}",
                    f"链接：{item.get('url') or '无链接'}",
                    f"摘要：{analyzed.get('short_summary', '')}",
                    f"价值判断：{analyzed.get('value_analysis', '')}",
                    f"风险提醒：{analyzed.get('risk_analysis', '')}",
                    f"推荐等级：{score.get('recommendation', '未知')}",
                ]
            )
        )
    return "\n\n".join(rows) if rows else "本轮 Agent 没有拿到可分析条目。"


def _build_direct_agent_answer(
    claw: dict[str, Any],
    artifact: dict[str, Any],
    evidence: str,
    execution_note: str,
) -> str:
    report = artifact["agent_report"]
    items = report.get("analyzed_items", [])[:5]
    lines = ["### 找到的材料"]
    if items:
        for index, analyzed in enumerate(items, start=1):
            raw = analyzed.get("raw_item", {})
            title = raw.get("title", "无标题")
            url = raw.get("url") or "无链接"
            summary = analyzed.get("short_summary") or raw.get("summary", "")
            lines.append(f"- [{index}] [{title}]({url})：{summary}")
    else:
        lines.append("- 本轮没有找到可用材料。")

    lines.extend(["", "### 简要解析"])
    summary = report.get("executive_summary") or "本轮没有形成有效摘要。"
    lines.append(summary)
    findings = report.get("key_findings", [])[:2]
    lines.extend(f"- {finding}" for finding in findings)

    lines.extend(["", "### 不足"])
    if artifact["evidence_count"] == 0:
        lines.append("- 没有有效材料，不能形成可靠结论。")
    elif artifact["evidence_count"] < 3:
        lines.append("- 材料数量偏少，适合做初步线索，不适合直接当完整日报。")
    else:
        lines.append("- 结果仍依赖公开搜索，可能遗漏官方发布、论文和开发者博客中的细节。")

    lines.extend(
        [
            "",
            "### 使用的 Agent",
            f"- 情报采集 Agent、{claw['title']}、报告生成 Agent。结果已保存到 `{artifact['report_path']}`。",
        ]
    )
    return "\n".join(lines)


def _remember_claw_artifact(claw_id: str, artifact: dict[str, Any]) -> None:
    path = f"data/{claw_id}_artifacts.json"
    artifacts = _read_json(path, [])
    if not isinstance(artifacts, list):
        artifacts = []
    artifacts.insert(0, artifact)
    _write_json(path, artifacts[:30])


def _target_report_for_text(claw_id: str, user_text: str) -> tuple[str, str] | None:
    text = user_text.lower()
    if not any(word in user_text for word in ("修改", "改进", "更新", "保存", "写入", "生成", "整理")):
        return None
    if "周报" in user_text:
        return "汇总周报", "reports/weekly_report.md"
    if "总控" in user_text or "大日报" in user_text or "总日报" in user_text:
        return "总控日报", "reports/daily_report.md"
    if "日报" in user_text or "report" in text:
        return CLAW_WORKSPACES[claw_id]["title"], CLAW_REPORT_PATH[claw_id]
    return None


def _save_report_revision(claw_id: str, user_text: str, content: str) -> str | None:
    target = _target_report_for_text(claw_id, user_text)
    if target is None:
        return None
    label, path = target
    old_content = _read_text(path, "")
    revision_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
    revision_path = f"reports/versions/{Path(path).stem}_{revision_id}.md"
    if old_content:
        save_text(revision_path, old_content)
    save_text(path, content)
    _save_today_archive_copy(path, content)
    history = _read_json("data/report_revisions.json", [])
    if not isinstance(history, list):
        history = []
    history.insert(
        0,
        {
            "id": revision_id,
            "created_at": _now(),
            "claw_id": claw_id,
            "target": label,
            "path": path,
            "backup_path": revision_path if old_content else None,
            "user_prompt": user_text,
        },
    )
    _write_json("data/report_revisions.json", history[:80])
    return f"\n\n---\n已保存为：`{path}`。旧版本备份在：`{revision_path}`。"


def _run_claw_pipeline(claw_id: str, config_path: str, user_text: str) -> dict[str, Any]:
    config = load_config(config_path)
    search_query = _extract_search_query(user_text) if _should_run_agent(user_text) else ""
    raw_items = collect_items(config, query=search_query)
    grouped = classify_items(raw_items, config)
    category = CLAW_CATEGORY[claw_id]
    max_n = config.get("runtime", {}).get("max_items_per_agent", 5)
    runner = CLAW_AGENT_RUNNERS[claw_id]
    selected_items = grouped.get(category, [])[:max_n]
    if search_query and not selected_items:
        selected_items = raw_items[:max_n]
    agent_report = runner(selected_items, config)
    heading = CLAW_REPORT_HEADINGS[claw_id]
    report_body = render_agent_section(
        agent_report,
        heading,
        config.get("report", {}).get("include_scores", True),
    )
    report_markdown = "\n".join(
        [
            f"# {CLAW_WORKSPACES[claw_id]['title']} 交互式日报",
            "",
            f"生成时间：{_now()}",
            f"用户任务：{user_text}",
            f"搜索关键词：{search_query or '未指定，使用默认数据源'}",
            f"采集配置：{config_path}",
            f"采集条目数：{len(raw_items)}",
            f"本 Claw 分析条目数：{len(agent_report.analyzed_items)}",
            "",
            report_body,
        ]
    )
    report_path = CLAW_REPORT_PATH[claw_id]
    save_text(report_path, report_markdown)
    artifact = {
        "id": f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}",
        "created_at": _now(),
        "claw_id": claw_id,
        "config_path": config_path,
        "user_prompt": user_text,
        "search_query": search_query,
        "raw_item_count": len(raw_items),
        "evidence_count": len(agent_report.analyzed_items),
        "report_path": report_path,
        "agent_report": agent_report.model_dump(),
    }
    save_json(f"data/{claw_id}_latest_agent_result.json", artifact)
    _remember_claw_artifact(claw_id, artifact)
    return artifact


def _build_claw_agent_response(
    claw_id: str,
    conversation: dict[str, Any],
    user_text: str,
    config_path: str,
) -> str:
    claw = CLAW_WORKSPACES[claw_id]
    action_executed = False
    artifact: dict[str, Any] | None = None
    execution_note = "本轮没有触发采集流程，只基于已有日报和聊天上下文回答。"

    if _should_run_agent(user_text):
        try:
            artifact = _run_claw_pipeline(claw_id, config_path, user_text)
            action_executed = True
            execution_note = (
                f"已执行真实流程：采集 {artifact['raw_item_count']} 条，"
                f"{claw['title']} 分析 {artifact['evidence_count']} 条，"
                f"结果保存到 {artifact['report_path']}。"
            )
        except Exception as exc:
            return "\n".join(
                [
                    "### 重点结论",
                    "- 本轮没有成功调用真实 Agent 流程。",
                    f"- 失败位置在采集或员工分析阶段：{exc}",
                    "- 因为没有拿到可靠的新证据，我不会继续编造结果。",
                    "",
                    "### 可以怎么处理",
                    "- 如果只是课堂演示，切到演示配置后再试一次。",
                    "- 如果要真实搜索，检查服务器网络、RSS/arXiv/GitHub 数据源和 API 配置。",
                ]
            )

    if artifact:
        evidence = _format_agent_evidence_dict(artifact["agent_report"])
    else:
        evidence = _evidence_context(claw_id)

    agents = "\n".join(f"- {agent}" for agent in claw["agents"])
    history = "\n".join(
        f"{item['role']}: {item['content']}" for item in conversation.get("messages", [])[-10:]
    )
    prompt = f"""
你是 {claw['title']} 的 OpenClaw 风格工作区，需要和使用者持续对话，并且根据真实执行结果回答。

本轮执行状态：
{execution_note}

项目主题：每日 AI 与机器人技术情报数字员工系统
负责人：{claw['owner']}
负责员工：{claw['employee']}
关注方向：{claw['focus']}

可调用 Agent：
{agents}

对话上下文：
{history}

本轮证据材料：
{evidence}

用户最新任务：
{user_text}

回答要求：
请严格按下面四段输出，不要使用“重点结论”标题：

### 找到的材料
- 先列出本轮找到的材料，每条用 1 句话概括，带证据编号和链接。
- 如果材料很少，直接说少，不要扩写。

### 简要解析
- 解释这些材料说明了什么。
- 只写和用户问题直接相关的内容，不要大段评价证据质量。

### 不足
- 简短说明还缺什么，例如材料数量少、缺少官方来源、缺少横向对比。
- 不要写太多风险套话。

### 使用的 Agent
- 最后用 1 行概括本轮用了哪些 Agent。
- 不要在开头强调调用过程。

整体要求：
- 只能依据“本轮证据材料”和已有对话回答；证据不足时直接说数据不足。
- 输出要简洁，避免长篇背景说明。
- 重要判断尽量标注证据编号，例如 [1]、[2]。
"""
    if not action_executed and "当前 data/raw_items.json 中没有匹配本 Claw" in evidence:
        return "\n".join(
            [
                "### 找到的材料",
                "- 当前没有可用材料。",
                "",
                "### 简要解析",
                "没有材料时不能形成可靠总结。你可以输入更明确的搜索词，例如“搜索 VLA robot learning 2025”。",
                "",
                "### 不足",
                "- 缺少可分析的搜索结果。",
                "",
                "### 使用的 Agent",
                f"- {execution_note}",
            ]
        )
    if artifact and not os.getenv("DEEPSEEK_API_KEY", "").strip():
        response = _build_direct_agent_answer(claw, artifact, evidence, execution_note)
        return response + (_save_report_revision(claw_id, user_text, response) or "")
    response = call_llm_with_fallback(
        prompt,
        provider="deepseek",
        system_prompt="你是严谨的 OpenClaw 风格任务工作区，只能基于真实证据和执行结果回答。",
    )
    return response + (_save_report_revision(claw_id, user_text, response) or "")


def _evidence_context(claw_id: str) -> str:
    items = [item for item in _raw_items() if _item_matches_claw(item, claw_id)]
    rows: list[str] = []
    for index, item in enumerate(items[:8], start=1):
        rows.append(
            "\n".join(
                [
                    f"[{index}] 标题：{item.get('title', '无标题')}",
                    f"来源：{item.get('source', '未知')}",
                    f"链接：{item.get('url') or '无链接'}",
                    f"摘要：{item.get('summary', '')}",
                    f"标签：{', '.join(item.get('tags', [])[:6]) if isinstance(item.get('tags'), list) else ''}",
                ]
            )
        )
    report_excerpt = _read_text(CLAW_REPORT_PATH[claw_id])[:2200]
    manager_excerpt = _read_text("reports/daily_report.md")[:1600]
    if not rows:
        rows.append("当前 data/raw_items.json 中没有匹配本 Claw 的真实采集条目。")
    return f"""
可用真实采集条目：
{chr(10).join(rows)}

本 Claw 当前日报片段：
{report_excerpt}

总控日报片段：
{manager_excerpt}
"""


def _conversation_store() -> dict[str, list[dict[str, Any]]]:
    store = _read_json("data/openclaw_conversations.json", {})
    for claw_id in CLAW_WORKSPACES:
        store.setdefault(claw_id, [])
    return store


def _save_conversation_store(store: dict[str, list[dict[str, Any]]]) -> None:
    _write_json("data/openclaw_conversations.json", store)


def _rename_conversation(claw_id: str, conv_id: str, title: str) -> None:
    title = title.strip()
    if not title:
        return
    store = _conversation_store()
    for conversation in store[claw_id]:
        if conversation["id"] == conv_id:
            conversation["title"] = title[:60]
            conversation["updated_at"] = _now()
            break
    _save_conversation_store(store)


def _delete_conversation(claw_id: str, conv_id: str) -> str:
    store = _conversation_store()
    store[claw_id] = [item for item in store[claw_id] if item["id"] != conv_id]
    _save_conversation_store(store)
    if not store[claw_id]:
        return _new_conversation(claw_id)
    return store[claw_id][-1]["id"]


def _new_conversation(claw_id: str) -> str:
    store = _conversation_store()
    conv_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
    store[claw_id].append(
        {
            "id": conv_id,
            "title": f"新对话 {_now()}",
            "created_at": _now(),
            "updated_at": _now(),
            "messages": [],
        }
    )
    _save_conversation_store(store)
    return conv_id


def _get_conversation(claw_id: str, conv_id: str) -> dict[str, Any]:
    store = _conversation_store()
    for conversation in store[claw_id]:
        if conversation["id"] == conv_id:
            return conversation
    return store[claw_id][-1] if store[claw_id] else {"messages": []}


def _append_message(claw_id: str, conv_id: str, role: str, content: str) -> None:
    store = _conversation_store()
    for conversation in store[claw_id]:
        if conversation["id"] == conv_id:
            conversation["messages"].append(
                {"role": role, "content": content, "timestamp": _now()}
            )
            if role == "user" and conversation["title"].startswith("新对话"):
                conversation["title"] = content[:24]
            conversation["updated_at"] = _now()
            break
    _save_conversation_store(store)


def _build_claw_response(
    claw_id: str,
    conversation: dict[str, Any],
    user_text: str,
    config_path: str = "config.yaml",
) -> str:
    return _build_claw_agent_response(claw_id, conversation, user_text, config_path)

    claw = CLAW_WORKSPACES[claw_id]
    agents = "\n".join(f"- {agent}" for agent in claw["agents"])
    history = "\n".join(
        f"{item['role']}: {item['content']}" for item in conversation.get("messages", [])[-10:]
    )
    evidence = _evidence_context(claw_id)
    prompt = f"""
你是 {claw['title']}，需要像真实 OpenClaw 工作区一样和使用者持续对话。

项目主题：每日 AI 与机器人技术情报数字员工系统
负责人：{claw['owner']}
负责员工：{claw['employee']}
关注方向：{claw['focus']}

你可以调用这些内部 Agent：
{agents}

对话上下文：
{history}

本轮可用证据材料：
{evidence}

用户最新消息：
{user_text}

请完成以下要求：
1. 必须优先依据“本轮可用证据材料”和对话上下文回答。
2. 如果证据材料不足，明确说“当前数据不足”，不要编造公司、论文、数字、发布时间或链接。
3. 开头先用 2-3 条“重点结论”突出重点。
4. 说明本轮调用了哪些 Agent，以及每个 Agent 做了什么。
5. 直接产出具体成果：可以是资料总结、模块方案、日报段落、关键词表、分析指标或执行清单。
6. 关键判断后面尽量标注证据编号，例如 [1]、[2]。
7. 输出格式根据问题自然组织，不要每次都机械套同一套编号。
8. 如果需要后续确认，提出 1-2 个明确问题。
5. 不要输出 SSH、sudo、删除文件、密钥读取等危险操作。
9. 不要只说“建议”，要给出能直接使用的内容。
"""
    return call_llm_with_fallback(
        prompt,
        provider="deepseek",
        system_prompt="你是严谨的 OpenClaw 多 Agent 对话工作区，会持续根据上下文协助用户完成具体任务。",
    )


def _render_css() -> None:
    st.markdown(
        """
<style>
@keyframes gridMove { from {background-position: 0 0;} to {background-position: 40px 40px;} }
@keyframes glow { 0%,100% {box-shadow: 0 0 18px rgba(56,189,248,.18);} 50% {box-shadow: 0 0 42px rgba(34,211,238,.36);} }
@keyframes sweep { 0% {transform: translateX(-120%);} 70%,100% {transform: translateX(120%);} }

html, body, #root {
  margin: 0 !important;
  min-height: 100% !important;
  background: #020617 !important;
  overscroll-behavior: none;
}
body {
  overflow-x: hidden;
}
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
main,
.st-emotion-cache-uf99v8,
.st-emotion-cache-1y4p8pa {
  background: transparent !important;
}
[data-testid="stHeader"],
header[data-testid="stHeader"] {
  height: 0 !important;
  min-height: 0 !important;
  background: transparent !important;
  visibility: hidden;
}
[data-testid="stToolbar"],
[data-testid="stDecoration"],
#MainMenu,
footer {
  display: none !important;
}
.stApp {
  min-height: 100vh;
  background:
    radial-gradient(circle at 18% 8%, rgba(59,130,246,.32), transparent 28%),
    radial-gradient(circle at 88% 14%, rgba(45,212,191,.22), transparent 24%),
    linear-gradient(135deg, #020617, #07152f 48%, #061a3d);
  color: #e5f2ff;
}
.stApp::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  background-image:
    linear-gradient(rgba(96,165,250,.065) 1px, transparent 1px),
    linear-gradient(90deg, rgba(96,165,250,.065) 1px, transparent 1px);
  background-size: 40px 40px;
  animation: gridMove 12s linear infinite;
  mask-image: linear-gradient(to bottom, rgba(0,0,0,.82), rgba(0,0,0,.18));
}
section[data-testid="stSidebar"] { display: none !important; }
.block-container { max-width: 1240px; padding-top: 1.2rem; padding-bottom: 3rem; }
h1 {
  font-size: 2.5rem !important;
  background: linear-gradient(90deg, #e0f2fe, #67e8f9, #60a5fa);
  -webkit-background-clip: text;
  color: transparent;
}
h2, h3 { color: #dbeafe !important; }
label, .stSelectbox label, .stTextInput label, .stTextArea label,
[data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] span {
  color: #7dd3fc !important;
  font-weight: 700 !important;
}
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 14px 18px;
  margin-bottom: 18px;
  border: 1px solid rgba(125,211,252,.28);
  border-radius: 18px;
  background: rgba(2,8,23,.58);
  backdrop-filter: blur(18px);
}
.brand {
  font-weight: 800;
  letter-spacing: .03em;
  color: #e0f2fe;
}
.hero {
  position: relative;
  overflow: hidden;
  padding: 34px 34px;
  border: 1px solid rgba(103,232,249,.35);
  border-radius: 24px;
  background:
    linear-gradient(135deg, rgba(15,23,42,.86), rgba(14,52,100,.62)),
    radial-gradient(circle at right top, rgba(34,211,238,.20), transparent 34%);
  animation: glow 5s ease-in-out infinite;
}
.hero::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(120deg, transparent, rgba(255,255,255,.08), transparent);
  animation: sweep 7s ease-in-out infinite;
}
.kicker { color: #67e8f9; letter-spacing: .18em; text-transform: uppercase; font-size: .82rem; }
.hero p { max-width: 760px; color: #b9d4ef; font-size: 1.05rem; }
.glass {
  padding: 18px;
  border: 1px solid rgba(125,211,252,.28);
  border-radius: 18px;
  background: rgba(8,20,44,.66);
  backdrop-filter: blur(16px);
}
.card {
  min-height: 190px;
  padding: 18px;
  border: 1px solid rgba(103,232,249,.28);
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(13,35,76,.76), rgba(2,8,23,.64));
  transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease;
}
.card:hover { transform: translateY(-5px); border-color: rgba(103,232,249,.7); box-shadow: 0 16px 44px rgba(0,0,0,.34), 0 0 24px rgba(34,211,238,.18); }
.badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 999px;
  background: linear-gradient(90deg, #67e8f9, #60a5fa);
  color: #06142b;
  font-size: .78rem;
  font-weight: 800;
}
.metric-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin: 18px 0;
}
.metric-box {
  padding: 16px;
  border-radius: 16px;
  background: rgba(3,12,30,.62);
  border: 1px solid rgba(125,211,252,.25);
}
.metric-box b { color: #67e8f9; font-size: 1.3rem; }
div[data-testid="stRadio"] > label { display: none; }
div[role="radiogroup"] {
  justify-content: flex-end;
  gap: 8px;
}
div[role="radiogroup"] label {
  border: 1px solid rgba(125,211,252,.28);
  border-radius: 999px;
  padding: 8px 14px;
  background: rgba(2,8,23,.84);
  color: #7dd3fc !important;
}
div[role="radiogroup"] label span,
div[role="radiogroup"] label div,
div[role="radiogroup"] label p {
  color: #7dd3fc !important;
  font-weight: 800 !important;
}
div[role="radiogroup"] label:has(input:checked) {
  border-color: rgba(103,232,249,.9);
  background: linear-gradient(90deg, rgba(14,116,144,.92), rgba(30,64,175,.84));
  box-shadow: 0 0 22px rgba(34,211,238,.22);
}
div[role="radiogroup"] label:has(input:checked) span,
div[role="radiogroup"] label:has(input:checked) div,
div[role="radiogroup"] label:has(input:checked) p {
  color: #e0faff !important;
}
.stButton > button, .stDownloadButton > button {
  border: 1px solid rgba(103,232,249,.55);
  border-radius: 12px;
  color: #06142b;
  font-weight: 800;
  background: linear-gradient(90deg, #67e8f9, #60a5fa);
  transition: transform .16s ease, box-shadow .16s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover {
  transform: translateY(-2px);
  box-shadow: 0 0 28px rgba(34,211,238,.34);
}
.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
  background: rgba(2,8,23,.90) !important;
  color: #e0faff !important;
  border-radius: 12px;
  border-color: rgba(125,211,252,.45) !important;
}
.stTextInput input::placeholder,
.stTextArea textarea::placeholder {
  color: #7dd3fc !important;
  opacity: .82 !important;
}
.stSelectbox div[data-baseweb="select"] span,
.stSelectbox div[data-baseweb="select"] div,
.stSelectbox div[data-baseweb="select"] svg {
  color: #7dd3fc !important;
  fill: #7dd3fc !important;
}
div[data-baseweb="popover"] ul,
div[data-baseweb="popover"] li,
div[data-baseweb="popover"] div {
  background: #04152f !important;
  color: #e0faff !important;
}
div[data-baseweb="popover"] li:hover,
div[data-baseweb="popover"] li[aria-selected="true"] {
  background: #0e7490 !important;
  color: #f0fdff !important;
}
div[data-testid="stExpander"], div[data-testid="stJson"], div[data-testid="stAlert"] {
  border-radius: 16px;
  background: rgba(8,20,44,.64);
  border: 1px solid rgba(125,211,252,.24);
}
[data-testid="stChatMessage"] {
  border: 1px solid rgba(125,211,252,.24);
  border-radius: 18px;
  background: rgba(3,12,30,.72);
  color: #eef7ff !important;
  max-width: 860px;
  margin-left: auto;
  margin-right: auto;
}
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li,
[data-testid="stChatMessage"] span,
[data-testid="stChatMessage"] div {
  color: #eef7ff !important;
}
[data-testid="stChatMessage"] code {
  color: #7dd3fc !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
  background: linear-gradient(180deg, rgba(14,45,91,.86), rgba(5,20,45,.78));
  box-shadow: 0 0 22px rgba(34,211,238,.12);
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
  background: rgba(8,29,62,.72);
}
.stMarkdown, .stMarkdown p, .stMarkdown li {
  color: #dcecff;
}
.chat-shell {
  width: min(920px, 100%);
  margin: 0 auto;
}
[data-testid="stChatInput"],
div[data-testid="stChatInput"] {
  max-width: 860px;
  margin: 0 auto;
}
</style>
""",
        unsafe_allow_html=True,
    )


def _top_nav() -> str:
    left, right = st.columns([1.1, 1.5], vertical_alignment="center")
    with left:
        st.markdown('<div class="brand">AI × Robotics OpenClaw Console</div>', unsafe_allow_html=True)
    with right:
        return st.radio(
            "导航",
            ["项目总览", "总结汇报", "OpenClaw 接入", "项目展示"],
            horizontal=True,
            label_visibility="collapsed",
        )


def _auth_gate() -> None:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if st.session_state.authenticated:
        return

    st.markdown(
        """
<div class="hero">
  <div class="kicker">Secure Console</div>
  <h1>AI 与机器人技术情报系统</h1>
  <p>请输入小组访问密码进入控制台。</p>
</div>
""",
        unsafe_allow_html=True,
    )
    password = st.text_input("访问密码", type="password")
    if st.button("进入系统", type="primary"):
        if password == APP_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        st.error("密码不正确，请重新输入。")
    st.stop()


def _page_home() -> None:
    st.markdown(
        """
<div class="hero">
  <div class="kicker">OpenClaw Multi-Agent Intelligence Console</div>
  <h1>每日 AI 与机器人技术情报指挥舱</h1>
  <p>三个 Claw 独立工作，分别生成日报；总控员工统一汇总，形成团队日报与周报。</p>
</div>
""",
        unsafe_allow_html=True,
    )
    st.markdown(
        """
<div class="metric-row">
  <div class="metric-box"><b>3</b><br/>独立 Claw 工作区</div>
  <div class="metric-box"><b>12+</b><br/>内部协作 Agent</div>
  <div class="metric-box"><b>5</b><br/>日报与周报输出</div>
  <div class="metric-box"><b>API</b><br/>DeepSeek 对话接入</div>
</div>
""",
        unsafe_allow_html=True,
    )
    cols = st.columns(3)
    for col, claw in zip(cols, CLAW_WORKSPACES.values()):
        with col:
            st.markdown(
                f"""
<div class="card">
  <span class="badge">{claw['owner']}</span>
  <h3>{claw['title']}</h3>
  <p><b>负责员工：</b>{claw['employee']}</p>
  <p><b>关注方向：</b>{claw['focus']}</p>
</div>
""",
                unsafe_allow_html=True,
            )
    st.markdown(
        """
<div class="glass">
  <h3>系统流程</h3>
  <p>数据采集 → 信息分类 → 三个 Claw 分别分析 → 总控汇总 → 日报 / 周报展示 → OpenClaw 对话迭代方案。</p>
</div>
""",
        unsafe_allow_html=True,
    )


def _page_reports(config_path: str) -> None:
    st.markdown(
        """
<div class="hero">
  <div class="kicker">REPORT CENTER</div>
  <h1>总结汇报中心</h1>
  <p>三个 Claw 各自形成独立日报，总控员工统一合成大日报和周报。</p>
</div>
""",
        unsafe_allow_html=True,
    )
    dates = _available_report_dates()
    selected_date = st.selectbox("选择报告日期", dates, index=0)
    is_archive = selected_date != _today()

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("生成今日全套报告", type="primary", use_container_width=True, disabled=is_archive):
            with st.spinner("三个 Claw 正在生成分日报，总控员工正在汇总..."):
                run_daily_report(config_path)
            st.success("日报、分日报和周报已生成。")
    with col2:
        st.caption("每天 08:00 自动采集并生成日报；每周日 08:20 自动整理周报。")
    with col3:
        if is_archive:
            st.markdown('<div class="badge">归档报告，只读</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="badge">今日报告，可更新</div>', unsafe_allow_html=True)

    st.markdown(
        """
<div class="metric-row">
  <div class="metric-box"><b>AI</b><br/>技术 Claw 独立日报</div>
  <div class="metric-box"><b>Robot</b><br/>机器人 Claw 独立日报</div>
  <div class="metric-box"><b>Biz</b><br/>产业产品 Claw 独立日报</div>
  <div class="metric-box"><b>Weekly</b><br/>总控周报汇总</div>
</div>
""",
        unsafe_allow_html=True,
    )

    report_tabs = st.tabs(list(REPORTS))
    for tab, (label, path) in zip(report_tabs, REPORTS.items()):
        with tab:
            report_path = _report_path_for_date(path, selected_date)
            if not report_path.exists():
                st.info(f"{selected_date} 暂无 {label}。")
                continue
            content = report_path.read_text(encoding="utf-8")
            st.markdown(
                f'<div class="glass"><span class="badge">{label}</span> '
                f'<span style="color:#7dd3fc;margin-left:10px;">{selected_date}</span></div>',
                unsafe_allow_html=True,
            )
            with st.container():
                st.markdown(content)
            st.download_button(
                f"下载{label}",
                content,
                file_name=f"{selected_date}_{Path(path).name}",
                mime="text/markdown",
                use_container_width=True,
                key=f"report_{selected_date}_{path}",
            )


def _page_chat(config_path: str) -> None:
    st.markdown('<div class="glass"><h2>OpenClaw 对话工作区</h2><p>每个 Claw 有独立上下文，可连续对话、调用 Agent、保存聊天和方案版本。</p></div>', unsafe_allow_html=True)
    claw_id = st.selectbox(
        "选择 Claw",
        list(CLAW_WORKSPACES),
        format_func=lambda value: CLAW_WORKSPACES[value]["title"],
    )
    claw = CLAW_WORKSPACES[claw_id]
    store = _conversation_store()
    if not store[claw_id]:
        st.session_state[f"active_{claw_id}"] = _new_conversation(claw_id)
        store = _conversation_store()

    current_id = st.session_state.get(f"active_{claw_id}", store[claw_id][-1]["id"])
    top1, top2, top3, top4 = st.columns([2.2, 1.2, 0.8, 0.8])
    with top1:
        labels = {f"{c['title']} | {c['updated_at']}": c["id"] for c in store[claw_id]}
        selected = st.selectbox(
            "选择对话",
            list(labels),
            index=max(0, list(labels.values()).index(current_id)) if current_id in labels.values() else len(labels) - 1,
        )
        current_id = labels[selected]
        st.session_state[f"active_{claw_id}"] = current_id
    with top2:
        rename_title = st.text_input(
            "重命名当前对话",
            value=_get_conversation(claw_id, current_id).get("title", ""),
            key=f"rename_{claw_id}_{current_id}",
            label_visibility="collapsed",
        )
    with top3:
        if st.button("重命名", use_container_width=True):
            _rename_conversation(claw_id, current_id, rename_title)
            st.rerun()
    with top4:
        if st.button("新建对话", use_container_width=True):
            st.session_state[f"active_{claw_id}"] = _new_conversation(claw_id)
            st.rerun()

    delete_col, hint_col = st.columns([0.8, 3.2])
    with delete_col:
        if st.button("删除当前对话", use_container_width=True):
            st.session_state[f"active_{claw_id}"] = _delete_conversation(claw_id, current_id)
            st.rerun()
    with hint_col:
        st.caption("删除只会移除当前 Claw 的这条聊天记录，不会删除已经生成的日报文件。")

    st.markdown(
        f"""
<div class="glass">
  <span class="badge">{claw['owner']}</span>
  <h3>{claw['title']}</h3>
  <p><b>可调用 Agent：</b>{' / '.join(claw['agents'])}</p>
</div>
""",
        unsafe_allow_html=True,
    )

    conversation = _get_conversation(claw_id, current_id)
    for message in conversation.get("messages", []):
        role = "user" if message["role"] == "user" else "assistant"
        with st.chat_message(role):
            st.markdown(message["content"])

    prompt = st.chat_input("输入你的任务，例如：生成本周机器人 Claw 汇报段落，调用风险分析 Agent 和报告生成 Agent。")
    if prompt:
        _append_message(claw_id, current_id, "user", prompt)
        conversation = _get_conversation(claw_id, current_id)
        with st.spinner("OpenClaw 正在调用内部 Agent 并整理回复..."):
            answer = _build_claw_response(claw_id, conversation, prompt, config_path)
        _append_message(claw_id, current_id, "assistant", answer)
        st.rerun()


def _page_openclaw_access() -> None:
    st.markdown(
        """
<div class="glass">
  <h2>OpenClaw 正式接入</h2>
  <p>本页只展示接入方式。真正的搜索、日报生成、周报汇总和报告修改由 OpenClaw Skill 调用项目工具完成。</p>
</div>
""",
        unsafe_allow_html=True,
    )
    rows = [
        (
            "AI 技术 Claw",
            "刘雨菲",
            "ai-intelligence-daily",
            'python openclaw_tools.py search --claw ai --query "OpenAI 最新动态"\npython openclaw_tools.py daily --claw ai',
        ),
        (
            "机器人与具身智能 Claw",
            "胡尊昊 组长",
            "robotics-intelligence-daily",
            'python openclaw_tools.py search --claw robotics --query "arXiv 最新机器人科研论文"\npython openclaw_tools.py daily --claw robotics',
        ),
        (
            "产业与产品 Claw",
            "刘子轩",
            "industry-intelligence-daily",
            'python openclaw_tools.py search --claw industry --query "机器人公司 产品 商业化 动态"\npython openclaw_tools.py daily --claw industry',
        ),
        (
            "总控 Claw",
            "胡尊昊",
            "manager-report-synthesis",
            "python openclaw_tools.py daily --claw all\npython openclaw_tools.py weekly",
        ),
    ]
    cols = st.columns(2)
    for index, (title, owner, skill, commands) in enumerate(rows):
        with cols[index % 2]:
            st.markdown(
                f"""
<div class="glass">
  <span class="badge">{owner}</span>
  <h3>{title}</h3>
  <p><b>OpenClaw Skill：</b>{skill}</p>
  <p>Skill 位置：<code>openclaw_workspace/skills/{skill}/SKILL.md</code></p>
</div>
""",
                unsafe_allow_html=True,
            )
            st.code(commands, language="bash")
    st.markdown(
        """
### 使用说明

- 队友不需要 SSH 到服务器；通过 OpenClaw 对应 Claw 发送任务即可。
- OpenClaw 调用 `openclaw_tools.py` 执行真实搜索和报告生成。
- DeepSeek 只负责基于搜索材料总结，不负责替代搜索。
- 今日报告可以修改，修改前会自动备份；历史归档报告只展示。
"""
    )


def _page_showcase() -> None:
    # ── Hero ──
    st.markdown(
        """
<div class="hero">
  <div class="kicker">Project Showcase</div>
  <h1>每日 AI 与机器人技术情报数字员工系统</h1>
  <p>三个 AI 数字员工每天早上 8 点自动采集、分析、评分，生成三份分方向日报和一份总控汇总，推送钉钉群。已连续运行 11 天，公网可访问。</p>
</div>
""",
        unsafe_allow_html=True,
    )

    # ── 四指标卡片 ──
    st.markdown(
        """
<div class="metric-row">
  <div class="metric-box"><b>3 + 1</b><br/>三个 Claw 员工 + 总控</div>
  <div class="metric-box"><b>08:00</b><br/>每日自动生成 & 钉钉推送</div>
  <div class="metric-box"><b>11 天</b><br/>连续稳定运行</div>
  <div class="metric-box"><b>5 维度</b><br/>评分 + A/B/C 推荐等级</div>
</div>
""",
        unsafe_allow_html=True,
    )

    # ── 核心架构：三层 ──
    st.markdown("## 核心架构")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            """
<div class="card">
  <span class="badge">展示层</span>
  <h3>Streamlit Web UI</h3>
  <p>项目总览 · 日报中心 · OpenClaw 对话 · 项目展示</p>
</div>
""",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            """
<div class="card">
  <span class="badge">调度层</span>
  <h3>crontab + CLI 工具</h3>
  <p>每日 08:00 日报 · 周日 08:20 周报 · search/daily/weekly/revise</p>
</div>
""",
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            """
<div class="card">
  <span class="badge">核心层</span>
  <h3>3 Claw + 总控</h3>
  <p>AI 技术 · 机器人 · 产业 → 总控合并去重 → 统一日报</p>
</div>
""",
            unsafe_allow_html=True,
        )

    # ── 三张 Claw 卡片 ──
    st.markdown("## 三个 Claw 数字员工")
    cols = st.columns(3)
    cards = [
        ("刘雨菲", "AI 技术 Claw", "大模型 · Agent · 多模态 · 开源项目", "跟踪模型更新与工具链，判断技术新颖性和学习价值"),
        ("胡尊昊（组长）", "机器人技术 Claw", "ROS2 · SLAM · 导航 · 具身智能", "跟踪论文与工程实践，判断落地条件与复现价值；统筹总控与部署"),
        ("刘子轩", "产业与产品 Claw", "机器人公司 · 产品发布 · 融资", "跟踪商业动态，判断产品趋势与市场价值"),
    ]
    for col, (name, title, focus, desc) in zip(cols, cards):
        with col:
            st.markdown(
                f"""
<div class="card">
  <span class="badge">{name}</span>
  <h3>{title}</h3>
  <p><b>方向：</b>{focus}</p>
  <p>{desc}</p>
</div>
""",
                unsafe_allow_html=True,
            )

    # ── 数据流 ──
    st.markdown(
        """
<div class="glass">
  <h2>数据流</h2>
  <p style="font-size:1.1rem;text-align:center;color:#67e8f9;">
  RSS / arXiv / GitHub 多源采集 → 关键词分类 → 三 Claw 并行分析 → 五维度评分 → 总控去重汇总 → Markdown 日报 → Web 展示 + 钉钉推送 + 归档
  </p>
</div>
""",
        unsafe_allow_html=True,
    )

    # ── 三大亮点 ──
    st.markdown("## 关键亮点")
    h1, h2, h3 = st.columns(3)
    with h1:
        st.markdown(
            """
<div class="card">
  <h3>防 AI 编造</h3>
  <p>来源链接保留 + 证据编号标注 + 不足显式声明 + Prompt 约束 + Demo 标注。每条结论可逐条追溯到原始 URL。</p>
</div>
""",
            unsafe_allow_html=True,
        )
    with h2:
        st.markdown(
            """
<div class="card">
  <h3>双模式一键切换</h3>
  <p><b>Demo 模式</b>：零依赖、零成本、课堂 100% 稳定。<br/><b>真实模式</b>：RSS + arXiv + GitHub + LLM API 全链路真实调用。</p>
</div>
""",
            unsafe_allow_html=True,
        )
    with h3:
        st.markdown(
            """
<div class="card">
  <h3>钉钉每日推送</h3>
  <p>日报生成后自动推送到钉钉群，队员无需登录服务器，群内即可查看每日技术情报。</p>
</div>
""",
            unsafe_allow_html=True,
        )

    # ── 部署信息 ──
    st.markdown("## 部署状态")
    d1, d2 = st.columns(2)
    with d1:
        st.markdown(
            f"""
<div class="glass">
  <h3>服务器</h3>
  <p>阿里云轻量 · 2C2G · Ubuntu 22.04</p>
  <p>公网：<code>http://47.97.114.62:8501</code></p>
  <p>进程管理：nohup + crontab</p>
  <p>LLM：SiliconFlow API（DeepSeek 模型）</p>
</div>
""",
            unsafe_allow_html=True,
        )
    with d2:
        st.markdown(
            f"""
<div class="glass">
  <h3>运行数据</h3>
  <p>首次部署：2026-06-05</p>
  <p>今日日报：2026-06-15 08:00 已生成 ✅</p>
  <p>连续归档：11 天</p>
  <p>采集源：RSS · arXiv · GitHub</p>
</div>
""",
            unsafe_allow_html=True,
        )

    # ── 报告草稿折叠 ──
    report_draft = _read_text("EXPERIMENT_REPORT_DRAFT.md", "")
    if report_draft:
        with st.expander("查看实验报告草稿"):
            st.markdown(report_draft)


st.set_page_config(page_title="AI 与机器人技术情报系统", layout="wide")
_render_css()
_auth_gate()

page = _top_nav()
config_label = st.selectbox("运行配置", list(CONFIG_OPTIONS), label_visibility="collapsed")
config_path = CONFIG_OPTIONS[config_label]

if page == "项目总览":
    _page_home()
elif page == "总结汇报":
    _page_reports(config_path)
elif page == "OpenClaw 接入":
    _page_openclaw_access()
else:
    _page_showcase()
