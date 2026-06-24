"""Router-level tests with mocked services."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from main import app

ACCOUNT_ID = uuid4()


def _auth_override():
    return ACCOUNT_ID


client = TestClient(app)


@pytest.fixture
def auth_client():
    from routers.chat import get_account_id_from_request as chat_auth
    from routers.tickets import get_account_id_from_request

    app.dependency_overrides[get_account_id_from_request] = _auth_override
    app.dependency_overrides[chat_auth] = _auth_override
    yield client
    app.dependency_overrides.clear()


class TestHealthRouter:
    def test_health_ok(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data


class TestTicketsRouter:
    def test_get_tickets_requires_auth(self):
        response = client.get("/tickets")
        assert response.status_code == 401

    def test_get_tickets_returns_list(self, auth_client):
        from repositories.ticket import TicketRecord

        with patch(
            "routers.tickets.ticket_service.get_tickets_for_account",
            new_callable=AsyncMock,
        ) as mock_get:
            mock_get.return_value = [
                TicketRecord(
                    ticket_number="T-001",
                    account_id=ACCOUNT_ID,
                    subject="Payment issue",
                    status="closed",
                    created_at="2026-03-19",
                    resolution="Fixed by updating billing info",
                )
            ]
            response = auth_client.get("/tickets")
            assert response.status_code == 200
            data = response.json()
            assert len(data["tickets"]) == 1
            assert data["tickets"][0]["ticket_number"] == "T-001"
            assert data["tickets"][0]["subject"] == "Payment issue"


class TestChatRouter:
    def test_chat_requires_auth(self):
        response = client.post("/chat", json={"query": "test"})
        assert response.status_code == 401

    def test_chat_validates_query(self, auth_client):
        response = auth_client.post("/chat", json={"query": ""})
        assert response.status_code == 422

    def test_chat_streams_sse(self, auth_client):
        async def mock_stream(query, account_id):
            yield 'data: {"type": "token", "content": "Hello"}\n\n'
            yield 'data: {"type": "done"}\n\n'

        with patch(
            "routers.chat.chat_service.stream_answer",
            new=mock_stream,
        ):
            response = auth_client.post("/chat", json={"query": "test"})
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]
            body = response.text
            assert "token" in body
            assert "done" in body
