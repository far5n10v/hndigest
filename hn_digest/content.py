"""Article content fetching with trafilatura extraction and file caching."""

from __future__ import annotations

import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx
import trafilatura

from hn_digest.config import CONTENT_CACHE_DIR, log

MAX_WORDS = 3000
FETCH_TIMEOUT = 15


def _truncate_words(text: str, max_words: int = MAX_WORDS) -> str:
    """Truncate text to max_words."""
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words])


def _cache_path(url: str):
    """Return cache file path for a URL."""
    return CONTENT_CACHE_DIR / f"{hashlib.md5(url.encode()).hexdigest()}.txt"


def _fetch_one(session: httpx.Client, url: str) -> str:
    """Fetch and extract article text from a single URL."""
    cache_file = _cache_path(url)
    if cache_file.exists():
        return cache_file.read_text(encoding="utf-8")

    text = ""
    try:
        r = session.get(url, timeout=FETCH_TIMEOUT, follow_redirects=True)
        r.raise_for_status()
        extracted = trafilatura.extract(r.text)
        if extracted:
            text = _truncate_words(extracted)
    except Exception as e:
        log.debug(f"Failed to fetch {url}: {e}")

    cache_file.write_text(text, encoding="utf-8")
    return text


def fetch_articles(
    session: httpx.Client, stories: list[dict], max_workers: int = 10
) -> dict[int, str]:
    """Fetch article content for stories in parallel.

    Returns a dict mapping story ID to extracted article text.
    Stories without URLs (Ask HN, etc.) get empty strings.
    """
    CONTENT_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    results: dict[int, str] = {}
    url_stories: list[dict] = []

    for story in stories:
        url = story.get("url", "")
        if not url:
            results[story["id"]] = ""
        else:
            url_stories.append(story)

    if not url_stories:
        return results

    log.info(f"Fetching content for {len(url_stories)} articles...")

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_story = {
            pool.submit(_fetch_one, session, s["url"]): s for s in url_stories
        }
        for future in as_completed(future_to_story):
            story = future_to_story[future]
            try:
                results[story["id"]] = future.result()
            except Exception:
                results[story["id"]] = ""

    fetched = sum(1 for v in results.values() if v)
    log.info(f"Extracted content from {fetched}/{len(url_stories)} articles")
    return results
