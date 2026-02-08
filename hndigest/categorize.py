"""Gemini-based story categorization and ranking with file caching."""

import hashlib
import time

import httpx

from hndigest.config import CACHE_DIR, GEMINI_API, log

CATEGORIZE_PROMPT = """You are a Hacker News editor curating a weekly digest.

1. Categorize each story into ONE category:
   ai, dev, ops, data, science, security, tech, career, culture
   (Do NOT assign show_hn or ask_hn — those are detected separately)

2. Mark the 10 most interesting stories as "top":
   - Genuinely novel, important, or thought-provoking
   - NOT just highest points — a brilliant technical post beats routine drama
   - Prefer diversity: don't put 10 AI stories in top

Category guide:
- ai: AI/ML, LLMs, autonomous vehicles, neural networks, robotics
- dev: Programming languages, compilers, algorithms, software architecture, WebAssembly
- ops: Linux, Docker, Kubernetes, databases, serverless, sysadmin, hardware
- data: Data engineering, analytics, visualization, spreadsheets, big data
- science: Physics, space, biology, climate, mathematics, energy
- security: Vulnerabilities, breaches, malware, privacy, encryption, CVEs
- tech: Startups, VC, antitrust, Big Tech, regulations, policy
- career: Remote work, hiring, burnout, productivity, salaries
- culture: History, urbanism, philosophy, gaming, typography, design, copyright, digital rights

Stories:
{stories}

Return EXACTLY one line per story:
1. category=ai, rank=top
2. category=dev, rank=regular
..."""

VALID_CATEGORIES = {
    "ai",
    "dev",
    "ops",
    "data",
    "science",
    "security",
    "tech",
    "career",
    "culture",
}


def categorize_and_rank_batch(
    session: httpx.Client,
    api_key: str,
    stories: list[dict],
) -> dict[int, tuple[str, bool]]:
    """Categorize and rank stories via Gemini. Returns {story_id: (category, is_top)}.

    Returns empty dict on failure (caller should fall back to keyword matching).
    """
    if not api_key or not stories:
        return {}

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Check cache
    cached: dict[int, tuple[str, bool]] = {}
    uncached: list[dict] = []
    for s in stories:
        cache_key = hashlib.md5(f"cat_v1|{s['id']}|{s['title']}".encode()).hexdigest()
        cache_file = CACHE_DIR / f"{cache_key}.txt"
        if cache_file.exists():
            val = cache_file.read_text(encoding="utf-8").strip()
            cat, is_top = _parse_cache_value(val)
            if cat:
                cached[s["id"]] = (cat, is_top)
            else:
                uncached.append(s)
        else:
            uncached.append(s)

    if not uncached:
        return cached

    # Build prompt
    story_lines = []
    for i, s in enumerate(uncached):
        points = s.get("points", 0)
        comments = s.get("comments", 0)
        story_lines.append(f"{i + 1}. {s['title']} ({points} pts, {comments} comments)")

    prompt = CATEGORIZE_PROMPT.format(stories="\n".join(story_lines))

    for attempt in range(3):
        try:
            r = session.post(
                f"{GEMINI_API}?key={api_key}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.3, "maxOutputTokens": 4000},
                },
                timeout=90,
            )
            r.raise_for_status()
            result = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

            # Parse response
            for line in result.split("\n"):
                line = line.strip()
                if not line or not line[0].isdigit():
                    continue
                parts = line.split(".", 1)
                if len(parts) != 2:
                    continue
                try:
                    num = int(parts[0].strip()) - 1
                except ValueError:
                    continue
                if not (0 <= num < len(uncached)):
                    continue

                rest = parts[1].strip().lower()
                cat = _extract_field(rest, "category")
                rank = _extract_field(rest, "rank")

                if cat not in VALID_CATEGORIES:
                    cat = "culture"
                is_top = rank == "top"

                s = uncached[num]
                cached[s["id"]] = (cat, is_top)

                # Write cache
                cache_key = hashlib.md5(f"cat_v1|{s['id']}|{s['title']}".encode()).hexdigest()
                cache_file = CACHE_DIR / f"{cache_key}.txt"
                cache_val = f"category={cat},rank={'top' if is_top else 'regular'}"
                cache_file.write_text(cache_val, encoding="utf-8")

            break
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                wait = (attempt + 1) * 10
                log.warning(f"Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                log.warning(f"Categorization failed: {e}")
                break
        except Exception as e:
            log.warning(f"Categorization failed: {e}")
            break

    return cached


def _extract_field(text: str, field: str) -> str:
    """Extract value from 'field=value' in text like 'category=ai, rank=top'."""
    for part in text.split(","):
        part = part.strip()
        if part.startswith(f"{field}="):
            return part.split("=", 1)[1].strip()
    return ""


def _parse_cache_value(val: str) -> tuple[str, bool]:
    """Parse cached value like 'category=ai,rank=top'. Returns (category, is_top)."""
    cat = _extract_field(val, "category")
    rank = _extract_field(val, "rank")
    if cat not in VALID_CATEGORIES:
        return ("", False)
    return (cat, rank == "top")
