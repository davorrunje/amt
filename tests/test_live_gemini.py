import os

import pytest

from turing.core.provider import LiteLLMProvider, Message

pytestmark = pytest.mark.live


@pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), reason="GEMINI_API_KEY not set")
def test_gemini_live_stream():
    provider = LiteLLMProvider("gemini/gemini-2.5-flash")
    out = "".join(
        provider.stream(
            "You are a calculator. Reply with only the number.",
            [Message("user", "What is 2 + 2?")],
            temperature=0.0,
            max_tokens=16,
        )
    )
    assert "4" in out
