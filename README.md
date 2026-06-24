# Virtual Alan Turing

A conversational, extrapolated Alan Turing you can chat with at three registers:
student, general public, and expert colleague. Prompt-only persona over a swappable
LLM provider (LiteLLM; Gemini by default).

## Develop

Open in the dev container (VS Code: "Reopen in Container"), or locally:

```bash
uv sync                 # Python deps
cp .env.example .env     # add GEMINI_API_KEY
uv run uvicorn turing.api.app:app --reload --port 8000
cd frontend && npm install && npm run dev   # http://localhost:5173
```

## Quality

```bash
uv run pytest --cov          # 100% coverage required
uv run ruff check .          # lint
uv run ruff format .         # format
uv run ty check              # type check
uv run pytest -m live        # optional: hits real Gemini (needs GEMINI_API_KEY)
```
