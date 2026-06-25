# Typer CLI Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the argparse layer of the `amt` CLI and `turing.sourcing.__main__` with Typer, preserving behaviour (except `--cli` becomes the implicit default) and the 100% coverage gate.

**Architecture:** Typer apps with typed command signatures replace `build_parser`/`Namespace`. The injectable logic functions (`run_cli`, `run_web`, persona build/apply, and a new shared `run_sourcing`) stay as plain functions so tests inject fakes; the Typer layer is thin and tested with `typer.testing.CliRunner`.

**Tech Stack:** Python 3.14, uv, Typer, pytest (+ `typer.testing.CliRunner`).

## Global Constraints

- Python `>=3.14`; all commands via `uv`. Python coverage MUST stay **100%** (`fail_under = 100`).
- `typer` declared in `[project.dependencies]` (runtime). No behavioural change to chat/sourcing/personas logic — CLI layer only.
- Console entry point unchanged: `[project.scripts] amt = "turing.cli.main:main"`, with `def main() -> None: app()`.
- Isolation rules unchanged: `litellm` only via `turing.core.provider`; `playwright`/`google-genai` only in `turing.sourcing`. The CLI imports library classes / `run_sourcing`, never those packages directly.
- `amt chat` mode is a single `--web` flag; terminal REPL is the default (drop the explicit `--cli`).
- `persona` is a `str`-Enum (`student`/`public`/`colleague`).
- No live calls in the default suite; ruff + `ty` clean. Commits staged by the implementer, committed by the controller.

---

## File Structure

```
pyproject.toml                          # add typer to [project.dependencies]
src/turing/sourcing/__main__.py         # argparse -> Typer; new run_sourcing(...) orchestration
src/turing/cli/main.py                  # argparse -> Typer app (callback load_env + 3 commands + Persona enum)
src/turing/cli/cmd_source.py            # run() -> keyword args; calls run_sourcing
src/turing/cli/cmd_chat.py              # run() -> keyword args (web/persona/keep)
src/turing/cli/cmd_personas.py          # run() -> keyword args (prompt/apply)
tests/sourcing/test_cli.py              # test run_sourcing directly + CliRunner wrapper
tests/cli/test_main.py                  # CliRunner command/enum/main tests + keep load_env tests
tests/cli/test_cmd_source.py            # new run() signature; monkeypatch run_sourcing
tests/cli/test_cmd_chat.py              # new run() signature (kwargs)
tests/cli/test_cmd_personas.py          # new run() signature (kwargs)
README.md, CLAUDE.md                    # drop --cli
```

---

### Task 1: Convert `turing.sourcing.__main__` to Typer + extract `run_sourcing`

**Files:**
- Modify: `pyproject.toml` (add `typer` to `[project.dependencies]`)
- Rewrite: `src/turing/sourcing/__main__.py`
- Rewrite: `tests/sourcing/test_cli.py`

**Interfaces:**
- Consumes: `turing.sourcing.pipeline.load_sources`/`run`, `turing.sourcing.browser.PlaywrightBrowser`, `turing.sourcing.transcriber.GeminiTranscriber`.
- Produces:
  - `run_sourcing(*, model: str = "gemini-2.5-pro", force: bool = False, sources: str = "corpus/sources.yaml", corpus_dir: str = "corpus", cache_dir: str = "corpus/cache", browser=None, transcriber=None) -> int` — the orchestration (build adapters when not injected, run pipeline, print one status line per ref, return non-zero on any error).
  - `app: typer.Typer` (single command via `@app.callback(invoke_without_command=True)`), `main() -> None`.

- [ ] **Step 1: Add `typer` to runtime dependencies**

In `pyproject.toml`, add `"typer>=0.12"` to the `[project] dependencies` list (the runtime deps, where fastapi/litellm live — NOT a dependency-group):
```toml
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "litellm>=1.55",
    "pydantic-settings>=2.6",
    "pyyaml>=6.0",
    "typer>=0.12",
]
```
Then run: `uv sync` (expected: typer + click/rich resolved/installed).

- [ ] **Step 2: Write the failing tests** (`tests/sourcing/test_cli.py`, full rewrite)

```python
from pathlib import Path

from typer.testing import CliRunner

from turing.sourcing import __main__ as cli
from turing.sourcing.browser import FakeBrowser
from turing.sourcing.models import FetchResult
from turing.sourcing.transcriber import FakeTranscriber

FIXTURE = (Path(__file__).parent / "fixtures" / "item_synthetic.html").read_text()


def _sources_file(tmp_path):
    p = tmp_path / "sources.yaml"
    p.write_text("sources:\n  - ref: AMT/C/10\n    title: T\n    type: ms\n")
    return p


def test_run_sourcing_with_injected_fakes(tmp_path, capsys):
    sources = _sources_file(tmp_path)
    browser = FakeBrowser(FetchResult(html=FIXTURE, pdf_url="https://x/s.pdf", pdf_bytes=b"%PDF"))
    code = cli.run_sourcing(
        sources=str(sources),
        corpus_dir=str(tmp_path / "c"),
        cache_dir=str(tmp_path / "cache"),
        browser=browser,
        transcriber=FakeTranscriber("BODY"),
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "AMT/C/10" in out and "written" in out
    assert (tmp_path / "c" / "amt-c-10.md").exists()


def test_run_sourcing_nonzero_on_error(tmp_path):
    sources = _sources_file(tmp_path)

    class _Boom:
        def fetch(self, url):
            raise RuntimeError("boom")

    code = cli.run_sourcing(
        sources=str(sources),
        corpus_dir=str(tmp_path / "c"),
        cache_dir=str(tmp_path / "cache"),
        browser=_Boom(),
        transcriber=FakeTranscriber("B"),
    )
    assert code == 1


def test_run_sourcing_builds_default_adapters(tmp_path, monkeypatch):
    sources = _sources_file(tmp_path)
    built = {}
    monkeypatch.setattr(cli, "PlaywrightBrowser", lambda **kw: built.setdefault("b", object()))
    monkeypatch.setattr(cli, "GeminiTranscriber", lambda **kw: built.setdefault("t", object()))
    monkeypatch.setattr(cli, "run", lambda *a, **kw: [])
    code = cli.run_sourcing(sources=str(sources), corpus_dir=str(tmp_path / "c"), cache_dir=str(tmp_path / "cache"))
    assert code == 0
    assert "b" in built and "t" in built


def test_cli_app_invokes_run_sourcing(monkeypatch):
    captured = {}
    monkeypatch.setattr(cli, "run_sourcing", lambda **kw: captured.update(kw) or 0)
    result = CliRunner().invoke(cli.app, ["--model", "gemini-2.5-flash", "--force"])
    assert result.exit_code == 0
    assert captured["model"] == "gemini-2.5-flash"
    assert captured["force"] is True


def test_cli_app_propagates_nonzero(monkeypatch):
    monkeypatch.setattr(cli, "run_sourcing", lambda **kw: 1)
    result = CliRunner().invoke(cli.app, [])
    assert result.exit_code == 1


def test_main_invokes_app(monkeypatch):
    called = {}
    monkeypatch.setattr(cli, "app", lambda: called.setdefault("ran", True))
    cli.main()
    assert called["ran"] is True
```

- [ ] **Step 3: Run to verify failure**

Run: `uv run pytest tests/sourcing/test_cli.py -v`
Expected: FAIL — `AttributeError: module 'turing.sourcing.__main__' has no attribute 'run_sourcing'` / `app`.

- [ ] **Step 4: Rewrite `src/turing/sourcing/__main__.py`**

```python
from pathlib import Path

import typer

from turing.sourcing.browser import PlaywrightBrowser
from turing.sourcing.pipeline import load_sources, run
from turing.sourcing.transcriber import GeminiTranscriber

app = typer.Typer(help="Transcribe curated archive items.")


def run_sourcing(
    *,
    model: str = "gemini-2.5-pro",
    force: bool = False,
    sources: str = "corpus/sources.yaml",
    corpus_dir: str = "corpus",
    cache_dir: str = "corpus/cache",
    browser=None,
    transcriber=None,
) -> int:
    if browser is None:
        browser = PlaywrightBrowser()
    if transcriber is None:
        transcriber = GeminiTranscriber(model=model)
    results = run(
        load_sources(Path(sources)),
        browser=browser,
        transcriber=transcriber,
        corpus_dir=Path(corpus_dir),
        cache_dir=Path(cache_dir),
        force=force,
    )
    for result in results:
        suffix = f" ({result.error})" if result.error else ""
        print(f"{result.ref}: {result.status}{suffix}")
    return 1 if any(r.status == "error" for r in results) else 0


@app.callback(invoke_without_command=True)
def _main(
    model: str = "gemini-2.5-pro",
    force: bool = False,
    sources: str = "corpus/sources.yaml",
    corpus_dir: str = "corpus",
    cache_dir: str = "corpus/cache",
) -> None:
    raise typer.Exit(
        run_sourcing(
            model=model, force=force, sources=sources, corpus_dir=corpus_dir, cache_dir=cache_dir
        )
    )


def main() -> None:
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
```

- [ ] **Step 5: Run to verify pass + coverage**

Run: `uv run pytest tests/sourcing/test_cli.py --cov=src/turing/sourcing -v && uv run pytest --cov`
Expected: tests pass; total coverage 100%. Also `uv run python -m turing.sourcing --help` shows the options.

- [ ] **Step 6: Lint/type, then stage**

Run: `uv run ruff check . && uv run ruff format --check . && uv run ty check`
```bash
git add pyproject.toml uv.lock src/turing/sourcing/__main__.py tests/sourcing/test_cli.py
# controller commits: "refactor(sourcing): Typer entry + shared run_sourcing"
```

---

### Task 2: Convert the `amt` app to Typer + keyword `run()` signatures

**Files:**
- Rewrite: `src/turing/cli/main.py`
- Modify: `src/turing/cli/cmd_source.py`, `cmd_chat.py`, `cmd_personas.py` (signatures only)
- Rewrite: `tests/cli/test_main.py`
- Modify: `tests/cli/test_cmd_source.py`, `tests/cli/test_cmd_chat.py`, `tests/cli/test_cmd_personas.py`

**Interfaces:**
- Consumes: `run_sourcing` (Task 1); existing `cmd_chat.run_cli`/`run_web`/`default_keep_name`, `cmd_personas.load_sources`/`load_build_config`.
- Produces:
  - `turing.cli.main.app: typer.Typer`, `load_env(path=Path(".env"))`, `Persona(str, Enum)`, `main() -> None`.
  - `cmd_source.run(*, model: str, force: bool, browser=None, transcriber=None) -> int`
  - `cmd_chat.run(*, web: bool, persona: str, keep: str | None, provider=None, input_stream=None, output_stream=None) -> int`
  - `cmd_personas.run(*, prompt: str | None = None, apply: bool = False, provider=None, build_config_path=None, corpus_dir=None, personas_dir=None, candidates_dir=None, output_stream=None) -> int`

- [ ] **Step 1: Update `cmd_source.py`** (replace its contents)

```python
import sys

from turing.sourcing.__main__ import run_sourcing


def run(*, model: str, force: bool, browser=None, transcriber=None) -> int:
    code = run_sourcing(model=model, force=force, browser=browser, transcriber=transcriber)
    if code != 0:
        print(
            "\nIf an item failed: ensure Chromium is installed (uv run playwright install chromium)"
            " and GEMINI_API_KEY is set.",
            file=sys.stderr,
        )
    return code
```

- [ ] **Step 2: Update `cmd_chat.run`** (replace ONLY the `run(...)` function at the bottom; keep `run_cli`/`run_web`/`_launch`/`_killpg`/`default_keep_name` unchanged)

```python
def run(
    *,
    web: bool,
    persona: str,
    keep: str | None,
    provider=None,
    input_stream=None,
    output_stream=None,
) -> int:
    if web:
        return run_web()
    keep_path = keep or default_keep_name()
    if provider is None:
        provider = LiteLLMProvider(Settings().model)
    return run_cli(
        persona,
        keep_path,
        provider=provider,
        input_stream=input_stream if input_stream is not None else sys.stdin,
        output_stream=output_stream if output_stream is not None else sys.stdout,
    )
```

- [ ] **Step 3: Update `cmd_personas.run`** (change only the signature + the two `args.` references)

Replace the `def run(args, *, ...)` signature with:
```python
def run(
    *,
    prompt: str | None = None,
    apply: bool = False,
    provider=None,
    build_config_path: Path | None = None,
    corpus_dir: Path | None = None,
    personas_dir: Path | None = None,
    candidates_dir: Path | None = None,
    output_stream=None,
) -> int:
```
Then inside the body, replace `if args.apply:` with `if apply:` and `if args.prompt:` with `if prompt:` and `f"{system}\n\n{args.prompt}"` with `f"{system}\n\n{prompt}"`. Everything else in the function is unchanged.

- [ ] **Step 4: Write the failing `amt` app tests** (`tests/cli/test_main.py`, full rewrite)

```python
import os

from typer.testing import CliRunner

from turing.cli import main as main_module

runner = CliRunner()


def test_load_env_sets_missing_keys(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("# comment\nGEMINI_API_KEY=abc123\nEMPTY\n\nFOO = bar \n")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("FOO", raising=False)
    main_module.load_env(env)
    assert os.environ["GEMINI_API_KEY"] == "abc123"
    assert os.environ["FOO"] == "bar"
    assert "EMPTY" not in os.environ


def test_load_env_does_not_override_existing(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("GEMINI_API_KEY=fromfile")
    monkeypatch.setenv("GEMINI_API_KEY", "fromenv")
    main_module.load_env(env)
    assert os.environ["GEMINI_API_KEY"] == "fromenv"


def test_load_env_missing_file_is_noop(tmp_path):
    main_module.load_env(tmp_path / "nope.env")


def test_source_command_wires_args(monkeypatch):
    monkeypatch.setattr(main_module, "load_env", lambda *a, **k: None)
    captured = {}
    monkeypatch.setattr(main_module.cmd_source, "run", lambda **kw: captured.update(kw) or 0)
    result = runner.invoke(main_module.app, ["source", "--model", "m", "--force"])
    assert result.exit_code == 0
    assert captured == {"model": "m", "force": True}


def test_chat_command_wires_args(monkeypatch):
    monkeypatch.setattr(main_module, "load_env", lambda *a, **k: None)
    captured = {}
    monkeypatch.setattr(main_module.cmd_chat, "run", lambda **kw: captured.update(kw) or 0)
    result = runner.invoke(main_module.app, ["chat", "--web", "--persona", "colleague"])
    assert result.exit_code == 0
    assert captured == {"web": True, "persona": "colleague", "keep": None}


def test_chat_defaults_to_student_terminal(monkeypatch):
    monkeypatch.setattr(main_module, "load_env", lambda *a, **k: None)
    captured = {}
    monkeypatch.setattr(main_module.cmd_chat, "run", lambda **kw: captured.update(kw) or 0)
    result = runner.invoke(main_module.app, ["chat"])
    assert result.exit_code == 0
    assert captured == {"web": False, "persona": "student", "keep": None}


def test_chat_rejects_unknown_persona(monkeypatch):
    monkeypatch.setattr(main_module, "load_env", lambda *a, **k: None)
    result = runner.invoke(main_module.app, ["chat", "--persona", "bogus"])
    assert result.exit_code != 0


def test_personas_command_wires_args(monkeypatch):
    monkeypatch.setattr(main_module, "load_env", lambda *a, **k: None)
    captured = {}
    monkeypatch.setattr(main_module.cmd_personas, "run", lambda **kw: captured.update(kw) or 0)
    result = runner.invoke(main_module.app, ["personas", "--prompt", "x", "--apply"])
    assert result.exit_code == 0
    assert captured == {"prompt": "x", "apply": True}


def test_command_propagates_nonzero(monkeypatch):
    monkeypatch.setattr(main_module, "load_env", lambda *a, **k: None)
    monkeypatch.setattr(main_module.cmd_source, "run", lambda **kw: 3)
    result = runner.invoke(main_module.app, ["source"])
    assert result.exit_code == 3


def test_main_invokes_app(monkeypatch):
    called = {}
    monkeypatch.setattr(main_module, "app", lambda: called.setdefault("ran", True))
    main_module.main()
    assert called["ran"] is True
```

- [ ] **Step 5: Run to verify failure**

Run: `uv run pytest tests/cli/test_main.py -v`
Expected: FAIL — `AttributeError`/import errors (`app`, `Persona` not defined; `build_parser` gone).

- [ ] **Step 6: Rewrite `src/turing/cli/main.py`**

```python
import os
from enum import Enum
from pathlib import Path

import typer

from turing.cli import cmd_chat, cmd_personas, cmd_source

app = typer.Typer(help="Virtual Alan Turing toolkit.", no_args_is_help=True)


class Persona(str, Enum):
    student = "student"
    public = "public"
    colleague = "colleague"


def load_env(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


@app.callback()
def _root() -> None:
    load_env()


@app.command(help="Download + transcribe archive references.")
def source(model: str = "gemini-2.5-pro", force: bool = False) -> None:
    raise typer.Exit(cmd_source.run(model=model, force=force))


@app.command(help="Talk to Turing (terminal by default, or --web).")
def chat(
    web: bool = False,
    persona: Persona = Persona.student,
    keep: str | None = None,
) -> None:
    raise typer.Exit(cmd_chat.run(web=web, persona=persona.value, keep=keep))


@app.command(help="LLM-build persona candidates from the corpus.")
def personas(prompt: str | None = None, apply: bool = False) -> None:
    raise typer.Exit(cmd_personas.run(prompt=prompt, apply=apply))


def main() -> None:
    app()
```

- [ ] **Step 7: Run the new `amt` tests + adapt the cmd_* tests**

First run: `uv run pytest tests/cli/test_main.py --cov=src/turing/cli/main -v` → expect pass, `main.py` 100%.

Then adapt the three cmd test files to the new keyword signatures:

`tests/cli/test_cmd_source.py` (full rewrite):
```python
from turing.cli import cmd_source


def test_run_delegates_model_force(monkeypatch):
    captured = {}

    def fake_run_sourcing(**kw):
        captured.update(kw)
        return 0

    monkeypatch.setattr(cmd_source, "run_sourcing", fake_run_sourcing)
    code = cmd_source.run(model="gemini-2.5-flash", force=True, browser=object(), transcriber=object())
    assert code == 0
    assert captured["model"] == "gemini-2.5-flash"
    assert captured["force"] is True


def test_run_prints_hint_on_failure(monkeypatch, capsys):
    monkeypatch.setattr(cmd_source, "run_sourcing", lambda **kw: 1)
    code = cmd_source.run(model="m", force=False)
    assert code == 1
    assert "playwright install chromium" in capsys.readouterr().err
```

In `tests/cli/test_cmd_chat.py`: every call to `cmd_chat.run(SimpleNamespace(web=..., persona=..., keep=...), ...)` becomes keyword args, e.g.
`cmd_chat.run(web=False, persona="student", keep=str(keep), provider=..., input_stream=..., output_stream=...)`
and `cmd_chat.run(SimpleNamespace(web=True, ...))` becomes `cmd_chat.run(web=True, persona="student", keep=None)`. The `run_cli`/`run_web` direct tests are unchanged.

In `tests/cli/test_cmd_personas.py`: every `cmd_personas.run(SimpleNamespace(prompt=..., apply=...), ...)` becomes keyword args, e.g.
`cmd_personas.run(prompt=None, apply=False, provider=..., build_config_path=..., corpus_dir=..., personas_dir=..., candidates_dir=..., output_stream=...)` and the apply test uses `apply=True`. Remove the now-unused `from types import SimpleNamespace` import if present.

- [ ] **Step 8: Run full suite + lint/type**

Run: `uv run pytest --cov && uv run ruff check . && uv run ruff format --check . && uv run ty check`
Expected: all pass; total coverage 100%. Also `uv run amt --help`, `uv run amt chat --help` show the Typer-generated usage.

- [ ] **Step 9: Stage**

```bash
git add src/turing/cli tests/cli
# controller commits: "refactor(cli): amt CLI on Typer (commands, Persona enum, keyword run signatures)"
```

---

### Task 3: Update docs (drop `--cli`)

**Files:**
- Modify: `README.md`, `CLAUDE.md`

**Interfaces:**
- Consumes: the Typer-based `amt` (Tasks 1-2).
- Produces: docs matching the new interface.

- [ ] **Step 1: Update `README.md` and `CLAUDE.md`**

Read both files; anywhere they show `amt chat --cli` or describe `--cli`, change to the terminal default (`amt chat`) and keep `amt chat --web` for web. No other command text changes. (`amt source`, `amt personas` lines are unchanged.)

- [ ] **Step 2: Verify no stale `--cli` references remain**

Run: `grep -rn "amt chat --cli\|--cli" README.md CLAUDE.md || echo "no stale --cli references"`
Expected: `no stale --cli references` (the design/plan docs may still mention `--cli` describing the change — those are exempt).

- [ ] **Step 3: Full verification**

Run: `uv run pytest --cov && uv run ruff check . && uv run ruff format --check . && uv run ty check`
Expected: all pass; coverage 100%.

- [ ] **Step 4: Stage**

```bash
git add README.md CLAUDE.md
# controller commits: "docs: amt chat terminal is default (drop --cli)"
```

---

## Self-Review

**Spec coverage:**
- `typer` in `[project.dependencies]`; entry point unchanged → Task 1. ✅
- `amt` app: Typer callback (load_env) + `source`/`chat`/`personas` commands + `Persona` enum + `main()` → Task 2. ✅
- `cmd_*` keyword `run()` signatures, injectable seams preserved → Task 2. ✅
- `turing.sourcing.__main__` Typer + shared `run_sourcing`; `amt source` calls it (no argv delegation) → Tasks 1, 2. ✅
- `amt chat` single `--web` flag, terminal default; `--cli` dropped → Task 2 (interface) + Task 3 (docs). ✅
- Isolation: CLI imports `run_sourcing`/library classes, not litellm/playwright/genai → cmd_source imports `run_sourcing`; unchanged elsewhere. ✅
- 100% coverage via CliRunner (Typer layer) + direct fakes (logic) → Tasks 1, 2. ✅
- Docs updated → Task 3. ✅

**Placeholder scan:** No TBD/TODO; complete code or precise edit instructions in every step; the only `# pragma: no cover` is the conventional `__main__` `if __name__` guard.

**Type consistency:** `run_sourcing(*, model, force, sources, corpus_dir, cache_dir, browser, transcriber)`, `cmd_source.run(*, model, force, browser, transcriber)`, `cmd_chat.run(*, web, persona, keep, provider, input_stream, output_stream)`, `cmd_personas.run(*, prompt, apply, provider, build_config_path, corpus_dir, personas_dir, candidates_dir, output_stream)`, `app`/`Persona`/`load_env`/`main` are used identically across tasks and tests. `cmd_source` monkeypatch target is `run_sourcing` (matches the new import). ✅
