from types import SimpleNamespace

import pytest

from turing.core import provider as provider_module
from turing.core.provider import FakeProvider, LiteLLMProvider, Message, ProviderError


def test_fakeprovider_yields_chunks_in_order():
    provider = FakeProvider(["Hello", ", ", "world"])
    out = list(provider.stream("sys", [Message("user", "hi")], temperature=0.7, max_tokens=10))
    assert out == ["Hello", ", ", "world"]


def test_fakeprovider_records_last_call():
    provider = FakeProvider(["x"])
    msgs = [Message("user", "hi")]
    list(provider.stream("the-system-prompt", msgs, temperature=0.1, max_tokens=5))
    assert provider.last_system == "the-system-prompt"
    assert provider.last_messages == msgs


def _chunk(content):
    return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=content))])


def test_litellmprovider_streams_nonempty_deltas(monkeypatch):
    captured = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return iter([_chunk("Hel"), _chunk(""), _chunk("lo"), _chunk(None)])

    monkeypatch.setattr(provider_module.litellm, "completion", fake_completion)

    out = list(
        LiteLLMProvider("gemini/test").stream(
            "sys", [Message("user", "hi")], temperature=0.5, max_tokens=20
        )
    )
    assert out == ["Hel", "lo"]
    assert captured["model"] == "gemini/test"
    assert captured["stream"] is True
    assert captured["messages"][0] == {"role": "system", "content": "sys"}
    assert captured["messages"][1] == {"role": "user", "content": "hi"}


def test_litellmprovider_wraps_errors(monkeypatch):
    def boom(**kwargs):
        raise RuntimeError("api down")

    monkeypatch.setattr(provider_module.litellm, "completion", boom)

    with pytest.raises(ProviderError, match="api down"):
        list(
            LiteLLMProvider("gemini/test").stream(
                "sys", [Message("user", "hi")], temperature=0.5, max_tokens=20
            )
        )
