# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

- Install: `uv sync`
- Talk to Turing (terminal): `uv run amt chat` · web: `uv run amt chat --web`
- Source archive docs: `uv run amt source` (needs `uv run playwright install chromium` + `GEMINI_API_KEY`)
- Rebuild persona candidates: `uv run amt personas` then `uv run amt personas --apply`
- Tests (100% coverage enforced): `uv run pytest --cov`
- Single test: `uv run pytest tests/test_api.py::test_list_personas -v`
- Live LLM test (needs `GEMINI_API_KEY`): `uv run pytest -m live`
- Lint / format / types: `uv run ruff check .` · `uv run ruff format .` · `uv run ty check`
- Frontend checks: `cd frontend && npm run lint && npm run test && npm run build`

## Architecture

Prompt-only persona chatbot. Data flows: frontend → FastAPI SSE (`src/turing/api/app.py`)
→ `ChatSession` (`src/turing/core/chat.py`) → `ChatProvider` (`src/turing/core/provider.py`) → LiteLLM → LLM.

- **Persona is content, not code.** `src/turing/personas/` holds a shared `base.md`
  plus per-audience overlays, registered in `personas.yaml`. `src/turing/core/personas.py` composes
  `base + overlay` into a system prompt. Add an audience by adding a `.md` + a registry
  entry — no code change.
- **Provider seam.** Only `src/turing/core/provider.py` may import `litellm`. Everything else
  depends on the `ChatProvider` protocol; `FakeProvider` backs offline tests,
  `LiteLLMProvider` is production. This is what keeps the system retargetable to
  Claude/OpenAI (and a future plugin).
- **100% coverage is a hard gate.** New code needs tests that keep coverage at 100%
  (`fail_under = 100`). Test against `FakeProvider`; never hit the network in the default
  suite. The one live test is `@pytest.mark.live` and excluded by `addopts`.
- **Persona guardrails** (in `base.md`): extrapolated/modern-aware Turing, never claims to
  be the real man, never fabricates citations, flags speculation. Preserve these when
  editing prompts.
- **Sourcing pipeline** (`src/turing/sourcing/`, offline tooling, not imported by the chat
  app): curated AMT references → headless-browser fetch (`browser.py`, Playwright only here)
  → Gemini transcription (`transcriber.py`, `google-genai` only here) → gitignored
  `corpus/`. Run with `uv run python -m turing.sourcing` (needs `playwright install
  chromium` + `GEMINI_API_KEY`). Tests mock both adapters; nothing sourced is committed.

## Design docs

See `docs/superpowers/specs/` and `docs/superpowers/plans/` for the design and plan.
