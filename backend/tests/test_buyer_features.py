from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import AnalyticsEvent


async def verified_headers(client: AsyncClient) -> dict[str, str]:
    sign_in = await client.post("/api/v1/auth/development", json={})
    token = sign_in.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    requested = await client.post(
        "/api/v1/auth/verification/request",
        json={"email": "buyer@harvard.edu"},
        headers=headers,
    )
    await client.post(
        "/api/v1/auth/verification/confirm",
        json={"email": "buyer@harvard.edu", "code": requested.json()["development_code"]},
        headers=headers,
    )
    return headers


async def test_save_is_idempotent_and_returns_active_listing(client: AsyncClient) -> None:
    headers = await verified_headers(client)
    listing_id = (await client.get("/api/v1/listings")).json()["items"][0]["id"]
    assert (await client.put(f"/api/v1/saved/{listing_id}", headers=headers)).status_code == 204
    assert (await client.put(f"/api/v1/saved/{listing_id}", headers=headers)).status_code == 204
    saved = await client.get("/api/v1/saved", headers=headers)
    assert saved.status_code == 200
    assert [item["id"] for item in saved.json()] == [listing_id]


async def test_buying_intent_persists_explained_matches(client: AsyncClient) -> None:
    headers = await verified_headers(client)
    created = await client.post(
        "/api/v1/intents",
        json={"query": "monitor", "maximum_price_cents": 10000},
        headers=headers,
    )
    assert created.status_code == 201
    matches = await client.get(f"/api/v1/intents/{created.json()['id']}/matches", headers=headers)
    assert matches.status_code == 200
    assert matches.json()[0]["listing"]["title"] == 'Dell 27" Monitor'
    assert matches.json()[0]["score_components"]["text"] == 1.0


async def test_recommendations_are_explainable_and_analytics_are_first_party(
    client: AsyncClient, seeded_session: AsyncSession
) -> None:
    headers = await verified_headers(client)
    search = await client.get("/api/v1/listings?query=monitor")
    listing_id = search.json()["items"][0]["id"]
    await client.put(f"/api/v1/saved/{listing_id}", headers=headers)

    response = await client.get("/api/v1/recommendations", headers=headers)

    assert response.status_code == 200
    assert response.json()
    assert all(item["reasons"] for item in response.json())
    events = list((await seeded_session.scalars(select(AnalyticsEvent))).all())
    assert {event.name for event in events} >= {"search_performed", "listing_saved"}


async def test_client_analytics_rejects_unknown_events(client: AsyncClient) -> None:
    headers = await verified_headers(client)
    rejected = await client.post(
        "/api/v1/analytics/events",
        json={"name": "made_up_metric", "properties": {}},
        headers=headers,
    )
    accepted = await client.post(
        "/api/v1/analytics/events",
        json={"name": "app_opened", "properties": {"source": "ios"}},
        headers=headers,
    )

    assert rejected.status_code == 422
    assert accepted.status_code == 202
