import pytest

from turing.core.chat import ChatSession
from turing.core.provider import FakeProvider, Message


def test_stream_reply_yields_provider_chunks():
    provider = FakeProvider(["Hello", " there"])
    session = ChatSession(provider)
    out = list(session.stream_reply("student", [Message("user", "hi")]))
    assert out == ["Hello", " there"]


def test_stream_reply_composes_persona_system_prompt():
    provider = FakeProvider(["x"])
    session = ChatSession(provider)
    list(session.stream_reply("colleague", [Message("user", "hi")]))
    assert "You are Alan Turing" in provider.last_system  # type: ignore
    assert "a knowledgeable, sceptical peer" in provider.last_system  # type: ignore


def test_stream_reply_passes_params():
    provider = FakeProvider(["x"])
    session = ChatSession(provider, temperature=0.2, max_tokens=42)
    captured = {}

    original = provider.stream

    def spy(system, messages, *, temperature, max_tokens):
        captured["temperature"] = temperature
        captured["max_tokens"] = max_tokens
        return original(system, messages, temperature=temperature, max_tokens=max_tokens)

    provider.stream = spy  # type: ignore
    list(session.stream_reply("student", [Message("user", "hi")]))
    assert captured == {"temperature": 0.2, "max_tokens": 42}


def test_stream_reply_unknown_persona_raises():
    session = ChatSession(FakeProvider(["x"]))
    with pytest.raises(KeyError):
        list(session.stream_reply("nope", [Message("user", "hi")]))
