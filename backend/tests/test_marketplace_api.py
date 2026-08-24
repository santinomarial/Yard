from httpx import AsyncClient


async def test_health(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    metrics = await client.get("/api/v1/metrics")
    assert "http_request_duration_seconds_count" in metrics.text


async def test_categories_are_backend_driven(client: AsyncClient) -> None:
    response = await client.get("/api/v1/categories")
    assert response.status_code == 200
    assert [item["slug"] for item in response.json()] == ["electronics", "furniture"]


async def test_listing_search_excludes_unavailable_inventory(client: AsyncClient) -> None:
    response = await client.get("/api/v1/listings", params={"query": "coding"})
    payload = response.json()
    assert response.status_code == 200
    assert payload["total"] == 1
    assert payload["items"][0]["title"] == 'Dell 27" Monitor'


async def test_listing_filters_compose(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/listings",
        params={"category": "furniture", "free_only": "true", "max_price_cents": 0},
    )
    payload = response.json()
    assert response.status_code == 200
    assert payload["total"] == 1
    assert payload["items"][0]["title"] == "Walnut Desk"


async def test_subcategory_and_listing_age_filters_compose(client: AsyncClient) -> None:
    monitors = await client.get(
        "/api/v1/listings",
        params={"category": "electronics", "subcategory": "monitors", "max_age_days": 7},
    )
    old_desks = await client.get(
        "/api/v1/listings",
        params={"subcategory": "desks", "max_age_days": 7},
    )

    assert [item["title"] for item in monitors.json()["items"]] == [
        'Dell 27" Monitor'
    ]
    assert old_desks.json()["items"] == []


async def test_closest_sort_prefers_requested_zone_without_hiding_inventory(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/api/v1/listings",
        params={"sort": "closest", "pickup_zone": "Harvard Square"},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert [item["title"] for item in response.json()["items"]] == [
        "Walnut Desk",
        'Dell 27" Monitor',
    ]


async def test_natural_search_extracts_free_and_price_constraints(client: AsyncClient) -> None:
    free_response = await client.get("/api/v1/listings", params={"query": "free desk"})
    priced_response = await client.get(
        "/api/v1/listings", params={"query": "monitor under 90"}
    )

    assert [item["title"] for item in free_response.json()["items"]] == ["Walnut Desk"]
    assert [item["title"] for item in priced_response.json()["items"]] == [
        'Dell 27" Monitor'
    ]


async def test_listing_detail_uses_consistent_not_found_error(client: AsyncClient) -> None:
    response = await client.get("/api/v1/listings/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "listing_not_found",
            "message": "This listing is unavailable.",
        }
    }


async def test_invalid_query_has_safe_error_envelope(client: AsyncClient) -> None:
    response = await client.get("/api/v1/listings", params={"limit": 500})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


async def test_rejects_oversized_request_before_routing(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/development",
        content=b"x" * 1_048_577,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "request_too_large"
