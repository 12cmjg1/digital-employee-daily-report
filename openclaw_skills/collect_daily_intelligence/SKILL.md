---
name: collect_daily_intelligence
description: Collect daily AI, robotics, and industry intelligence from configured sources.
---

# collect_daily_intelligence

## Purpose

Collect daily technical intelligence based on user-defined keywords and configured data sources.

## Input

- keywords: list of keywords
- sources: rss, arxiv, github, demo
- max_items: maximum number of items

## Output

A JSON list of raw intelligence items. Each item contains id, title, url, source, published_at, summary, category, and tags.

## Procedure

1. Read keywords from config.
2. Collect information from enabled sources.
3. Remove duplicated items by URL and title.
4. Return structured JSON.

## Safety Rules

- Do not execute unknown remote code.
- Prefer RSS, public APIs, or manually provided links.
- Keep collected content within the project data directory.
