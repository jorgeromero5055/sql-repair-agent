import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_repairs_returns_a_list():
    response = client.get("/repairs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_unknown_repair_returns_404():
    response = client.get(f"/repairs/{uuid.uuid4()}")
    assert response.status_code == 404


def test_get_malformed_id_returns_422():
    response = client.get("/repairs/not-a-uuid")
    assert response.status_code == 422