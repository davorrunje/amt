# Virtual Alan Turing — Sub-project 1 (Vertical Slice) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A running web chat where a user picks an audience (student / general public / expert colleague) and converses with an extrapolated "Alan Turing", powered by an LLM through a swappable provider seam.

**Architecture:** A pure Python chat core (persona composition + a `ChatProvider` abstraction over LiteLLM) sits behind a thin FastAPI SSE layer, consumed by a minimal Vite + React + TypeScript frontend. The persona is carried entirely by hand-authored system prompts (a shared base + per-audience overlay). Quality is enforced by ruff, `ty`, and 100%-coverage pytest, run in pre-commit and GitHub Actions with Codecov.

**Tech Stack:** Python 3.14, uv, FastAPI, uvicorn, LiteLLM, pydantic-settings, PyYAML, pytest + pytest-cov; Vite + React + TypeScript + vitest; ruff, `ty`, pre-commit; GitHub Actions + Codecov; dev container.

## Global Constraints

- Python `>=3.14`; manage all Python deps and runs through `uv` (`uv sync`, `uv run ...`).
- No code outside `src/turing/core/provider.py` may import `litellm`.
- Python test coverage MUST stay at **100%** (`fail_under = 100`); the marker-gated live test is excluded from coverage measurement.
- The persona must never claim to literally *be* the real Turing, never fabricate quotations/citations/dates, and openly flag extrapolation when addressing topics he never covered.
- No archive content (scanned or transcribed) is committed or redistributed — out of scope here entirely.
- Secrets (`GEMINI_API_KEY`, etc.) come from env / a gitignored `.env`; never commit them.
- Default model id: `gemini/gemini-2.5-flash` (overridable via `TURING_MODEL`).
- Lint/format with ruff; type-check with `ty`; commit frequently (one commit per completed task step group).

---

## File Structure

```
turing/
  .devcontainer/devcontainer.json   # python:3.14 image + Node feature, ports 8000/5173
  .devcontainer/setup.sh            # install uv; uv sync; pre-commit install; npm install
  .pre-commit-config.yaml           # ruff + ruff-format + ty
  .github/workflows/ci.yml          # python (lint/type/test/codecov) + frontend (lint/test/build)
  codecov.yml                       # 100% project + patch targets
  pyproject.toml                    # deps + ruff/ty/pytest/coverage config
  .env.example                      # documents TURING_* and provider key vars
  src/turing/__init__.py
  src/turing/personas/base.md       # shared persona: voice, extrapolation rules, guardrails
  src/turing/personas/student.md    # informal overlay
  src/turing/personas/public.md     # general-audience overlay
  src/turing/personas/colleague.md  # expert/sceptical overlay
  src/turing/personas/personas.yaml # registry: id/name/description/overlay_file
  src/turing/core/__init__.py
  src/turing/core/personas.py       # Persona, load_registry, get_persona, compose_system_prompt
  src/turing/core/provider.py       # Message, ProviderError, ChatProvider, FakeProvider, LiteLLMProvider
  src/turing/core/chat.py           # ChatSession
  src/turing/api/__init__.py
  src/turing/api/config.py          # Settings (pydantic-settings)
  src/turing/api/app.py             # create_app(): GET /personas, POST /chat (SSE)
  tests/__init__.py
  tests/test_personas.py
  tests/test_provider.py
  tests/test_chat.py
  tests/test_config.py
  tests/test_api.py
  tests/test_live_gemini.py         # @pytest.mark.live, excluded by default + from coverage
  frontend/                         # Vite + React + TS (scaffolded in Task 8)
  README.md
  CLAUDE.md
```

Each file has one responsibility; persona content (`*.md`, `*.yaml`) is data, not code, so it does not affect coverage.

---

### Task 1: Project scaffolding, tooling, and dev container

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore` (already exists from spec commit — extend it)
- Create: `src/turing/__init__.py`, `src/turing/core/__init__.py`, `src/turing/api/__init__.py`
- Create: `tests/__init__.py`, `tests/test_smoke.py`
- Create: `.pre-commit-config.yaml`
- Create: `.devcontainer/devcontainer.json`, `.devcontainer/setup.sh`
- Create: `.env.example`

**Interfaces:**
- Consumes: nothing.
- Produces: a working `uv` environment; `uv run pytest --cov` passes at 100%; `uv run ruff check .`, `uv run ruff format --check .`, and `uv run ty check` pass. The `turing`, `turing.core`, `turing.api` packages are importable.

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "turing"
version = "0.1.0"
description = "A conversational, extrapolated Alan Turing."
requires-python = ">=3.14"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "litellm>=1.55",
    "pydantic-settings>=2.6",
    "pyyaml>=6.0",
]

[dependency-groups]
dev = [
    "pytest>=8.3",
    "pytest-cov>=6.0",
    "httpx>=0.28",
    "ruff>=0.8",
    "ty>=0.0.1a5",
    "pre-commit>=4.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/turing"]

[tool.ruff]
line-length = 100
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-m 'not live'"
markers = ["live: hits a real LLM provider; requires API key, excluded by default"]
pythonpath = ["src"]

[tool.coverage.run]
source = ["src/turing"]
branch = true

[tool.coverage.report]
fail_under = 100
show_missing = true
exclude_lines = [
    "pragma: no cover",
    "\\.\\.\\.",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
]
```

- [ ] **Step 2: Create empty package files**

Create these as empty files:
- `src/turing/__init__.py`
- `src/turing/core/__init__.py`
- `src/turing/api/__init__.py`
- `tests/__init__.py`

- [ ] **Step 3: Write the smoke test**

`tests/test_smoke.py`:
```python
import turing


def test_package_importable():
    assert turing is not None
```

- [ ] **Step 4: Sync the environment and run the smoke test with coverage**

Run: `uv sync && uv run pytest --cov`
Expected: 1 passed; coverage report shows 100% (only the empty `__init__.py` files are measured).

- [ ] **Step 5: Write `.pre-commit-config.yaml`**

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.6
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: local
    hooks:
      - id: ty
        name: ty check
        entry: uv run ty check
        language: system
        types: [python]
        pass_filenames: false
```

- [ ] **Step 6: Write the dev container files**

`.devcontainer/devcontainer.json`:
```json
{
  "name": "turing",
  "image": "mcr.microsoft.com/devcontainers/python:3.14",
  "features": {
    "ghcr.io/devcontainers/features/node:1": { "version": "20" }
  },
  "postCreateCommand": "bash .devcontainer/setup.sh",
  "forwardPorts": [8000, 5173],
  "customizations": {
    "vscode": {
      "extensions": [
        "charliermarsh.ruff",
        "ms-python.python",
        "dbaeumer.vscode-eslint",
        "esbenp.prettier-vscode"
      ]
    }
  }
}
```

`.devcontainer/setup.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail

# Install uv if not already present
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

uv sync
uv run pre-commit install

if [ -d frontend ]; then
  (cd frontend && npm install)
fi
```

- [ ] **Step 7: Write `.env.example`**

```bash
# Copy to .env and fill in. .env is gitignored.
GEMINI_API_KEY=
# Optional overrides (defaults shown):
# TURING_MODEL=gemini/gemini-2.5-flash
# TURING_TEMPERATURE=0.7
# TURING_MAX_TOKENS=1024
```

- [ ] **Step 8: Verify lint, format, and type checks pass**

Run: `uv run ruff check . && uv run ruff format --check . && uv run ty check`
Expected: all pass (no errors).

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml uv.lock src/turing tests .pre-commit-config.yaml .devcontainer .env.example .gitignore
git commit -m "chore: scaffold project, tooling, and dev container"
```

---

### Task 2: Persona content and loader

**Files:**
- Create: `src/turing/personas/base.md`, `student.md`, `public.md`, `colleague.md`, `personas.yaml`
- Create: `src/turing/core/personas.py`
- Test: `tests/test_personas.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `Persona` (frozen dataclass): `id: str`, `name: str`, `description: str`, `overlay_file: str`
  - `load_registry(personas_dir: Path = PERSONAS_DIR) -> list[Persona]`
  - `get_persona(persona_id: str, personas_dir: Path = PERSONAS_DIR) -> Persona` (raises `KeyError` if unknown)
  - `compose_system_prompt(persona_id: str, personas_dir: Path = PERSONAS_DIR) -> str`
  - `PERSONAS_DIR: Path` (module-level default pointing at the packaged `personas/` dir)

- [ ] **Step 1: Write the persona content files**

`src/turing/personas/base.md`:
```markdown
# You are Alan Turing

You portray Alan Turing (1912–1954): mathematician, logician, codebreaker, and
founder of theoretical computer science — the mind behind the universal machine,
the wartime work at Bletchley Park, the imitation game, and the earliest serious
thinking about machine intelligence and morphogenesis.

## Voice and character
- Speak in the first person as Turing: precise, curious, playful, disarmingly direct.
  You love a concrete example or a thought experiment, and you are unafraid of
  unorthodox conclusions.
- You reason from first principles rather than appeal to consensus or authority.
- You have a dry, understated humour and a streak of self-deprecation. You take ideas,
  not yourself, seriously.

## What you know
- You are aware of developments since your lifetime, including the modern history of
  computing and artificial intelligence. Engage with them freely and with interest.
- When asked about something you never addressed in life, reason it out *as Turing
  would* — from your known commitments (mechanism, the primacy of computation,
  empiricism, behaviour as the test of mind) — and make clear when you are
  extrapolating rather than recalling.

## Honesty
- You are a reconstruction of Turing's thought, not the living man. If asked directly,
  say so plainly.
- Never invent quotations, citations, dates, or sources. If you are unsure of a fact,
  admit it.
```

`src/turing/personas/student.md`:
```markdown
## This conversation: a student
You are speaking with a curious student who is still learning. Be warm, encouraging,
and informal. Lead with intuition and vivid analogies before any formalism, and define
terms as you introduce them. Ask the occasional gentle question to check understanding.
Keep the mathematics light unless invited to go deeper.
```

`src/turing/personas/public.md`:
```markdown
## This conversation: a general audience
You are speaking with an intelligent person who has no special training. Explain
plainly, with everyday analogies, and keep jargon to a minimum — introduce a technical
term only when it earns its place. Favour the big ideas and their human significance
over technical detail.
```

`src/turing/personas/colleague.md`:
```markdown
## This conversation: an expert colleague
You are speaking with a knowledgeable, sceptical peer. Be rigorous and concise. Use
precise terminology, state your assumptions, and defend your claims with argument.
Welcome challenge, concede good objections, and distinguish carefully between what is
established, what is conjecture, and what is your own extrapolation.
```

`src/turing/personas/personas.yaml`:
```yaml
personas:
  - id: student
    name: Student
    description: Informal, encouraging explanations for a curious learner.
    overlay_file: student.md
  - id: public
    name: General public
    description: Plain-language conversation for a general audience.
    overlay_file: public.md
  - id: colleague
    name: Expert colleague
    description: Rigorous, sceptical discussion with a knowledgeable peer.
    overlay_file: colleague.md
```

- [ ] **Step 2: Write the failing tests**

`tests/test_personas.py`:
```python
import pytest

from turing.core.personas import (
    Persona,
    compose_system_prompt,
    get_persona,
    load_registry,
)


def test_load_registry_returns_three_personas():
    registry = load_registry()
    ids = [p.id for p in registry]
    assert ids == ["student", "public", "colleague"]
    assert all(isinstance(p, Persona) for p in registry)


def test_get_persona_returns_matching_persona():
    persona = get_persona("colleague")
    assert persona.name == "Expert colleague"
    assert persona.overlay_file == "colleague.md"


def test_get_persona_unknown_raises_keyerror():
    with pytest.raises(KeyError):
        get_persona("nonexistent")


def test_compose_system_prompt_combines_base_and_overlay():
    prompt = compose_system_prompt("student")
    assert "You are Alan Turing" in prompt  # from base
    assert "a curious student" in prompt  # from student overlay
    # base comes before overlay
    assert prompt.index("You are Alan Turing") < prompt.index("a curious student")


def test_compose_system_prompt_unknown_raises_keyerror():
    with pytest.raises(KeyError):
        compose_system_prompt("nonexistent")
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_personas.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'turing.core.personas'`.

- [ ] **Step 4: Implement `src/turing/core/personas.py`**

```python
from dataclasses import dataclass
from pathlib import Path

import yaml

PERSONAS_DIR = Path(__file__).resolve().parent.parent / "personas"


@dataclass(frozen=True)
class Persona:
    id: str
    name: str
    description: str
    overlay_file: str


def load_registry(personas_dir: Path = PERSONAS_DIR) -> list[Persona]:
    data = yaml.safe_load((personas_dir / "personas.yaml").read_text(encoding="utf-8"))
    return [Persona(**entry) for entry in data["personas"]]


def get_persona(persona_id: str, personas_dir: Path = PERSONAS_DIR) -> Persona:
    for persona in load_registry(personas_dir):
        if persona.id == persona_id:
            return persona
    raise KeyError(persona_id)


def compose_system_prompt(persona_id: str, personas_dir: Path = PERSONAS_DIR) -> str:
    persona = get_persona(persona_id, personas_dir)
    base = (personas_dir / "base.md").read_text(encoding="utf-8")
    overlay = (personas_dir / persona.overlay_file).read_text(encoding="utf-8")
    return f"{base.strip()}\n\n{overlay.strip()}\n"
```

- [ ] **Step 5: Run tests to verify they pass at 100% coverage**

Run: `uv run pytest tests/test_personas.py --cov -v`
Expected: 5 passed; `personas.py` at 100%.

- [ ] **Step 6: Commit**

```bash
git add src/turing/personas src/turing/core/personas.py tests/test_personas.py
git commit -m "feat: persona content and loader"
```

---

### Task 3: Provider interface and FakeProvider

**Files:**
- Create: `src/turing/core/provider.py`
- Test: `tests/test_provider.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `Message` (frozen dataclass): `role: str`, `content: str`
  - `ProviderError(Exception)`
  - `ChatProvider` (Protocol): `stream(self, system: str, messages: list[Message], *, temperature: float, max_tokens: int) -> Iterator[str]`
  - `FakeProvider`: `__init__(self, chunks: list[str])`; implements `stream(...)` yielding the chunks; records the last call's `system` and `messages` on `self.last_system` / `self.last_messages`.

- [ ] **Step 1: Write the failing tests**

`tests/test_provider.py`:
```python
from turing.core.provider import FakeProvider, Message


def test_fakeprovider_yields_chunks_in_order():
    provider = FakeProvider(["Hello", ", ", "world"])
    out = list(
        provider.stream("sys", [Message("user", "hi")], temperature=0.7, max_tokens=10)
    )
    assert out == ["Hello", ", ", "world"]


def test_fakeprovider_records_last_call():
    provider = FakeProvider(["x"])
    msgs = [Message("user", "hi")]
    list(provider.stream("the-system-prompt", msgs, temperature=0.1, max_tokens=5))
    assert provider.last_system == "the-system-prompt"
    assert provider.last_messages == msgs
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_provider.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'turing.core.provider'`.

- [ ] **Step 3: Implement the interface and FakeProvider in `src/turing/core/provider.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass at 100% coverage**

Run: `uv run pytest tests/test_provider.py --cov=src/turing/core/provider -v`
Expected: 2 passed; `provider.py` at 100% (the `ChatProvider.stream` `...` body is excluded by config).

- [ ] **Step 5: Commit**

```bash
git add src/turing/core/provider.py tests/test_provider.py
git commit -m "feat: ChatProvider interface and FakeProvider"
```

---

### Task 4: LiteLLMProvider and the gated live test

**Files:**
- Modify: `src/turing/core/provider.py` (append `LiteLLMProvider`)
- Test: `tests/test_provider.py` (append), `tests/test_live_gemini.py` (create)

**Interfaces:**
- Consumes: `Message`, `ProviderError` from Task 3.
- Produces: `LiteLLMProvider`: `__init__(self, model: str)`; implements `stream(...)` by calling `litellm.completion(..., stream=True)`, yielding non-empty content deltas, and re-raising any exception as `ProviderError`.

- [ ] **Step 1: Write the failing tests (append to `tests/test_provider.py`)**

```python
from types import SimpleNamespace

import pytest

from turing.core import provider as provider_module
from turing.core.provider import LiteLLMProvider, Message, ProviderError


def _chunk(content):
    return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=content))])


def test_litellmprovider_streams_nonempty_deltas(monkeypatch):
    captured = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return iter([_chunk("Hel"), _chunk(""), _chunk("lo"), _chunk(None)])

    monkeypatch.setattr(provider_module.litellm, "completion", fake_completion)

    out = list(
        LiteLLMProvider("gemini/test").stream(
            "sys", [Message("user", "hi")], temperature=0.5, max_tokens=20
        )
    )
    assert out == ["Hel", "lo"]
    assert captured["model"] == "gemini/test"
    assert captured["stream"] is True
    assert captured["messages"][0] == {"role": "system", "content": "sys"}
    assert captured["messages"][1] == {"role": "user", "content": "hi"}


def test_litellmprovider_wraps_errors(monkeypatch):
    def boom(**kwargs):
        raise RuntimeError("api down")

    monkeypatch.setattr(provider_module.litellm, "completion", boom)

    with pytest.raises(ProviderError, match="api down"):
        list(
            LiteLLMProvider("gemini/test").stream(
                "sys", [Message("user", "hi")], temperature=0.5, max_tokens=20
            )
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_provider.py -v`
Expected: FAIL — `ImportError: cannot import name 'LiteLLMProvider'`.

- [ ] **Step 3: Implement `LiteLLMProvider` (append to `src/turing/core/provider.py`)**

Add this import at the top of the file (with the other imports):
```python
import litellm
```

Append the class:
```python
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
```

- [ ] **Step 4: Write the gated live test**

`tests/test_live_gemini.py`:
```python
import os

import pytest

from turing.core.provider import LiteLLMProvider, Message

pytestmark = pytest.mark.live


@pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY"), reason="GEMINI_API_KEY not set"
)
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
```

- [ ] **Step 5: Run unit tests to verify pass at 100% (live test excluded by default)**

Run: `uv run pytest tests/test_provider.py --cov=src/turing/core/provider -v`
Expected: 4 passed; `provider.py` at 100%. The live test is not collected (`-m 'not live'` from `addopts`).

- [ ] **Step 6: Commit**

```bash
git add src/turing/core/provider.py tests/test_provider.py tests/test_live_gemini.py
git commit -m "feat: LiteLLMProvider with gated live test"
```

---

### Task 5: ChatSession

**Files:**
- Create: `src/turing/core/chat.py`
- Test: `tests/test_chat.py`

**Interfaces:**
- Consumes: `compose_system_prompt` (Task 2); `ChatProvider`, `Message` (Task 3).
- Produces: `ChatSession`: `__init__(self, provider: ChatProvider, *, temperature: float = 0.7, max_tokens: int = 1024)`; `stream_reply(self, persona_id: str, messages: list[Message]) -> Iterator[str]` — composes the system prompt for `persona_id` and delegates to `provider.stream`. Propagates `KeyError` for an unknown persona.

- [ ] **Step 1: Write the failing tests**

`tests/test_chat.py`:
```python
import pytest

from turing.core.chat import ChatSession
from turing.core.provider import FakeProvider, Message


def test_stream_reply_yields_provider_chunks():
    provider = FakeProvider(["Hello", " there"])
    session = ChatSession(provider)
    out = list(session.stream_reply("student", [Message("user", "hi")]))
    assert out == ["Hello", " there"]


def test_stream_reply_composes_persona_system_prompt():
    provider = FakeProvider(["x"])
    session = ChatSession(provider)
    list(session.stream_reply("colleague", [Message("user", "hi")]))
    assert "You are Alan Turing" in provider.last_system
    assert "a knowledgeable, sceptical peer" in provider.last_system


def test_stream_reply_passes_params():
    provider = FakeProvider(["x"])
    session = ChatSession(provider, temperature=0.2, max_tokens=42)
    captured = {}

    original = provider.stream

    def spy(system, messages, *, temperature, max_tokens):
        captured["temperature"] = temperature
        captured["max_tokens"] = max_tokens
        return original(system, messages, temperature=temperature, max_tokens=max_tokens)

    provider.stream = spy  # type: ignore[method-assign]
    list(session.stream_reply("student", [Message("user", "hi")]))
    assert captured == {"temperature": 0.2, "max_tokens": 42}


def test_stream_reply_unknown_persona_raises():
    session = ChatSession(FakeProvider(["x"]))
    with pytest.raises(KeyError):
        list(session.stream_reply("nope", [Message("user", "hi")]))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_chat.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'turing.core.chat'`.

- [ ] **Step 3: Implement `src/turing/core/chat.py`**

```python
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

    def stream_reply(
        self, persona_id: str, messages: list[Message]
    ) -> Iterator[str]:
        system = compose_system_prompt(persona_id)
        return self._provider.stream(
            system,
            messages,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )
```

- [ ] **Step 4: Run tests to verify they pass at 100% coverage**

Run: `uv run pytest tests/test_chat.py --cov=src/turing/core/chat -v`
Expected: 4 passed; `chat.py` at 100%.

- [ ] **Step 5: Commit**

```bash
git add src/turing/core/chat.py tests/test_chat.py
git commit -m "feat: ChatSession composing persona and provider"
```

---

### Task 6: Settings

**Files:**
- Create: `src/turing/api/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `Settings` (pydantic-settings `BaseSettings`): fields `model: str = "gemini/gemini-2.5-flash"`, `temperature: float = 0.7`, `max_tokens: int = 1024`; env prefix `TURING_`; reads `.env`; `protected_namespaces=()` so the `model` field is allowed.

- [ ] **Step 1: Write the failing tests**

`tests/test_config.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'turing.api.config'`.

- [ ] **Step 3: Implement `src/turing/api/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TURING_",
        env_file=".env",
        extra="ignore",
        protected_namespaces=(),
    )

    model: str = "gemini/gemini-2.5-flash"
    temperature: float = 0.7
    max_tokens: int = 1024
```

- [ ] **Step 4: Run tests to verify they pass at 100% coverage**

Run: `uv run pytest tests/test_config.py --cov=src/turing/api/config -v`
Expected: 2 passed; `config.py` at 100%.

- [ ] **Step 5: Commit**

```bash
git add src/turing/api/config.py tests/test_config.py
git commit -m "feat: Settings via pydantic-settings"
```

---

### Task 7: FastAPI app (GET /personas, POST /chat SSE)

**Files:**
- Create: `src/turing/api/app.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: `load_registry`, `get_persona` (Task 2); `Message`, `LiteLLMProvider`, `ProviderError` (Tasks 3–4); `ChatSession` (Task 5); `Settings` (Task 6).
- Produces:
  - `create_app(session: ChatSession | None = None) -> FastAPI` — if `session` is None, builds one from `Settings()` + `LiteLLMProvider`.
  - `app = create_app()` module-level instance (uvicorn target `turing.api.app:app`).
  - `GET /personas` → `[{"id", "name", "description"}]`.
  - `POST /chat` body `{"persona_id": str, "messages": [{"role", "content"}]}` → `text/event-stream`; unknown persona → 400.
  - SSE event lines are `data: {json}\n\n` with `{"type": "token", "text": ...}`, then `{"type": "done"}`, or `{"type": "error", "message": ...}` on provider failure.

- [ ] **Step 1: Write the failing tests**

`tests/test_api.py`:
```python
import json

from fastapi.testclient import TestClient

from turing.api.app import create_app
from turing.core.chat import ChatSession
from turing.core.provider import Message, ProviderError


class _RaisingProvider:
    def stream(self, system, messages, *, temperature, max_tokens):
        raise ProviderError("boom")
        yield  # pragma: no cover


def _events(text):
    return [
        json.loads(line[len("data: ") :])
        for line in text.strip().split("\n\n")
        if line.startswith("data: ")
    ]


def test_list_personas():
    client = TestClient(create_app(ChatSession(_fake(["x"]))))
    resp = client.get("/personas")
    assert resp.status_code == 200
    ids = [p["id"] for p in resp.json()]
    assert ids == ["student", "public", "colleague"]
    assert set(resp.json()[0]) == {"id", "name", "description"}


def test_chat_streams_tokens_then_done():
    client = TestClient(create_app(ChatSession(_fake(["Hi", " there"]))))
    resp = client.post(
        "/chat",
        json={"persona_id": "student", "messages": [{"role": "user", "content": "hello"}]},
    )
    assert resp.status_code == 200
    events = _events(resp.text)
    assert events == [
        {"type": "token", "text": "Hi"},
        {"type": "token", "text": " there"},
        {"type": "done"},
    ]


def test_chat_unknown_persona_returns_400():
    client = TestClient(create_app(ChatSession(_fake(["x"]))))
    resp = client.post(
        "/chat",
        json={"persona_id": "nope", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert resp.status_code == 400


def test_chat_provider_error_emits_error_event():
    client = TestClient(create_app(ChatSession(_RaisingProvider())))
    resp = client.post(
        "/chat",
        json={"persona_id": "student", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert resp.status_code == 200
    events = _events(resp.text)
    assert events[-1] == {"type": "error", "message": "boom"}


def test_create_app_without_session_builds_default():
    # Exercises the `session is None` branch; no network call is made here.
    app = create_app()
    client = TestClient(app)
    assert client.get("/personas").status_code == 200


def _fake(chunks):
    from turing.core.provider import FakeProvider

    return FakeProvider(chunks)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_api.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'turing.api.app'`.

- [ ] **Step 3: Implement `src/turing/api/app.py`**

```python
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
        return [
            {"id": p.id, "name": p.name, "description": p.description}
            for p in load_registry()
        ]

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
```

- [ ] **Step 4: Run the full suite to verify pass at 100% coverage**

Run: `uv run pytest --cov`
Expected: all tests pass; total coverage 100%.

- [ ] **Step 5: Verify the server boots and streams (manual smoke; optional but recommended)**

Run: `GEMINI_API_KEY=... uv run uvicorn turing.api.app:app --port 8000` then in another shell `curl -N -X POST localhost:8000/chat -H 'content-type: application/json' -d '{"persona_id":"student","messages":[{"role":"user","content":"Hello, who are you?"}]}'`
Expected: a stream of `data: {"type":"token",...}` lines ending in `data: {"type":"done"}`.

- [ ] **Step 6: Run lint, format, and type checks**

Run: `uv run ruff check . && uv run ruff format --check . && uv run ty check`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add src/turing/api/app.py tests/test_api.py
git commit -m "feat: FastAPI app with SSE chat endpoint"
```

---

### Task 8: Minimal frontend (Vite + React + TS)

**Files:**
- Create: `frontend/` (scaffolded), then overwrite/add `frontend/src/api.ts`, `frontend/src/App.tsx`, `frontend/src/App.test.tsx`, `frontend/vite.config.ts`, `frontend/src/setupTests.ts`
- Modify: `frontend/package.json` (scripts + deps)

**Interfaces:**
- Consumes: backend `GET /personas` and `POST /chat` (SSE) from Task 7.
- Produces: a single-page chat UI with a persona `<select>` (populated from `/personas`) and a message list + input that streams the reply. `api.ts` exports `fetchPersonas(): Promise<Persona[]>` and `streamChat(personaId, messages, onToken): Promise<void>`.

- [ ] **Step 1: Scaffold the Vite app**

Run: `npm create vite@latest frontend -- --template react-ts && cd frontend && npm install && npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom`
Expected: `frontend/` created with a React+TS template; dev deps installed.

- [ ] **Step 2: Configure Vite (dev proxy + vitest)**

Overwrite `frontend/vite.config.ts`:
```typescript
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/personas": "http://localhost:8000",
      "/chat": "http://localhost:8000",
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/setupTests.ts",
  },
});
```

Create `frontend/src/setupTests.ts`:
```typescript
import "@testing-library/jest-dom";
```

- [ ] **Step 3: Set package scripts**

In `frontend/package.json`, ensure the `scripts` block contains:
```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "eslint .",
    "test": "vitest run"
  }
}
```

- [ ] **Step 4: Write the API client**

Create `frontend/src/api.ts`:
```typescript
export interface Persona {
  id: string;
  name: string;
  description: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export async function fetchPersonas(): Promise<Persona[]> {
  const res = await fetch("/personas");
  return res.json();
}

export async function streamChat(
  personaId: string,
  messages: ChatMessage[],
  onToken: (text: string) => void,
): Promise<void> {
  const res = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ persona_id: personaId, messages }),
  });
  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const part of parts) {
      if (!part.startsWith("data: ")) continue;
      const event = JSON.parse(part.slice("data: ".length));
      if (event.type === "token") onToken(event.text);
      else if (event.type === "error") onToken(`\n[error: ${event.message}]`);
    }
  }
}
```

- [ ] **Step 5: Write the App component**

Overwrite `frontend/src/App.tsx`:
```tsx
import { useEffect, useState } from "react";
import { ChatMessage, Persona, fetchPersonas, streamChat } from "./api";

export default function App() {
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [personaId, setPersonaId] = useState("student");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetchPersonas().then(setPersonas);
  }, []);

  async function send() {
    if (!input.trim() || busy) return;
    const next: ChatMessage[] = [...messages, { role: "user", content: input }];
    setMessages([...next, { role: "assistant", content: "" }]);
    setInput("");
    setBusy(true);
    await streamChat(personaId, next, (text) => {
      setMessages((cur) => {
        const copy = [...cur];
        copy[copy.length - 1] = {
          role: "assistant",
          content: copy[copy.length - 1].content + text,
        };
        return copy;
      });
    });
    setBusy(false);
  }

  return (
    <main style={{ maxWidth: 640, margin: "2rem auto", fontFamily: "sans-serif" }}>
      <h1>Talk to Alan Turing</h1>
      <label>
        Audience:{" "}
        <select value={personaId} onChange={(e) => setPersonaId(e.target.value)}>
          {personas.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </label>
      <div style={{ margin: "1rem 0", minHeight: 200 }}>
        {messages.map((m, i) => (
          <p key={i}>
            <strong>{m.role === "user" ? "You" : "Turing"}:</strong> {m.content}
          </p>
        ))}
      </div>
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && send()}
        placeholder="Ask Turing something…"
        style={{ width: "80%" }}
      />
      <button onClick={send} disabled={busy}>
        Send
      </button>
    </main>
  );
}
```

- [ ] **Step 6: Write a render test**

Create `frontend/src/App.test.tsx`:
```tsx
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import App from "./App";

afterEach(() => vi.restoreAllMocks());

test("renders heading and personas from the API", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify([{ id: "student", name: "Student", description: "x" }]),
      { headers: { "Content-Type": "application/json" } },
    ),
  );
  render(<App />);
  expect(screen.getByText("Talk to Alan Turing")).toBeInTheDocument();
  await waitFor(() => expect(screen.getByText("Student")).toBeInTheDocument());
});
```

- [ ] **Step 7: Run frontend lint, test, and build**

Run: `cd frontend && npm run lint && npm run test && npm run build`
Expected: lint clean, 1 test passes, build succeeds.

- [ ] **Step 8: Commit**

```bash
git add frontend
git commit -m "feat: minimal React chat frontend"
```

---

### Task 9: CI, Codecov, README, and CLAUDE.md

**Files:**
- Create: `.github/workflows/ci.yml`, `codecov.yml`, `README.md`, `CLAUDE.md`

**Interfaces:**
- Consumes: everything above (runs the same commands locally-verified in earlier tasks).
- Produces: CI that enforces ruff/`ty`/100%-coverage pytest + Codecov upload for Python, and lint/test/build for the frontend.

- [ ] **Step 1: Write the CI workflow**

`.github/workflows/ci.yml`:
```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:

jobs:
  python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          python-version: "3.14"
      - run: uv sync
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run ty check
      - run: uv run pytest --cov --cov-report=xml
      - uses: codecov/codecov-action@v5
        with:
          fail_ci_if_error: true
        env:
          CODECOV_TOKEN: ${{ secrets.CODECOV_TOKEN }}

  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - run: npm ci
      - run: npm run lint
      - run: npm run test
      - run: npm run build
```

- [ ] **Step 2: Write the Codecov config**

`codecov.yml`:
```yaml
coverage:
  status:
    project:
      default:
        target: 100%
    patch:
      default:
        target: 100%
comment: false
```

- [ ] **Step 3: Write the README**

`README.md`:
```markdown
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
```

- [ ] **Step 4: Write CLAUDE.md**

`CLAUDE.md`:
```markdown
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
```

- [ ] **Step 5: Final full verification**

Run: `uv run ruff check . && uv run ruff format --check . && uv run ty check && uv run pytest --cov && (cd frontend && npm run lint && npm run test && npm run build)`
Expected: everything passes; Python coverage 100%.

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/ci.yml codecov.yml README.md CLAUDE.md
git commit -m "ci: GitHub Actions, Codecov, README, and CLAUDE.md"
```

---

## Self-Review

**Spec coverage:**
- Prompt-only persona, base+overlay, 3 audiences → Tasks 2 (content/loader), 5 (composition). ✅
- LiteLLM behind `ChatProvider` seam; only `provider.py` imports litellm → Tasks 3–4; enforced in CLAUDE.md + global constraints. ✅
- FastAPI `GET /personas` + `POST /chat` SSE, typed error event, 400 on bad persona → Task 7. ✅
- Provider-agnostic config, default Gemini model → Task 6. ✅
- Extrapolated/modern-aware persona + guardrails → Task 2 `base.md`. ✅
- Minimal Vite+React+TS frontend with audience selector → Task 8. ✅
- Dev container (Python 3.14 + Node + uv, setup.sh, ports) → Task 1. ✅
- pre-commit (ruff + ty), 100% pytest coverage, GitHub Actions, Codecov → Tasks 1, 9; `fail_under=100` in pyproject. ✅
- `LiteLLMProvider` covered via mocked `litellm.completion`; live test gated + excluded from coverage → Task 4 + coverage config. ✅
- No archive content committed → not in scope of any task; noted in constraints. ✅

**Placeholder scan:** No TBD/TODO; every code step shows complete code; the only `# pragma: no cover` is the intentional unreachable `yield` in the raising test provider. ✅

**Type consistency:** `Message(role, content)`, `ChatProvider.stream(system, messages, *, temperature, max_tokens) -> Iterator[str]`, `ChatSession.stream_reply(persona_id, messages)`, `compose_system_prompt(persona_id)`, `Settings.model/temperature/max_tokens`, and the SSE event shapes (`token`/`done`/`error`) are used identically across Tasks 3–8. ✅
