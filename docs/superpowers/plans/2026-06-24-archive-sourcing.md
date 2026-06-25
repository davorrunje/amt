# Archive Sourcing + Persona Revision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a `src/turing/sourcing/` pipeline that turns curated AMT catalogue references into a local Markdown corpus (headless-browser fetch → Gemini transcription), then use that grounding to rewrite the personas so they stop sounding "too cheerful for AMT".

**Architecture:** A new offline `sourcing` package, isolated from the chat runtime: `resolver` (ref→URL), `metadata` (HTML→fields), `browser` (a `Browser` protocol with a `PlaywrightBrowser` that renders the JS viewer and intercepts the PDF, plus a `FakeBrowser`), `transcriber` (a `Transcriber` protocol with a `GeminiTranscriber` via `google-genai`, plus a `FakeTranscriber`), `corpus` (Markdown writer with front-matter, idempotent), and a `pipeline` + CLI tying them together. All browser/Gemini I/O is mocked in tests to keep 100% coverage and zero live calls by default.

**Tech Stack:** Python 3.14, uv, Playwright (Chromium), google-genai, BeautifulSoup4, PyYAML, pytest.

## Global Constraints

- Python `>=3.14`; all Python commands via `uv`.
- Python coverage MUST stay at **100%** (`fail_under = 100`); browser/Gemini adapters are covered by mocking `sync_playwright` / the genai client. The single live test is `@pytest.mark.live` and excluded from the default run.
- `playwright` is imported **only** in `src/turing/sourcing/browser.py`; `google-genai` (`from google import genai`) **only** in `src/turing/sourcing/transcriber.py`. The chat path's `litellm`-only rule is unchanged.
- New third-party deps go in a `sourcing` dependency group that the `dev` group includes; `[project.dependencies]` (chat runtime) stays unchanged/lean.
- **No sourced content is ever committed.** `corpus/` is gitignored except `corpus/sources.yaml`. Tests use synthetic fixtures, never real archive pages/scans.
- The fetcher MUST be polite: descriptive User-Agent, configurable inter-request delay, on-disk cache so nothing is fetched twice.
- Default transcription model: `gemini-2.5-pro`.
- Persona guardrails from sub-project 1 are preserved (modern-aware/extrapolated, no impersonation, no fabricated citations); the revision only changes register/tone.
- ruff + `ty` clean; commit per task.

---

## File Structure

```
corpus/
  sources.yaml                       # committed: curation list (refs + metadata, no content)
  cache/                             # gitignored: downloaded PDFs
  *.md                               # gitignored: transcriptions
src/turing/sourcing/
  __init__.py
  models.py                          # SourceEntry, ItemMetadata, FetchResult, RunResult
  resolver.py                        # reference_to_slug, resolve_url
  metadata.py                        # parse_metadata(html, source_url) -> ItemMetadata
  browser.py                         # Browser protocol, FakeBrowser, PlaywrightBrowser
  transcriber.py                     # Transcriber protocol, FakeTranscriber, GeminiTranscriber
  corpus.py                          # corpus_path, is_done, write_item
  pipeline.py                        # load_sources, run(...)
  __main__.py                        # CLI: python -m turing.sourcing
tests/sourcing/
  __init__.py
  fixtures/item_synthetic.html       # synthetic item-page fixture (no real content)
  test_models.py  test_resolver.py  test_metadata.py  test_browser.py
  test_transcriber.py  test_corpus.py  test_pipeline.py  test_cli.py
tests/test_live_sourcing.py          # @pytest.mark.live, excluded by default + coverage
docs/superpowers/turing-voice-guide.md   # committed: distilled voice guide (Task 9)
```

---

### Task 1: Scaffold the sourcing package, deps, models, gitignore, sources seed

**Files:**
- Modify: `pyproject.toml`
- Modify: `.gitignore`
- Create: `src/turing/sourcing/__init__.py`, `src/turing/sourcing/models.py`
- Create: `tests/sourcing/__init__.py`, `tests/sourcing/test_models.py`
- Create: `corpus/sources.yaml`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `SourceEntry` (frozen dataclass): `ref: str`, `title: str | None = None`, `type: str | None = None`, `url: str | None = None`
  - `ItemMetadata` (frozen dataclass): `ref: str`, `date: str | None`, `description: str | None`, `copyright: str | None`, `provenance: str | None`, `source_url: str`
  - `FetchResult` (frozen dataclass): `html: str`, `pdf_url: str | None`, `pdf_bytes: bytes | None`
  - `RunResult` (frozen dataclass): `ref: str`, `status: str`, `path: str | None = None`, `error: str | None = None`

- [ ] **Step 1: Add the `sourcing` dependency group and wire it into `dev`**

In `pyproject.toml`, change the `[dependency-groups]` section so it reads (keep the existing `dev` entries, add the include + new group):
```toml
[dependency-groups]
dev = [
    "pytest>=8.3",
    "pytest-cov>=6.0",
    "httpx>=0.28",
    "ruff>=0.8",
    "ty>=0.0.1a5",
    "pre-commit>=4.0",
    {include-group = "sourcing"},
]
sourcing = [
    "playwright>=1.49",
    "google-genai>=1.0",
    "beautifulsoup4>=4.12",
]
```
(If a pinned version does not resolve, pick the nearest installable one and note it.)

- [ ] **Step 2: Sync and confirm the new deps install**

Run: `uv sync`
Expected: resolves and installs playwright, google-genai, beautifulsoup4 (no Chromium binary needed yet).

- [ ] **Step 3: Extend `.gitignore` to keep the corpus local but track the curation list**

Append to `.gitignore`:
```
corpus/
!corpus/sources.yaml
```

- [ ] **Step 4: Write the failing test for the models**

`tests/sourcing/__init__.py`: empty file.
`tests/sourcing/test_models.py`:
```python
from turing.sourcing.models import FetchResult, ItemMetadata, RunResult, SourceEntry


def test_source_entry_defaults():
    entry = SourceEntry(ref="AMT/C/10")
    assert entry.ref == "AMT/C/10"
    assert entry.title is None
    assert entry.type is None
    assert entry.url is None


def test_item_metadata_fields():
    meta = ItemMetadata(
        ref="AMT/C/10",
        date="[After 1954]",
        description="A solution of the morphogenetical equations.",
        copyright="Copyright (c) King's College Cambridge.",
        provenance="Assembled after AMT's death.",
        source_url="https://example.test/amt-c-10",
    )
    assert meta.ref == "AMT/C/10"
    assert meta.date == "[After 1954]"


def test_fetch_and_run_results():
    fr = FetchResult(html="<html></html>", pdf_url="https://x/y.pdf", pdf_bytes=b"%PDF")
    assert fr.pdf_bytes == b"%PDF"
    rr = RunResult(ref="AMT/C/10", status="written", path="corpus/amt-c-10.md")
    assert rr.status == "written"
    assert rr.error is None
```

- [ ] **Step 5: Run the test to verify it fails**

Run: `uv run pytest tests/sourcing/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'turing.sourcing'`.

- [ ] **Step 6: Implement the package marker and models**

`src/turing/sourcing/__init__.py`: empty file.
`src/turing/sourcing/models.py`:
```python
from dataclasses import dataclass


@dataclass(frozen=True)
class SourceEntry:
    ref: str
    title: str | None = None
    type: str | None = None
    url: str | None = None


@dataclass(frozen=True)
class ItemMetadata:
    ref: str
    date: str | None
    description: str | None
    copyright: str | None
    provenance: str | None
    source_url: str


@dataclass(frozen=True)
class FetchResult:
    html: str
    pdf_url: str | None
    pdf_bytes: bytes | None


@dataclass(frozen=True)
class RunResult:
    ref: str
    status: str
    path: str | None = None
    error: str | None = None
```

- [ ] **Step 7: Create the curation seed file**

`corpus/sources.yaml`:
```yaml
# Curated Turing Digital Archive references to transcribe.
# Add entries by browsing https://turingarchive.kings.cam.ac.uk and noting the
# catalogue reference. `url` is optional — only needed when the item's page slug
# is not the default lowercased-dashed form (e.g. it lives under a section path).
# `title`/`type` are your labels; they feed the transcription's front-matter.
# For the persona voice work, prioritise correspondence (AMT/D, letters in AMT/A
# and AMT/K) over formal papers — the informal voice is what fixes "too cheerful".
sources:
  - ref: AMT/C/10
    title: Morphogenesis manuscripts (Richards)
    type: unpublished-manuscript
  - ref: AMT/C/7
    title: Notes on computability / unpublished manuscript
    type: unpublished-manuscript
  - ref: AMT/B/25
    title: Lecture / publication
    type: publication
```

- [ ] **Step 8: Run tests, lint, type-check**

Run: `uv run pytest tests/sourcing/test_models.py --cov -v && uv run ruff check . && uv run ruff format --check . && uv run ty check`
Expected: 3 passed; coverage 100%; lint/format/type all pass. (`corpus/sources.yaml` is tracked; `corpus/cache/` and `corpus/*.md` are ignored.)

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml uv.lock .gitignore src/turing/sourcing tests/sourcing corpus/sources.yaml
git commit -m "feat(sourcing): scaffold package, deps, models, curation seed"
```

---

### Task 2: Reference resolver

**Files:**
- Create: `src/turing/sourcing/resolver.py`
- Test: `tests/sourcing/test_resolver.py`

**Interfaces:**
- Consumes: `SourceEntry` (Task 1).
- Produces:
  - `BASE_URL = "https://turingarchive.kings.cam.ac.uk"`
  - `reference_to_slug(ref: str) -> str` — `"AMT/C/10"` → `"amt-c-10"`
  - `resolve_url(entry: SourceEntry) -> str` — uses `entry.url` if set, else `f"{BASE_URL}/{reference_to_slug(entry.ref)}"`

- [ ] **Step 1: Write the failing tests**

`tests/sourcing/test_resolver.py`:
```python
from turing.sourcing.models import SourceEntry
from turing.sourcing.resolver import BASE_URL, reference_to_slug, resolve_url


def test_reference_to_slug():
    assert reference_to_slug("AMT/C/10") == "amt-c-10"
    assert reference_to_slug(" AMT/K/1/77 ") == "amt-k-1-77"


def test_resolve_url_default():
    assert resolve_url(SourceEntry(ref="AMT/C/10")) == f"{BASE_URL}/amt-c-10"


def test_resolve_url_override():
    entry = SourceEntry(ref="AMT/K/1/77", url="https://x.test/longer/slug")
    assert resolve_url(entry) == "https://x.test/longer/slug"
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/sourcing/test_resolver.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'turing.sourcing.resolver'`.

- [ ] **Step 3: Implement `src/turing/sourcing/resolver.py`**

```python
from turing.sourcing.models import SourceEntry

BASE_URL = "https://turingarchive.kings.cam.ac.uk"


def reference_to_slug(ref: str) -> str:
    return ref.strip().lower().replace("/", "-")


def resolve_url(entry: SourceEntry) -> str:
    if entry.url:
        return entry.url
    return f"{BASE_URL}/{reference_to_slug(entry.ref)}"
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/sourcing/test_resolver.py --cov=src/turing/sourcing/resolver -v`
Expected: 3 passed; `resolver.py` 100%.

- [ ] **Step 5: Commit**

```bash
git add src/turing/sourcing/resolver.py tests/sourcing/test_resolver.py
git commit -m "feat(sourcing): reference resolver"
```

---

### Task 3: Metadata parser

**Files:**
- Create: `src/turing/sourcing/metadata.py`
- Create: `tests/sourcing/fixtures/item_synthetic.html`
- Test: `tests/sourcing/test_metadata.py`

**Interfaces:**
- Consumes: `ItemMetadata` (Task 1).
- Produces: `parse_metadata(html: str, source_url: str) -> ItemMetadata`. Extracts `ref` from the first `<h1>`; `copyright` and `provenance` from `<p><strong>Copyright:</strong> …</p>` / `<p><strong>Provenance:</strong> …</p>` inside `<article>`; `description` = the article's other paragraph text joined with a space; `date` = first bracketed token containing a 4-digit year (regex `\[[^\]]*\d{4}[^\]]*\]`) found in the description, else `None`.

- [ ] **Step 1: Create the synthetic fixture (mirrors the real Drupal structure, no real content)**

`tests/sourcing/fixtures/item_synthetic.html`:
```html
<!doctype html>
<html lang="en">
  <head><title>AMT-C-10 | The Turing Digital Archive</title></head>
  <body>
    <h1>AMT/C/10</h1>
    <article>
      <div class="field">
        <p>Sample scope and content describing the item. [After 1954].</p>
        <p>Paper, 16 sh. in envelope.</p>
      </div>
      <p><strong>Provenance:</strong> Assembled after the author's death.</p>
      <p><strong>Copyright:</strong> Copyright (c) Example College.</p>
    </article>
  </body>
</html>
```

- [ ] **Step 2: Write the failing tests**

`tests/sourcing/test_metadata.py`:
```python
from pathlib import Path

from turing.sourcing.metadata import parse_metadata

FIXTURE = (Path(__file__).parent / "fixtures" / "item_synthetic.html").read_text()


def test_parses_ref_from_h1():
    meta = parse_metadata(FIXTURE, "https://x.test/amt-c-10")
    assert meta.ref == "AMT/C/10"
    assert meta.source_url == "https://x.test/amt-c-10"


def test_parses_copyright_and_provenance():
    meta = parse_metadata(FIXTURE, "https://x.test/amt-c-10")
    assert meta.copyright == "Copyright (c) Example College."
    assert meta.provenance == "Assembled after the author's death."


def test_description_excludes_labeled_fields_and_finds_date():
    meta = parse_metadata(FIXTURE, "https://x.test/amt-c-10")
    assert "Sample scope and content" in meta.description
    assert "Paper, 16 sh." in meta.description
    assert "Provenance:" not in meta.description
    assert meta.date == "[After 1954]"


def test_missing_fields_are_none():
    html = "<html><body><h1>AMT/X/1</h1><article><p>No date here.</p></article></body></html>"
    meta = parse_metadata(html, "https://x.test/amt-x-1")
    assert meta.ref == "AMT/X/1"
    assert meta.date is None
    assert meta.copyright is None
    assert meta.provenance is None
    assert meta.description == "No date here."
```

- [ ] **Step 3: Run to verify it fails**

Run: `uv run pytest tests/sourcing/test_metadata.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'turing.sourcing.metadata'`.

- [ ] **Step 4: Implement `src/turing/sourcing/metadata.py`**

```python
import re

from bs4 import BeautifulSoup

from turing.sourcing.models import ItemMetadata

_DATE_RE = re.compile(r"\[[^\]]*\d{4}[^\]]*\]")
_LABELS = ("Provenance:", "Copyright:")


def _labeled(article, label: str) -> str | None:
    for p in article.find_all("p"):
        strong = p.find("strong")
        if strong and strong.get_text(strip=True).rstrip(":") == label.rstrip(":"):
            text = p.get_text(" ", strip=True)
            return text[len(strong.get_text(strip=True)) :].strip()
    return None


def parse_metadata(html: str, source_url: str) -> ItemMetadata:
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.find("h1")
    ref = h1.get_text(strip=True) if h1 else ""
    article = soup.find("article")

    copyright_ = provenance = description = None
    if article:
        copyright_ = _labeled(article, "Copyright:")
        provenance = _labeled(article, "Provenance:")
        parts = []
        for p in article.find_all("p"):
            strong = p.find("strong")
            label = strong.get_text(strip=True) if strong else ""
            if label in _LABELS:
                continue
            parts.append(p.get_text(" ", strip=True))
        description = " ".join(parts) if parts else None

    date = None
    if description:
        match = _DATE_RE.search(description)
        date = match.group(0) if match else None

    return ItemMetadata(
        ref=ref,
        date=date,
        description=description,
        copyright=copyright_,
        provenance=provenance,
        source_url=source_url,
    )
```

- [ ] **Step 5: Run to verify it passes**

Run: `uv run pytest tests/sourcing/test_metadata.py --cov=src/turing/sourcing/metadata -v`
Expected: 4 passed; `metadata.py` 100%.

- [ ] **Step 6: Commit**

```bash
git add src/turing/sourcing/metadata.py tests/sourcing/test_metadata.py tests/sourcing/fixtures/item_synthetic.html
git commit -m "feat(sourcing): item-page metadata parser"
```

---

### Task 4: Browser (Playwright) with FakeBrowser

**Files:**
- Create: `src/turing/sourcing/browser.py`
- Test: `tests/sourcing/test_browser.py`

**Interfaces:**
- Consumes: `FetchResult` (Task 1).
- Produces:
  - `Browser` (Protocol): `fetch(self, url: str) -> FetchResult`
  - `FakeBrowser`: `__init__(self, result: FetchResult)`; `fetch(url)` records `last_url` and returns the result.
  - `PlaywrightBrowser`: `__init__(self, *, user_agent: str = DEFAULT_USER_AGENT, delay: float = 1.0, timeout_ms: int = 60000, sleep=time.sleep)`; `fetch(url)` renders the page in headless Chromium, captures the first response whose URL ends in `.pdf` or whose content-type contains `application/pdf`, downloads its bytes via `page.request`, and returns a `FetchResult`. Sleeps `delay` seconds (politeness) via the injected `sleep`.
  - `DEFAULT_USER_AGENT: str`

- [ ] **Step 1: Write the failing tests (with Playwright fakes)**

`tests/sourcing/test_browser.py`:
```python
from types import SimpleNamespace

from turing.sourcing import browser as browser_module
from turing.sourcing.browser import FakeBrowser, PlaywrightBrowser
from turing.sourcing.models import FetchResult


def test_fakebrowser_returns_result_and_records_url():
    result = FetchResult(html="<h1>x</h1>", pdf_url="https://x/y.pdf", pdf_bytes=b"%PDF")
    fake = FakeBrowser(result)
    assert fake.fetch("https://x/page") is result
    assert fake.last_url == "https://x/page"


class _Resp:
    def __init__(self, url, ctype):
        self.url = url
        self.headers = {"content-type": ctype}


class _Req:
    def __init__(self, body):
        self._body = body
        self.requested = None

    def get(self, url):
        self.requested = url
        return self

    def body(self):
        return self._body


class _Page:
    def __init__(self, html, responses, pdf_body):
        self._html = html
        self._responses = responses
        self.request = _Req(pdf_body)
        self._handlers = {}

    def on(self, event, handler):
        self._handlers[event] = handler

    def goto(self, url, **kwargs):
        for resp in self._responses:
            self._handlers["response"](resp)

    def content(self):
        return self._html


class _Browser:
    def __init__(self, page):
        self._page = page
        self.closed = False

    def new_page(self, **kwargs):
        return self._page

    def close(self):
        self.closed = True


def _fake_playwright(page):
    browser = _Browser(page)
    chromium = SimpleNamespace(launch=lambda **kw: browser)
    pw = SimpleNamespace(chromium=chromium)

    class _CM:
        def __enter__(self):
            return pw

        def __exit__(self, *a):
            return False

    return lambda: _CM()


def test_playwrightbrowser_captures_pdf(monkeypatch):
    page = _Page("<h1>doc</h1>", [_Resp("https://x/scan.pdf", "application/pdf")], b"%PDF-bytes")
    monkeypatch.setattr(browser_module, "sync_playwright", _fake_playwright(page))
    slept = []
    pb = PlaywrightBrowser(delay=0.5, sleep=lambda s: slept.append(s))
    result = pb.fetch("https://x/amt-c-10")
    assert result.html == "<h1>doc</h1>"
    assert result.pdf_url == "https://x/scan.pdf"
    assert result.pdf_bytes == b"%PDF-bytes"
    assert slept == [0.5]


def test_playwrightbrowser_no_pdf(monkeypatch):
    page = _Page("<h1>doc</h1>", [_Resp("https://x/style.css", "text/css")], b"unused")
    monkeypatch.setattr(browser_module, "sync_playwright", _fake_playwright(page))
    pb = PlaywrightBrowser(delay=0, sleep=lambda s: None)
    result = pb.fetch("https://x/amt-c-10")
    assert result.pdf_url is None
    assert result.pdf_bytes is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/sourcing/test_browser.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'turing.sourcing.browser'`.

- [ ] **Step 3: Implement `src/turing/sourcing/browser.py`**

```python
import time
from typing import Protocol

from playwright.sync_api import sync_playwright

from turing.sourcing.models import FetchResult

DEFAULT_USER_AGENT = "VirtualTuring/0.1 (research; +https://github.com/davorrunje/amt)"


class Browser(Protocol):
    def fetch(self, url: str) -> FetchResult: ...


class FakeBrowser:
    def __init__(self, result: FetchResult) -> None:
        self._result = result
        self.last_url: str | None = None

    def fetch(self, url: str) -> FetchResult:
        self.last_url = url
        return self._result


class PlaywrightBrowser:
    def __init__(
        self,
        *,
        user_agent: str = DEFAULT_USER_AGENT,
        delay: float = 1.0,
        timeout_ms: int = 60000,
        sleep=time.sleep,
    ) -> None:
        self._user_agent = user_agent
        self._delay = delay
        self._timeout_ms = timeout_ms
        self._sleep = sleep

    def fetch(self, url: str) -> FetchResult:
        captured: dict[str, str] = {}

        def on_response(response):
            ctype = response.headers.get("content-type", "")
            if response.url.lower().endswith(".pdf") or "application/pdf" in ctype:
                captured.setdefault("url", response.url)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=self._user_agent)
            page.on("response", on_response)
            page.goto(url, wait_until="networkidle", timeout=self._timeout_ms)
            html = page.content()
            pdf_url = captured.get("url")
            pdf_bytes = page.request.get(pdf_url).body() if pdf_url else None
            browser.close()

        if self._delay:
            self._sleep(self._delay)
        return FetchResult(html=html, pdf_url=pdf_url, pdf_bytes=pdf_bytes)
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/sourcing/test_browser.py --cov=src/turing/sourcing/browser -v`
Expected: 3 passed; `browser.py` 100% (the `Browser.fetch` `...` stub is excluded by config).

- [ ] **Step 5: Commit**

```bash
git add src/turing/sourcing/browser.py tests/sourcing/test_browser.py
git commit -m "feat(sourcing): Playwright browser + FakeBrowser"
```

---

### Task 5: Transcriber (Gemini) with FakeTranscriber

**Files:**
- Create: `src/turing/sourcing/transcriber.py`
- Test: `tests/sourcing/test_transcriber.py`

**Interfaces:**
- Consumes: nothing from earlier tasks (operates on bytes/str).
- Produces:
  - `Transcriber` (Protocol): `transcribe(self, pdf_bytes: bytes) -> str`
  - `FakeTranscriber`: `__init__(self, text: str)`; `transcribe(pdf_bytes)` records `last_pdf_bytes` and returns `text`.
  - `GeminiTranscriber`: `__init__(self, *, model: str = DEFAULT_MODEL, client=None)`; `transcribe(pdf_bytes)` uploads the bytes (written to a temp file) via the genai Files API, calls `generate_content` with `TRANSCRIBE_PROMPT` + the uploaded file, returns `response.text or ""`. Uses `genai.Client()` when `client` is None.
  - `DEFAULT_MODEL = "gemini-2.5-pro"`, `TRANSCRIBE_PROMPT: str`

- [ ] **Step 1: Write the failing tests**

`tests/sourcing/test_transcriber.py`:
```python
from types import SimpleNamespace

from turing.sourcing import transcriber as transcriber_module
from turing.sourcing.transcriber import FakeTranscriber, GeminiTranscriber


def test_faketranscriber_returns_text_and_records_bytes():
    fake = FakeTranscriber("transcribed text")
    assert fake.transcribe(b"%PDF") == "transcribed text"
    assert fake.last_pdf_bytes == b"%PDF"


def test_geminitranscriber_uploads_and_generates(monkeypatch):
    calls = {}

    class _Files:
        def upload(self, *, file):
            calls["uploaded_path"] = file
            return SimpleNamespace(name="files/abc")

    class _Models:
        def generate_content(self, *, model, contents):
            calls["model"] = model
            calls["contents"] = contents
            return SimpleNamespace(text="# Transcription\n\nHello.")

    fake_client = SimpleNamespace(files=_Files(), models=_Models())
    monkeypatch.setattr(transcriber_module.genai, "Client", lambda: fake_client)

    out = GeminiTranscriber().transcribe(b"%PDF-data")
    assert out == "# Transcription\n\nHello."
    assert calls["model"] == "gemini-2.5-pro"
    # the uploaded path is a real temp file that contained the bytes
    assert calls["uploaded_path"].endswith(".pdf")
    # prompt is the first content item, uploaded file the second
    assert calls["contents"][0] == transcriber_module.TRANSCRIBE_PROMPT
    assert calls["contents"][1].name == "files/abc"


def test_geminitranscriber_handles_empty_text(monkeypatch):
    class _Files:
        def upload(self, *, file):
            return SimpleNamespace(name="files/x")

    class _Models:
        def generate_content(self, *, model, contents):
            return SimpleNamespace(text=None)

    fake_client = SimpleNamespace(files=_Files(), models=_Models())
    out = GeminiTranscriber(client=fake_client).transcribe(b"%PDF")
    assert out == ""
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/sourcing/test_transcriber.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'turing.sourcing.transcriber'`.

- [ ] **Step 3: Implement `src/turing/sourcing/transcriber.py`**

```python
import os
import tempfile
from typing import Protocol

from google import genai

DEFAULT_MODEL = "gemini-2.5-pro"
TRANSCRIBE_PROMPT = (
    "Transcribe this scanned document to clean GitHub-flavored Markdown. "
    "Preserve the author's exact words, paragraph breaks, and any headings or "
    "lists. Do not summarise, correct, modernise, or add commentary. Mark any "
    "illustrations or diagrams as [diagram]. If a word is illegible, write "
    "[illegible]."
)


class Transcriber(Protocol):
    def transcribe(self, pdf_bytes: bytes) -> str: ...


class FakeTranscriber:
    def __init__(self, text: str) -> None:
        self._text = text
        self.last_pdf_bytes: bytes | None = None

    def transcribe(self, pdf_bytes: bytes) -> str:
        self.last_pdf_bytes = pdf_bytes
        return self._text


class GeminiTranscriber:
    def __init__(self, *, model: str = DEFAULT_MODEL, client=None) -> None:
        self._model = model
        self._client = client or genai.Client()

    def transcribe(self, pdf_bytes: bytes) -> str:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            path = tmp.name
        try:
            uploaded = self._client.files.upload(file=path)
            response = self._client.models.generate_content(
                model=self._model,
                contents=[TRANSCRIBE_PROMPT, uploaded],
            )
            return response.text or ""
        finally:
            os.unlink(path)
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/sourcing/test_transcriber.py --cov=src/turing/sourcing/transcriber -v`
Expected: 3 passed; `transcriber.py` 100%.

- [ ] **Step 5: Commit**

```bash
git add src/turing/sourcing/transcriber.py tests/sourcing/test_transcriber.py
git commit -m "feat(sourcing): Gemini transcriber + FakeTranscriber"
```

---

### Task 6: Corpus writer

**Files:**
- Create: `src/turing/sourcing/corpus.py`
- Test: `tests/sourcing/test_corpus.py`

**Interfaces:**
- Consumes: `SourceEntry`, `ItemMetadata` (Task 1); `reference_to_slug` (Task 2).
- Produces:
  - `corpus_path(ref: str, corpus_dir: Path) -> Path` — `corpus_dir / f"{slug}.md"`
  - `is_done(ref: str, corpus_dir: Path) -> bool` — whether that file already exists
  - `write_item(entry: SourceEntry, metadata: ItemMetadata, transcription: str, corpus_dir: Path) -> Path` — writes YAML front-matter (`ref`, `title` [entry.title or metadata.ref], `type` [entry.type or `"unknown"`], `date`, `source_url`, `copyright`) then a blank line then the transcription; creates `corpus_dir` if missing; returns the path.

- [ ] **Step 1: Write the failing tests**

`tests/sourcing/test_corpus.py`:
```python
import yaml

from turing.sourcing.corpus import corpus_path, is_done, write_item
from turing.sourcing.models import ItemMetadata, SourceEntry


def _meta(ref="AMT/C/10"):
    return ItemMetadata(
        ref=ref,
        date="[After 1954]",
        description="desc",
        copyright="Copyright (c) Example.",
        provenance="prov",
        source_url="https://x.test/amt-c-10",
    )


def test_corpus_path_uses_slug(tmp_path):
    assert corpus_path("AMT/C/10", tmp_path) == tmp_path / "amt-c-10.md"


def test_is_done_false_then_true(tmp_path):
    entry = SourceEntry(ref="AMT/C/10", title="Morphogenesis", type="ms")
    assert is_done("AMT/C/10", tmp_path) is False
    write_item(entry, _meta(), "the transcription", tmp_path)
    assert is_done("AMT/C/10", tmp_path) is True


def test_write_item_front_matter_and_body(tmp_path):
    entry = SourceEntry(ref="AMT/C/10", title="Morphogenesis", type="ms")
    path = write_item(entry, _meta(), "BODY TEXT", tmp_path)
    text = path.read_text()
    assert text.startswith("---\n")
    front, body = text.split("---\n", 2)[1:]
    meta = yaml.safe_load(front)
    assert meta["ref"] == "AMT/C/10"
    assert meta["title"] == "Morphogenesis"
    assert meta["type"] == "ms"
    assert meta["date"] == "[After 1954]"
    assert meta["source_url"] == "https://x.test/amt-c-10"
    assert "BODY TEXT" in body


def test_write_item_title_and_type_fallback(tmp_path):
    entry = SourceEntry(ref="AMT/X/1")  # no title/type
    path = write_item(entry, _meta(ref="AMT/X/1"), "b", tmp_path)
    meta = yaml.safe_load(path.read_text().split("---\n", 2)[1])
    assert meta["title"] == "AMT/X/1"
    assert meta["type"] == "unknown"
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/sourcing/test_corpus.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'turing.sourcing.corpus'`.

- [ ] **Step 3: Implement `src/turing/sourcing/corpus.py`**

```python
from pathlib import Path

import yaml

from turing.sourcing.models import ItemMetadata, SourceEntry
from turing.sourcing.resolver import reference_to_slug


def corpus_path(ref: str, corpus_dir: Path) -> Path:
    return corpus_dir / f"{reference_to_slug(ref)}.md"


def is_done(ref: str, corpus_dir: Path) -> bool:
    return corpus_path(ref, corpus_dir).exists()


def write_item(
    entry: SourceEntry,
    metadata: ItemMetadata,
    transcription: str,
    corpus_dir: Path,
) -> Path:
    corpus_dir.mkdir(parents=True, exist_ok=True)
    front = {
        "ref": metadata.ref or entry.ref,
        "title": entry.title or metadata.ref or entry.ref,
        "type": entry.type or "unknown",
        "date": metadata.date,
        "source_url": metadata.source_url,
        "copyright": metadata.copyright,
    }
    text = "---\n" + yaml.safe_dump(front, sort_keys=False) + "---\n\n" + transcription
    path = corpus_path(entry.ref, corpus_dir)
    path.write_text(text, encoding="utf-8")
    return path
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/sourcing/test_corpus.py --cov=src/turing/sourcing/corpus -v`
Expected: 4 passed; `corpus.py` 100%.

- [ ] **Step 5: Commit**

```bash
git add src/turing/sourcing/corpus.py tests/sourcing/test_corpus.py
git commit -m "feat(sourcing): corpus markdown writer"
```

---

### Task 7: Pipeline + CLI + live test

**Files:**
- Create: `src/turing/sourcing/pipeline.py`
- Create: `src/turing/sourcing/__main__.py`
- Create: `tests/sourcing/test_pipeline.py`, `tests/sourcing/test_cli.py`, `tests/test_live_sourcing.py`

**Interfaces:**
- Consumes: all earlier tasks (`SourceEntry`, `RunResult`, `resolve_url`, `parse_metadata`, `Browser`, `Transcriber`, `corpus.is_done`, `corpus.write_item`).
- Produces:
  - `load_sources(path: Path) -> list[SourceEntry]` — reads `sources.yaml` (`sources:` list of dicts).
  - `run(sources, *, browser, transcriber, corpus_dir, cache_dir, force=False) -> list[RunResult]` — per entry: if `is_done` and not `force` → `RunResult(status="skipped")`; else `resolve_url` → `browser.fetch` → if `pdf_bytes` is None → `RunResult(status="no_pdf")`; else cache the PDF bytes to `cache_dir/<slug>.pdf`, `parse_metadata`, `transcriber.transcribe`, `write_item` → `RunResult(status="written", path=...)`. Catches per-item exceptions into `RunResult(status="error", error=str(exc))`.
  - `main(argv: list[str] | None = None, *, browser=None, transcriber=None) -> int` — argparse CLI (`--sources`, `--corpus-dir`, `--cache-dir`, `--model`, `--force`); builds a `PlaywrightBrowser` / `GeminiTranscriber` when not injected; prints a one-line summary per result; returns process exit code (0 unless any `error`).

- [ ] **Step 1: Write the failing pipeline tests**

`tests/sourcing/test_pipeline.py`:
```python
from pathlib import Path

from turing.sourcing.browser import FakeBrowser
from turing.sourcing.models import FetchResult, SourceEntry
from turing.sourcing.pipeline import load_sources, run
from turing.sourcing.transcriber import FakeTranscriber

FIXTURE = (Path(__file__).parent / "fixtures" / "item_synthetic.html").read_text()


def test_load_sources(tmp_path):
    p = tmp_path / "sources.yaml"
    p.write_text("sources:\n  - ref: AMT/C/10\n    title: T\n    type: ms\n")
    entries = load_sources(p)
    assert entries == [SourceEntry(ref="AMT/C/10", title="T", type="ms")]


def _browser(pdf=b"%PDF"):
    return FakeBrowser(FetchResult(html=FIXTURE, pdf_url="https://x/scan.pdf", pdf_bytes=pdf))


def test_run_writes_item_and_caches_pdf(tmp_path):
    corpus_dir = tmp_path / "corpus"
    cache_dir = tmp_path / "cache"
    results = run(
        [SourceEntry(ref="AMT/C/10", title="Morpho", type="ms")],
        browser=_browser(b"%PDF-bytes"),
        transcriber=FakeTranscriber("BODY"),
        corpus_dir=corpus_dir,
        cache_dir=cache_dir,
    )
    assert results[0].status == "written"
    assert (corpus_dir / "amt-c-10.md").exists()
    assert (cache_dir / "amt-c-10.pdf").read_bytes() == b"%PDF-bytes"
    assert "BODY" in (corpus_dir / "amt-c-10.md").read_text()


def test_run_skips_when_done(tmp_path):
    corpus_dir = tmp_path / "corpus"
    cache_dir = tmp_path / "cache"
    args = dict(browser=_browser(), transcriber=FakeTranscriber("B"), corpus_dir=corpus_dir, cache_dir=cache_dir)
    run([SourceEntry(ref="AMT/C/10")], **args)
    results = run([SourceEntry(ref="AMT/C/10")], **args)
    assert results[0].status == "skipped"


def test_run_force_reprocesses(tmp_path):
    corpus_dir = tmp_path / "corpus"
    cache_dir = tmp_path / "cache"
    args = dict(browser=_browser(), transcriber=FakeTranscriber("B"), corpus_dir=corpus_dir, cache_dir=cache_dir)
    run([SourceEntry(ref="AMT/C/10")], **args)
    results = run([SourceEntry(ref="AMT/C/10")], force=True, **args)
    assert results[0].status == "written"


def test_run_no_pdf(tmp_path):
    browser = FakeBrowser(FetchResult(html=FIXTURE, pdf_url=None, pdf_bytes=None))
    results = run(
        [SourceEntry(ref="AMT/C/10")],
        browser=browser,
        transcriber=FakeTranscriber("B"),
        corpus_dir=tmp_path / "c",
        cache_dir=tmp_path / "cache",
    )
    assert results[0].status == "no_pdf"


def test_run_captures_errors(tmp_path):
    class _Boom:
        def fetch(self, url):
            raise RuntimeError("network down")

    results = run(
        [SourceEntry(ref="AMT/C/10")],
        browser=_Boom(),
        transcriber=FakeTranscriber("B"),
        corpus_dir=tmp_path / "c",
        cache_dir=tmp_path / "cache",
    )
    assert results[0].status == "error"
    assert "network down" in results[0].error
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/sourcing/test_pipeline.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'turing.sourcing.pipeline'`.

- [ ] **Step 3: Implement `src/turing/sourcing/pipeline.py`**

```python
from pathlib import Path

import yaml

from turing.sourcing import corpus
from turing.sourcing.browser import Browser
from turing.sourcing.metadata import parse_metadata
from turing.sourcing.models import RunResult, SourceEntry
from turing.sourcing.resolver import reference_to_slug, resolve_url
from turing.sourcing.transcriber import Transcriber


def load_sources(path: Path) -> list[SourceEntry]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return [SourceEntry(**entry) for entry in data["sources"]]


def run(
    sources: list[SourceEntry],
    *,
    browser: Browser,
    transcriber: Transcriber,
    corpus_dir: Path,
    cache_dir: Path,
    force: bool = False,
) -> list[RunResult]:
    results: list[RunResult] = []
    for entry in sources:
        if not force and corpus.is_done(entry.ref, corpus_dir):
            results.append(RunResult(ref=entry.ref, status="skipped"))
            continue
        try:
            fetched = browser.fetch(resolve_url(entry))
            if fetched.pdf_bytes is None:
                results.append(RunResult(ref=entry.ref, status="no_pdf"))
                continue
            cache_dir.mkdir(parents=True, exist_ok=True)
            (cache_dir / f"{reference_to_slug(entry.ref)}.pdf").write_bytes(fetched.pdf_bytes)
            metadata = parse_metadata(fetched.html, resolve_url(entry))
            transcription = transcriber.transcribe(fetched.pdf_bytes)
            path = corpus.write_item(entry, metadata, transcription, corpus_dir)
            results.append(RunResult(ref=entry.ref, status="written", path=str(path)))
        except Exception as exc:  # noqa: BLE001 — per-item failures are recorded, not fatal
            results.append(RunResult(ref=entry.ref, status="error", error=str(exc)))
    return results
```

- [ ] **Step 4: Run to verify pipeline tests pass**

Run: `uv run pytest tests/sourcing/test_pipeline.py --cov=src/turing/sourcing/pipeline -v`
Expected: 7 passed; `pipeline.py` 100%.

- [ ] **Step 5: Write the failing CLI tests**

`tests/sourcing/test_cli.py`:
```python
from pathlib import Path

from turing.sourcing import __main__ as cli
from turing.sourcing.browser import FakeBrowser
from turing.sourcing.models import FetchResult
from turing.sourcing.transcriber import FakeTranscriber

FIXTURE = (Path(__file__).parent / "fixtures" / "item_synthetic.html").read_text()


def _sources_file(tmp_path):
    p = tmp_path / "sources.yaml"
    p.write_text("sources:\n  - ref: AMT/C/10\n    title: T\n    type: ms\n")
    return p


def test_main_runs_with_injected_fakes(tmp_path, capsys):
    sources = _sources_file(tmp_path)
    browser = FakeBrowser(FetchResult(html=FIXTURE, pdf_url="https://x/s.pdf", pdf_bytes=b"%PDF"))
    code = cli.main(
        ["--sources", str(sources), "--corpus-dir", str(tmp_path / "c"), "--cache-dir", str(tmp_path / "cache")],
        browser=browser,
        transcriber=FakeTranscriber("BODY"),
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "AMT/C/10" in out
    assert "written" in out
    assert (tmp_path / "c" / "amt-c-10.md").exists()


def test_main_returns_nonzero_on_error(tmp_path):
    sources = _sources_file(tmp_path)

    class _Boom:
        def fetch(self, url):
            raise RuntimeError("boom")

    code = cli.main(
        ["--sources", str(sources), "--corpus-dir", str(tmp_path / "c"), "--cache-dir", str(tmp_path / "cache")],
        browser=_Boom(),
        transcriber=FakeTranscriber("B"),
    )
    assert code == 1


def test_main_builds_default_adapters(tmp_path, monkeypatch):
    # Exercise the `browser is None` / `transcriber is None` construction branch
    # without touching the network: stub the adapters and the run() call.
    sources = _sources_file(tmp_path)
    built = {}
    monkeypatch.setattr(cli, "PlaywrightBrowser", lambda **kw: built.setdefault("b", object()))
    monkeypatch.setattr(cli, "GeminiTranscriber", lambda **kw: built.setdefault("t", object()))
    monkeypatch.setattr(cli, "run", lambda *a, **kw: [])
    code = cli.main(["--sources", str(sources), "--corpus-dir", str(tmp_path / "c"), "--cache-dir", str(tmp_path / "cache")])
    assert code == 0
    assert "b" in built and "t" in built
```

- [ ] **Step 6: Run to verify CLI tests fail**

Run: `uv run pytest tests/sourcing/test_cli.py -v`
Expected: FAIL — `ImportError`/attribute errors (no `__main__` yet).

- [ ] **Step 7: Implement `src/turing/sourcing/__main__.py`**

```python
import argparse
from pathlib import Path

from turing.sourcing.browser import PlaywrightBrowser
from turing.sourcing.pipeline import load_sources, run
from turing.sourcing.transcriber import GeminiTranscriber


def main(argv: list[str] | None = None, *, browser=None, transcriber=None) -> int:
    parser = argparse.ArgumentParser(prog="turing.sourcing", description="Transcribe curated archive items.")
    parser.add_argument("--sources", default="corpus/sources.yaml")
    parser.add_argument("--corpus-dir", default="corpus")
    parser.add_argument("--cache-dir", default="corpus/cache")
    parser.add_argument("--model", default="gemini-2.5-pro")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    if browser is None:
        browser = PlaywrightBrowser()
    if transcriber is None:
        transcriber = GeminiTranscriber(model=args.model)

    results = run(
        load_sources(Path(args.sources)),
        browser=browser,
        transcriber=transcriber,
        corpus_dir=Path(args.corpus_dir),
        cache_dir=Path(args.cache_dir),
        force=args.force,
    )
    for result in results:
        suffix = f" ({result.error})" if result.error else ""
        print(f"{result.ref}: {result.status}{suffix}")
    return 1 if any(r.status == "error" for r in results) else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
```

- [ ] **Step 8: Write the gated live test**

`tests/test_live_sourcing.py`:
```python
import os

import pytest

pytestmark = pytest.mark.live


@pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), reason="GEMINI_API_KEY not set")
def test_live_fetch_and_transcribe(tmp_path):
    from turing.sourcing.browser import PlaywrightBrowser
    from turing.sourcing.models import SourceEntry
    from turing.sourcing.pipeline import run
    from turing.sourcing.transcriber import GeminiTranscriber

    results = run(
        [SourceEntry(ref="AMT/C/10", title="Morphogenesis", type="ms")],
        browser=PlaywrightBrowser(delay=0),
        transcriber=GeminiTranscriber(),
        corpus_dir=tmp_path / "corpus",
        cache_dir=tmp_path / "cache",
    )
    assert results[0].status == "written"
    assert (tmp_path / "corpus" / "amt-c-10.md").read_text().strip()
```

- [ ] **Step 9: Run the full default suite (offline) with coverage**

Run: `uv run pytest --cov`
Expected: all pass; `1 deselected` (the live test); **total coverage 100%**.

- [ ] **Step 10: Lint, format, type-check**

Run: `uv run ruff check . && uv run ruff format --check . && uv run ty check`
Expected: all pass.

- [ ] **Step 11: Commit**

```bash
git add src/turing/sourcing/pipeline.py src/turing/sourcing/__main__.py tests/sourcing/test_pipeline.py tests/sourcing/test_cli.py tests/test_live_sourcing.py
git commit -m "feat(sourcing): pipeline, CLI, and gated live test"
```

---

### Task 8: Document running the pipeline

**Files:**
- Modify: `README.md`
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: the CLI (Task 7).
- Produces: docs describing how to install the browser binary and run the pipeline.

- [ ] **Step 1: Add a "Sourcing" section to `README.md`**

Add this section near the Quality section:
````markdown
## Sourcing archive content (optional)

Build a local corpus from curated Turing Archive references to ground the personas.
Content is never committed (`corpus/` is gitignored except `sources.yaml`).

```bash
uv sync                         # installs the sourcing deps (dev group)
uv run playwright install chromium   # one-time: the headless browser
# edit corpus/sources.yaml to list the catalogue references you want
GEMINI_API_KEY=... uv run python -m turing.sourcing
```
Transcriptions land in `corpus/<ref>.md`. Re-runs skip already-done items (use `--force` to redo).
````

- [ ] **Step 2: Add a sourcing note to `CLAUDE.md`**

Under the Architecture section, append:
```markdown
- **Sourcing pipeline** (`src/turing/sourcing/`, offline tooling, not imported by the chat
  app): curated AMT references → headless-browser fetch (`browser.py`, Playwright only here)
  → Gemini transcription (`transcriber.py`, `google-genai` only here) → gitignored
  `corpus/`. Run with `uv run python -m turing.sourcing` (needs `playwright install
  chromium` + `GEMINI_API_KEY`). Tests mock both adapters; nothing sourced is committed.
```

- [ ] **Step 3: Commit**

```bash
git add README.md CLAUDE.md
git commit -m "docs: how to run the archive sourcing pipeline"
```

---

### Task 9: Persona revision — fix "too cheerful"

**Files:**
- Create: `docs/superpowers/turing-voice-guide.md`
- Modify: `src/turing/personas/base.md`, `student.md`, `public.md`, `colleague.md`
- Modify: `tests/test_personas.py`

**Interfaces:**
- Consumes: the voice grounding (public-domain writings now; `corpus/` later).
- Produces: a committed voice guide and revised persona prompts; updated persona tests.

This task changes *content/tone*, not code paths. The persona tests assert specific overlay phrases, so they must be updated in lockstep with the rewrites. Tone is ultimately the user's judgment — present before/after samples for review after implementing.

- [ ] **Step 1: Write the voice guide**

`docs/superpowers/turing-voice-guide.md`:
```markdown
# Turing voice guide

Distilled from his published writing (the 1950 *Mind* paper, the 1948 "Intelligent
Machinery" report, the 1947 LMS lecture, the BBC talks) to keep the personas in his
register. Deepen this from the `corpus/` transcriptions as they accumulate.

## How he writes
- Plain, exact, economical. Short declaratives. Concrete examples over abstraction.
- Logical scaffolding stated openly ("I shall consider…", "It will be seen that…").
- Dry, deadpan wit — understatement and irony, never exclamation.
- Willing to be blunt: dismisses weak arguments directly, concedes good ones plainly.
- Confident but not grandiose; qualifies honestly ("I have no very convincing arguments
  of a positive nature to support my views").

## What he is NOT (the "too cheerful" antidotes)
- Not bubbly or effusive. No "Great question!", no exclamation marks, no cheerleading.
- Not flattering or solicitous. Does not gush, reassure, or pad with warmth.
- Not chatty or padded. No filler enthusiasm, no emoji, no motivational tone.
```

- [ ] **Step 2: Rewrite `src/turing/personas/base.md`** (replace the "Voice and character" section)

Replace the existing `## Voice and character` block with:
```markdown
## Voice and character
- Speak in the first person as Turing: plain, exact, and economical. Prefer short
  declaratives and a concrete example to abstraction. State your reasoning openly.
- Your humour is dry and deadpan — understatement and irony, never exclamation or
  enthusiasm. You do not gush, flatter, reassure, or pad your answers with warmth.
- You are direct: dismiss a weak argument plainly and concede a good one just as plainly.
  Confident but not grandiose; qualify your claims honestly when the evidence is thin.
- You reason from first principles rather than appeal to consensus or authority.
```

- [ ] **Step 3: Rewrite the overlays**

`src/turing/personas/student.md`:
```markdown
## This conversation: a student
You are speaking with a student who is still learning. Be patient and plain, not chipper.
Lead with a concrete example or analogy before any formalism, and define terms as you use
them. You may pose a sharp question back to make them think. Keep the mathematics light
unless invited deeper. Encourage by taking their question seriously, not by praising it.
```

`src/turing/personas/public.md`:
```markdown
## This conversation: a general audience
You are speaking with an intelligent person who has no special training. Explain plainly,
with everyday analogies, and keep jargon to a minimum. Favour the big ideas and their
significance over technical detail. Be matter-of-fact, not breezy.
```

`src/turing/personas/colleague.md`:
```markdown
## This conversation: an expert colleague
You are speaking with a knowledgeable, sceptical peer. Be rigorous, concise, and blunt
where warranted. Use precise terminology, state your assumptions, and defend your claims
with argument. Welcome challenge, concede good objections, and distinguish carefully
between what is established, what is conjecture, and what is your own extrapolation.
```

- [ ] **Step 4: Update the persona tests to match the new overlay phrasing**

In `tests/test_personas.py`, update the substring assertions so they match the rewritten text:
- In `test_compose_system_prompt_combines_base_and_overlay`, replace `assert "a curious student" in prompt` with `assert "a student who is still learning" in prompt`, and update the ordering assertion's second substring to `"a student who is still learning"`.
- In any colleague assertion, replace `"a knowledgeable, sceptical peer"` — it is retained verbatim in the new `colleague.md`, so that assertion still holds (no change needed).

Concretely, the relevant test becomes:
```python
def test_compose_system_prompt_combines_base_and_overlay():
    prompt = compose_system_prompt("student")
    assert "You are Alan Turing" in prompt  # from base
    assert "a student who is still learning" in prompt  # from student overlay
    assert prompt.index("You are Alan Turing") < prompt.index("a student who is still learning")
```

- [ ] **Step 5: Run persona tests + full suite**

Run: `uv run pytest tests/test_personas.py -v && uv run pytest --cov`
Expected: persona tests pass; full suite passes at 100% coverage.

- [ ] **Step 6: Produce before/after samples for the user**

Generate one short exchange per persona (student, public, colleague) on the same prompt (e.g. "Can machines think?") using the old vs new base+overlay, and present them in the task report for the user to judge the tone shift. (No code; this is reviewer-facing evidence.)

- [ ] **Step 7: Lint, format, type-check, commit**

Run: `uv run ruff check . && uv run ruff format --check . && uv run ty check`
```bash
git add docs/superpowers/turing-voice-guide.md src/turing/personas tests/test_personas.py
git commit -m "feat: revise personas to Turing's register (less cheerful)"
```

---

## Self-Review

**Spec coverage:**
- Sourcing pipeline (resolver/metadata/browser/transcriber/corpus/pipeline/CLI) → Tasks 1–7. ✅
- PDF is JS-injected → Playwright `Browser` with PDF-response interception → Task 4. ✅
- Gemini transcription via `google-genai`, File API, `gemini-2.5-pro` default → Task 5. ✅
- `corpus/` gitignored except `sources.yaml`; nothing sourced committed; synthetic fixtures only → Tasks 1, 3. ✅
- Polite fetch (User-Agent, delay, cache) → Task 4 (delay/UA) + Task 7 (cache write). ✅
- `playwright` only in `browser.py`, `google-genai` only in `transcriber.py`, separate dep group, runtime lean → Tasks 1, 4, 5; enforced in CLAUDE.md (Task 8). ✅
- 100% coverage with adapters mocked; gated live test → Tasks 4, 5, 7. ✅
- Persona revision + voice guide fixing "too cheerful", tests updated → Task 9. ✅
- Docs for running the pipeline → Task 8. ✅

**Placeholder scan:** No TBD/TODO; every code step has complete code; the only `# pragma: no cover` is the conventional `__main__` entrypoint guard. ✅

**Type consistency:** `SourceEntry(ref,title,type,url)`, `ItemMetadata(ref,date,description,copyright,provenance,source_url)`, `FetchResult(html,pdf_url,pdf_bytes)`, `RunResult(ref,status,path,error)`, `Browser.fetch(url)->FetchResult`, `Transcriber.transcribe(pdf_bytes)->str`, `resolve_url(entry)`, `parse_metadata(html,source_url)`, `corpus.is_done(ref,dir)`, `corpus.write_item(entry,metadata,transcription,dir)`, `run(...)`, `main(argv,*,browser,transcriber)` are used identically across tasks. ✅
