from collections.abc import Iterator

from turing.core.personas import compose_system_prompt
from turing.core.provider import ChatProvider, Message


class ChatSession:
    def __init__(
        self,
        provider: ChatProvider,
        *,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> None:
        self._provider = provider
        self._temperature = temperature
        self._max_tokens = max_tokens

    def stream_reply(self, persona_id: str, messages: list[Message]) -> Iterator[str]:
        system = compose_system_prompt(persona_id)
        return self._provider.stream(
            system,
            messages,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )
