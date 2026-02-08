"""Hacker News API: fetch and select stories."""

import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import httpx

from hndigest.config import HN_API, JOB_WORDS, log


def _parse_hits(hits: list[dict]) -> list[dict]:
    """Parse API hits into story dicts."""
    return [
        {
            "id": int(h["objectID"]),
            "title": h.get("title", ""),
            "url": h.get("url", ""),
            "points": h.get("points", 0) or 0,
            "comments": h.get("num_comments", 0) or 0,
        }
        for h in hits
    ]


def fetch_stories(
    session: httpx.Client, days: int, min_points: int, tag: str = "story",
) -> list[dict]:
    """Fetch stories from last N days, filtered by tag."""
    since = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())
    stories = []

    for page in range(5):
        try:
            r = session.get(HN_API, params={
                "tags": tag,
                "numericFilters": f"created_at_i>{since},points>={min_points}",
                "hitsPerPage": 100,
                "page": page,
            }, timeout=30)
            r.raise_for_status()
            hits = r.json().get("hits", [])
            if not hits:
                break
            stories.extend(_parse_hits(hits))
            time.sleep(0.2)
        except Exception as e:
            log.warning(f"Fetch error: {e}")
            break

    return stories


def select_stories(stories: list[dict], limit: int) -> list[dict]:
    """Select top stories, filtering jobs and limiting per domain."""
    filtered = []
    for s in stories:
        title_lower = s["title"].lower()
        if any(w in title_lower for w in JOB_WORDS):
            continue
        if not s["url"] and len(s["title"]) < 20:
            continue
        s["score"] = s["points"] + s["comments"] * 2
        s["domain"] = urlparse(s["url"]).netloc.replace("www.", "") if s["url"] else ""
        filtered.append(s)

    filtered.sort(key=lambda x: x["score"], reverse=True)

    # Limit 3 per domain
    domain_count: dict[str, int] = {}
    result = []
    for s in filtered:
        d = s["domain"]
        if domain_count.get(d, 0) < 3:
            result.append(s)
            domain_count[d] = domain_count.get(d, 0) + 1
        if len(result) >= limit:
            break

    return result
