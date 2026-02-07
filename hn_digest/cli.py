"""CLI entry point: argument parsing and digest generation."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import httpx

from hn_digest.config import CHANNELS, Channel, categorize_story, log
from hn_digest.content import fetch_articles
from hn_digest.formatter import format_digest
from hn_digest.hn import fetch_stories, select_stories
from hn_digest.http import get_client
from hn_digest.process import process_stories
from hn_digest.telegram import post_thread


def generate_digest(channel: Channel, session: httpx.Client) -> list[str]:
    """Generate digest for a channel. Returns list of messages."""
    log.info(f"Generating {channel.telegram}...")

    stories = fetch_stories(session, channel.days, channel.min_points)
    log.info(f"Fetched {len(stories)} stories")

    # Fetch Show HN and Ask HN separately (lower min_points to ensure results)
    show_hn = fetch_stories(session, channel.days, min_points=30, tag="show_hn")
    ask_hn = fetch_stories(session, channel.days, min_points=30, tag="ask_hn")
    log.info(f"Fetched {len(show_hn)} Show HN, {len(ask_hn)} Ask HN")

    top = select_stories(stories, channel.limit)

    # Add top Show HN and Ask HN if not already included
    existing_ids = {s["id"] for s in top}
    show_selected = select_stories(show_hn, 2)
    ask_selected = select_stories(ask_hn, 2)

    for s in show_selected + ask_selected:
        if s["id"] not in existing_ids:
            top.append(s)
            existing_ids.add(s["id"])

    log.info(f"Selected {len(top)} stories (incl. Show/Ask HN)")

    # Fetch article content
    log.info("Fetching article content...")
    article_contents = fetch_articles(session, top)

    api_key = os.environ.get("GEMINI_API_KEY", "")

    # One Gemini call: categorize, rank, translate, and summarize
    if api_key:
        log.info("Processing stories via Gemini...")
        results = process_stories(session, api_key, top, article_contents, channel)
        for s in top:
            r = results.get(s["id"])
            if r:
                if s["title"].lower().startswith("show hn"):
                    s["category"] = "show_hn"
                elif s["title"].lower().startswith("ask hn"):
                    s["category"] = "ask_hn"
                else:
                    s["category"] = r.category
                s["is_top"] = r.is_top
            else:
                s["category"] = categorize_story(s)
                s["is_top"] = False
        titles = {s["id"]: results[s["id"]].translation for s in top if s["id"] in results}
        summaries = {s["id"]: results[s["id"]].summary for s in top if s["id"] in results}
        # Fill in any missing stories with defaults
        for s in top:
            if s["id"] not in titles:
                titles[s["id"]] = s["title"]
            if s["id"] not in summaries:
                summaries[s["id"]] = ""
    else:
        for s in top:
            s["category"] = categorize_story(s)
            s["is_top"] = False
        titles = {s["id"]: s["title"] for s in top}
        summaries = {s["id"]: "" for s in top}

    return format_digest(channel, top, titles, summaries)


def main() -> int:
    parser = argparse.ArgumentParser(description="HN Digest for Telegram")
    parser.add_argument("--channel", default="hn_uz", choices=list(CHANNELS.keys()))
    parser.add_argument("--all", action="store_true", help="All channels")
    parser.add_argument("--list", action="store_true", help="List channels")
    parser.add_argument("--post", action="store_true", help="Post to Telegram")
    parser.add_argument("--out", help="Output file")
    args = parser.parse_args()

    if args.list:
        for c in CHANNELS.values():
            print(f"{c.id:12} {c.telegram:16} ({c.language})")
        return 0

    session = get_client()
    channels = list(CHANNELS.values()) if args.all else [CHANNELS[args.channel]]

    for channel in channels:
        messages = generate_digest(channel, session)

        if args.post:
            token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
            if not token:
                log.error("TELEGRAM_BOT_TOKEN not set")
                return 1
            post_thread(token, channel.telegram, messages)
        elif args.out:
            Path(args.out).write_text("\n\n---\n\n".join(messages), encoding="utf-8")
            log.info(f"Saved to {args.out}")
        else:
            for i, msg in enumerate(messages):
                if i > 0:
                    print("\n--- reply ---\n")
                print(msg)

    return 0
