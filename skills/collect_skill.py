from __future__ import annotations

from datetime import datetime, timezone
import base64
import html
import os
from pathlib import Path
import re
from typing import Any
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import feedparser
import requests

from core.schemas import RawItem
from core.storage import load_json, save_json


def load_demo_items(path: str = "data/demo_items.json") -> list[RawItem]:
    raw_data = load_json(path)
    return [RawItem(**item) for item in raw_data]


def deduplicate_items(items: list[RawItem]) -> list[RawItem]:
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    unique_items: list[RawItem] = []
    for item in items:
        normalized_title = item.title.strip().lower()
        normalized_url = (item.url or "").strip().lower()
        if normalized_url and normalized_url in seen_urls:
            continue
        if normalized_title in seen_titles:
            continue
        if normalized_url:
            seen_urls.add(normalized_url)
        seen_titles.add(normalized_title)
        unique_items.append(item)
    return unique_items


def _request_json(url: str, headers: dict[str, str] | None = None, timeout: int = 20) -> Any:
    response = requests.get(url, headers=headers or {}, timeout=timeout)
    response.raise_for_status()
    return response.json()


def _clean_text(text: str | None, max_length: int = 1200) -> str:
    if not text:
        return ""
    cleaned = html.unescape(text)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:max_length]


def _request_text(url: str, headers: dict[str, str] | None = None, timeout: int = 20) -> str:
    response = requests.get(url, headers=headers or {}, timeout=timeout)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding
    return response.text


def _decode_bing_url(url: str) -> str:
    parsed = urlparse(html.unescape(url))
    if "bing.com" not in parsed.netloc:
        return html.unescape(url)
    encoded = parse_qs(parsed.query).get("u", [""])[0]
    if not encoded:
        return html.unescape(url)
    if encoded.startswith("a1"):
        encoded = encoded[2:]
    encoded += "=" * (-len(encoded) % 4)
    try:
        return base64.urlsafe_b64decode(encoded).decode("utf-8", errors="replace")
    except Exception:
        return unquote(encoded)


QUERY_STOPWORDS = (
    "帮我",
    "请",
    "去",
    "找到",
    "查找",
    "搜索",
    "搜集",
    "收集",
    "整理",
    "一些",
    "一下",
    "相关",
    "关于",
    "方向",
    "前沿",
    "最新",
    "动态",
    "资料",
    "信息",
    "科研论文",
    "论文",
    "paper",
    "papers",
)

ARXIV_HINTS = ("arxiv", "论文", "paper", "papers", "research", "科研", "preprint", "预印本")
GITHUB_HINTS = ("github", "开源", "repo", "repository", "代码仓库")


def normalize_search_query(query: str) -> str:
    """Clean conversational Chinese task text into a search-friendly query."""
    normalized = query.strip()
    if not normalized:
        return ""
    normalized = re.sub(r"[，。！？、；：,.!?;:()\[\]【】\"“”'‘’]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    lower = normalized.lower()
    preserved: list[str] = []
    for token in re.findall(r"[A-Za-z][A-Za-z0-9._+-]*", normalized):
        if token.lower() not in {"paper", "papers", "research"}:
            preserved.append(token)

    cleaned = normalized
    for word in QUERY_STOPWORDS:
        cleaned = re.sub(re.escape(word), " ", cleaned, flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    cjk_terms: list[str] = []
    if any(word in normalized for word in ("机器人", "具身", "机械臂", "导航", "SLAM", "slam")):
        cjk_terms.append("机器人")
    if "大模型" in normalized or "多模态" in normalized or "agent" in lower:
        cjk_terms.append("AI")
    if "OpenAI" in normalized or "openai" in lower:
        cjk_terms.append("OpenAI")
    if "VLA" in normalized or "vla" in lower:
        cjk_terms.append("VLA")

    pieces = preserved + cjk_terms
    if pieces:
        return " ".join(dict.fromkeys(pieces))
    return cleaned or normalized


def _should_use_arxiv(query: str) -> bool:
    lower = query.lower()
    return any(hint in lower or hint in query for hint in ARXIV_HINTS)


def _should_use_github(query: str) -> bool:
    lower = query.lower()
    return any(hint in lower or hint in query for hint in GITHUB_HINTS)


def _arxiv_terms_from_query(query: str) -> list[str]:
    lower = query.lower()
    terms: list[str] = []

    def add(value: str) -> None:
        if value not in terms:
            terms.append(value)

    if any(word in query for word in ("机器人", "具身", "机械臂", "导航")) or "robot" in lower:
        add("robotics")
        add("robot learning")
        add("robot manipulation")
        add("robot navigation")
    if "slam" in lower or "SLAM" in query:
        add("SLAM")
    if "vla" in lower or "vision language action" in lower:
        add("vision language action")
        add("VLA")
    if "embodied" in lower or "具身" in query:
        add("embodied intelligence")
    if any(word in query for word in ("大模型", "多模态")) or "agent" in lower:
        add("artificial intelligence")
        add("multimodal")
        add("AI agent")
    if not terms:
        add("robotics")
    return terms[:6]


def collect_from_arxiv_query(config: dict, query: str) -> list[RawItem]:
    """Collect arXiv papers for a user query instead of sending paper requests to web search."""
    categories = config.get("sources", {}).get("arxiv", {}).get("categories", [])
    if not categories:
        categories = ["cs.RO", "cs.AI", "cs.LG"]
    per_source_limit = config.get("runtime", {}).get("max_search_results", 6)
    terms = _arxiv_terms_from_query(query)
    if any(word in query for word in ("机器人", "具身", "机械臂", "导航")) or "robot" in query.lower():
        ordered_categories = ["cs.RO"]
    else:
        ordered_categories = categories
    category_expr = " OR ".join([f"cat:{category}" for category in ordered_categories])
    # Keep the API query broad and rank locally. arXiv's API can return no results
    # for strict phrase combinations such as Chinese task text + quoted terms.
    search_query = f"({category_expr})"
    url = (
        "https://export.arxiv.org/api/query?"
        f"search_query={quote_plus(search_query)}&start=0&max_results={per_source_limit}"
        "&sortBy=submittedDate&sortOrder=descending"
    )
    try:
        parsed = feedparser.parse(_request_text(url, timeout=20))
    except Exception:
        return _collect_from_arxiv_rss(ordered_categories, config, terms)
    if not parsed.entries:
        return _collect_from_arxiv_rss(ordered_categories, config, terms)
    items: list[RawItem] = []
    for entry in parsed.entries:
        tags = [tag.get("term", "") for tag in entry.get("tags", []) if tag.get("term")]
        category = "robotics" if "cs.RO" in tags or any("robot" in tag.lower() for tag in tags) else "ai"
        title = _clean_text(entry.get("title", "Untitled arXiv paper").replace("\n", " "), 240)
        summary = _clean_text(entry.get("summary", "").replace("\n", " "), 900)
        if not title:
            continue
        items.append(
            RawItem(
                id=f"arxiv-{entry.get('id', '').rsplit('/', 1)[-1]}",
                title=title,
                url=entry.get("link"),
                source="arXiv",
                published_at=entry.get("published"),
                summary=summary,
                content=summary,
                category=category,
                tags=tags + terms,
            )
        )
    unique_items = deduplicate_items(items)
    term_lowers = [term.lower() for term in terms]
    unique_items.sort(
        key=lambda item: sum(
            1
            for term in term_lowers
            if term in f"{item.title} {item.summary} {' '.join(item.tags)}".lower()
        ),
        reverse=True,
    )
    return unique_items


def _collect_from_arxiv_rss(categories: list[str], config: dict, terms: list[str] | None = None) -> list[RawItem]:
    per_source_limit = config.get("runtime", {}).get("max_search_results", 6)
    items: list[RawItem] = []
    for category_name in categories:
        url = f"https://rss.arxiv.org/rss/{category_name}"
        try:
            parsed = feedparser.parse(_request_text(url, timeout=20))
        except Exception:
            continue
        for entry in parsed.entries[:per_source_limit]:
            title = _clean_text(entry.get("title", "Untitled arXiv paper").replace("\n", " "), 240)
            summary = _clean_text(
                entry.get("summary") or entry.get("description") or "",
                900,
            )
            link = entry.get("link")
            if not title or not link:
                continue
            item_category = "robotics" if category_name == "cs.RO" else "ai"
            items.append(
                RawItem(
                    id=f"arxiv-rss-{abs(hash((category_name, link)))}",
                    title=title,
                    url=link,
                    source=f"arXiv RSS:{category_name}",
                    published_at=entry.get("published") or entry.get("updated"),
                    summary=summary,
                    content=summary,
                    category=item_category,
                    tags=[category_name] + (terms or []),
                )
            )
    return deduplicate_items(items)[:per_source_limit]


def _build_search_queries(query: str) -> list[str]:
    original = query.strip()
    normalized = normalize_search_query(query)
    if not normalized:
        return []

    lower = f"{original} {normalized}".lower()
    ascii_terms = re.findall(r"[A-Za-z][A-Za-z0-9._-]*", normalized)
    has_cjk = bool(re.search(r"[\u4e00-\u9fff]", original))
    wants_news = any(word in original for word in ("动态", "新闻", "资讯", "进展", "发布", "更新", "最新"))
    queries: list[str] = []

    def add(value: str) -> None:
        value = re.sub(r"\s+", " ", value).strip()
        if value and value not in queries:
            queries.append(value)

    if wants_news and ascii_terms:
        add(f"{' '.join(ascii_terms)} news")
        add(f"{' '.join(ascii_terms)} latest news")
    if "openai" in lower:
        add("OpenAI news")
        add("OpenAI latest model release")
        add("OpenAI product update")
    if has_cjk and not ascii_terms and not wants_news:
        add(f'"{normalized}"')
    else:
        cleaned = normalized
        for word in ("动态", "新闻", "资讯", "进展", "最新", "发布", "更新"):
            cleaned = cleaned.replace(word, " ")
        if ascii_terms and wants_news:
            add(f"{cleaned} news")
        else:
            add(cleaned)
    add(normalized)
    return queries[:5]


def _collect_bing_rss(query: str, headers: dict[str, str], limit: int) -> list[RawItem]:
    rss_url = (
        "https://www.bing.com/search?format=rss&mkt=zh-CN&setlang=zh-Hans&cc=CN"
        f"&q={quote_plus(query)}"
    )
    rss_response = _request_text(rss_url, headers=headers)
    parsed = feedparser.parse(rss_response)
    items: list[RawItem] = []
    for entry in parsed.entries[:limit]:
        title = _clean_text(entry.get("title", ""), 240)
        link = entry.get("link")
        summary = _clean_text(entry.get("summary") or entry.get("description") or "", 600)
        if not title or not link:
            continue
        items.append(
            RawItem(
                id=f"web-{abs(hash((query, link)))}",
                title=title,
                url=link,
                source="web-search:Bing",
                published_at=entry.get("published"),
                summary=summary or f"搜索关键词：{query}",
                content=summary,
                category="unknown",
                tags=["web-search", query],
            )
        )
    return items


def collect_from_industry_news(config: dict) -> list[RawItem]:
    """Collect company, product, deployment, and funding news for the industry Claw."""
    source_config = config.get("sources", {}).get("industry_news", {})
    feed_urls = source_config.get("feeds", [])
    queries = source_config.get("queries", [])
    if not queries:
        queries = [
            "robotics startup funding product launch",
            "AI robotics product commercialization deployment",
            "humanoid robot company partnership manufacturing",
            "warehouse robot customer deployment funding",
        ]
    per_source_limit = config.get("runtime", {}).get("max_items_per_source", 5)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        )
    }

    items: list[RawItem] = []
    for feed_url in feed_urls:
        try:
            parsed = feedparser.parse(feed_url)
        except Exception:
            continue
        feed_title = parsed.feed.get("title", feed_url)
        for entry in parsed.entries[:per_source_limit]:
            item_id = entry.get("id") or entry.get("link") or entry.get("title")
            title = _clean_text(entry.get("title", "Untitled industry news"), 240)
            link = entry.get("link")
            summary = _clean_text(entry.get("summary") or entry.get("description") or "", 900)
            if not title or not link:
                continue
            candidate = RawItem(
                id=f"industry-rss-{abs(hash((feed_url, item_id)))}",
                title=title,
                url=link,
                source=f"industry-rss:{feed_title}",
                published_at=entry.get("published") or entry.get("updated"),
                summary=summary,
                content=summary,
                category="industry",
                tags=["industry", "product", "commercialization"],
            )
            if not _has_industry_signal(candidate):
                continue
            items.append(
                candidate
            )
    for query in queries:
        try:
            query_items = _collect_bing_rss(query, headers, per_source_limit)
        except Exception:
            continue
        for item in query_items:
            if _is_generic_industry_result(item):
                continue
            if not _has_industry_signal(item):
                continue
            item.category = "industry"
            item.source = f"industry-news:{item.source}"
            item.tags = ["industry", "product", "commercialization", query] + item.tags
            if not item.summary:
                item.summary = f"Industry intelligence collected with query: {query}"
            items.append(item)
    return deduplicate_items(items)


def _has_industry_signal(item: RawItem) -> bool:
    text = f"{item.title} {item.summary} {item.content or ''} {item.url or ''}".lower()
    domain_signals = (
        "robot",
        "robotics",
        "humanoid",
        "automation",
        "autonomous",
        "warehouse",
        "manufacturing",
        "factory",
        "industrial",
        "inspection",
        "deployment",
        "customer",
        "ai-powered",
        "ai robot",
    )
    business_signals = (
        "funding",
        "startup",
        "partnership",
        "product",
        "commercial",
        "acquisition",
        "launch",
        "customer",
    )
    return any(signal in text for signal in domain_signals) and any(
        signal in text for signal in business_signals
    )


def _is_generic_industry_result(item: RawItem) -> bool:
    text = f"{item.title} {item.summary} {item.url or ''}".lower()
    bad_domains = (
        "wikipedia.org",
        "britannica.com",
        "robotsguide.com",
        "dictionary",
        "baike.baidu.com",
    )
    bad_phrases = (
        "definition",
        "your guide to",
        "what is robotics",
        "robotics - wikipedia",
        "applications, & facts",
    )
    return any(domain in text for domain in bad_domains) or any(phrase in text for phrase in bad_phrases)


def _web_result_score(original_query: str, item: RawItem) -> int:
    text = f"{item.title} {item.summary} {item.url or ''}".lower()
    score = 0
    if any(word in original_query for word in ("动态", "新闻", "资讯", "进展", "发布", "更新")):
        score += 5
    for word in ("news", "latest", "release", "update", "动态", "新闻", "发布", "更新", "进展", "gpt-"):
        if word in text:
            score += 3
    for domain in ("ithome.com", "36kr.com", "news.qq.com", "openai.com/news", "openai.com/index"):
        if domain in text:
            score += 3
    for bad in ("baike.baidu.com", "apifox.com", "smapply.org", "教程", "官网入口", "国内使用方式", "github.com/openai"):
        if bad in text:
            score -= 6
    return score


def collect_from_web_search(query: str, config: dict) -> list[RawItem]:
    original_query = query.strip()
    query = normalize_search_query(query)
    if not query:
        return []

    limit = config.get("runtime", {}).get("max_search_results", 6)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        )
    }
    rss_items: list[RawItem] = []
    for search_query in _build_search_queries(original_query):
        try:
            rss_items.extend(_collect_bing_rss(search_query, headers, limit))
        except Exception:
            continue
    if rss_items:
        items = deduplicate_items(rss_items)
        items.sort(key=lambda item: _web_result_score(original_query, item), reverse=True)
        filtered = [item for item in items if _web_result_score(original_query, item) > 0]
        return (filtered or items)[:limit]

    search_url = f"https://www.bing.com/search?q={quote_plus(query)}"
    html_text = _request_text(search_url, headers=headers)
    parts = re.split(r'<li[^>]+class="[^"]*\bb_algo\b[^"]*"[^>]*>', html_text, flags=re.I)
    blocks = parts[1:]
    items: list[RawItem] = []
    for index, block in enumerate(blocks[:limit], start=1):
        link_match = re.search(r'<h2[^>]*>.*?<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block, flags=re.I | re.S)
        if not link_match:
            continue
        url = _decode_bing_url(link_match.group(1))
        title = _clean_text(link_match.group(2), 240)
        snippet_match = re.search(r'<p[^>]*>(.*?)</p>', block, flags=re.I | re.S)
        snippet = _clean_text(snippet_match.group(1), 600) if snippet_match else ""
        if not title or not url:
            continue
        items.append(
            RawItem(
                id=f"web-{abs(hash((query, url)))}",
                title=title,
                url=url,
                source="web-search:Bing",
                published_at=None,
                summary=snippet or f"搜索关键词：{query}",
                content=snippet,
                category="unknown",
                tags=["web-search", query],
            )
        )
    return deduplicate_items(items)


def collect_from_rss(config: dict) -> list[RawItem]:
    urls = config.get("sources", {}).get("rss", {}).get("urls", [])
    per_source_limit = config.get("runtime", {}).get("max_items_per_source", 5)
    feed_groups: list[list[RawItem]] = []
    for url in urls:
        parsed = feedparser.parse(url)
        feed_items: list[RawItem] = []
        for entry in parsed.entries[:per_source_limit]:
            item_id = entry.get("id") or entry.get("link") or entry.get("title")
            summary = _clean_text(entry.get("summary", ""))
            feed_items.append(
                RawItem(
                    id=f"rss-{abs(hash(item_id))}",
                    title=_clean_text(entry.get("title", "Untitled RSS item"), 200),
                    url=entry.get("link"),
                    source=f"rss:{parsed.feed.get('title', url)}",
                    published_at=entry.get("published") or entry.get("updated"),
                    summary=summary,
                    content=summary,
                    tags=[tag.get("term", "") for tag in entry.get("tags", []) if tag.get("term")],
                )
            )
        if feed_items:
            feed_groups.append(feed_items)

    items: list[RawItem] = []
    max_group_length = max((len(group) for group in feed_groups), default=0)
    for index in range(max_group_length):
        for group in feed_groups:
            if index < len(group):
                items.append(group[index])
    return items


def collect_from_arxiv(config: dict) -> list[RawItem]:
    categories = config.get("sources", {}).get("arxiv", {}).get("categories", [])
    per_source_limit = config.get("runtime", {}).get("max_items_per_source", 5)
    if not categories:
        return []

    query = "+OR+".join([f"cat:{category}" for category in categories])
    url = (
        "https://export.arxiv.org/api/query?"
        f"search_query={query}&start=0&max_results={per_source_limit}&sortBy=submittedDate&sortOrder=descending"
    )
    try:
        parsed = feedparser.parse(_request_text(url, timeout=20))
    except Exception:
        return _collect_from_arxiv_rss(categories, config)
    if not parsed.entries:
        return _collect_from_arxiv_rss(categories, config)
    items: list[RawItem] = []
    for entry in parsed.entries:
        tags = [tag.get("term", "") for tag in entry.get("tags", []) if tag.get("term")]
        category = "robotics" if "cs.RO" in tags else "ai"
        items.append(
            RawItem(
                id=f"arxiv-{entry.get('id', '').rsplit('/', 1)[-1]}",
                title=_clean_text(entry.get("title", "Untitled arXiv paper").replace("\n", " "), 200),
                url=entry.get("link"),
                source="arXiv",
                published_at=entry.get("published"),
                summary=_clean_text(entry.get("summary", "").replace("\n", " ")),
                content=_clean_text(entry.get("summary", "").replace("\n", " ")),
                category=category,
                tags=tags,
            )
        )
    return items


def collect_from_github(config: dict) -> list[RawItem]:
    query = config.get("sources", {}).get("github", {}).get("query", "")
    per_source_limit = config.get("runtime", {}).get("max_items_per_source", 5)
    if not query:
        return []

    token = os.getenv("GITHUB_TOKEN", "").strip()
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "digital-employee-daily-report",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    encoded_query = quote_plus(f"{query} stars:>50 pushed:>2025-01-01")
    url = f"https://api.github.com/search/repositories?q={encoded_query}&sort=updated&order=desc&per_page={per_source_limit}"
    data = _request_json(url, headers=headers)
    items: list[RawItem] = []
    for repo in data.get("items", []):
        name = repo.get("full_name", "unknown/repo")
        description = _clean_text(repo.get("description") or "")
        topics = repo.get("topics") or []
        text = f"{name} {description} {' '.join(topics)}".lower()
        category = "robotics" if any(word in text for word in ["robot", "ros", "slam"]) else "ai"
        items.append(
            RawItem(
                id=f"github-{repo.get('id')}",
                title=name,
                url=repo.get("html_url"),
                source="GitHub",
                published_at=repo.get("updated_at"),
                summary=description,
                content=f"Stars: {repo.get('stargazers_count', 0)}. Language: {repo.get('language')}. {description}",
                category=category,
                tags=topics[:8],
            )
        )
    return items


def collect_items(config: dict, query: str | None = None) -> list[RawItem]:
    """Collect daily intelligence items from demo data or configured real sources."""
    mode = config.get("runtime", {}).get("mode", "demo")
    max_items_total = config.get("runtime", {}).get("max_items_total", 15)
    original_query = (query or "").strip()
    search_query = normalize_search_query(original_query)

    if original_query:
        errors: list[str] = []
        route = "web-search"
        try:
            if _should_use_arxiv(original_query):
                route = "arxiv"
                items = collect_from_arxiv_query(config, search_query or original_query)
            elif _should_use_github(original_query):
                route = "github"
                config_for_query = dict(config)
                sources = dict(config.get("sources", {}))
                github = dict(sources.get("github", {}))
                github["query"] = search_query
                sources["github"] = github
                config_for_query["sources"] = sources
                items = collect_from_github(config_for_query)
            else:
                items = collect_from_web_search(search_query, config)
        except Exception as exc:
            items = []
            errors.append(f"{route}: {exc}")
        metadata = {
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "mode": mode,
            "query": original_query,
            "normalized_query": search_query,
            "route": route,
            "errors": errors,
            "count": len(items),
            "items": [item.model_dump() for item in items[:max_items_total]],
        }
        save_json("data/raw_items.json", metadata)
        return items[:max_items_total]

    if mode == "demo":
        demo_path = Path("data/demo_items.json")
        items = deduplicate_items(load_demo_items(str(demo_path)))
        items = items[:max_items_total]
        save_json("data/raw_items.json", [item.model_dump() for item in items])
        return items

    source_groups: list[list[RawItem]] = []
    errors: list[str] = []
    sources = config.get("sources", {})

    collectors = [
        ("rss", collect_from_rss),
        ("arxiv", collect_from_arxiv),
        ("github", collect_from_github),
        ("industry_news", collect_from_industry_news),
    ]
    for source_name, collector in collectors:
        if not sources.get(source_name, {}).get("enabled", False):
            continue
        try:
            collected = collector(config)
            if collected:
                source_groups.append(collected)
        except Exception as exc:
            errors.append(f"{source_name}: {exc}")

    items: list[RawItem] = []
    max_group_length = max((len(group) for group in source_groups), default=0)
    for index in range(max_group_length):
        for group in source_groups:
            if index < len(group):
                items.append(group[index])

    items = deduplicate_items(items)
    if not items and config.get("runtime", {}).get("allow_demo_fallback", True):
        items = load_demo_items("data/demo_items.json")
        for item in items:
            item.source = f"demo-fallback:{item.source}"

    if not items:
        error_text = "; ".join(errors) if errors else "no real source is enabled"
        raise RuntimeError(f"Real collection returned no items: {error_text}")

    items = items[:max_items_total]
    metadata = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "errors": errors,
        "count": len(items),
        "items": [item.model_dump() for item in items],
    }
    save_json("data/raw_items.json", metadata)
    return items
