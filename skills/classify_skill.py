from __future__ import annotations

from collections import defaultdict

from core.schemas import RawItem


SUPPORTED_CATEGORIES = ("ai", "robotics", "industry", "unknown")
INDUSTRY_HINTS = (
    "acquisition",
    "application",
    "business",
    "commercialization",
    "customer",
    "deployment",
    "factory",
    "funding",
    "ipo",
    "launch",
    "partnership",
    "startup",
    "company",
    "product",
    "platform",
    "market",
    "investment",
    "data center",
    "research center",
    "warehouse",
    "manufacturing",
    "commercial",
    "conference",
    "revenue",
    "supply chain",
)

INDUSTRY_DOMAIN_HINTS = (
    "ai product",
    "artificial intelligence",
    "automation",
    "autonomous",
    "data center",
    "factory",
    "humanoid",
    "industrial",
    "inspection",
    "manufacturing",
    "robot",
    "robotics",
    "warehouse",
)


def classify_items(items: list[RawItem], config: dict) -> dict[str, list[RawItem]]:
    """Classify items into ai, robotics, industry, and unknown."""
    grouped: dict[str, list[RawItem]] = {category: [] for category in SUPPORTED_CATEGORIES}
    keywords = config.get("keywords", {})

    for item in items:
        if item.category in ("ai", "robotics", "industry"):
            grouped[item.category].append(item)
            continue

        text = " ".join([item.title, item.summary, item.content or "", " ".join(item.tags)]).lower()
        scores: dict[str, int] = defaultdict(int)
        for category in ("ai", "robotics", "industry"):
            for keyword in keywords.get(category, []):
                if keyword.lower() in text:
                    scores[category] += 1

        best_category = max(scores, key=scores.get) if scores else "unknown"
        if scores and scores[best_category] > 0:
            if best_category == "industry" and not any(
                hint in text for hint in INDUSTRY_DOMAIN_HINTS
            ):
                grouped["unknown"].append(item)
                continue
            item.category = best_category  # type: ignore[assignment]
            grouped[best_category].append(item)
        elif any(hint in text for hint in INDUSTRY_HINTS) and any(
            hint in text for hint in INDUSTRY_DOMAIN_HINTS
        ):
            item.category = "industry"
            grouped["industry"].append(item)
        else:
            grouped["unknown"].append(item)

    return grouped
