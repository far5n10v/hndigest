"""Telegram message posting."""

from __future__ import annotations

import httpx

from hn_digest.config import TELEGRAM_API, log


def post_to_telegram(token: str, chat_id: str, text: str, reply_to: int | None = None) -> int | None:
    """Post message to Telegram channel. Returns message_id on success."""
    try:
        payload: dict = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        if reply_to is not None:
            payload["reply_to_message_id"] = reply_to

        r = httpx.post(TELEGRAM_API.format(token), json=payload, timeout=30)
        r.raise_for_status()
        message_id = r.json()["result"]["message_id"]
        log.info(f"Posted to {chat_id} (msg {message_id})")
        return message_id
    except Exception as e:
        log.error(f"Telegram error: {e}")
        if hasattr(e, "response") and e.response is not None:
            log.error(e.response.text)
        return None


def post_thread(token: str, chat_id: str, messages: list[str]) -> bool:
    """Post main message + category replies as a thread."""
    if not messages:
        return False

    main_id = post_to_telegram(token, chat_id, messages[0])
    if main_id is None:
        return False

    for msg in messages[1:]:
        post_to_telegram(token, chat_id, msg, reply_to=main_id)

    return True
