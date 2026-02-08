# HN Digest

Multi-language weekly Hacker News digest for Telegram channels.

## Quick Reference

```bash
uv run python -m hndigest --channel hn_uz   # Generate Uzbek digest
uv run python -m hndigest --channel hn_ru   # Generate Russian digest
uv run python -m hndigest --channel hn_en   # Generate English digest
uv run python -m hndigest --list            # List all channels
uv run python -m hndigest --post            # Post to Telegram
uv run python -m hndigest --out digest.html # Save to file
```

## Environment Variables

- `GEMINI_API_KEY` — Google Gemini API key (required for LLM processing)
- `TELEGRAM_BOT_TOKEN` — Telegram bot token (required for `--post`)

Both are loaded from `.env` via python-dotenv.

## Architecture

### Pipeline

```
fetch_stories → select_stories → fetch_articles → process_stories → format_digest
```

All categorization, ranking, translation, and summarization happen in **one Gemini API call** via `process.py`. This avoids rate limits and keeps the pipeline fast.

### Module Responsibilities

| Module | Purpose |
|---|---|
| `cli.py` | Entry point, orchestrates the pipeline |
| `config.py` | Channels, categories, constants, keyword fallback |
| `hn.py` | Hacker News Algolia API — fetch and select stories |
| `content.py` | Parallel article content fetching via trafilatura |
| `process.py` | Unified Gemini call — categorize, rank, translate, summarize |
| `categorize.py` | LLM batch categorization (legacy) + keyword fallback |
| `translate.py` | LLM batch title translation (legacy) |
| `formatter.py` | Telegram HTML formatting — main post + category replies |
| `telegram.py` | Post messages as threaded replies |
| `http.py` | Shared httpx client with retries |

### Caching

Two cache directories under `cache/`:
- `cache/gemini/` — LLM results (categorization, translation, summaries) keyed by content hash
- `cache/content/` — Extracted article text keyed by URL hash

Cache files are plain text. Delete `cache/` to force a fresh run.

### Channels

Defined in `config.py` as `Channel` dataclasses. Each channel specifies:
- `language` — output language (`uz`, `ru`, `en`)
- `prompt` — translation instructions (empty = no translation, e.g. English)
- `days`, `limit`, `min_points` — story selection parameters

### Output Format

Telegram HTML with thread structure:
1. Main post: header + top 10 stories
2. Category replies: ai, dev, ops, data, science, security, tech, career, culture, show_hn, ask_hn

## Code Conventions

- Python 3.11+, type hints throughout
- `from __future__ import annotations` in every module
- httpx for all HTTP (sync client, no async)
- Linter: `uv run ruff check hndigest/` (line-length 100, E/F/I/W rules)
- No test framework yet — verify manually with `uv run python -m hndigest`
- Single `log` logger from `config.py` — use `log.info()` / `log.warning()`
- All text files end with a newline

### Commit Messages

- Imperative mood, short subject line (≤ 72 chars): `Add cache TTL`, `Fix translation for empty titles`
- No period at the end of the subject
- Capitalize the first word
- Body (optional) separated by a blank line — explain *why*, not *what*
