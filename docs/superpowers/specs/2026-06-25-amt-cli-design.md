# `amt` CLI — Design

**Date:** 2026-06-25
**Status:** Approved
**Replaces:** `tools/run.sh`, `tools/source.sh`

## Goal

Replace the ad-hoc `tools/` shell scripts with a single packaged console command, `amt`,
exposing three subcommands:

```
amt source   [--model MODEL] [--force]                       # download + transcribe archive refs
amt chat     [--cli | --web] [--persona NAME] [--keep FILE]  # talk to Turing (terminal or web)
amt personas [--prompt TEXT] [--apply]                       # LLM-build persona candidates from the corpus
```

## Architecture & packaging

- Console entry point: `[project.scripts] amt = "turing.cli:main"`. Invoked as `amt …`
  (installed) or `uv run amt …`.
- New package `src/turing/cli/`:
  - `main.py` — argparse parser with subparsers; **loads `.env` once at startup** (via the
    same mechanism `Settings` uses) so every subcommand sees `GEMINI_API_KEY`. Exposes
    `main(argv=None) -> int`.
  - `cmd_source.py`, `cmd_chat.py`, `cmd_personas.py` — one focused module per command.
- **argparse** (stdlib), consistent with the existing `turing.sourcing` CLI — no new CLI
  framework dependency.
- Subcommands are thin shells: they wire parsed arguments to the existing libraries
  (`turing.sourcing.pipeline`, `turing.core.chat`, `turing.core.provider`,
  `turing.core.personas`). Logic stays in the libraries; the CLI stays testable.

## `amt source`

Replaces `tools/source.sh`. Loads `.env`, then runs the sourcing pipeline
(`turing.sourcing.pipeline.run`) over `corpus/sources.yaml` with a `PlaywrightBrowser` +
`GeminiTranscriber`. Honors `--model` (transcription model) and `--force`. The pipeline's
"only fetch/OCR missing items" behavior is unchanged. Prints one status line per ref and
returns non-zero if any item errored.

Chromium remains a documented one-time step (`uv run playwright install chromium`). If it
is missing, `amt source` catches the Playwright launch error and prints that exact command
rather than failing with a cryptic stack trace.

## `amt chat`

Replaces `tools/run.sh`. `--cli` and `--web` are mutually exclusive; `--cli` is the default.

- **`--cli`** — a terminal REPL backed by `ChatSession` + `LiteLLMProvider`. `--persona`
  selects the audience (`student` | `public` | `colleague`, default `student`); the system
  prompt is composed via `compose_system_prompt`. Replies stream to the terminal. The full
  exchange is written to `--keep` (default `amt-<timestamp>.md`) as a clean Markdown
  transcript (persona, timestamp, then alternating user/Turing turns). The REPL takes its
  input/output streams and provider by injection so it is deterministically testable.
- **`--web`** — launches the FastAPI backend (uvicorn) and the Vite frontend (npm) as
  subprocesses, with the recursive process-tree teardown from `run.sh` ported to Python (a
  signal handler kills each process subtree). Ports 8000/5173, overridable. Uses the
  in-page audience selector; no transcript is persisted. The subprocess launch is isolated
  behind a thin `launch(cmd)` seam so tests can monkeypatch it (no real servers start).

## `amt personas`

New LLM-driven persona builder that **generates candidates for human review** — it never
overwrites live persona files without an explicit `--apply`.

**Inputs:** `src/turing/personas/build-personas.yaml`:
```yaml
# Document refs (from corpus/) used as voice/source material. Per the methodology spec,
# these are the register sources (informal correspondence), not formal/technical docs.
sources:
  - AMT/D/4
# Optional: a first pass that distils a voice guide from the sources.
voice_guide:
  file: ../../../docs/superpowers/turing-voice-guide.md
  prompt: |
    From the supplied letters, describe Turing's actual register ... (patterns, not verbatim text).
# Per-persona build instructions. The builder injects the source transcriptions + this prompt.
personas:
  base:
    file: base.md
    prompt: |
      Write the shared base persona. PRESERVE verbatim the guardrails: a reconstruction not
      the living man; never fabricate citations; modern-aware/extrapolated. Ground the voice
      in the supplied letters — dry, exact, blunt where warranted, never cheerful.
  student:   { file: student.md,   prompt: "Write the student overlay: patient and plain, not chipper ..." }
  public:    { file: public.md,    prompt: "Write the general-audience overlay: matter-of-fact, not breezy ..." }
  colleague: { file: colleague.md, prompt: "Write the expert-colleague overlay: rigorous, concise, blunt ..." }
```

**Behavior:**
1. Read the `sources` doc refs; load their `corpus/<slug>.md` transcriptions (error clearly
   if a referenced doc has not been transcribed yet).
2. For each persona entry, call the LLM with the source context + that persona's prompt
   (+ the `--prompt` addendum, if given). Optionally run the `voice_guide` step first.
3. Write each result to `src/turing/personas/candidates/<file>`, then print a **unified
   diff** of each candidate against the live file. Stop (no live file changed).
4. `amt personas --apply` copies the staged candidates over the live persona files
   (and the voice guide, if generated).

The LLM client is injected, so the build is tested against a fake without network calls.

## Tooling removal & docs

- Delete `tools/run.sh` and `tools/source.sh`.
- Update `README.md` and `CLAUDE.md`: document `amt source` / `amt chat` / `amt personas`
  (install with `uv sync`; `uv run playwright install chromium` once for web sourcing).

## Testing & quality

The 100%-coverage gate binds `src/turing/cli/`.

- **Arg parsing** — unit tests for flags, defaults, and the mutually-exclusive `--cli/--web`.
- **`amt source`** — monkeypatch/inject a fake pipeline run; assert argument wiring and the
  missing-Chromium error branch (simulate the Playwright error → printed install hint).
- **`amt chat --cli`** — drive the REPL with a scripted `FakeProvider` + injected
  input/output streams; assert streamed output and that `--keep` writes the expected
  Markdown transcript.
- **`amt chat --web`** — monkeypatch the `launch(cmd)` seam; assert the backend and frontend
  commands and the teardown handler are wired; no real servers start.
- **`amt personas`** — fake LLM client + temp `corpus/` and temp `build-personas.yaml`;
  assert candidates written, diff produced, guardrails present in the build prompt and
  retained in candidates, and `--apply` promotes them.
- No live calls in the default suite; ruff + ty clean. An optional `@pytest.mark.live`
  smoke test may exercise `amt source`/`amt personas`, gated + excluded from coverage.

## Out of scope

- Packaging/publishing `amt` to PyPI (it's run from the repo via `uv run amt`).
- Persisting web-chat transcripts server-side (`--keep` is CLI-only).
- Auto-installing the Chromium binary from within `amt`.
- Changing the persona *content* — `amt personas` builds candidates; the actual voice
  decisions remain a human review (per the persona-sourcing methodology spec).

## Implementation phasing

One spec, but the plan lands it in three reviewable slices, in order:
1. CLI scaffold (entry point, argparse, `.env` loading) + `amt source`.
2. `amt chat` (`--cli` REPL + transcript, `--web` subprocess launch).
3. `amt personas` (builder, `build-personas.yaml`, candidate staging, diff, `--apply`),
   then delete `tools/` and update docs.
