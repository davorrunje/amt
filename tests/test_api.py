import json

from fastapi.testclient import TestClient

from turing.api.app import create_app
from turing.core.chat import ChatSession
from turing.core.provider import ProviderError


class _RaisingProvider:
    def stream(self, system, messages, *, temperature, max_tokens):
        raise ProviderError("boom")
        yield  # pragma: no cover


def _events(text):
    return [
        json.loads(line[len("data: ") :])
        for line in text.strip().split("\n\n")
        if line.startswith("data: ")
    ]


def test_list_personas():
    client = TestClient(create_app(ChatSession(_fake(["x"]))))
    resp = client.get("/personas")
    assert resp.status_code == 200
    ids = [p["id"] for p in resp.json()]
    assert ids == ["student", "public", "colleague"]
    assert set(resp.json()[0]) == {"id", "name", "description"}


def test_chat_streams_tokens_then_done():
    client = TestClient(create_app(ChatSession(_fake(["Hi", " there"]))))
    resp = client.post(
        "/chat",
        json={"persona_id": "student", "messages": [{"role": "user", "content": "hello"}]},
    )
    assert resp.status_code == 200
    events = _events(resp.text)
    assert events == [
        {"type": "token", "text": "Hi"},
        {"type": "token", "text": " there"},
        {"type": "done"},
    ]


def test_chat_unknown_persona_returns_400():
    client = TestClient(create_app(ChatSession(_fake(["x"]))))
    resp = client.post(
        "/chat",
        json={"persona_id": "nope", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert resp.status_code == 400


def test_chat_provider_error_emits_error_event():
    client = TestClient(create_app(ChatSession(_RaisingProvider())))
    resp = client.post(
        "/chat",
        json={"persona_id": "student", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert resp.status_code == 200
    events = _events(resp.text)
    assert events == [{"type": "error", "message": "boom"}]


def test_chat_invalid_role_returns_422():
    client = TestClient(create_app(ChatSession(_fake(["x"]))))
    resp = client.post(
        "/chat",
        json={"persona_id": "student", "messages": [{"role": "system", "content": "hi"}]},
    )
    assert resp.status_code == 422


def test_create_app_without_session_builds_default():
    # Exercises the `session is None` branch; no network call is made here.
    app = create_app()
    client = TestClient(app)
    assert client.get("/personas").status_code == 200


def _fake(chunks):
    from turing.core.provider import FakeProvider

    return FakeProvider(chunks)
