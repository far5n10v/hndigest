"""Gemini-based title translation with file caching."""

import hashlib
import time

import httpx

from hndigest.config import CACHE_DIR, GEMINI_API, log


def translate_batch(
    session: httpx.Client, api_key: str, prompt_base: str, titles: list[str]
) -> list[str]:
    """Translate all titles in one batch request. Returns originals on failure."""
    if not prompt_base or not titles:
        return titles

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Check cache for all
    cached = {}
    uncached_idx = []
    for i, title in enumerate(titles):
        cache_key = hashlib.md5(f"{prompt_base[:20]}|{title}".encode()).hexdigest()
        cache_file = CACHE_DIR / f"{cache_key}.txt"
        if cache_file.exists():
            cached[i] = cache_file.read_text(encoding="utf-8").strip()
        else:
            uncached_idx.append(i)

    if not uncached_idx:
        return [cached.get(i, titles[i]) for i in range(len(titles))]

    # Build batch prompt
    uncached_titles = [titles[i] for i in uncached_idx]
    numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(uncached_titles))

    batch_prompt = f"""{prompt_base}

Quyidagi sarlavhalarni tarjima qil. Har bir tarjimani yangi qatordan yoz, raqamlari bilan:

{numbered}

Faqat tarjimalarni qaytar, raqamlari bilan (1. tarjima, 2. tarjima, ...)"""

    for attempt in range(3):
        try:
            r = session.post(
                f"{GEMINI_API}?key={api_key}",
                json={
                    "contents": [{"parts": [{"text": batch_prompt}]}],
                    "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2000},
                },
                timeout=60,
            )
            r.raise_for_status()
            result = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

            # Parse numbered results
            translations = {}
            for line in result.split("\n"):
                line = line.strip()
                if line and line[0].isdigit():
                    parts = line.split(".", 1)
                    if len(parts) == 2:
                        num = int(parts[0].strip()) - 1
                        trans = parts[1].strip().strip("\"'")
                        if 0 <= num < len(uncached_titles):
                            translations[num] = trans

            # Cache results
            for local_idx, trans in translations.items():
                orig_idx = uncached_idx[local_idx]
                cache_key = hashlib.md5(
                    f"{prompt_base[:20]}|{titles[orig_idx]}".encode()
                ).hexdigest()
                cache_file = CACHE_DIR / f"{cache_key}.txt"
                cache_file.write_text(trans, encoding="utf-8")
                cached[orig_idx] = trans

            break
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                wait = (attempt + 1) * 10
                log.warning(f"Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                log.warning(f"Batch translation failed: {e}")
                break
        except Exception as e:
            log.warning(f"Batch translation failed: {e}")
            break

    return [cached.get(i, titles[i]) for i in range(len(titles))]


