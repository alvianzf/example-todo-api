import os

# The tests use an in-memory SQLite database, so they need no PostgreSQL.
# This must be set before `app` is imported, because app.py reads it at import time.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest

from app import app, db


@pytest.fixture
def client():
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def test_health_does_not_need_the_database(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_health_db_checks_the_database(client):
    response = client.get("/api/health/db")
    assert response.status_code == 200
    assert response.get_json()["database"] == "ok"


def test_list_starts_empty(client):
    assert client.get("/api/todos").get_json() == []


def test_create_and_list(client):
    created = client.post("/api/todos", json={"title": "  Buy milk  "})
    assert created.status_code == 201
    body = created.get_json()
    assert body["title"] == "Buy milk"
    assert body["done"] is False

    todos = client.get("/api/todos").get_json()
    assert [t["title"] for t in todos] == ["Buy milk"]


@pytest.mark.parametrize("payload", [{}, {"title": ""}, {"title": "   "}, {"title": "x" * 201}])
def test_create_rejects_bad_titles(client, payload):
    assert client.post("/api/todos", json=payload).status_code == 400


def test_mark_done(client):
    todo_id = client.post("/api/todos", json={"title": "Write tests"}).get_json()["id"]
    response = client.patch(f"/api/todos/{todo_id}", json={"done": True})
    assert response.status_code == 200
    assert response.get_json()["done"] is True


def test_done_must_be_boolean(client):
    todo_id = client.post("/api/todos", json={"title": "Write tests"}).get_json()["id"]
    assert client.patch(f"/api/todos/{todo_id}", json={"done": "yes"}).status_code == 400


def test_delete(client):
    todo_id = client.post("/api/todos", json={"title": "Temporary"}).get_json()["id"]
    assert client.delete(f"/api/todos/{todo_id}").status_code == 204
    assert client.get("/api/todos").get_json() == []


def test_missing_todo_is_404(client):
    assert client.patch("/api/todos/999", json={"done": True}).status_code == 404
    assert client.delete("/api/todos/999").status_code == 404
