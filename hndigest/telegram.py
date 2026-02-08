"""Telegram message posting."""

from collections.abc import Callable

import httpx

from hndigest.config import TELEGRAM_API, TELEGRAM_EDIT_API, log


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


def edit_message(token: str, chat_id: str, message_id: int, text: str) -> bool:
    """Edit an existing Telegram message. Returns True on success."""
    try:
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        r = httpx.post(TELEGRAM_EDIT_API.format(token), json=payload, timeout=30)
        r.raise_for_status()
        log.info(f"Edited message {message_id} in {chat_id}")
        return True
    except Exception as e:
        log.warning(f"Telegram edit error: {e}")
        return False


def post_thread(
    token: str,
    chat_id: str,
    messages: list[str],
    reply_categories: list[str] | None = None,
    edit_main_callback: Callable[[str, list[str], list[int]], str] | None = None,
) -> bool:
    """Post main message + category replies as a thread.

    If reply_categories and edit_main_callback are provided, collects reply
    message IDs and calls edit_main_callback(main_text, reply_categories,
    message_ids) to get updated main text, then edits the main post.
    """
    if not messages:
        return False

    main_id = post_to_telegram(token, chat_id, messages[0])
    if main_id is None:
        return False

    reply_ids: list[int] = []
    for msg in messages[1:]:
        msg_id = post_to_telegram(token, chat_id, msg, reply_to=main_id)
        if msg_id is not None:
            reply_ids.append(msg_id)

    # Edit main post with links to category replies
    if reply_categories and edit_main_callback and len(reply_ids) == len(reply_categories):
        updated_text = edit_main_callback(messages[0], reply_categories, reply_ids)
        if updated_text != messages[0]:
            edit_message(token, chat_id, main_id, updated_text)

    return True
