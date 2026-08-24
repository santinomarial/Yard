from httpx import AsyncClient


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
