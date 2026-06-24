# Archive Sourcing + Persona Revision — Design

**Date:** 2026-06-24
**Status:** Approved
**Sub-project:** 2 (of the Virtual Alan Turing project; see `2026-06-24-virtual-turing-design.md`)

## Goal

Ground the Turing personas in his actual writing so they stop sounding "too cheerful for
AMT" and start sounding like him — dry, exact, often blunt, wry rather than bubbly. Two
coupled deliverables toward that goal:

- **(A) Sourcing pipeline** — a reusable capability: AMT catalogue reference → archive PDF
  → Gemini transcription → Markdown corpus.
- **(B) Persona revision** — distill a voice guide from the corpus and rewrite `base.md`
  and the audience overlays.

"Public-text-first": deliverable **B can begin immediately** from public-domain published
writings (the 1950 *Mind* paper, the 1948 "Intelligent Machinery" report, the 1947 LMS
lecture, the BBC talks), while **A deepens** the corpus with the personal and handwritten
material — correspondence, unpublished manuscripts — that most strongly fixes the tone and
is not cleanly transcribed anywhere else.

## Archive facts (from investigation)

- Organized by **AMT catalogue references**, eight sections: A (biographical), B
  (publications/lectures), C (unpublished mss), D (correspondence), E (event video), F
  (Furbank papers), H (Hanslope Park), K (1960 materials).
- Item pages live at clean URLs, usually `/<lowercased-dashed-ref>` (e.g. `AMT/C/10` →
  `https://turingarchive.kings.cam.ac.uk/amt-c-10`); some items use a longer
  section-prefixed slug, so a manual URL override is required for the irregular ones.
- Each item page embeds the document as a **scanned PDF** in a custom viewer (no API, no
  IIIF, no existing transcriptions). Some PDFs approach 100 MB. **The PDF URL is injected
  at runtime by the viewer's JavaScript** — it is *not* in the static HTML (verified on
  `AMT/C/10` = `node/117`), so a plain HTTP client can read the page metadata but cannot
  obtain the PDF. Capturing the PDF requires rendering the page in a headless browser.
- `robots.txt` (Drupal default) disallows only `/admin`, `/search`, `/user/*`, etc. — the
  archive item pages and PDFs are **not** disallowed; there is no crawl-delay directive.
- Downloads are permitted **for personal use**; all material is **copyright-restricted**.

## Legal / ethical constraints

- **No sourced content is ever committed or redistributed.** `corpus/` (raw PDFs and
  transcriptions alike) is entirely gitignored. This single rule keeps us within the
  archive's "personal use, no redistribution" terms regardless of the 2039-rule status of
  any individual unpublished item.
- Automated fetching hits a live institutional site, so the fetcher MUST be polite: a
  descriptive User-Agent, a configurable inter-request delay, an on-disk cache so nothing
  is fetched twice, and it MUST respect `robots.txt`.
- Committed artifacts are our own derived work: the pipeline code, a curation list
  (`corpus/sources.yaml` — references/URLs + metadata, no content), a distilled voice
  guide, and the revised persona prompts.

## Architecture

New package `src/turing/sourcing/`, under the existing **100% coverage gate** (all network
and Gemini calls mocked in tests). Driven by a thin CLI (`python -m turing.sourcing`). The
chat application never imports this package, so there is no runtime coupling.

```
  corpus/sources.yaml ──► resolver ──► fetcher ──► transcriber ──► corpus/<ref>.md
  (references + URLs)      (ref→URL)   (HTTP+cache) (Gemini OCR)    (md + front-matter)
                                          │
                                   corpus/cache/*.pdf (gitignored)
                                                                         │
                                          (deliverable B) corpus ──► voice guide ──► personas
```

### Components (each one responsibility)

- **`resolver`** — maps an AMT reference (`AMT/C/10`) to its item-page URL
  (`/amt-c-10`). Honors a per-entry `url:` override in `sources.yaml` for irregular slugs.
- **`metadata`** — pure HTML → `ItemMetadata` parser (catalogue ref, title, date,
  physical description, copyright); tested against recorded HTML fixtures.
- **`browser`** — a `Browser` protocol with a `PlaywrightBrowser` implementation that
  renders the item page in headless Chromium, intercepts the network response whose
  content is the PDF, and returns `(html, pdf_url, pdf_bytes)`. A custom User-Agent and a
  configurable inter-request delay keep it polite; downloads are written to an on-disk
  cache so nothing is fetched twice. A `FakeBrowser` backs offline tests (mirrors the
  `ChatProvider`/`FakeProvider` pattern).
- **`transcriber`** — uploads the PDF to **Gemini via `google-genai`** (File API, so large
  scans work) and requests a faithful Markdown transcription. Default model
  `gemini-2.5-pro` (better at handwriting); configurable. Returns Markdown text.
- **`corpus`** — writes `corpus/<ref>.md` with YAML front-matter (`ref`, `title`, `date`,
  `type`, `source_url`) followed by the transcription. **Idempotent**: skips an item whose
  output already exists unless `--force`.

### Why `google-genai` here instead of LiteLLM

Sourcing is offline tooling that needs the Gemini File API and vision handling that the
chat path's LiteLLM seam does not cleanly provide for ~100 MB scanned PDFs. `google-genai`
is imported **only** within `src/turing/sourcing/` — a deliberate parallel to the "only
`core/provider.py` imports `litellm`" rule — and, with `playwright`, ships as a separate
optional dependency group (`sourcing`) so the chat runtime stays lean. `playwright` is
likewise imported only within `src/turing/sourcing/browser`. The browser binary
(`playwright install chromium`) is needed only to run the pipeline / the live test, not
the default mocked suite.

## Data flow & storage

- **Gitignored (local only):** `corpus/cache/*.pdf` (raw downloads), `corpus/*.md`
  (transcriptions).
- **Committed:** `corpus/sources.yaml` (curation list), `src/turing/sourcing/**`, tests,
  `docs/superpowers/turing-voice-guide.md`, and the revised persona files.
- `.gitignore` gains `corpus/` with an exception for `corpus/sources.yaml`.

## Deliverable B: persona revision

- Distill a concise **voice guide** (`docs/superpowers/turing-voice-guide.md`) from the
  corpus: characteristic diction and sentence rhythm, his actual register (dry, precise,
  occasionally blunt or impatient, wry not bubbly), and an explicit **"what he is not"**
  list — no exclamatory enthusiasm, no cheerleading, no "great question!". This is the
  direct antidote to "too cheerful".
- Rewrite `base.md` to tighten the "playful / warm" language currently driving cheer, and
  especially the **student overlay** ("warm, encouraging" → patient and plain, not chipper).
- Validation is qualitative: a few before/after sample exchanges per persona, shown to the
  user for judgment. No automated test asserts tone.

## Testing & quality

- 100% coverage on `src/turing/sourcing/`, with **all browser and Gemini calls mocked**:
  recorded item-page HTML fixtures + a `FakeBrowser` and a fake transcriber, mirroring the
  `FakeProvider` pattern. The thin `PlaywrightBrowser` and `google-genai` adapters are
  covered by unit tests that monkeypatch `sync_playwright` / the genai client (the same
  technique used for `LiteLLMProvider`). The default suite launches no browser and makes no
  network/Gemini calls.
- One optional `@pytest.mark.live` test fetches and transcribes a single real reference
  end-to-end behind `GEMINI_API_KEY` (and a locally installed Chromium); excluded from the
  default run and from coverage.
- ruff + `ty` clean; same gates as the rest of the repo.

## Out of scope

- Live retrieval / RAG at chat time (personas remain prompt-only).
- Reproducing or shipping any archive content.
- A general web crawler — only curated references in `sources.yaml` are fetched.
- Automated tone scoring — persona quality stays a human judgment.
