"""HTTP client with retry logic."""

import httpx


def get_client() -> httpx.Client:
    transport = httpx.HTTPTransport(retries=3)
    return httpx.Client(transport=transport)
