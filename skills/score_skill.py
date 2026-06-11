from __future__ import annotations

from core.schemas import RawItem, Score
from core.utils import clamp


def score_item(item: RawItem) -> Score:
    text = " ".join([item.title, item.summary, item.content or "", " ".join(item.tags)]).lower()
    novelty = 3
    engineering_value = 3
    learning_value = 3
    business_value = 3
    difficulty = 3

    if any(word in text for word in ["new", "improve", "benchmark", "foundation", "agent"]):
        novelty += 1
    if any(word in text for word in ["ros2", "slam", "navigation", "simulation", "inspection", "fine-tuning"]):
        engineering_value += 1
        learning_value += 1
    if any(word in text for word in ["startup", "product", "warehouse", "industrial", "nvidia", "business"]):
        business_value += 1
    if any(word in text for word in ["foundation model", "humanoid", "bimanual", "simulation-to-real"]):
        difficulty += 1

    total = novelty + engineering_value + learning_value + business_value
    recommendation = "A" if total >= 17 else "B" if total >= 13 else "C"
    return Score(
        novelty=clamp(novelty),
        engineering_value=clamp(engineering_value),
        learning_value=clamp(learning_value),
        business_value=clamp(business_value),
        difficulty=clamp(difficulty),
        recommendation=recommendation,
    )
