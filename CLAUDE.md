# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

- Install: `uv sync`
- Run backend: `uv run uvicorn turing.api.app:app --reload --port 8000`
- Run frontend: `cd frontend && npm run dev`
- Tests (100% coverage enforced): `uv run pytest --cov`
- Single test: `uv run pytest tests/test_api.py::test_list_personas -v`
- Live LLM test (needs `GEMINI_API_KEY`): `uv run pytest -m live`
- Lint / format / types: `uv run ruff check .` · `uv run ruff format .` · `uv run ty check`
- Frontend checks: `cd frontend && npm run lint && npm run test && npm run build`

## Architecture

Prompt-only persona chatbot. Data flows: frontend → FastAPI SSE (`src/turing/api/app.py`)
→ `ChatSession` (`core/chat.py`) → `ChatProvider` (`core/provider.py`) → LiteLLM → LLM.

- **Persona is content, not code.** `src/turing/personas/` holds a shared `base.md`
  plus per-audience overlays, registered in `personas.yaml`. `core/personas.py` composes
  `base + overlay` into a system prompt. Add an audience by adding a `.md` + a registry
  entry — no code change.
- **Provider seam.** Only `core/provider.py` may import `litellm`. Everything else
  depends on the `ChatProvider` protocol; `FakeProvider` backs offline tests,
  `LiteLLMProvider` is production. This is what keeps the system retargetable to
  Claude/OpenAI (and a future plugin).
- **100% coverage is a hard gate.** New code needs tests that keep coverage at 100%
  (`fail_under = 100`). Test against `FakeProvider`; never hit the network in the default
  suite. The one live test is `@pytest.mark.live` and excluded by `addopts`.
- **Persona guardrails** (in `base.md`): extrapolated/modern-aware Turing, never claims to
  be the real man, never fabricates citations, flags speculation. Preserve these when
  editing prompts.

## Design docs

See `docs/superpowers/specs/` and `docs/superpowers/plans/` for the design and plan.
