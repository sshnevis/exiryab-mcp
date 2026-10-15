"""Shared async HTTP client for the ExirYab public API (https://exiryab.com/api/v1).

Every tool goes through `fetch`, which caps concurrency, retries once on connection errors, timeouts and
gateway 5xx, and turns HTTP failures into `ToolError` messages the model can act on.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any
from urllib.parse import urlsplit

import httpx
from mcp.server.mcpserver.exceptions import ToolError

from . import __version__

DEFAULT_BASE_URL = "https://exiryab.com"
HEADERS = {
    "User-Agent": f"exiryab-mcp/{__version__} (+https://github.com/sshnevis/exiryab-mcp)",
    "Accept": "application/json",
}

MAX_CONCURRENCY = 4
TIMEOUT = httpx.Timeout(20, connect=10)
RETRY_STATUS = {502, 503, 504}

_transport: httpx.AsyncBaseTransport | None = None
_client: httpx.AsyncClient | None = None
_limit: asyncio.Semaphore | None = None


class ApiError(ToolError):
    """A failed API call; `status` is the HTTP status (None for network errors)."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


def base_url() -> str:
    return (os.environ.get("EXIRYAB_MCP_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")


def set_transport(transport: httpx.AsyncBaseTransport | None) -> None:
    """Swap the transport (tests use httpx.MockTransport). Drops the current client."""
    global _transport, _client, _limit
    _transport, _client, _limit = transport, None, None


def _get_client() -> tuple[httpx.AsyncClient, asyncio.Semaphore]:
    global _client, _limit
    if _client is None:
        # Ignore system proxy settings unless the user opts in with EXIRYAB_MCP_PROXY.
        _client = httpx.AsyncClient(
            transport=_transport,
            base_url=base_url(),
            headers=HEADERS,
            timeout=TIMEOUT,
            follow_redirects=True,
            trust_env=False,
            proxy=os.environ.get("EXIRYAB_MCP_PROXY") or None,
        )
        _limit = asyncio.Semaphore(MAX_CONCURRENCY)
    assert _limit is not None
    return _client, _limit


def as_object(body: Any, host: str | None = None) -> dict[str, Any]:
    """The API bodies are JSON objects; a list or string means a broken deployment, not a tool bug."""
    if not isinstance(body, dict):
        raise ApiError(f"{host or urlsplit(base_url()).hostname} returned an unexpected response (expected a JSON object).")
    return body


async def fetch(path: str, params: dict[str, Any] | None = None) -> Any:
    """GET an API path (e.g. '/api/v1/cities') and return the parsed JSON body. None params are dropped."""
    client, limit = _get_client()
    host = urlsplit(str(client.base_url)).hostname
    query = {k: v for k, v in (params or {}).items() if v is not None}
    r = None
    for attempt in range(2):
        try:
            async with limit:
                r = await client.get(path, params=query)
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            if attempt == 0:
                await asyncio.sleep(1)
                continue
            if isinstance(e, httpx.TimeoutException):
                raise ApiError(f"{host} did not answer in time. Try again in a moment.") from e
            raise ApiError(
                f"Could not reach {host} ({type(e).__name__}). Check the internet connection, or set EXIRYAB_MCP_PROXY."
            ) from e
        except httpx.RequestError as e:
            raise ApiError(
                f"Could not reach {host} ({type(e).__name__}). Check the internet connection, or set EXIRYAB_MCP_PROXY."
            ) from e
        if r.status_code in RETRY_STATUS and attempt == 0:
            await asyncio.sleep(1)
            continue
        break
    assert r is not None

    if r.status_code >= 400:
        raise ApiError(_status_message(r, host), r.status_code)
    try:
        return r.json()
    except ValueError as e:
        raise ApiError(f"{host} returned a non-JSON response (HTTP {r.status_code}).", r.status_code) from e


def _status_message(r: httpx.Response, host: str | None) -> str:
    code = r.status_code
    detail = error_text(r)
    if code == 429:
        return f"{host} is rate limiting requests (HTTP 429): {detail} Do not retry before a minute has passed."
    if code == 404:
        return f"Not found on {host} (HTTP 404): {detail}. The API may not be deployed at EXIRYAB_MCP_BASE_URL."
    if code >= 500:
        return f"{host} had a server error (HTTP {code}): {detail}. Try again later."
    return f"{host} rejected the request (HTTP {code}): {detail}"


def error_text(r: httpx.Response) -> str:
    """The API answers errors as {"error": "..."}; anything else is summarized."""
    try:
        body = r.json()
    except ValueError:
        return "HTML error page" if "<html" in r.text[:500].lower() else r.text[:200]
    if isinstance(body, dict):
        for key in ("error", "message", "title"):
            if isinstance(body.get(key), str):
                return body[key][:300]
    return str(body)[:300]
