from __future__ import annotations

from datetime import datetime, timezone


def _recency_score(updated_at: str) -> float:
    try:
        updated = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    except Exception:
        return 0.2
    days = (datetime.now(timezone.utc) - updated).days
    if days <= 30:
        return 1.0
    if days <= 90:
        return 0.8
    if days <= 180:
        return 0.6
    if days <= 365:
        return 0.4
    return 0.2


def score_repository(item: dict) -> dict:
    stars = item.get("stargazers_count", 0)
    forks = item.get("forks_count", 0)
    issues = item.get("open_issues_count", 0)
    readme_signal = 1.0 if item.get("description") else 0.4
    archived_penalty = 0.0 if not item.get("archived") else -0.4

    score = (
        min(stars / 50000, 1.0) * 0.25
        + min(forks / 5000, 1.0) * 0.10
        + _recency_score(item.get("updated_at", "")) * 0.20
        + readme_signal * 0.10
        + (0.10 if not item.get("private") else 0.0)
        + (0.10 if issues < 500 else 0.03)
        + (0.15 if item.get("language") in {"Python", "Go", "TypeScript", "Rust"} else 0.08)
        + archived_penalty
    )
    score = max(0.0, min(1.0, score))
    return {"score": round(score, 4), "reason": "Scored by recency, stars, activity, docs and integration fit"}
