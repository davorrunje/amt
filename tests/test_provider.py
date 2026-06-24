from turing.core.provider import FakeProvider, Message


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
