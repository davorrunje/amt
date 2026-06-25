# Typer CLI Refactor — Design

**Date:** 2026-06-25
**Status:** Approved
**Refactors:** `src/turing/cli/` and `turing.sourcing.__main__` (argparse → Typer)

## Goal

Replace the hand-rolled argparse layer of the `amt` CLI (and the `python -m turing.sourcing`
entry) with **Typer**, per the original instruction. Typer derives the option spec from typed
command-function signatures, removing the `build_parser`/`Namespace` boilerplate while keeping
behaviour and the 100% test-coverage gate.

Behaviour is preserved except: `amt chat`'s mode is now a single `--web` flag (terminal REPL
is the default), dropping the redundant explicit `--cli` flag.

## Dependency

- Add `typer` to `[project.dependencies]` (runtime — the `amt` console script imports it).
  It is already present transitively; this just declares it. Entry point unchanged:
  `[project.scripts] amt = "turing.cli.main:main"`.

## `amt` app — `src/turing/cli/`

- **`main.py`** becomes a single `app = typer.Typer(help="Virtual Alan Turing toolkit.")`:
  - `@app.callback()` runs `load_env()` before any command (so every command sees
    `GEMINI_API_KEY`). `load_env` keeps its current semantics (`os.environ.setdefault`,
    no-op on missing file).
  - Three `@app.command()` functions whose typed parameters ARE the option spec:
    - `source(model: str = "gemini-2.5-pro", force: bool = False)`
    - `chat(web: bool = False, persona: Persona = Persona.student, keep: str | None = None)`
    - `personas(prompt: str | None = None, apply: bool = False)`
  - `Persona` is a `str`-`Enum` (`student`/`public`/`colleague`) so Typer validates the
    value and lists choices in `--help`.
  - Each command calls the underlying logic and `raise typer.Exit(code)` to propagate the
    process exit code (non-zero on failure).
  - `def main() -> None: app()` is the console-script entry.
- **`cmd_source.py` / `cmd_chat.py` / `cmd_personas.py`** keep their logic; their public
  `run(...)` functions change signature from `run(args, *, deps)` to **explicit keyword
  args** (e.g. `run(*, model, force, browser=None, transcriber=None) -> int`). The
  injectable seams (`provider`, `input_stream`/`output_stream`, `launch`/`killpg`, the
  `*_dir`/path params) are unchanged — they are what keep tests network-free at 100%.

## Sourcing entry — `turing.sourcing.__main__`

- Converted to Typer via `typer.run(...)` over a shared orchestration function
  `run_sourcing(*, model: str, force: bool, browser=None, transcriber=None) -> int` (build
  adapters when not injected, run the pipeline over `corpus/sources.yaml`, print one status
  line per ref, return non-zero on any error).
- `amt source` (`cmd_source.run`) calls the same `run_sourcing` and adds its Chromium hint.
  One orchestration, no argv-building delegation, no duplication.

## Testing (100% coverage preserved)

- **Logic functions** (`run_cli`, `run_web`, `_launch`/`_killpg`, the personas build/apply
  helpers, `load_sources`, `run_sourcing`, `load_env`, and the `cmd_*.run` wrappers) are
  unit-tested directly with injected fakes and monkeypatched dependency constructors
  (`LiteLLMProvider`, `PlaywrightBrowser`, `GeminiTranscriber`) — the existing approach,
  adapted to the new keyword signatures.
- **The Typer layer** (callback, commands, the `Persona` enum, option parsing, exit codes)
  is tested with `typer.testing.CliRunner`: invoke `app`/the sourcing command with argv and
  assert `result.exit_code` and that the underlying `run`/`run_sourcing` was called
  (monkeypatched to capture). These replace the old argparse `build_parser`/dispatch tests.
- No live calls in the default suite; the existing `@pytest.mark.live` tests are unaffected.
- ruff + `ty` clean. `typer` pulls `click`/`rich` transitively — acceptable runtime deps.

## Docs

- Update `README.md` and `CLAUDE.md`: `amt chat` (terminal, default) and `amt chat --web`;
  drop any `--cli` mention. Other command docs unchanged.

## Out of scope

- No behavioural change to the chat/sourcing/personas logic itself — this is a CLI-layer
  refactor only.
- No change to the `amt` command names or their options beyond dropping `--cli`.

## Implementation phasing

Behaviour-preserving refactor; the plan lands it in reviewable slices:
1. Add `typer` dep; convert `src/turing/cli/main.py` + `cmd_*` to Typer (commands, callback,
   `Persona` enum, keyword `run` signatures); rewrite the `amt` CLI tests to `CliRunner` +
   adapted logic tests.
2. Convert `turing.sourcing.__main__` to Typer over a shared `run_sourcing`; point
   `cmd_source` at it; adapt the sourcing-CLI tests.
3. Update README/CLAUDE docs.
