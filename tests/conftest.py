import asyncio
import json
from pathlib import Path

import httpx
import pytest
from mcp import Client

from exiryab_mcp import http
from exiryab_mcp.server import mcp

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


async def live_call(client, name: str, args: dict) -> dict:
    """Call a tool against the real site, about one request per second, and fail on tool errors."""
    await asyncio.sleep(1)
    result = await client.call_tool(name, args)
    assert not result.is_error, result.content[0].text
    return result.structured_content


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def fresh_http_client(monkeypatch):
    """The shared httpx client is bound to one event loop; each test gets a new one, aimed at production."""
    monkeypatch.delenv("EXIRYAB_MCP_BASE_URL", raising=False)
    http.set_transport(None)
    yield
    http.set_transport(None)


@pytest.fixture
def api():
    """Route table for a fake API keyed by URL path: api["/path"] = JSON body, (status, JSON body),
    or a callable(request) -> httpx.Response.

    Unknown paths return 404. Every request is appended to api.calls so tests can assert on what was sent.
    """

    class Routes(dict):
        calls: list[httpx.Request]

    routes = Routes()
    routes.calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        routes.calls.append(request)
        target = routes.get(request.url.path)
        if target is None:
            return httpx.Response(404, text="<html>Not found</html>", headers={"content-type": "text/html"})
        if callable(target):
            return target(request)
        if isinstance(target, tuple):
            return httpx.Response(target[0], json=target[1])
        return httpx.Response(200, json=target)

    http.set_transport(httpx.MockTransport(handler))
    return routes


@pytest.fixture
async def client():
    async with Client(mcp, raise_exceptions=True) as c:
        yield c
