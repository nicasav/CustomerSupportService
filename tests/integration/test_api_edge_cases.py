import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def client():
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    )


@pytest.mark.asyncio
async def test_unknown_reference_returns_not_found(client: AsyncClient) -> None:
    async with app.router.lifespan_context(app):
        async with client:
            response = await client.post(
                "/requests/does-not-exist/decision",
                json={"approved": True},
            )

    assert response.status_code == 404
    assert response.json() == {"detail": "Unknown request reference"}


@pytest.mark.asyncio
async def test_duplicate_decision_returns_conflict(client: AsyncClient) -> None:
    async with app.router.lifespan_context(app):
        async with client:
            start = await client.post(
                "/requests",
                json={
                    "message": (
                        "Refund my ORD-10432 today or I will take legal action."
                    )
                },
            )
            reference = start.json()["reference"]
            first = await client.post(
                f"/requests/{reference}/decision",
                json={"approved": True},
            )
            second = await client.post(
                f"/requests/{reference}/decision",
                json={"approved": False},
            )

    assert first.status_code == 200
    assert first.json()["status"] == "completed"
    assert second.status_code == 409
    assert second.json() == {"detail": "Request is already resolved"}


@pytest.mark.asyncio
async def test_unknown_order_is_reported_in_step_summary(
    client: AsyncClient,
) -> None:
    async with app.router.lifespan_context(app):
        async with client:
            response = await client.post(
                "/requests",
                json={"message": "Where is my ORD-99999 order?"},
            )

    assert response.status_code == 201
    assert response.json()["status"] == "completed"
    assert "ORD-99999 was not found" in response.json()["steps"][1]["detail"]


@pytest.mark.asyncio
async def test_empty_and_oversized_messages_are_rejected(
    client: AsyncClient,
) -> None:
    async with app.router.lifespan_context(app):
        async with client:
            empty = await client.post("/requests", json={"message": ""})
            oversized = await client.post(
                "/requests",
                json={"message": "x" * 5_001},
            )

    assert empty.status_code == 422
    assert oversized.status_code == 422
