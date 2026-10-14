"""Against the real API: uv run pytest -m live.

Set EXIRYAB_MCP_LIVE_BASE_URL (e.g. http://localhost:5082) to run them against a local ExirYab instead.
"""

import os

import pytest
from conftest import live_call

pytestmark = [pytest.mark.anyio, pytest.mark.live]


@pytest.fixture(autouse=True)
def live_base_url(monkeypatch):
    if value := os.environ.get("EXIRYAB_MCP_LIVE_BASE_URL"):
        monkeypatch.setenv("EXIRYAB_MCP_BASE_URL", value)


async def test_live_ranking_search(client):
    data = await live_call(client, "ey_search_doctors", {"city": "تهران", "specialty": "قلب", "alternatives": 2})
    assert data["confidence"] == "ranking"
    assert data["understood"]["specialty"] == "قلب و عروق"
    assert data["best_match"]["url"].startswith("https://exiryab.com/dr/")
    assert len(data["alternatives"]) == 2


async def test_live_name_round_trip(client):
    first = await live_call(client, "ey_search_doctors", {"city": "شیراز", "specialty": "اطفال", "alternatives": 0})
    name = first["best_match"]["name"]
    data = await live_call(client, "ey_search_doctors", {"name": name, "city": "شیراز"})
    assert data["best_match"]["name"] == name
    assert data["confidence"] in ("high", "medium")


async def test_live_lookups(client):
    cities = await live_call(client, "ey_cities", {"query": "تهران", "limit": 3})
    assert cities["cities"][0]["name"] == "تهران" and cities["cities"][0]["doctors"] > 1000
    specialties = await live_call(client, "ey_specialties", {"query": "پوست", "limit": 3})
    assert specialties["specialties"] and all(s["doctors"] > 0 for s in specialties["specialties"])
