from typing import Literal

from pydantic import BaseModel, Field


Category = Literal["ai", "robotics", "industry", "unknown"]
RecommendationLevel = Literal["A", "B", "C"]


class RawItem(BaseModel):
    id: str
    title: str
    url: str | None = None
    source: str = "demo"
    published_at: str | None = None
    summary: str = ""
    content: str | None = None
    category: Category = "unknown"
    tags: list[str] = Field(default_factory=list)


class Score(BaseModel):
    novelty: int = Field(ge=1, le=5)
    engineering_value: int = Field(ge=1, le=5)
    learning_value: int = Field(ge=1, le=5)
    business_value: int = Field(ge=1, le=5)
    difficulty: int = Field(ge=1, le=5)
    recommendation: RecommendationLevel


class AnalyzedItem(BaseModel):
    raw_item: RawItem
    short_summary: str
    technical_keywords: list[str] = Field(default_factory=list)
    value_analysis: str
    risk_analysis: str
    score: Score


class AgentReport(BaseModel):
    agent_name: str
    category: Category
    executive_summary: str
    analyzed_items: list[AnalyzedItem]
    key_findings: list[str] = Field(default_factory=list)
    learning_advice: list[str] = Field(default_factory=list)


class FinalReport(BaseModel):
    title: str
    date: str
    summary: str
    ai_report: AgentReport
    robotics_report: AgentReport
    industry_report: AgentReport
    recommendations: list[str]
    markdown: str
