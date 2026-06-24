from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol


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
