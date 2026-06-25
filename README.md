# Virtual Alan Turing

A conversational, extrapolated Alan Turing you can chat with at three registers:
student, general public, and expert colleague. Prompt-only persona over a swappable
LLM provider (LiteLLM; Gemini by default).

## Develop

Open in the dev container (VS Code: "Reopen in Container"), or locally:

```bash
uv sync                 # Python deps
cp .env.example .env     # add GEMINI_API_KEY
uv run amt chat --web   # web UI: http://localhost:5173
```

Or start the terminal chat REPL:

```bash
uv run amt chat
```

## Quality

### Backend

```bash
uv run pytest --cov          # 100% coverage required
uv run ruff check .          # lint
uv run ruff format .         # format (use --check to verify without writing, as CI does)
uv run ty check              # type check
uv run pytest -m live        # optional: hits real Gemini (needs GEMINI_API_KEY)
```

### Frontend

```bash
cd frontend
npm run lint    # oxlint
npm run test    # vitest
npm run build
```

## Sourcing archive content (optional)

Build a local corpus from curated Turing Archive references to ground the personas.
Content is never committed (`corpus/` is gitignored except `sources.yaml`).

```bash
uv run playwright install chromium   # one-time: the headless browser
# edit corpus/sources.yaml to list the catalogue references you want
uv run amt source
```
Transcriptions land in `corpus/<ref>.md`. Re-runs skip already-done items (use `--force` to redo).

## Persona candidates

Review and rebuild persona candidates:

```bash
uv run amt personas           # review candidates
uv run amt personas --apply   # commit candidates as new personas
```
