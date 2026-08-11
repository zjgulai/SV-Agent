from httpx import ASGITransport, AsyncClient

from app.main import create_app


async def test_liveness_reports_service_identity() -> None:
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "reverse-engineer-mode-api"}
