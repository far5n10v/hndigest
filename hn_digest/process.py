"""Unified Gemini processing: categorize, rank, translate, and summarize in one call."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass

import httpx

from hn_digest.categorize import VALID_CATEGORIES, _extract_field
from hn_digest.config import CACHE_DIR, GEMINI_API, Channel, log

PROCESS_PROMPT = """You are a Hacker News editor curating a weekly digest.

For each story below, do ALL of the following:
1. Categorize into ONE category: ai, code, data, science, security, design, business, work, learn, other
   (Do NOT assign show_hn or ask_hn — those are detected separately)
2. Mark the 10 most interesting stories as "top" rank (others are "regular"):
   - Genuinely novel, important, or thought-provoking
   - NOT just highest points — a brilliant technical post beats routine drama
   - Prefer diversity: don't put 10 AI stories in top
3. {translation_instruction}
4. Write a one-sentence summary (max 20 words) in {language}

Category guide:
- ai: AI/ML, LLMs, autonomous vehicles, neural networks, robotics
- code: Programming languages, compilers, Git, Linux, open source, APIs, Docker, CLI tools
- data: Databases, SQL, Postgres, Redis, data engineering, analytics, data science
- science: Research, physics, biology, space, NASA, quantum, climate, arxiv
- security: Vulnerabilities, breaches, malware, privacy, encryption, CVEs
- design: UI/UX, typography, CSS, SVG, accessibility, Figma
- business: Startups, funding, acquisitions, regulations, legal, antitrust, policy
- work: Career, remote work, management, hiring, interviews, workplace culture
- learn: Tutorials, guides, educational content, talks, "how I built", courses
- other: Everything else

Stories:
{stories}

Return EXACTLY one line per story in this format:
1. category=ai, rank=top, title=Translated title here, summary=One sentence summary here
2. category=code, rank=regular, title=Another title, summary=Another summary

IMPORTANT: Return one line for EVERY story. Do not skip any."""

TRANSLATION_TRANSLATE = "Translate the title to {language} ({instructions})"
TRANSLATION_KEEP = "Keep the original title as-is (do not translate)"


@dataclass(frozen=True)
class StoryResult:
    category: str
    is_top: bool
    translation: str
    summary: str


def _content_hash(content: str) -> str:
    """Short hash of content for cache key differentiation."""
    return hashlib.md5(content.encode()).hexdigest()[:8]


def _cache_key_for_story(story: dict, content: str, language: str) -> str:
    """Generate cache key for a single story result."""
    content_h = _content_hash(content) if content else "empty"
    raw = f"process_v1|{story['id']}|{story['title']}|{content_h}|{language}"
    return hashlib.md5(raw.encode()).hexdigest()


def _parse_cache_line(val: str) -> StoryResult | None:
    """Parse cached value like 'category=ai,rank=top,title=...,summary=...'."""
    cat = _extract_field(val, "category")
    rank = _extract_field(val, "rank")
    title = _extract_field(val, "title")
    summary = _extract_field(val, "summary")
    if cat not in VALID_CATEGORIES:
        return None
    return StoryResult(
        category=cat,
        is_top=rank == "top",
        translation=title,
        summary=summary,
    )


def _serialize_result(r: StoryResult) -> str:
    """Serialize a StoryResult for caching."""
    rank = "top" if r.is_top else "regular"
    return f"category={r.category},rank={rank},title={r.translation},summary={r.summary}"


def _build_prompt(
    stories: list[dict],
    contents: dict[int, str],
    channel: Channel,
) -> str:
    """Build the mega-prompt for all stories."""
    if channel.prompt:
        translation_instruction = TRANSLATION_TRANSLATE.format(
            language=channel.language,
            instructions=channel.prompt,
        )
    else:
        translation_instruction = TRANSLATION_KEEP

    story_lines = []
    for i, s in enumerate(stories):
        points = s.get("points", 0)
        comments = s.get("comments", 0)
        parts = [f"{i + 1}. Title: {s['title']} ({points} pts, {comments} comments)"]
        content = contents.get(s["id"], "")
        if content:
            parts.append(f"Article: {content[:12000]}")
        story_lines.append("\n".join(parts))

    return PROCESS_PROMPT.format(
        translation_instruction=translation_instruction,
        language=channel.language,
        stories="\n---\n".join(story_lines),
    )


def _parse_result_line(line: str) -> tuple[int, StoryResult] | None:
    """Parse a single result line like '1. category=ai, rank=top, title=..., summary=...'."""
    line = line.strip()
    if not line or not line[0].isdigit():
        return None

    parts = line.split(".", 1)
    if len(parts) != 2:
        return None

    try:
        num = int(parts[0].strip()) - 1
    except ValueError:
        return None

    rest = parts[1].strip()
    rest_lower = rest.lower()

    cat = _extract_field(rest_lower, "category")
    rank = _extract_field(rest_lower, "rank")

    # Extract title and summary preserving original case
    title = _extract_field(rest, "title")
    summary = _extract_field(rest, "summary")

    if cat not in VALID_CATEGORIES:
        cat = "other"

    return num, StoryResult(
        category=cat,
        is_top=rank == "top",
        translation=title.strip("\"'"),
        summary=summary.strip("\"'"),
    )


def process_stories(
    session: httpx.Client,
    api_key: str,
    stories: list[dict],
    contents: dict[int, str],
    channel: Channel,
) -> dict[int, StoryResult]:
    """Categorize, rank, translate, and summarize all stories in one Gemini call.

    Returns {story_id: StoryResult} for each successfully processed story.
    """
    if not api_key or not stories:
        return {}

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Check cache for all stories
    cached: dict[int, StoryResult] = {}
    for s in stories:
        content = contents.get(s["id"], "")
        cache_key = _cache_key_for_story(s, content, channel.language)
        cache_file = CACHE_DIR / f"{cache_key}.txt"
        if cache_file.exists():
            val = cache_file.read_text(encoding="utf-8").strip()
            result = _parse_cache_line(val)
            if result:
                cached[s["id"]] = result

    if len(cached) == len(stories):
        log.info("All stories found in cache")
        return cached

    # Build and send mega-prompt (ranking needs full context, so send all)
    prompt = _build_prompt(stories, contents, channel)

    for attempt in range(3):
        try:
            r = session.post(
                f"{GEMINI_API}?key={api_key}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.3, "maxOutputTokens": 8000},
                },
                timeout=120,
            )
            r.raise_for_status()
            response_text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

            # Parse response
            results: dict[int, StoryResult] = {}
            for line in response_text.split("\n"):
                parsed = _parse_result_line(line)
                if parsed is None:
                    continue
                num, result = parsed
                if not (0 <= num < len(stories)):
                    continue
                story = stories[num]
                results[story["id"]] = result

                # Write cache
                content = contents.get(story["id"], "")
                cache_key = _cache_key_for_story(story, content, channel.language)
                cache_file = CACHE_DIR / f"{cache_key}.txt"
                cache_file.write_text(_serialize_result(result), encoding="utf-8")

            log.info(f"Processed {len(results)}/{len(stories)} stories via Gemini")
            return results

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                wait = (attempt + 1) * 10
                log.warning(f"Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                log.warning(f"Processing failed: {e}")
                break
        except Exception as e:
            log.warning(f"Processing failed: {e}")
            break

    log.warning("All processing attempts failed, returning cached results only")
    return cached
