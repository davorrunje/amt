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
