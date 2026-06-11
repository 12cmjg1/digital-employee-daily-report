---
name: score_technical_value
description: Score technical intelligence items by novelty, engineering value, learning value, business value, and difficulty.
---

# score_technical_value

## Purpose

Evaluate the importance of each technical intelligence item.

## Input

- title
- summary
- category
- tags

## Output

A score object with novelty, engineering_value, learning_value, business_value, difficulty, and recommendation A/B/C.

## Procedure

1. Check technical novelty.
2. Check engineering relevance.
3. Check learning value.
4. Check business potential.
5. Estimate implementation difficulty.
6. Produce final recommendation level.
