import pytest
from conftest import fixture

pytestmark = pytest.mark.anyio


async def test_cities(client, api):
    api["/api/v1/cities"] = fixture("cities.json")
    data = (await client.call_tool("ey_cities", {"query": "شیر", "limit": 5})).structured_content

    assert dict(api.calls[0].url.params) == {"q": "شیر", "limit": "5"}
    assert data["total"] == 8 and len(data["cities"]) == 5
    assert data["cities"][0] == {
        "name": "شیراز",
        "province": "فارس",
        "doctors": 4597,
        "url": "https://exiryab.com/شیراز/",
    }


async def test_cities_without_query_lists_the_largest(client, api):
    api["/api/v1/cities"] = fixture("cities.json")
    await client.call_tool("ey_cities", {})
    assert dict(api.calls[0].url.params) == {"limit": "20"}


async def test_specialties_name_their_parent(client, api):
    api["/api/v1/specialties"] = fixture("specialties.json")
    data = (await client.call_tool("ey_specialties", {"query": "قلب", "limit": 4})).structured_content

    assert dict(api.calls[0].url.params) == {"q": "قلب", "limit": "4"}
    assert [s["name"] for s in data["specialties"][:2]] == ["قلب و عروق", "جراح قلب"]
    assert data["specialties"][0]["parent"] is None and data["specialties"][0]["doctors"] == 2786
    assert data["specialties"][3]["parent"] == "کودکان (اطفال)"
