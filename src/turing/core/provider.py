from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol

import litellm


@dataclass(frozen=True)
class Message:
    role: str
    content: str


class ProviderError(Exception):
    """Raised when the underlying LLM provider fails."""


class ChatProvider(Protocol):
    def stream(
        self,
        system: str,
        messages: list[Message],
        *,
        temperature: float,
        max_tokens: int,
    ) -> Iterator[str]: ...


class FakeProvider:
    """In-memory provider for tests; yields scripted chunks, records calls."""

    def __init__(self, chunks: list[str]) -> None:
        self._chunks = chunks
        self.last_system: str | None = None
        self.last_messages: list[Message] | None = None

    def stream(
        self,
        system: str,
        messages: list[Message],
        *,
        temperature: float,
        max_tokens: int,
    ) -> Iterator[str]:
        self.last_system = system
        self.last_messages = messages
        yield from self._chunks


class LiteLLMProvider:
    """ChatProvider backed by LiteLLM, supporting Gemini/Claude/OpenAI/etc."""

    def __init__(self, model: str) -> None:
        self._model = model

    def stream(
        self,
        system: str,
        messages: list[Message],
        *,
        temperature: float,
        max_tokens: int,
    ) -> Iterator[str]:
        payload = [{"role": "system", "content": system}]
        payload += [{"role": m.role, "content": m.content} for m in messages]
        try:
            response = litellm.completion(
                model=self._model,
                messages=payload,
                stream=True,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            for chunk in response:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as exc:  # noqa: BLE001 — re-raised as a typed ProviderError
            raise ProviderError(str(exc)) from exc
