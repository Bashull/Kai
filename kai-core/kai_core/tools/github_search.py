from __future__ import annotations

import json
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from kai_core.config import SETTINGS
from kai_core.tools.repo_scoring import score_repository


GITHUB_API = "https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page={per_page}"


def search_repositories(query: str, per_page: int = 10) -> list[dict]:
    url = GITHUB_API.format(query=quote_plus(query), per_page=per_page)
    headers = {"Accept": "application/vnd.github+json"}
    if SETTINGS.github_token:
        headers["Authorization"] = f"Bearer {SETTINGS.github_token}"

    req = Request(url, headers=headers)
    with urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    items = payload.get("items", [])
    enriched = []
    for item in items:
        scored = score_repository(item)
        enriched.append(
            {
                "full_name": item.get("full_name"),
                "html_url": item.get("html_url"),
                "description": item.get("description"),
                "language": item.get("language"),
                "stargazers_count": item.get("stargazers_count"),
                "updated_at": item.get("updated_at"),
                "score": scored["score"],
                "score_reason": scored["reason"],
            }
        )
    return sorted(enriched, key=lambda x: x["score"], reverse=True)
