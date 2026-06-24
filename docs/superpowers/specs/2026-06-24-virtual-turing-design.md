# Virtual Alan Turing — Design

**Date:** 2026-06-24
**Status:** Approved (overall architecture + sub-project 1)

## Goal

A conversational "virtual Alan Turing" you can chat with, adapting its register to
the audience — from informal exchanges with students to rigorous discussion with
skeptical colleagues. Starts as a PhD research prototype; intended to grow into a
public-facing thing (standalone website and/or a plugin for existing assistants).

## Key decisions

- **Grounding: prompt-only persona.** No fine-tuning, no live retrieval. Modern LLMs
  already absorbed most of Turing's published work; the persona is carried by
  hand-authored system prompts.
- **Archive role: curated sourcing.** The Turing Digital Archive
  (https://turingarchive.kings.cam.ac.uk/) is mined for authentic material to *write
  better prompts* — not scraped wholesale, not retrieved at runtime. A few dozen
  high-value documents (key letters, the 1950 paper, replies to objections, informal
  personal letters) are transcribed to Markdown via Gemini and read by a human while
  authoring prompts.
- **Audiences: a few discrete personas.** Three presets — `student` (informal),
  `public` (general), `colleague` (expert/skeptical). Each is a system prompt composed
  from a shared base plus an audience overlay. Adding a fourth is trivial.
- **Provider: LiteLLM behind our own `ChatProvider` interface.** Unified multi-provider
  API (start on Gemini; Claude/OpenAI later). The app never imports `litellm` directly,
  so LiteLLM itself stays swappable and mockable.
- **Stack:** Python 3.14 + FastAPI + `uv`; Vite + React + TypeScript frontend; dev
  container for a reproducible environment.
- **Quality gates:** ruff (lint + format) and `ty` (type checking) via pre-commit;
  pytest with **100% coverage required**; GitHub Actions enforces all of it; Codecov
  for coverage reporting.

## Legal / ethical constraint

- We **never redistribute** transcribed or scanned archive content. It is used only as
  reference for prompt authoring.
- Turing's **published** works (e.g. the 1950 *Computing Machinery and Intelligence*)
  entered the public domain on 2025-01-01 (life+70; he died 1954). His **unpublished**
  manuscripts/letters may still be protected in the UK until 2039 under the CDPA 1988
  transitional "2039 rule." Non-commercial, no-redistribution, reference-only use keeps
  us on safe ground regardless. Revisit at the public-launch stage.
- Persona behaviour: the persona is an **extrapolated Turing** — aware of modern
  developments (including post-1954 advances in computing and AI) and willing to engage
  with them, but it responds with the views Turing would most plausibly hold, reasoned
  from his documented thinking, values, and intellectual style. When a topic is one he
  demonstrably never addressed, it **reasons openly as Turing would** (transparent
  extrapolation) rather than asserting a firm historical opinion he never held. It must
  not claim to literally *be* the real person, and must not fabricate citations.

## System architecture (whole project)

Five units that chain cleanly; most of the weight is content, not code.

```
   ┌─────────────┐      ┌──────────────┐      ┌──────────────┐
   │ 1. Sourcing │ ───► │  corpus/     │ ───► │ 2. Persona   │
   │ (offline)   │      │  *.md + meta │      │   authoring  │
   │ scans→MD    │      └──────────────┘      └──────┬───────┘
   │ via Gemini  │                                   │ personas/
   └─────────────┘                                   ▼
   ┌───────────┐   HTTP/SSE   ┌──────────────┐   ┌──────────────┐
   │5. Frontend│ ◄──────────►│ 4. Backend    │──►│ 3. Chat core │──► Gemini (now)
   │ web chat  │             │   API (FastAPI)│  │ (Python lib) │   /Claude/OpenAI
   └───────────┘             └──────────────┘   └──────────────┘    (later)
```

1. **Sourcing** *(offline)* — curated fetch of archive documents + Gemini-based
   transcription to a versioned `corpus/`. Human-in-the-loop, not a crawler.
2. **Persona authoring** *(content)* — corpus mined to write the base + overlays.
3. **Chat core** *(Python library)* — persona loading/composition, provider
   abstraction, message assembly, streaming. No web concerns.
4. **Backend API** *(FastAPI)* — thin HTTP/SSE layer over the chat core.
5. **Frontend** — minimal SPA: audience selector + chat window.

### Build order

- **Sub-project 1 — vertical slice (this spec).** Chat core + API + minimal frontend +
  dev container, with v1 personas hand-written from general knowledge. Yields a running
  web chat you can talk to and share.
- **Sub-project 2 — sourcing + enrichment (later spec).** Build the curated
  scans→Markdown pipeline and use the material to enrich personas. Real conversations
  from sub-project 1 reveal *where* the persona is thin, making sourcing demand-driven.

## Sub-project 1 — detailed design

### Repo layout

```
turing/
  .devcontainer/
    devcontainer.json       # python:3.14 image + Node feature, ports 8000/5173
    setup.sh                # install uv; uv sync; npm install; pre-commit install
  .pre-commit-config.yaml   # ruff (lint+format) + ty hooks
  .github/workflows/
    ci.yml                  # lint, type-check, test+coverage, upload to Codecov
  codecov.yml               # require 100% project coverage
  pyproject.toml            # uv-managed; ruff/ty/pytest/coverage config
  src/turing/
    personas/               # CONTENT, not code
      base.md               # shared "who Turing is", extrapolation rules, guardrails
      student.md            # informal / learning overlay
      public.md             # general-audience overlay
      colleague.md          # expert / skeptical overlay
      personas.yaml         # registry: id, name, description, file refs
    core/
      personas.py           # load + compose base + overlay → system prompt
      provider.py           # ChatProvider interface + LiteLLMProvider + FakeProvider
      chat.py               # ChatSession: (persona_id, history) → streamed reply
    api/
      app.py                # FastAPI: GET /personas, POST /chat (SSE)
      config.py             # pydantic-settings: model id, API keys, params
  tests/
  frontend/                 # Vite + React + TS: audience selector + chat window
  docs/superpowers/specs/
```

### Components

- **Persona model.** A system prompt = `base.md` + one audience overlay, composed at
  load time. `base.md` carries voice, biographical anchors, the extrapolation rules
  (modern-aware, reasons as Turing would, open about speculation), and guardrails.
  Overlays adjust only tone / depth / assumed knowledge. `personas.yaml`
  registers id → name/description/overlay-file so the API and frontend can list them.
- **Provider interface.** `ChatProvider.stream(system, messages, params) -> Iterator[str]`.
  `LiteLLMProvider` wraps `litellm.completion(stream=True)`. `FakeProvider` returns
  scripted chunks for offline tests. Nothing outside `provider.py` imports `litellm`.
- **ChatSession.** Given `persona_id` + message history, composes the system prompt,
  assembles the provider message list, delegates to the provider, yields text chunks.
- **Config.** `pydantic-settings` reads model id (default a Gemini model), provider API
  keys, temperature/max-tokens from env. Secrets via env / gitignored `.env` only.

### API

- `GET /personas` → `[{id, name, description}]`.
- `POST /chat` body `{persona_id, messages: [{role, content}]}` → `text/event-stream`
  of token events; a terminal `done` event; a typed `error` event on failure.

### Data flow

Frontend sends `{persona_id, messages[]}` → API validates → `ChatSession` composes
system prompt + history → `LiteLLMProvider.stream()` → tokens streamed over SSE →
frontend renders incrementally.

### Error handling

Provider errors (rate limit, auth, timeout) are caught at the API boundary and emitted
as a typed `error` SSE event. The frontend shows a friendly message and preserves
client-side conversation state so the user can retry. Invalid `persona_id` → 400.

### Frontend

Single page: a persona/audience selector (populated from `GET /personas`) and a chat
window that POSTs to `/chat` and renders the streamed reply incrementally. Minimal
styling; no accounts, no persistence yet.

### Testing

- Unit: persona composition, message assembly, error mapping — all against
  `FakeProvider`, no network.
- `LiteLLMProvider` covered by a unit test that **mocks `litellm.completion`** (no
  network), so its streaming/error-mapping code counts toward coverage.
- Integration (optional, env/marker-gated): one test that hits Gemini live. Excluded
  from the coverage run; suite runs fully offline by default.

### Quality gates & CI

- **pre-commit** (`.pre-commit-config.yaml`): `ruff check` (lint), `ruff format`
  (formatting), and `ty` (type check) run on every commit. Installed by `setup.sh`.
- **Coverage:** pytest + `pytest-cov` with `fail_under = 100` in `pyproject.toml`. The
  marker-gated live test is excluded from the coverage measurement so 100% is
  achievable offline.
- **GitHub Actions** (`.github/workflows/ci.yml`): on push/PR — `uv sync`, then run
  ruff lint, ruff format `--check`, `ty`, and `pytest --cov`; upload the coverage report
  to **Codecov**. Pipeline fails if any check fails or coverage < 100%.
- **Codecov** (`codecov.yml`): project + patch targets set to 100%; PRs blocked on a
  coverage drop.
- Frontend linting (ESLint/TS) is wired in CI but not gated at 100% coverage — the
  coverage requirement applies to the Python codebase.

### Out of scope for sub-project 1

Archive sourcing pipeline; persistence/accounts; conversation storage; plugin
packaging; multi-provider config beyond the seam (only Gemini wired up).
