import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_request_api_completes_routine_request() -> None:
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/requests",
                json={"message": "Where is my ORD-10433 order?"},
            )

    body = response.json()
    assert response.status_code == 201
    assert body["status"] == "completed"
    assert body["customer_response"]


@pytest.mark.asyncio
async def test_request_api_pauses_and_resumes_approval() -> None:
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            start = await client.post(
                "/requests",
                json={
                    "message": (
                        "Refund my ORD-10432 today or I will take legal action."
                    )
                },
            )
            reference = start.json()["reference"]
            resume = await client.post(
                f"/requests/{reference}/decision",
                json={"approved": True, "note": "Approved for testing"},
            )

    assert start.status_code == 201
    assert start.json()["status"] == "pending_approval"
    assert resume.status_code == 200
    assert resume.json()["status"] == "completed"
    assert "approved" in resume.json()["customer_response"].lower()
