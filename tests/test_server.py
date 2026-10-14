import json
import re
import sys
from pathlib import Path

import httpx
import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters

from exiryab_mcp import http
from exiryab_mcp.server import INSTRUCTIONS

pytestmark = pytest.mark.anyio

ROOT = Path(__file__).parent.parent


async def test_tools_are_read_only_and_documented(client):
    tools = (await client.list_tools()).tools
    assert all(t.name.startswith("ey_") and t.annotations.read_only_hint for t in tools)
    assert all(t.title and t.description for t in tools)
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert sorted(re.findall(r"^\| `(ey_\w+)` \|", readme, re.M)) == sorted(t.name for t in tools)
    assert f"All {len(tools)} tools" in readme


def test_instructions_cover_workflow_and_limits():
    for word in ("ey_search_doctors", "ey_cities", "ey_specialties", "confidence", "60 requests", "url"):
        assert word in INSTRUCTIONS


def test_source_only_reads():
    """The API is read-only; the client must never send anything but GET."""
    for path in (ROOT / "src").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"\.(post|put|patch|delete)\(|method=", text), path


def test_no_invisible_zwnj_in_code():
    for path in [*(ROOT / "src").rglob("*.py"), *(ROOT / "tests").glob("*.py")]:
        assert "\u200c" not in path.read_text(encoding="utf-8"), path


def test_versions_match():
    version = re.search(r'^version = "(.+)"', (ROOT / "pyproject.toml").read_text(encoding="utf-8"), re.M).group(1)
    server = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))
    assert version == server["version"] == server["packages"][0]["version"]
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert f"<!-- mcp-name: {server['name']} -->" in readme


async def test_retries_gateway_timeout_once(client, api):
    answers = iter([httpx.Response(504, text="<html>Gateway Timeout</html>")])
    api["/api/v1/cities"] = lambda r: next(answers, httpx.Response(200, json={"total": 0, "items": []}))
    data = (await client.call_tool("ey_cities", {})).structured_content
    assert data == {"total": 0, "cities": []}
    assert len(api.calls) == 2


async def test_second_gateway_timeout_is_an_error(client, api):
    api["/api/v1/cities"] = lambda r: httpx.Response(504, text="<html>Gateway Timeout</html>")
    result = await client.call_tool("ey_cities", {})
    assert result.is_error and "HTTP 504" in result.content[0].text and len(api.calls) == 2


async def test_missing_api_says_so(client, api):
    result = await client.call_tool("ey_cities", {})
    assert result.is_error and "HTTP 404" in result.content[0].text and "EXIRYAB_MCP_BASE_URL" in result.content[0].text


def test_proxy_env_is_the_only_proxy(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9")
    http.set_transport(None)
    client, _ = http._get_client()
    assert client.trust_env is False


def test_base_url_defaults_to_production_and_can_be_overridden(monkeypatch):
    http.set_transport(None)
    assert str(http._get_client()[0].base_url) == "https://exiryab.com"
    monkeypatch.setenv("EXIRYAB_MCP_BASE_URL", "http://localhost:5082/")
    http.set_transport(None)
    assert str(http._get_client()[0].base_url) == "http://localhost:5082"


async def test_stdio_smoke():
    """Start the real server process over stdio; the call fails validation before any network request."""
    params = StdioServerParameters(command=sys.executable, args=["-m", "exiryab_mcp.server"])
    async with Client(params) as c:
        names = {t.name for t in (await c.list_tools()).tools}
        assert names == {"ey_search_doctors", "ey_cities", "ey_specialties"}
        result = await c.call_tool("ey_search_doctors", {})
        assert result.is_error and "at least one" in result.content[0].text
