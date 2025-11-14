from unittest.mock import patch

from fastapi.testclient import TestClient

from src import server


client = TestClient(server.app)


def test_io_emit_rejects_invalid_envelope(monkeypatch):
    response = client.post("/io/emit", json={"payload": "missing required fields"})

    assert response.status_code == 400
    assert response.json()["detail"].startswith("Invalid event envelope")


def test_io_emit_forwards_valid_envelope(monkeypatch):
    valid_envelope = {
        "timestamp": "2025-11-13T00:00:00Z",
        "source": "test-client",
        "intent": "echo",
        "payload": {"message": "hi"},
    }

    called = {}

    def fake_post(host, port, path, payload, headers=None):
        called["payload"] = payload
        return True, 200, {"ok": True}

    with patch.object(server, "http_post_json", side_effect=fake_post):
        response = client.post("/io/emit", json=valid_envelope)

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert called["payload"]["payload"]["message"] == "hi"
