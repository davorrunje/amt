from turing.api.config import Settings


def test_defaults():
    settings = Settings()
    assert settings.model == "gemini/gemini-2.5-flash"
    assert settings.temperature == 0.7
    assert settings.max_tokens == 1024


def test_env_override(monkeypatch):
    monkeypatch.setenv("TURING_MODEL", "claude/sonnet")
    monkeypatch.setenv("TURING_TEMPERATURE", "0.1")
    monkeypatch.setenv("TURING_MAX_TOKENS", "256")
    settings = Settings()
    assert settings.model == "claude/sonnet"
    assert settings.temperature == 0.1
    assert settings.max_tokens == 256
