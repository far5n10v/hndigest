"""HTTP client with retry logic."""

from __future__ import annotations

import httpx


def get_client() -> httpx.Client:
    transport = httpx.HTTPTransport(retries=3)
    return httpx.Client(transport=transport)
