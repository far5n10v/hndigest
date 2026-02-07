"""Telegram HTML formatting for digests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from hn_digest.config import (
    HN_ITEM,
    LABELS,
    MONTHS,
    Channel,
    categorize_story,
    category_name,
)


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def format_category_header(cat_key: str, lang: str) -> str:
    """Format category header with # prefix."""
    name = category_name(cat_key, lang)
    return f"<b># {name}</b>"


def format_digest(
    channel: Channel,
    stories: list[dict],
    titles: dict[int, str],
    summaries: dict[int, str] | None = None,
) -> list[str]:
    """Format digest as list of Telegram HTML messages.

    Returns a list where the first element is the main post (header + top 5)
    and each subsequent element is a category reply.
    """
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=channel.days)
    first = datetime.fromisoformat(channel.first_issue_date).replace(tzinfo=timezone.utc)
    issue = max(1, (now - first).days // 7 + 1)
    lang = channel.language

    months = MONTHS.get(lang, MONTHS["en"])
    start_str = f"{start.day} {months[start.month - 1]}"
    now_str = f"{now.day} {months[now.month - 1]} {now.year}"

    sums = summaries or {}

    # Top stories: use is_top flag, fallback to first 10
    top_stories = [s for s in stories if s.get("is_top")]
    if not top_stories:
        top_stories = stories[:10]
    top_stories = top_stories[:10]
    top_ids = {s["id"] for s in top_stories}

    # Group non-top stories by category
    by_category: dict[str, list[dict]] = {}
    for s in stories:
        if s["id"] in top_ids:
            continue
        cat = s.get("category") or categorize_story(s)
        by_category.setdefault(cat, []).append(s)

    # --- Main post: header + top 10 ---
    main_lines = [
        f"<b>{channel.title} #{issue}</b> | <i>{start_str} \u2014 {now_str}</i>",
        "",
        format_category_header("top", lang),
    ]
    for s in top_stories:
        main_lines.append("")
        main_lines.extend(format_story_lines(s, titles, sums, lang))

    tag = f"#digest_{issue}"

    main_lines.append("")
    main_lines.append(channel.footer)
    main_lines.append(tag)

    messages = ["\n".join(main_lines)]

    # --- Category replies (5 per category) ---
    category_order = [
        "ai",
        "code",
        "data",
        "science",
        "security",
        "design",
        "business",
        "work",
        "learn",
        "show_hn",
        "ask_hn",
        "other",
    ]

    for cat_key in category_order:
        cat_stories = by_category.get(cat_key, [])
        if not cat_stories:
            continue
        lines = [format_category_header(cat_key, lang)]
        for s in cat_stories[:5]:
            lines.append("")
            lines.extend(format_story_lines(s, titles, sums, lang))
        lines.append("")
        lines.append(tag)
        messages.append("\n".join(lines))

    return messages


def format_story_lines(
    s: dict,
    titles: dict[int, str],
    summaries: dict[int, str] | None = None,
    lang: str = "en",
) -> list[str]:
    """Format a single story: bold title, summary, italic metadata."""
    title = escape_html(titles.get(s["id"], s["title"]))
    url = s["url"]
    hn_url = HN_ITEM.format(s["id"])
    comments = s.get("comments", 0)
    points = s.get("points", 0)
    lbl_points = LABELS["points"].get(lang, "points")
    lbl_comments = LABELS["comments"].get(lang, "comments")

    cat = s.get("category", "")
    is_hn_thread = cat in ("show_hn", "ask_hn")

    # Title: Show/Ask HN link to HN item, others link to external URL
    if is_hn_thread:
        title_line = f'<b><a href="{hn_url}">{title}</a></b>'
    elif url:
        title_line = f'<b><a href="{url}">{title}</a></b>'
    else:
        title_line = f"<b>{title}</b>"

    result = [title_line]

    # No summaries for Show/Ask HN
    if not is_hn_thread:
        summary = (summaries or {}).get(s["id"], "")
        if summary:
            result.append(escape_html(summary))

    # Comments: plain text for Show/Ask HN, linked for others
    if is_hn_thread:
        meta_line = f"<i>{points}\u00a0{lbl_points} \u00b7 {comments}\u00a0{lbl_comments}</i>"
    else:
        meta_line = f'<i>{points}\u00a0{lbl_points} \u00b7 <a href="{hn_url}">{comments}\u00a0{lbl_comments}</a></i>'
    result.append(meta_line)
    return result
