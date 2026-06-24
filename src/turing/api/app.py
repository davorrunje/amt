import json
from collections.abc import Iterator

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from turing.api.config import Settings
from turing.core.chat import ChatSession
from turing.core.personas import get_persona, load_registry
from turing.core.provider import LiteLLMProvider, Message, ProviderError


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    persona_id: str
    messages: list[ChatMessage]


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def create_app(session: ChatSession | None = None) -> FastAPI:
    if session is None:
        settings = Settings()
        session = ChatSession(
            LiteLLMProvider(settings.model),
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
        )

    app = FastAPI(title="Virtual Alan Turing")

    @app.get("/personas")
    def list_personas() -> list[dict]:
        return [{"id": p.id, "name": p.name, "description": p.description} for p in load_registry()]

    @app.post("/chat")
    def chat(request: ChatRequest) -> StreamingResponse:
        try:
            get_persona(request.persona_id)
        except KeyError as exc:
            raise HTTPException(status_code=400, detail="Unknown persona") from exc

        messages = [Message(m.role, m.content) for m in request.messages]

        def event_stream() -> Iterator[str]:
            try:
                for token in session.stream_reply(request.persona_id, messages):
                    yield _sse({"type": "token", "text": token})
                yield _sse({"type": "done"})
            except ProviderError as exc:
                yield _sse({"type": "error", "message": str(exc)})

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    return app


app = create_app()
